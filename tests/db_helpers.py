"""Start the real Postgres image with this repo's init scripts, for tests."""
import re
import subprocess
import time
import uuid

from helpers import ROOT, compose_image

IMAGE = compose_image("postgres")
DB_DIR = ROOT / "src" / "dsv-db"
# The same mounts, in the same name order, as dsv-db in docker-compose.yml.
INIT_FILES = {
    "init.sql": DB_DIR / "init.sql",
    "set-passwords.sh": DB_DIR / "set-passwords.sh",
}
MIGRATIONS = sorted((DB_DIR / "migrations").glob("*.sql"))
# Read from apply_migrations, so these tests run the real command line.
MIGRATE_PSQL = re.search(r"'(psql [^']*)'", (ROOT / "scripts" / "lib.sh").read_text())[1]


def docker(*args, check=True):
    return subprocess.run(
        ["docker", *args], capture_output=True, text=True, check=check, timeout=120
    )


def start_db(env):
    name = f"dsv-dbtest-{uuid.uuid4().hex[:8]}"
    args = [
        "run", "-d", "--name", name,
        "-e", "POSTGRES_USER=test_superuser",
        "-e", "POSTGRES_PASSWORD=superpw",
        "-e", "POSTGRES_DB=dinesafe",
    ]
    for target, src in INIT_FILES.items():
        # --mount fails on a missing source; -v would create a root-owned dir.
        args += ["--mount", f"type=bind,src={src},dst=/docker-entrypoint-initdb.d/{target},readonly"]
    for key, value in env.items():
        args += ["-e", f"{key}={value}"]
    docker(*args, IMAGE)
    return name


def wait_ready(name, timeout=90):
    """True once Postgres accepts TCP connections, False if it exits.

    During init the image's temporary server listens on the Unix socket
    only, so a TCP answer means every init script has finished.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        state = docker("inspect", "-f", "{{.State.Status}}", name).stdout.strip()
        if state != "running":
            return False
        ready = docker(
            "exec", name, "pg_isready", "-h", "127.0.0.1", "-U", "test_superuser",
            check=False,
        )
        if ready.returncode == 0:
            return True
        time.sleep(1)
    raise TimeoutError(f"{name} didn't become ready in {timeout}s")


def run_migration(name, sql):
    """Run sql through apply_migrations' own psql command line."""
    return subprocess.run(
        ["docker", "exec", "-i", name, "sh", "-c", MIGRATE_PSQL],
        input=sql, capture_output=True, text=True, timeout=60,
    )


def migrate(name):
    """Apply every migration as the superuser, the way apply_migrations in
    scripts/lib.sh does."""
    for migration in MIGRATIONS:
        result = run_migration(name, migration.read_text())
        if result.returncode != 0:
            return result
    return result


def container_ip(name):
    return docker(
        "inspect", "-f", "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}", name
    ).stdout.strip()


def psql(name, sql, user="test_superuser", password="superpw"):
    """Run SQL over TCP to the container's own address, which uses password auth."""
    return docker(
        "exec", "-e", f"PGPASSWORD={password}", name,
        "psql", "-v", "ON_ERROR_STOP=1", "-h", container_ip(name), "-U", user,
        "-d", "dinesafe", "-tAc", sql,
        check=False,
    )

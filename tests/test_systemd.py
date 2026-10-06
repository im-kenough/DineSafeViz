"""Static checks of the systemd units in deploy/systemd."""
import configparser
import re

from helpers import ROOT

UNITS = ROOT / "deploy" / "systemd"


def unit(name):
    parser = configparser.ConfigParser(strict=False, interpolation=None)
    parser.optionxform = str
    parser.read(UNITS / name)
    return parser


def test_data_service_runs_data_sh_with_load_as_admin():
    svc = unit("dsv-data.service")
    assert svc["Service"]["Type"] == "oneshot"
    assert svc["Service"]["User"] == "@ADMIN_USER@"
    assert svc["Service"]["ExecStart"] == "@REPO_DIR@/scripts/data.sh @ENV@ --load"
    assert "docker.service" in svc["Unit"]["Requires"]
    # A stalled run must end, or the timer can't start the next one.
    assert svc["Service"]["TimeoutStartSec"] == "30min"


def test_timer_runs_business_day_mornings_toronto_time():
    timer = unit("dsv-data.timer")
    assert timer["Timer"]["OnCalendar"] == "Mon..Fri *-*-* 07:30:00 America/Toronto"
    assert timer["Timer"]["Persistent"] == "true"
    assert timer["Install"]["WantedBy"] == "timers.target"


def test_imds_block_drops_metadata_and_wireserver_from_containers():
    svc = unit("dsv-imds-block.service")
    start = svc["Service"]["ExecStart"]
    assert "169.254.169.254" in start and "168.63.129.16" in start
    # Only the WireServer's agent ports: older Docker sends container DNS
    # to 168.63.129.16:53 from the container's namespace.
    assert "-p tcp" in start and "80,32526" in start
    assert "DOCKER-USER" in start
    assert svc["Unit"]["PartOf"] == "docker.service"
    assert svc["Install"]["WantedBy"] == "docker.service"


def test_shell_variables_are_escaped_from_systemd():
    # systemd expands $VAR in ExecStart itself; the shell needs $$VAR.
    for name in ("dsv-imds-block.service", "dsv-data.service"):
        for key in ("ExecStart", "ExecStop"):
            line = unit(name)["Service"].get(key, "")
            assert not re.search(r"\$", line.replace("$$", "")), (name, key)

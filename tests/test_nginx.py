"""nginx.conf and the VM snippet in the real nginx image.

The upstreams point at 127.0.0.1, where nothing listens, so a proxied
request returns 502. A 404 means nginx itself blocked the path.
"""
import time
import urllib.error
import urllib.request
import uuid

import pytest

from helpers import ROOT, compose_image, docker

IMAGE = compose_image("nginx")
# --mount fails on a missing source; -v would create a root-owned dir.
CONF = ["--mount", f"type=bind,src={ROOT}/src/dsv-nginx/nginx.conf,dst=/etc/nginx/nginx.conf,readonly"]
SNIPPETS = ["--mount", f"type=bind,src={ROOT}/src/dsv-nginx/snippets,dst=/etc/nginx/snippets,readonly"]
HOSTS = ["--add-host", "dsv-app:127.0.0.1", "--add-host", "dsv-analytics:127.0.0.1"]


def start_nginx(with_snippets):
    name = f"dsv-nginxtest-{uuid.uuid4().hex[:8]}"
    args = ["run", "-d", "--name", name, "-p", "127.0.0.1::80", *HOSTS, *CONF]
    if with_snippets:
        args += SNIPPETS
    docker(*args, IMAGE)
    port = docker("port", name, "80/tcp").stdout.splitlines()[0].rsplit(":", 1)[1]
    return name, f"http://127.0.0.1:{port}"


def get(url, headers=None):
    request = urllib.request.Request(url, headers=headers or {})
    for _ in range(20):
        try:
            with urllib.request.urlopen(request, timeout=3) as response:
                return response.status, response.headers
        except urllib.error.HTTPError as error:
            return error.code, error.headers
        except (urllib.error.URLError, ConnectionError):
            time.sleep(0.5)
    raise TimeoutError(url)


@pytest.fixture(scope="module")
def vm_nginx():
    name, url = start_nginx(with_snippets=True)
    yield name, url
    docker("rm", "-f", name, check=False)


@pytest.fixture(scope="module")
def local_nginx():
    name, url = start_nginx(with_snippets=False)
    yield name, url
    docker("rm", "-f", name, check=False)


@pytest.mark.parametrize("with_snippets", [False, True])
def test_config_is_valid(with_snippets):
    args = ["run", "--rm", *HOSTS, *CONF]
    if with_snippets:
        args += SNIPPETS
    result = docker(*args, IMAGE, "nginx", "-t", check=False)
    assert result.returncode == 0, result.stderr


def test_vm_hides_grafana_login(vm_nginx):
    _, url = vm_nginx
    assert get(url + "/analytics/login")[0] == 404


def test_vm_still_proxies_the_rest_of_analytics(vm_nginx):
    _, url = vm_nginx
    assert get(url + "/analytics/")[0] == 502


def test_local_keeps_grafana_login(local_nginx):
    _, url = local_nginx
    assert get(url + "/analytics/login")[0] == 502


def test_server_header_has_no_version(local_nginx):
    _, url = local_nginx
    _, headers = get(url + "/")
    assert headers["Server"] == "nginx"


def test_access_log_records_cloudflare_visitor_ip(local_nginx):
    name, url = local_nginx
    get(url + "/", headers={"CF-Connecting-IP": "203.0.113.7"})
    time.sleep(0.5)
    assert "cf=203.0.113.7" in docker("logs", name).stdout


# /search is rate-limited per visitor (#348). The fixtures are module-scoped,
# so each test uses its own CF-Connecting-IP to get a fresh bucket.
def burst(url, headers=None, count=30):
    return [get(url + "/search?q=que", headers=headers)[0] for _ in range(count)]


def test_search_burst_is_rate_limited(local_nginx):
    _, url = local_nginx
    statuses = burst(url, {"CF-Connecting-IP": "203.0.113.10"})
    assert statuses[0] == 502
    assert set(statuses) <= {502, 429}
    assert 429 in statuses


def test_search_limit_leaves_other_routes_alone(local_nginx):
    _, url = local_nginx
    headers = {"CF-Connecting-IP": "203.0.113.11"}
    assert 429 in burst(url, headers)
    assert get(url + "/", headers=headers)[0] == 502
    assert get(url + "/establishment/x", headers=headers)[0] == 502


def test_search_limit_is_per_client(local_nginx):
    _, url = local_nginx
    assert 429 in burst(url, {"CF-Connecting-IP": "203.0.113.12"})
    assert get(url + "/search?q=que", headers={"CF-Connecting-IP": "198.51.100.12"})[0] == 502


def test_search_limit_falls_back_to_remote_addr(local_nginx):
    _, url = local_nginx
    assert 429 in burst(url)


def test_search_gets_the_same_proxy_headers_as_root():
    conf = (ROOT / "src/dsv-nginx/nginx.conf").read_text()

    def block(start):
        body = conf[conf.index(start):]
        return body[: body.index("}")]

    def headers(text):
        return sorted(line.strip() for line in text.splitlines() if "proxy_set_header" in line)

    search, root = block("location = /search {"), block("location / {")
    assert "proxy_pass         http://app;" in search
    assert headers(search) == headers(root)
    assert len(headers(search)) == 4

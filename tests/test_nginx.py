"""nginx.conf and the VM snippet in the real nginx image.

The upstreams point at 127.0.0.1, where nothing listens, so a proxied
request returns 502. A 404 means nginx itself blocked the path.
"""
import re
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


def proxy_headers(text):
    return re.findall(r"^\s*proxy_set_header\s+(.+?);", text, re.M)


def location_block(conf, header):
    """Body of the location whose opening line is `header`, e.g. "location / {"."""
    return re.search(rf"^\s*{re.escape(header)}\n(.*?)^\s*}}", conf, re.M | re.S)[1]


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



# Server-level proxy_set_header is inherited only by locations that set none of
# their own. One added line would silently drop X-Real-IP (rate limit, logs).
PROXY_HEADERS = [
    "Host $http_host",
    "X-Real-IP $remote_addr",
    "X-Forwarded-For $proxy_add_x_forwarded_for",
    "X-Forwarded-Proto $scheme",
]


def test_server_sets_proxy_headers_before_any_location():
    conf = (ROOT / "src/dsv-nginx/nginx.conf").read_text()
    server = re.split(r"^\s*location ", conf.split("server {", 1)[1], maxsplit=1, flags=re.M)[0]
    assert [" ".join(h.split()) for h in proxy_headers(server)] == PROXY_HEADERS


@pytest.mark.parametrize("header", ["location = /search {", "location / {"])
def test_locations_inherit_proxy_headers(header):
    conf = (ROOT / "src/dsv-nginx/nginx.conf").read_text()
    assert proxy_headers(location_block(conf, header)) == []


def test_analytics_repeats_proxy_headers():
    conf = (ROOT / "src/dsv-nginx/nginx.conf").read_text()
    own = [" ".join(h.split()) for h in proxy_headers(location_block(conf, "location /analytics/ {"))]
    assert [h for h in own if not h.startswith(("Upgrade", "Connection"))] == PROXY_HEADERS


# Security headers (Mozilla Observatory). Set once in server {}; a location's
# own add_header would silently drop them all, so none may have one.
SECURITY_HEADERS = {
    "Strict-Transport-Security": "max-age=300; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "SAMEORIGIN",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
}


@pytest.mark.parametrize("path", ["/", "/search?q=que", "/analytics/"])
def test_security_headers_on_every_route(local_nginx, path):
    _, url = local_nginx
    _, headers = get(url + path, headers={"CF-Connecting-IP": "203.0.113.20"})
    for name, value in SECURITY_HEADERS.items():
        assert headers.get_all(name) == [value], name


def test_vm_login_404_keeps_security_headers(vm_nginx):
    _, url = vm_nginx
    _, headers = get(url + "/analytics/login")
    assert headers["X-Frame-Options"] == "SAMEORIGIN"


def test_app_pages_get_strict_csp(local_nginx):
    _, url = local_nginx
    _, headers = get(url + "/")
    directives = dict(d.strip().split(" ", 1) for d in headers["Content-Security-Policy"].split(";"))
    assert directives["script-src"] == "'self'"
    assert directives["frame-ancestors"] == "'self'"
    assert directives["object-src"] == "'none'"


def test_grafana_gets_no_csp(local_nginx):
    _, url = local_nginx
    _, headers = get(url + "/analytics/")
    assert headers["Content-Security-Policy"] is None


def test_no_location_sets_its_own_add_header():
    conf = (ROOT / "src/dsv-nginx/nginx.conf").read_text()
    for header in ["location /analytics/ {", "location = /search {", "location / {"]:
        assert "add_header" not in location_block(conf, header), header
    assert "add_header" not in (ROOT / "src/dsv-nginx/snippets/vm-public.conf").read_text()

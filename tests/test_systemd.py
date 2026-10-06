"""Static checks of the systemd units in deploy/systemd."""
import configparser

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


def test_timer_runs_business_day_mornings_toronto_time():
    timer = unit("dsv-data.timer")
    assert timer["Timer"]["OnCalendar"] == "Mon..Fri *-*-* 07:30:00 America/Toronto"
    assert timer["Timer"]["Persistent"] == "true"
    assert timer["Install"]["WantedBy"] == "timers.target"


def test_imds_block_drops_metadata_and_wireserver_from_containers():
    svc = unit("dsv-imds-block.service")
    start = svc["Service"]["ExecStart"]
    assert "169.254.169.254" in start and "168.63.129.16" in start
    assert "DOCKER-USER" in start
    assert svc["Unit"]["PartOf"] == "docker.service"
    assert svc["Install"]["WantedBy"] == "docker.service"

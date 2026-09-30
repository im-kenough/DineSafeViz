import re
from datetime import date
from unittest.mock import patch, MagicMock


def _mock_db(rows):
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    mock_cur.fetchall.return_value = rows
    return mock_conn


def _row_tuple(name="Pasta Palace", address="99 King St W", est_type="Restaurant",
               status="Pass", details="Improper storage", severity="M - Minor",
               category="Food storage"):
    """One row in the SELECT column order used by the /inspections route."""
    return (
        date(2024, 2, 14),
        status,
        "Notice to Comply",
        details,
        name,
        address,
        est_type,
        "Pass",
        "2024-02-20",
        "0.00",
        "10002",
        severity,
        category,
    )


def _render(client, rows):
    with patch("app.psycopg2.connect", return_value=_mock_db(rows)):
        resp = client.get("/inspections?year=2024&q=1")
    return resp.data.decode()


_HOME_STATS = {"total_inspections": 12345, "years_of_data": 25}


def test_home_has_dashboard_link(client):
    with patch("app._get_home_stats", return_value=_HOME_STATS):
        resp = client.get("/")
    assert b'href="/dashboard"' in resp.data
    assert b"Dashboard" in resp.data
    assert b'href="/info"' in resp.data
    assert b"Info" in resp.data


def test_info_page(client):
    resp = client.get("/info")
    assert resp.status_code == 200
    assert b"DineSafeViz Info" in resp.data
    assert b"Data Dictionary" in resp.data
    assert b"<table>" in resp.data
    assert b"Establishment ID" in resp.data


def test_route_returns_200(client):
    with patch("app._get_home_stats", return_value=_HOME_STATS):
        resp = client.get("/")
    assert resp.status_code == 200


def test_route_renders_day_boxes(client):
    with patch("app.psycopg2.connect", return_value=_mock_db([])):
        resp = client.get("/inspections")
    assert b"day-box" in resp.data


def test_route_shows_inspection_data(client):
    html = _render(client, [_row_tuple(name="Risky Bistro", status="Conditional Pass",
                                       details="Rats observed", severity="C - Crucial",
                                       category="Pest control")])
    assert "Risky Bistro" in html
    assert "CONDITIONAL PASS" in html
    assert "Rats observed" in html
    assert "Pest control" in html
    assert "C - Crucial" in html


def test_route_invalid_params_returns_200(client):
    with patch("app.psycopg2.connect", return_value=_mock_db([])):
        resp = client.get("/inspections?year=1900&q=99")
    assert resp.status_code == 200


def test_route_no_data_day_shows_no_data_text(client):
    with patch("app.psycopg2.connect", return_value=_mock_db([])):
        resp = client.get("/inspections")
    assert b"No data" in resp.data


def test_status_class_on_row(client):
    assert 'class="est-card status-conditional"' in _render(client, [_row_tuple(status="Conditional Pass")])


def test_footer_content(client):
    with patch("app._get_home_stats", return_value=_HOME_STATS):
        resp = client.get("/")
    assert b"&copy; 2026 Kenneth Ho" in resp.data
    assert b"DineSafeViz v0.1.0" in resp.data


def test_dropdown_menu_present(client):
    with patch("app._get_home_stats", return_value=_HOME_STATS):
        resp = client.get("/")
    assert b'class="dropdown"' in resp.data
    assert b'class="dropdown-menu"' in resp.data


def test_dropdown_has_year_and_quarter_links(client):
    with patch("app._get_home_stats", return_value=_HOME_STATS):
        resp = client.get("/")
    assert b'href="/inspections?year=2023&q=4"' in resp.data
    assert b'href="/inspections?year=2023&q=1"' in resp.data
    assert b'href="/inspections?year=2024&q=1"' in resp.data
    assert b'href="/inspections?year=2024&q=4"' in resp.data


def test_standalone_year_tabs_removed(client):
    with patch("app._get_home_stats", return_value=_HOME_STATS):
        resp = client.get("/")
    assert b'href="/inspections?year=2024"' not in resp.data
    assert b'href="/inspections?year=2023"' not in resp.data


def test_dropdown_present_on_dashboard(client):
    resp = client.get("/dashboard")
    assert b'class="dropdown"' in resp.data
    assert b'class="dropdown-menu"' in resp.data


def test_dropdown_has_links_on_dashboard(client):
    resp = client.get("/dashboard")
    assert b'href="/inspections?year=2023&q=4"' in resp.data
    assert b'href="/inspections?year=2024&q=1"' in resp.data


def test_dropdown_present_on_info(client):
    resp = client.get("/info")
    assert b'class="dropdown"' in resp.data
    assert b'class="dropdown-menu"' in resp.data


def test_dropdown_has_links_on_info(client):
    resp = client.get("/info")
    assert b'href="/inspections?year=2023&q=4"' in resp.data
    assert b'href="/inspections?year=2024&q=1"' in resp.data


def test_dashboard_nav_active_class(client):
    resp = client.get("/dashboard")
    assert b'href="/dashboard" class="nav-btn active"' in resp.data


def test_info_nav_active_class(client):
    resp = client.get("/info")
    assert b'href="/info" class="nav-btn active"' in resp.data


def test_index_nav_active_class(client):
    with patch("app.psycopg2.connect", return_value=_mock_db([])):
        resp = client.get("/inspections")
    assert b'class="nav-btn active">Inspections' in resp.data


def test_dropdown_has_archive_item(client):
    with patch("app._get_home_stats", return_value=_HOME_STATS):
        resp = client.get("/")
    assert b'archive-item' in resp.data
    assert b'Archive' in resp.data


def test_archive_contains_old_year_links(client):
    with patch("app._get_home_stats", return_value=_HOME_STATS):
        resp = client.get("/")
    assert b'href="/inspections?year=2022&q=1"' in resp.data


def test_recent_years_not_in_archive(client):
    with patch("app._get_home_stats", return_value=_HOME_STATS):
        resp = client.get("/")
    assert b'href="/inspections?year=2023&q=4"' in resp.data


def test_location_left_of_results(client):
    html = _render(client, [_row_tuple()])
    assert html.index('class="est-location"') < html.index('class="est-results"')


def test_establishment_type_rendered(client):
    assert "UNIQUE_EST_TYPE_XYZ" in _render(client, [_row_tuple(est_type="UNIQUE_EST_TYPE_XYZ")])


def test_location_contains_name_and_address(client):
    html = _render(client, [_row_tuple()])
    location = html[html.index('class="est-location"'):html.index('class="est-results"')]
    assert "Pasta Palace" in location
    assert "99 King St W" in location


def test_multiple_infractions_share_one_card(client):
    assert _render(client, [_row_tuple(), _row_tuple()]).count('class="est-card') == 1


def _results_html(client, rows):
    html = _render(client, rows)
    return html[html.index('class="est-results"'):]


def test_results_have_column_headers(client):
    headers = re.findall(r'<th[^>]*>([^<]+)</th>', _results_html(client, [_row_tuple()]))
    assert headers == ["Severity", "Category of Infraction"]


def test_severity_and_category_share_a_row(client):
    results = _results_html(client, [_row_tuple()])
    cells = re.findall(r'<tr class="inf-summary">\s*<td>([^<]+)</td>\s*<td>([^<]+)</td>', results)
    assert cells == [("M - Minor", "Food storage")]


def test_details_in_category_column_beneath_category(client):
    results = _results_html(client, [_row_tuple()])
    details = re.findall(r'<tr class="inf-details">\s*<td></td>\s*<td>\s*([^<]+?)\s*<', results)
    assert details == ["Improper storage"]
    assert results.index("Food storage") < results.index("Improper storage")


def test_details_has_no_label(client):
    assert "Details" not in _results_html(client, [_row_tuple()])


def test_inspection_status_uppercase_and_formatted_like_name(client):
    results = _results_html(client, [_row_tuple()])
    assert '<span class="label">Inspection Status</span> <strong>PASS</strong>' in results


def test_infraction_counts_under_address(client):
    html = _render(client, [
        _row_tuple(severity="C - Crucial"),
        _row_tuple(severity="M - Minor", details="Dirty floor"),
        _row_tuple(severity="M - Minor", details="No thermometer"),
        _row_tuple(severity="NA", details="Other"),
    ])
    location = html[html.index('class="est-location"'):html.index('class="est-results"')]
    assert '<span class="label">Infractions</span> <strong>4</strong>' in location
    assert location.index("99 King St W") < location.index('<span class="label">Infractions</span> <strong>4</strong>')
    counts = re.findall(r'<th>([^<]+)</th>\s*<td>(\d+)</td>', location)
    assert counts == [("Crucial", "1"), ("Significant", "0"), ("Minor", "2"), ("NA", "1")]


def test_no_infraction_counts_without_infractions(client):
    assert '<span class="label">Infractions</span>' not in _render(client, [_row_tuple(details=None, severity=None)])


def test_address_rendered_as_lines(client):
    html = _render(client, [_row_tuple(address="102 BERKELEY ST None M5A 2W7")])
    assert "<span>102 BERKELEY ST</span>" in html
    assert "<span>Toronto, ON</span>" in html
    assert "<span>M5A 2W7</span>" in html
    assert "None" not in html


def test_heading_shows_quarter_and_date_range(client):
    html = _render(client, [])
    assert ('<h2 class="page-heading">DineSafe Inspections | Q1 2024'
            '<span class="heading-sep"> | </span>'
            '<span class="heading-dates">January 1, 2024 - March 31, 2024</span></h2>') in html


def test_heading_end_date_is_today_for_current_quarter(client):
    today = date.today()
    q = (today.month - 1) // 3 + 1
    start = date(today.year, 3 * q - 2, 1)
    with patch("app.psycopg2.connect", return_value=_mock_db([])):
        html = client.get(f"/inspections?year={today.year}&q={q}").data.decode()
    expected = (f'DineSafe Inspections | Q{q} {today.year}<span class="heading-sep"> | </span>'
                f'<span class="heading-dates">{start.strftime("%B %-d, %Y")} - {today.strftime("%B %-d, %Y")}</span>')
    assert f'<h2 class="page-heading">{expected}</h2>' in html
    assert f"<h2>{today.strftime('%A, %B %-d, %Y')}</h2>" in html

import re
from datetime import date
from unittest.mock import patch, MagicMock


def _mock_db(rows):
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    mock_cur.fetchall.return_value = rows
    return mock_conn


def _row(name="Pasta Palace", address="99 King St W", est_type="Restaurant",
               status="Pass", details="Improper storage", severity="M - Minor",
               category="Food storage", street="99 King St W", unit=None, postal=None):
    """One row as returned by the /inspections route's RealDictCursor query."""
    return {
        "inspection_date": date(2024, 2, 14),
        "establishment_status": status,
        "action": "Notice to Comply",
        "infraction_details": details,
        "establishment_name": name,
        "establishment_address": address,
        "establishment_type": est_type,
        "street": street,
        "unit": unit,
        "postal_code": postal,
        "outcome": "Pass",
        "outcome_date": "2024-02-20",
        "amount_fined": "0.00",
        "establishment_id": "10002",
        "severity": severity,
        "infraction_category": category,
    }


def _render(client, rows):
    """Render the February 2024 month fragment, which holds _row()'s date."""
    with patch("app.psycopg2.connect", return_value=_mock_db(rows)):
        resp = client.get("/inspections/month?year=2024&m=2")
    return resp.data.decode()


def _render_page(client, db=None, url="/inspections?year=2024&q=1"):
    """Render an /inspections page, Q1 2024 by default."""
    with patch("app.psycopg2.connect", return_value=db or _mock_db([])):
        return client.get(url).data.decode()


_HOME_STATS = {
    "total_inspections": 12345, "years_of_data": 25,
    "min_date": date(2001, 1, 1), "max_date": date.today(),
}


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
    html = _render(client, [_row(name="Risky Bistro", status="Conditional Pass",
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
    assert 'class="est-card status-conditional"' in _render(client, [_row(status="Conditional Pass")])


def test_footer_content(client):
    with patch("app._get_home_stats", return_value=_HOME_STATS):
        resp = client.get("/")
    assert b"&copy; 2026 Kenneth Ho" in resp.data
    assert b"DineSafeViz v0.1.0" in resp.data


def _picker(html):
    """The Inspections period picker markup from the nav."""
    return html[html.index('<details class="dropdown"'):html.index('<a href="/dashboard"')]


def _older_years(html):
    """The collapsed "Older years" section of the period picker."""
    picker = _picker(html)
    return picker[picker.index('class="picker-archive"'):]


def test_dropdown_menu_present(client):
    with patch("app._get_home_stats", return_value=_HOME_STATS):
        resp = client.get("/")
    assert b'<details class="dropdown"' in resp.data
    assert b'class="dropdown-menu"' in resp.data


def test_picker_rows_have_four_quarter_columns(client):
    html = _picker(client.get("/info").data.decode())
    assert re.findall(r'<th scope="col">(Q\d)</th>', html) == ["Q1", "Q2", "Q3", "Q4"]
    row_2024 = re.search(r'<th scope="row">2024</th>(.*?)</tr>', html, re.S).group(1)
    assert re.findall(r'href="/inspections\?year=2024&q=(\d)"', row_2024) == ["1", "2", "3", "4"]


def test_picker_quarters_without_data_are_empty_cells(client):
    import app as app_module
    app_module._stats_cache["data"].update(min_date=date(2010, 6, 1), max_date=date(2025, 2, 1))
    html = _picker(client.get("/info").data.decode())
    row_2025 = re.search(r'<th scope="row">2025</th>(.*?)</tr>', html, re.S).group(1)
    assert row_2025.count('class="picker-cell is-empty"') == 3
    row_2010 = re.search(r'<th scope="row">2010</th>(.*?)</tr>', html, re.S).group(1)
    assert row_2010.count('class="picker-cell is-empty"') == 1


def test_picker_older_years_collapsed_with_range_label(client):
    html = client.get("/info").data.decode()
    older = _older_years(html)
    assert older.startswith('class="picker-archive">')
    this_year = date.today().year
    assert f"Older years (2001–{this_year - 4})" in older
    assert 'href="/inspections?year=2001&q=1"' in older
    assert f'href="/inspections?year={this_year - 3}&q=1"' not in older


def test_picker_older_years_open_when_viewing_archived_quarter(client):
    html = _render_page(client, url="/inspections?year=2005&q=3")
    assert 'class="picker-archive" open>' in html
    assert 'href="/inspections?year=2005&q=3" class="nav-btn picker-cell active" aria-current="page"' in html


def test_picker_highlights_quarter_only_on_inspections_page(client):
    assert "picker-cell active" not in _picker(client.get("/info").data.decode())
    html = _render_page(client)
    assert 'href="/inspections?year=2024&q=1" class="nav-btn picker-cell active" aria-current="page"' in html


def _timeline(html):
    """The sticky month/quarter timeline bar on the inspections page."""
    start = html.index('<nav class="timeline"')
    return html[start:html.index('</nav>', start)]


def test_timeline_quarter_links_flank_months(client):
    bar = _timeline(_render_page(client))
    assert ('<a class="nav-btn quarter-link" href="/inspections?year=2023&q=4" rel="prev">'
            '‹ Q4<span class="long"> 2023</span></a>') in bar
    assert ('<a class="nav-btn quarter-link" href="/inspections?year=2024&q=2" rel="next">'
            'Q2<span class="long"> 2024</span> ›</a>') in bar
    assert bar.index('rel="prev"') < bar.index('class="nav-btn month-link"')
    assert bar.rindex('class="nav-btn month-link"') < bar.index('rel="next"')


def test_timeline_omits_prev_at_first_quarter(client):
    bar = _timeline(_render_page(client, url="/inspections?year=2001&q=1"))
    assert 'rel="prev"' not in bar
    assert 'href="/inspections?year=2001&q=2" rel="next"' in bar


def test_timeline_omits_next_at_latest_quarter(client):
    bar = _timeline(_render_page(client, url="/inspections"))
    assert 'rel="prev"' in bar
    assert 'rel="next"' not in bar


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
    assert b'<details class="dropdown"' in resp.data
    assert b'class="dropdown-menu"' in resp.data


def test_dropdown_has_links_on_dashboard(client):
    resp = client.get("/dashboard")
    assert b'href="/inspections?year=2023&q=4"' in resp.data
    assert b'href="/inspections?year=2024&q=1"' in resp.data


def test_dropdown_present_on_info(client):
    resp = client.get("/info")
    assert b'<details class="dropdown"' in resp.data
    assert b'class="dropdown-menu"' in resp.data


def test_dropdown_has_links_on_info(client):
    resp = client.get("/info")
    assert b'href="/inspections?year=2023&q=4"' in resp.data
    assert b'href="/inspections?year=2024&q=1"' in resp.data


def test_nav_matches_db_range(client):
    import app as app_module
    app_module._stats_cache["data"].update(min_date=date(2010, 6, 1), max_date=date(2025, 2, 1))
    html = client.get("/info").data.decode()
    assert 'href="/inspections?year=2010&q=2"' in html
    assert 'href="/inspections?year=2010&q=1"' not in html
    assert 'href="/inspections?year=2025&q=1"' in html
    assert 'href="/inspections?year=2025&q=2"' not in html
    assert 'href="/inspections?year=2009' not in html
    assert 'href="/inspections?year=2026' not in html


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


def test_location_left_of_results(client):
    html = _render(client, [_row()])
    assert html.index('class="est-location"') < html.index('class="est-results"')


def test_establishment_type_rendered(client):
    assert "UNIQUE_EST_TYPE_XYZ" in _render(client, [_row(est_type="UNIQUE_EST_TYPE_XYZ")])


def test_location_contains_name_and_address(client):
    html = _render(client, [_row()])
    location = html[html.index('class="est-location"'):html.index('class="est-results"')]
    assert "Pasta Palace" in location
    assert "99 King St W" in location


def test_multiple_infractions_share_one_card(client):
    assert _render(client, [_row(), _row()]).count('class="est-card') == 1


def _results_html(client, rows):
    html = _render(client, rows)
    return html[html.index('class="est-results"'):]


def test_results_have_column_headers(client):
    headers = re.findall(r'<th[^>]*>([^<]+)</th>', _results_html(client, [_row()]))
    assert headers == ["Severity", "Category of Infraction"]


def test_severity_and_category_share_a_row(client):
    results = _results_html(client, [_row()])
    cells = re.findall(r'<tr class="inf-summary">\s*<td>([^<]+)</td>\s*<td>([^<]+)</td>', results)
    assert cells == [("M - Minor", "Food storage")]


def test_details_in_category_column_beneath_category(client):
    results = _results_html(client, [_row()])
    details = re.findall(r'<tr class="inf-details">\s*<td></td>\s*<td>\s*<ul>\s*<li>\s*([^<]+?)\s*<', results)
    assert details == ["Improper storage"]
    assert results.index("Food storage") < results.index("Improper storage")


def test_same_severity_and_category_share_one_summary_row(client):
    results = _results_html(client, [
        _row(details="Dirty floor"),
        _row(details="No thermometer"),
        _row(severity="C - Crucial", details="Hot food too cold"),
    ])
    summaries = re.findall(r'<tr class="inf-summary">\s*<td>([^<]+)</td>\s*<td>([^<]+)</td>', results)
    assert summaries == [("C - Crucial", "Food storage"), ("M - Minor", "Food storage")]
    items = re.findall(r'<li>\s*([^<]+?)\s*<', results)
    assert items == ["Hot food too cold", "Dirty floor", "No thermometer"]


def test_details_has_no_label(client):
    assert "Details" not in _results_html(client, [_row()])


def test_inspection_status_uppercase_and_formatted_like_name(client):
    results = _results_html(client, [_row()])
    assert '<span class="label">Inspection Status</span> <strong>PASS</strong>' in results


def test_infraction_counts_under_address(client):
    html = _render(client, [
        _row(severity="C - Crucial"),
        _row(severity="M - Minor", details="Dirty floor"),
        _row(severity="M - Minor", details="No thermometer"),
        _row(severity="NA", details="Other"),
    ])
    location = html[html.index('class="est-location"'):html.index('class="est-results"')]
    assert '<span class="label">Infractions</span> <strong>4</strong>' in location
    assert location.index("99 King St W") < location.index('<span class="label">Infractions</span> <strong>4</strong>')
    counts = re.findall(r'<th>([^<]+)</th>\s*<td>(\d+)</td>', location)
    assert counts == [("Crucial", "1"), ("Significant", "0"), ("Minor", "2"), ("NA", "1")]


def test_no_infraction_counts_without_infractions(client):
    assert '<span class="label">Infractions</span>' not in _render(client, [_row(details=None, severity=None)])


def test_address_rendered_as_lines(client):
    html = _render(client, [_row(street="102 BERKELEY ST", postal="M5A 2W7")])
    assert "<span>102 BERKELEY ST</span><span>Toronto, ON</span><span>M5A 2W7</span>" in html


def test_address_unit_on_street_line(client):
    html = _render(client, [_row(street="65 Front St W", unit="Unit-442")])
    assert "<span>65 Front St W Unit-442</span><span>Toronto, ON</span>" in html


def test_address_without_street_shows_dash(client):
    html = _render(client, [_row(street=None)])
    location = html[html.index('class="est-location"'):html.index('class="est-results"')]
    assert "<span>—</span>" in location
    assert "Toronto, ON" not in location


def test_heading_shows_quarter_and_date_range(client):
    html = _render_page(client)
    assert ('<h2 class="page-heading">DineSafe Inspections | Q1 2024'
            '<span class="heading-dates">January 1, 2024 - March 31, 2024</span></h2>') in html


def test_heading_end_date_is_today_for_current_quarter(client):
    today = date.today()
    q = (today.month - 1) // 3 + 1
    start = date(today.year, 3 * q - 2, 1)
    with patch("app.psycopg2.connect", return_value=_mock_db([])):
        html = client.get(f"/inspections?year={today.year}&q={q}").data.decode()
    expected = (f'DineSafe Inspections | Q{q} {today.year}'
                f'<span class="heading-dates">{start.strftime("%B %-d, %Y")} - {today.strftime("%B %-d, %Y")}</span>')
    assert f'<h2 class="page-heading">{expected}</h2>' in html
    assert f"<h2>{today.strftime('%A, %B %-d, %Y')}</h2>" in html


def test_inspections_latest_month_open_and_inlined(client):
    db = _mock_db([])
    html = _render_page(client, db)
    assert re.search(r'<details class="month-box" id="month-2024-03" open>', html)
    assert "Sunday, March 31, 2024" in html
    # Only the latest month is queried; older months are fetched on expand.
    assert db.cursor.return_value.execute.call_args[0][1] == (date(2024, 3, 1), date(2024, 3, 31))


def test_inspections_older_months_collapsed_and_lazy(client):
    html = _render_page(client)
    for m in ("01", "02"):
        assert (f'<details class="month-box" id="month-2024-{m}" '
                f'data-src="/inspections/month?year=2024&amp;m={int(m)}">') in html
    assert "February 29, 2024" not in html
    assert "January 1, 2024" not in html.split("</h2>", 1)[1]


def test_timeline_months_oldest_first_with_short_names(client):
    bar = _timeline(_render_page(client))
    links = re.findall(r'<a class="nav-btn month-link" href="#month-(\d{4}-\d{2})">'
                       r'<span class="long">(\w+)</span><span class="short">(\w+)</span></a>', bar)
    assert links == [("2024-01", "January", "Jan"), ("2024-02", "February", "Feb"),
                     ("2024-03", "March", "Mar")]


def test_timeline_has_single_expand_collapse_toggle(client):
    html = _render_page(client)
    bar = _timeline(html)
    assert '<button type="button" class="toggle-all" id="toggle-all" aria-label="Expand all">' in bar
    assert 'id="expand-all"' not in html
    assert 'id="collapse-all"' not in html
    assert 'class="contents"' not in html


def test_month_fragment_renders_only_that_month(client):
    db = _mock_db([_row(name="Risky Bistro")])
    with patch("app.psycopg2.connect", return_value=db):
        resp = client.get("/inspections/month?year=2024&m=2")
    html = resp.data.decode()
    assert resp.status_code == 200
    assert "Thursday, February 29, 2024" in html
    assert "Thursday, February 1, 2024" in html
    assert "March" not in html and "January" not in html
    assert "Risky Bistro" in html
    assert "<html" not in html
    assert db.cursor.return_value.execute.call_args[0][1] == (date(2024, 2, 1), date(2024, 2, 29))


def test_month_fragment_bad_params_404(client):
    next_year = date.today().year + 1
    for qs in ("", "year=2024", "year=2024&m=13", "year=2024&m=0", "year=abc&m=2",
               "year=2000&m=12", f"year={next_year}&m=1"):
        with patch("app.psycopg2.connect", return_value=_mock_db([])):
            resp = client.get(f"/inspections/month?{qs}")
        assert resp.status_code == 404, qs

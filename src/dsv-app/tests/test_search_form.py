from unittest.mock import patch

from db_fakes import search_conn


def test_nav_has_search_form(client):
    html = client.get("/info").data.decode()
    assert '<form class="search-form nav-search" role="search" action="/search" method="get">' in html
    assert '<label class="visually-hidden" for="nav-q">Search restaurants by name or address</label>' in html
    assert 'id="nav-q" name="q" value=""' in html
    assert 'placeholder="Enter restaurant name"' in html
    assert 'minlength="3" maxlength="100" required' in html


def test_home_has_hero_form_instead_of_nav_form(client):
    html = client.get("/").data.decode()
    assert 'class="search-form hero-search"' in html
    assert 'id="hero-q"' in html
    assert 'id="nav-q"' not in html


def test_404_page_has_nav_form(client):
    html = client.get("/no-such-page").data.decode()
    assert 'id="nav-q"' in html


def test_search_page_prefills_nav_input(client):
    with patch("app.psycopg2.connect", return_value=search_conn([])):
        html = client.get("/search?q=pizza+queen").data.decode()
    assert 'id="nav-q" name="q" value="pizza queen"' in html


def test_nav_input_value_is_escaped(client):
    with patch("app.psycopg2.connect", return_value=search_conn([])):
        html = client.get("/search", query_string={"q": '"><b>pizza'}).data.decode()
    assert '"><b>pizza' not in html
    assert 'value="&#34;&gt;&lt;b&gt;pizza"' in html

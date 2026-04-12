from __future__ import annotations

from ai_events.html_content import extract_main_text_html, merge_description_with_main_content


def test_merge_prefers_longer_when_existing_is_subset() -> None:
    main = "Alpha beta gamma delta London executives."
    assert merge_description_with_main_content("Alpha beta", main) == main


def test_merge_keeps_existing_when_body_is_subset() -> None:
    long = "Full prose about the summit in London for VPs and founders."
    assert merge_description_with_main_content(long, "London") == long


def test_merge_concat_when_distinct() -> None:
    m = merge_description_with_main_content("Short meta.", "Body line one.\nBody line two.")
    assert "Short meta." in m
    assert "---" in m
    assert "Body line one." in m


def test_extract_prefers_main_element() -> None:
    html = """
 <html><body>
    <header>Skip me</header>
    <main><p>London enterprise AI summit for executives.</p></main>
    <footer>Also skip</footer>
    </body></html>
    """
    t = extract_main_text_html(html)
    assert "London enterprise AI summit" in t
    assert "Skip me" not in t


def test_extract_article_when_no_main() -> None:
    html = """
    <html><body><nav>Nav</nav>
    <article><h1>GenAI</h1><p>Corporate roundtable in Westminster.</p></article>
    </body></html>
    """
    t = extract_main_text_html(html)
    assert "Corporate roundtable" in t
    assert "Nav" not in t


def test_extract_body_fallback_strips_chrome() -> None:
    html = """
    <html><body>
    <header>Logo</header>
    <div class="content"><p>Canary Wharf B2B AI leadership day.</p></div>
    <footer>Copyright</footer>
    </body></html>
    """
    t = extract_main_text_html(html)
    assert "Canary Wharf" in t
    assert "Logo" not in t
    assert "Copyright" not in t


def test_extract_max_chars() -> None:
    html = "<html><body><main>" + ("word " * 5000) + "</main></body></html>"
    t = extract_main_text_html(html, max_chars=100)
    assert len(t) == 100
    assert t.endswith("…")


def test_extract_strips_scripts() -> None:
    html = """<html><body><main>
    <script>alert('x')</script>
    <p>Visible only.</p>
    </main></body></html>"""
    t = extract_main_text_html(html)
    assert "Visible only" in t
    assert "alert" not in t

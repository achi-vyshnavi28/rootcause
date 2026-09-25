"""End-to-end UI tests in a real browser (Playwright). Screenshots are saved as evidence.

    pytest tests_ui            # needs the database (or demo mode) and GEMINI_API_KEY for the question test

Not in the default test run: they start the Streamlit app and, for one test, call the LLM.
"""

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs" / "quality" / "ui_evidence"
PORT = 8766


@pytest.fixture(scope="module")
def app_url():
    proc = subprocess.Popen([sys.executable, "-m", "streamlit", "run", "frontend/app.py", "--server.port", str(PORT),
                             "--server.headless", "true"], cwd=ROOT, env=os.environ.copy(),
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(90):
        try:
            socket.create_connection(("localhost", PORT), timeout=1).close()
            break
        except OSError:
            time.sleep(1)
    yield f"http://localhost:{PORT}"
    proc.terminate()


def shot(page: Page, name: str) -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=EVIDENCE / f"{name}.png", full_page=True)


def open_app(page: Page, url: str) -> None:
    page.set_viewport_size({"width": 1400, "height": 900})
    page.goto(url)
    expect(page.get_by_role("heading", name="RootCause")).to_be_visible(timeout=60_000)


def test_empty_question_shows_a_clear_warning(page: Page, app_url):
    open_app(page, app_url)
    page.get_by_role("button", name="Investigate").click()
    expect(page.get_by_text("Please type a question first")).to_be_visible()
    shot(page, "01_empty_question_warning")


def test_known_answer_question_is_answered_with_evidence(page: Page, app_url):
    """TC04 in the test library: the true count is 625, and the answer must cite the query behind it."""
    open_app(page, app_url)
    page.get_by_test_id("stSidebar").get_by_role("combobox").click()
    page.get_by_role("option", name="Olist e-commerce (original)").click()
    page.get_by_label("Your question").fill("How many orders were canceled?")
    page.get_by_role("button", name="Investigate").click()
    expect(page.get_by_text("625").first).to_be_visible(timeout=300_000)
    expect(page.get_by_text("Numbers not found in the evidence")).to_have_count(0)
    trail = page.get_by_text("Audit trail:")
    expect(trail).to_be_visible()
    trail.click()
    sql = page.locator("code").filter(has_text="LIMIT").first     # the validated SQL, as executed
    expect(sql).to_be_visible()
    expect(sql).to_contain_text("canceled")
    page.wait_for_timeout(1000)                                   # let the expander finish opening
    for label in ("Helpful", "Not helpful"):                      # BUG-001 regression: labels must not be cut off
        button = page.get_by_role("button", name=label, exact=False).last
        cut = button.evaluate("b => [b, ...b.querySelectorAll('*')].some(e => e.scrollWidth > e.clientWidth + 1)")
        assert not cut, f"'{label}' button text is truncated"
    shot(page, "02_answer_with_audit_trail")


def test_history_tab_verifies_the_audit_trail(page: Page, app_url):
    """21 CFR Part 11 §11.10(e): the stored answers are checked against the hash-chained audit log on every visit."""
    open_app(page, app_url)
    page.get_by_role("tab", name="History").click()
    expect(page.get_by_text("Audit trail intact")).to_be_visible(timeout=30_000)
    shot(page, "03_history_audit_trail_intact")


def test_evals_tab_shows_the_benchmark(page: Page, app_url):
    open_app(page, app_url)
    page.get_by_role("tab", name="Evals").click()
    expect(page.get_by_text("gemini/gemini-3.6-flash").first).to_be_visible(timeout=30_000)
    shot(page, "04_evals_benchmark")

#!/usr/bin/env python3
"""
Scrape hospitals from a Google Maps saved/community list URL using Playwright.

Target URL: https://www.google.com/maps/@40.8267709,-74.3719346,11z/data=!4m3!11m2!2sas1zuEdkTwyX5nGWg9Zlqg!3e3!5m1!1e1
Area: Northern NJ (~40.83, -74.37), zoom 11
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "hospitals"
OUTPUT_CSV = DATA_DIR / "hospitals_raw.csv"
PROGRESS_FILE = DATA_DIR / "scraping_progress.json"

GMAPS_URL = (
    "https://www.google.com/maps/@40.8267709,-74.3719346,11z"
    "/data=!4m3!11m2!2sas1zuEdkTwyX5nGWg9Zlqg!3e3!5m1!1e1"
)

# How long to wait (seconds) for the feed to load / per scroll cycle
LOAD_TIMEOUT_MS = 15_000
SCROLL_PAUSE_S = 2
MAX_SCROLL_ATTEMPTS = 40  # safety cap (~800 items)


def load_progress() -> dict:
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    return {"completed": False, "total_found": 0, "started_at": None}


def save_progress(progress: dict):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f, indent=2)


def find_list_container(page) -> str | None:
    """Return the CSS selector for the scrollable list container, or None."""
    candidates = [
        'div[role="feed"]',
        'div.m6QErb.DxyBCb',
        'div.m6QErb',
        'div[jsaction*="scroll"]',
    ]
    for sel in candidates:
        count = page.locator(sel).count()
        if count > 0:
            print(f"  Found list container: {sel} ({count} match(es))")
            return sel
    return None


def scroll_feed_to_end(page, container_sel: str) -> None:
    """Scroll the left-panel feed until no new items load."""
    print("  Scrolling through list to load all items...")
    prev_count = 0
    no_change_streak = 0

    for attempt in range(MAX_SCROLL_ATTEMPTS):
        # Use fontHeadlineSmall count as the loaded-items proxy
        current_count = page.locator('div.fontHeadlineSmall').count()

        if current_count == prev_count:
            no_change_streak += 1
            if no_change_streak >= 3:
                print(f"  No new items after 3 checks. Final count: {current_count}")
                break
        else:
            no_change_streak = 0
            print(f"  Scroll {attempt + 1}: {current_count} items loaded")

        prev_count = current_count

        # Scroll the container (div.m6QErb.DxyBCb) to its bottom
        page.evaluate("""
            const c = document.querySelector('div.m6QErb.DxyBCb');
            if (c) c.scrollTop = c.scrollHeight;
        """)
        time.sleep(SCROLL_PAUSE_S)

        # Click "Show more results" if present
        show_more = page.locator('button:has-text("Show more results")').first
        if show_more.is_visible():
            show_more.click()
            time.sleep(SCROLL_PAUSE_S)


def extract_items(page) -> list[dict]:
    """
    Extract hospital records via JavaScript evaluation.
    Each card is: div.BsJqK > div.ZSOIif > button.SMP2wb > div.H1bDYe
    with div.fontHeadlineSmall for name and sibling divs for rating/type.
    """
    print("  Extracting hospital data via JS evaluation...")

    records = page.evaluate("""() => {
        const re_rating = /^(\\d+\\.?\\d*)/;
        const re_reviews = /\\((\\d[\\d,]*)\\)/;
        const results = [];

        // Each name element is a direct proxy for one card
        const nameEls = document.querySelectorAll('div.fontHeadlineSmall');
        nameEls.forEach(nameEl => {
            const name = nameEl.innerText.trim();
            if (!name) return;

            // The card button (2 levels up from nameEl) contains full card text
            let btn = nameEl.parentElement && nameEl.parentElement.parentElement;
            const cardText = btn ? btn.innerText : '';
            const lines = cardText.split('\\n').map(s => s.trim()).filter(Boolean);

            // lines[0] = name, lines[1] might be rating, others = type/status
            let rating = '';
            let reviews = '';
            let place_type = '';

            lines.forEach(line => {
                if (!rating) {
                    const rm = line.match(re_rating);
                    if (rm && parseFloat(rm[1]) <= 5.0 && line.length < 15) {
                        rating = rm[1];
                    }
                }
                if (!reviews) {
                    const rvm = line.match(re_reviews);
                    if (rvm) reviews = rvm[1].replace(',', '');
                }
                if (!place_type && line !== name && !line.match(re_rating) && !line.match(re_reviews)) {
                    place_type = line;
                }
            });

            results.push({ name, rating, reviews, place_type });
        });

        return results;
    }""")

    print(f"  Extracted {len(records)} records via JS")
    now = datetime.now().isoformat()
    for r in records:
        r["address"] = ""  # filled in step 2 via Places API
        r["scraped_at"] = now
    return records


def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ERROR: playwright not installed. Run: pip install playwright && playwright install chromium")
        sys.exit(1)

    import pandas as pd

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    progress = load_progress()
    if progress.get("completed") and OUTPUT_CSV.exists():
        print(f"Scraping already completed ({progress['total_found']} hospitals). Delete {PROGRESS_FILE} to re-run.")
        return

    print("=" * 70)
    print("HOSPITAL LIST SCRAPER — Google Maps")
    print("=" * 70)
    print(f"URL: {GMAPS_URL}")
    print()

    progress["started_at"] = datetime.now().isoformat()
    save_progress(progress)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=False,  # non-headless to avoid Google bot detection
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ]
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            locale="en-US",
        )
        page = context.new_page()

        print("Navigating to Google Maps URL...")
        page.goto(GMAPS_URL, wait_until="domcontentloaded", timeout=60_000)

        # Dismiss cookie / consent dialogs if they appear (EU)
        try:
            consent_btn = page.locator('button:has-text("Accept all")').first
            if consent_btn.is_visible(timeout=3000):
                consent_btn.click()
                time.sleep(1)
        except Exception:
            pass

        # Give the page time to render the list
        print("Waiting for hospital list to render...")
        time.sleep(6)

        # Take a debug screenshot so we can verify the list loaded
        page.screenshot(path=str(DATA_DIR / "debug_screenshot.png"), full_page=False)
        print("  Screenshot saved to data/hospitals/debug_screenshot.png")

        container_sel = find_list_container(page)
        if not container_sel:
            print("WARNING: No scrollable list container found. Will still attempt extraction.")
            container_sel = 'div.m6QErb'


        # Scroll to load all items
        scroll_feed_to_end(page, container_sel)

        # Extract data
        hospitals = extract_items(page)

        browser.close()

    print(f"\nExtracted {len(hospitals)} hospitals.")

    if not hospitals:
        print("WARNING: No hospitals extracted. Check data/hospitals/debug_screenshot.png if it exists.")
        progress["completed"] = False
        progress["total_found"] = 0
        save_progress(progress)
        return

    df = pd.DataFrame(hospitals)
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"Saved to {OUTPUT_CSV}")

    progress["completed"] = True
    progress["total_found"] = len(hospitals)
    progress["completed_at"] = datetime.now().isoformat()
    save_progress(progress)

    print("\nSample records:")
    print(df[["name", "address", "rating"]].head(10).to_string(index=False))
    print()
    print("=" * 70)
    print(f"DONE — {len(hospitals)} hospitals saved.")
    print(f"Next: run 02_enrich_hospitals.py")
    print("=" * 70)


if __name__ == "__main__":
    main()

"""
Collect Google Play reviews for Egyptian fintech apps.

Usage (run from the repo root):
    python src/collect_reviews.py --find-ids              # look up package IDs
    python src/collect_reviews.py                         # collect all apps in config/apps.json
    python src/collect_reviews.py --apps Telda valU       # only some apps
    python src/collect_reviews.py --max 2000              # quick test run
    python src/collect_reviews.py --since 2023-01-01      # stop at older reviews

Output:
    data/raw/<app>_<lang>.csv     one file per app and language (saved as it goes)
    data/raw/reviews_raw.csv      all reviews combined, deduplicated
    data/raw/apps_metadata.csv    rating, installs, version per app on collection day

Each review gets lang_detected (arabic / english / franco / unknown) from src/language.py,
because the store returns Arabic reviews for English requests too.
"""

import argparse
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
from google_play_scraper import Sort, app as app_details, reviews, search

from language import add_language_column

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "apps.json"
RAW_DIR = ROOT / "data" / "raw"

COUNTRY = "eg"
LANGS = ["ar", "en"]
BATCH_SIZE = 200          # max the Play Store returns per request
SLEEP_SECONDS = 1.0       # pause between requests, be polite
MAX_RETRIES = 3

# Columns we keep. User names and profile pictures are dropped on purpose (privacy).
KEEP_COLS = [
    "reviewId", "app", "lang_requested", "lang_detected", "content", "score", "thumbsUpCount",
    "appVersion", "at", "replyContent", "repliedAt", "collected_at",
]


def load_config():
    with open(CONFIG, encoding="utf-8") as f:
        return json.load(f)["apps"]


def slug(name):
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def find_ids(apps):
    """Print the top Play Store search results so you can pick the right package ID."""
    for a in apps:
        print(f"\n== {a['name']}  (search: '{a['search']}')")
        try:
            results = search(a["search"], lang="en", country=COUNTRY, n_hits=5)
        except Exception as e:
            print(f"   search failed: {e}")
            continue
        for r in results:
            print(f"   {r.get('appId') or '?':45s} {r.get('title')}  |  {r.get('developer')}")
    print("\nCopy the right appId into config/apps.json, then run the script without --find-ids.")
    print("A '?' is a known google-play-scraper bug for the top search result: open the app on")
    print("play.google.com and copy the part after 'id=' in the URL instead.")


def keyword_filter(df, keywords):
    """Keep only reviews that mention at least one keyword (case-insensitive)."""
    pattern = "|".join(re.escape(k) for k in keywords)
    mask = df["content"].fillna("").str.contains(pattern, case=False, regex=True)
    return df[mask]


def fetch_page(app_id, lang, token):
    """One request with retries. Returns (reviews, next_token)."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return reviews(app_id, lang=lang, country=COUNTRY, sort=Sort.NEWEST,
                           count=BATCH_SIZE, continuation_token=token)
        except Exception as e:
            wait = 5 * attempt
            print(f"   request failed ({e}); retry {attempt}/{MAX_RETRIES} in {wait}s")
            time.sleep(wait)
    raise RuntimeError(f"Giving up on {app_id} ({lang}) after {MAX_RETRIES} retries")


def fetch_reviews(app_id, lang, max_count, since=None):
    rows, token = [], None
    while len(rows) < max_count:
        batch, token = fetch_page(app_id, lang, token)
        if not batch:
            break
        rows.extend(batch)
        oldest = batch[-1]["at"]
        print(f"   {lang}: {len(rows):>6} reviews (oldest so far {oldest:%Y-%m-%d})", end="\r")
        if since and oldest < since:
            break
        if token is None:
            break
        time.sleep(SLEEP_SECONDS)
    print()
    if since:
        rows = [r for r in rows if r["at"] >= since]
    return rows[:max_count]


def fetch_metadata(name, app_id, collected_at):
    try:
        d = app_details(app_id, lang="en", country=COUNTRY)
    except Exception as e:
        print(f"   metadata failed: {e}")
        return None
    return {
        "app": name, "app_id": app_id, "title": d.get("title"),
        "developer": d.get("developer"), "score": d.get("score"),
        "ratings": d.get("ratings"), "reviews_total": d.get("reviews"),
        "installs": d.get("installs"), "version": d.get("version"),
        "last_updated": d.get("lastUpdatedOn"), "collected_at": collected_at,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--find-ids", action="store_true", help="search the Play Store for package IDs and exit")
    p.add_argument("--apps", nargs="*", help="only these app names (as in config/apps.json)")
    p.add_argument("--langs", nargs="*", default=LANGS, help="review languages to request (default: ar en)")
    p.add_argument("--max", type=int, help="max reviews per app per language (default: app's max in config, else 15000)")
    p.add_argument("--since", help="only keep reviews on or after this date, YYYY-MM-DD")
    args = p.parse_args()

    apps = load_config()
    if args.apps:
        wanted = {a.lower() for a in args.apps}
        apps = [a for a in apps if a["name"].lower() in wanted]

    if args.find_ids:
        find_ids(apps)
        return

    missing = [a["name"] for a in apps if not a["app_id"]]
    if missing:
        sys.exit(f"Missing app_id for: {', '.join(missing)}. Run with --find-ids first and fill config/apps.json.")

    since = datetime.strptime(args.since, "%Y-%m-%d") if args.since else None
    collected_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    frames, meta = [], []
    for a in apps:
        print(f"\n== {a['name']} ({a['app_id']})")
        m = fetch_metadata(a["name"], a["app_id"], collected_at)
        if m:
            meta.append(m)
        max_count = args.max or a.get("max", 15000)
        for lang in args.langs:
            rows = fetch_reviews(a["app_id"], lang, max_count, since)
            if not rows:
                print(f"   {lang}: no reviews")
                continue
            df = pd.DataFrame(rows)
            df["app"], df["lang_requested"], df["collected_at"] = a["name"], lang, collected_at
            df = add_language_column(df)   # the store's lang is only a request; label the real language
            df = df[[c for c in KEEP_COLS if c in df.columns]]
            if a.get("filter_keywords"):
                before = len(df)
                df = keyword_filter(df, a["filter_keywords"])
                print(f"   {lang}: kept {len(df)} of {before} reviews matching filter_keywords")
                if df.empty:
                    continue
            out = RAW_DIR / f"{slug(a['name'])}_{lang}.csv"
            df.to_csv(out, index=False, encoding="utf-8-sig")   # utf-8-sig: Arabic opens correctly in Excel
            print(f"   saved {len(df)} -> {out.relative_to(ROOT)}")
            frames.append(df)

    if not frames:
        sys.exit("No reviews collected.")

    allr = pd.concat(frames, ignore_index=True).drop_duplicates("reviewId")
    allr.to_csv(RAW_DIR / "reviews_raw.csv", index=False, encoding="utf-8-sig")
    if meta:
        pd.DataFrame(meta).to_csv(RAW_DIR / "apps_metadata.csv", index=False, encoding="utf-8-sig")

    print(f"\nDone: {len(allr)} unique reviews -> data/raw/reviews_raw.csv")
    print("\nReviews by real language:")
    print(allr.groupby(["app", "lang_detected"]).size().unstack(fill_value=0))


if __name__ == "__main__":
    main()

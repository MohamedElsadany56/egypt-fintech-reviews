"""
Clean the raw Play Store reviews and add the columns the analysis needs.

Usage (from the repo root):
    python src/cleaning.py
Reads  data/raw/reviews_raw.csv
Writes data/processed/reviews_clean.csv     one row per review, ready for analysis
       data/processed/removed_reviews.csv   every removed row with the reason
       data/processed/cleaning_log.csv      rows before/after each step

Main decisions (explained in notebooks/01_cleaning.ipynb):
  - Duplicates are found by reviewId only. Thousands of different people write the same short text
    ("ممتاز", "Good"), so removing repeated text would delete real reviews.
  - Emoji-only and one-word reviews are KEPT: their star rating is still valid for rating analysis.
    `text_usable` marks the reviews that have enough text for topic and sentiment analysis.
  - The Arabic results from the store go back less far than the English ones. `in_full_coverage`
    marks the dates where both languages are collected for that app; use it for trends over time.
"""

import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from language import detect_language  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "reviews_raw.csv"
OUT_DIR = ROOT / "data" / "processed"

URL = re.compile(r"https?://\S+|www\.\S+")
EMOJI_AND_SYMBOLS = re.compile(
    "[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\uFE0F\u200d\u200c\u200b\u200e\u200f]+"
)
TASHKEEL = re.compile(r"[\u0617-\u061A\u064B-\u0652\u0670]")
TATWEEL = "\u0640"
REPEATED = re.compile(r"(.)\1{2,}")        # 3+ of the same character -> 2 ("حلوووو" -> "حلوو")
WORD_TOKEN = re.compile(r"[^\W_]+")         # runs of letters/digits in any script
REPEATED_UNIT = re.compile(r"(.{2,8}?)\1+.{0,8}")   # "جداجداجدا..." = one short piece repeated
ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")


# ---------- text helpers ----------

def normalize_text(text):
    """Text for keyword matching and NLP: one spelling per Arabic letter, lower-case Latin, no emoji."""
    if not isinstance(text, str):
        return ""
    t = URL.sub(" ", text)
    t = EMOJI_AND_SYMBOLS.sub(" ", t)
    t = TASHKEEL.sub("", t).replace(TATWEEL, "")
    t = re.sub("[إأآٱ]", "ا", t)
    t = t.replace("ة", "ه").replace("ى", "ي").replace("ؤ", "و").replace("ئ", "ي")
    t = t.translate(ARABIC_DIGITS)
    t = REPEATED.sub(r"\1\1", t)
    t = t.lower()
    return re.sub(r"\s+", " ", t).strip()


def is_spam(text):
    """Keyboard-mash spam such as 'Ďdddďdďddd22d...'.

    Stretched words ("تمااااااام", "خرااااا", "فاااااشل") are real, strong opinions, so repeated
    letters are shortened first. Words are split on anything that is not a letter or digit, so
    "كل.مره.يتطلب" and error codes like "java.lang.RuntimeException" become normal short words.
    After that, no real word is 30+ characters long; a keyboard mash is. A long word that is one
    short piece repeated ("جداجداجدا...") is an enthusiastic review, not spam.
    """
    if not isinstance(text, str):
        return False
    collapsed = REPEATED.sub(r"\1\1", URL.sub(" ", text))
    for token in WORD_TOKEN.findall(collapsed):
        if len(token) >= 30 and not REPEATED_UNIT.fullmatch(token):
            return True
    return False


def version_minor(v):
    """'1.12.0' -> '1.12', '2026.10.2' -> '2026.10'. Missing stays missing."""
    if not isinstance(v, str):
        return None
    parts = v.split(".")
    return ".".join(parts[:2]) if len(parts) >= 2 else v


# ---------- pipeline ----------

def clean(raw):
    log, removed = [], []

    def step(name, df_before, df_after, reason=None):
        n_removed = len(df_before) - len(df_after)
        log.append({"step": name, "rows_before": len(df_before), "removed": n_removed, "rows_after": len(df_after)})
        if reason and n_removed:
            gone = df_before.loc[~df_before.index.isin(df_after.index)].copy()
            gone["removed_reason"] = reason
            removed.append(gone)
        return df_after

    df = raw.copy()
    log.append({"step": "raw data", "rows_before": len(df), "removed": 0, "rows_after": len(df)})

    # 1. Empty reviews: no text at all.
    df = step("remove empty reviews", df,
              df[df["content"].fillna("").str.strip() != ""], "empty")

    # 2. Duplicate review IDs (the same review returned twice by the store).
    df = step("remove duplicate reviewId", df,
              df.drop_duplicates("reviewId"), "duplicate reviewId")

    # 3. Keyboard-mash spam.
    df = step("remove spam (keyboard mash)", df,
              df[~df["content"].apply(is_spam)], "spam")

    df = df.copy()

    # 4. Language: re-detect with the current rules (the raw file may use an older version).
    df["lang_detected"] = df["content"].apply(detect_language)

    # 5. Normalized text and text features.
    df["content_clean"] = df["content"].apply(normalize_text)
    df["word_count"] = df["content_clean"].str.split().str.len().fillna(0).astype(int)
    df["char_count"] = df["content"].str.len()
    df["text_usable"] = (df["lang_detected"] != "unknown") & (df["word_count"] >= 3)

    # 6. Dates.
    df["at"] = pd.to_datetime(df["at"])
    df["repliedAt"] = pd.to_datetime(df["repliedAt"])
    df["date"] = df["at"].dt.date
    df["year"] = df["at"].dt.year
    df["year_month"] = df["at"].dt.to_period("M").astype(str)
    df["week"] = df["at"].dt.to_period("W-SUN").dt.start_time.dt.date   # week starting Monday

    # 7. Coverage: both store languages are collected from the later of the two start dates.
    starts = df.groupby(["app", "lang_requested"])["at"].min().unstack()
    coverage_start = starts.max(axis=1).rename("coverage_start")
    df = df.join(coverage_start, on="app")
    df["in_full_coverage"] = df["at"] >= df["coverage_start"]

    # 8. Stars.
    df["is_negative"] = df["score"] <= 2
    df["is_positive"] = df["score"] >= 4
    df["star_sentiment"] = pd.cut(df["score"], bins=[0, 2, 3, 5], labels=["negative", "neutral", "positive"])

    # 9. Company replies.
    df["has_reply"] = df["replyContent"].notna()
    hours = (df["repliedAt"] - df["at"]).dt.total_seconds() / 3600
    df["reply_hours"] = hours.where(hours >= 0).round(1)   # negative = clock/edit noise -> missing

    # 10. App version (major.minor) for version-level comparisons.
    df["app_version_minor"] = df["appVersion"].apply(version_minor)

    cols = [
        "reviewId", "app", "score", "star_sentiment", "is_negative", "is_positive",
        "content", "content_clean", "lang_detected", "lang_requested", "word_count", "char_count",
        "text_usable", "at", "date", "year", "year_month", "week", "coverage_start", "in_full_coverage",
        "appVersion", "app_version_minor", "thumbsUpCount", "has_reply", "replyContent", "repliedAt",
        "reply_hours", "collected_at",
    ]
    df = df[cols].sort_values(["app", "at"], ascending=[True, False]).reset_index(drop=True)
    log.append({"step": "clean data", "rows_before": len(df), "removed": 0, "rows_after": len(df)})

    removed_df = pd.concat(removed) if removed else pd.DataFrame()
    return df, pd.DataFrame(log), removed_df


def main():
    raw = pd.read_csv(RAW)
    df, log, removed = clean(raw)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_DIR / "reviews_clean.csv", index=False, encoding="utf-8-sig")
    log.to_csv(OUT_DIR / "cleaning_log.csv", index=False)
    if len(removed):
        removed.to_csv(OUT_DIR / "removed_reviews.csv", index=False, encoding="utf-8-sig")
    print(log.to_string(index=False))
    print(f"\nSaved {len(df)} reviews -> data/processed/reviews_clean.csv")


if __name__ == "__main__":
    main()

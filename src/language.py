"""
Detect the real language of a review: arabic, english, franco (Arabic written in Latin letters), or unknown.

The Play Store `lang` parameter is only a request: the "en" results contain many Arabic reviews,
so every review is labeled by its text instead.

Rules (simple and explainable on purpose):
  1. Count Arabic letters vs Latin letters. More Arabic letters -> arabic.
     (Arabic text with an English word like "Vodafone" stays arabic.)
  2. Latin text gets a franco score and an english score:
       franco  = 2 points per word with an Arabic-sound digit inside (3ala, 7aga, ba2a, 5alas)
               + 1 point per common franco word (msh, keda, ezay ...)
       english = 1 point per common English word (the, is, not, app ...)
     franco if franco score >= 2 and higher than the english score, otherwise english.
  3. No letters at all (emoji, numbers) -> unknown.

Usage (from the repo root) to label CSVs you already collected:
    python src/language.py data/raw/vodafone_cash_en.csv data/raw/vodafone_cash_ar.csv
"""

import re
import sys

ARABIC_LETTER = re.compile(r"[ء-ي٠-٩پچڤگ]")
LATIN_LETTER = re.compile(r"[A-Za-z]")
WORD = re.compile(r"[A-Za-z0-9']+")

# A word with 2/3/5/7/8/9 used as a letter: 3ala, 7aga, ba2a, 5alas, mesh3arf.
# Needs letters around the digit, so phone models (S24, A52) and "4G"/"5G" are not counted.
FRANCO_DIGIT_WORD = re.compile(r"^(?=.*[a-z])(?:[a-z]+[235789][a-z]*|[235789][a-z]{2,}[a-z0-9]*)$")

# Common franco words. Words that are also English or brand names ("ana" in "Ana Vodafone",
# "el", "w", "ya", "fe") are left out because they cause false positives.
FRANCO_WORDS = {
    "msh", "mesh", "mish", "mosh", "enta", "enty", "ento", "ehna", "howa", "heya",
    "keda", "kda", "leh", "leeh", "ezay", "ezzay", "ezai", "eh", "eih", "aho", "ahe",
    "bta3", "beta3", "bta3et", "ba2a", "ba2o", "7aga", "7aja", "kwayes", "kwais", "kowayes",
    "zay", "3la", "3ala", "mafi", "mfesh", "mafeesh", "tamam", "awy", "awi", "khales",
    "5ales", "gamed", "fein", "feen", "emta", "lessa", "lesa", "bardo", "kman", "kaman",
    "elly", "elli", "illi", "ya3ni", "yani", "fa2", "felos", "flos", "floos", "mabye",
    "mabyeshtaghal", "byfta7", "bt3ml", "wala", "walla", "law", "lama", "3ashan", "3shan",
    "alashan", "3lshan", "ma3", "m3", "betaa", "kol", "kolo", "haga", "7elw", "helw",
    "wahsh", "we7esh", "zeft", "5ara", "khara", "harame", "7arame", "sabab", "el2", "da",
    "dah", "di", "deh", "dool", "eltatbeek", "eltatbe2", "tatbe2", "tatbeek", "elbarnameg",
}

ENGLISH_WORDS = {
    "the", "is", "are", "was", "were", "not", "and", "but", "it", "its", "this", "that",
    "app", "i", "my", "me", "you", "to", "of", "in", "on", "for", "with", "can", "cant",
    "can't", "don't", "doesn't", "isn't", "very", "bad", "good", "worst", "best", "work",
    "working", "update", "after", "when", "every", "time", "have", "has", "be", "please",
    "money", "service", "problem", "issue", "open", "use", "great", "nice", "useless",
}


def detect_language(text):
    if not isinstance(text, str) or not text.strip():
        return "unknown"
    n_ar = len(ARABIC_LETTER.findall(text))
    n_lat = len(LATIN_LETTER.findall(text))
    if n_ar == 0 and n_lat == 0:
        return "unknown"
    if n_ar >= n_lat:
        return "arabic"

    words = [w.lower() for w in WORD.findall(text)]
    franco = sum(2 for w in words if FRANCO_DIGIT_WORD.match(w)) + sum(1 for w in words if w in FRANCO_WORDS)
    english = sum(1 for w in words if w in ENGLISH_WORDS)
    if franco >= 2 and franco > english:
        return "franco"
    return "english"


def add_language_column(df, text_col="content"):
    df = df.copy()
    df["lang_detected"] = df[text_col].apply(detect_language)
    return df


if __name__ == "__main__":
    import pandas as pd

    if len(sys.argv) < 2:
        sys.exit(__doc__)
    for path in sys.argv[1:]:
        df = add_language_column(pd.read_csv(path))
        df.to_csv(path, index=False, encoding="utf-8-sig")
        print(f"{path}: {df['lang_detected'].value_counts().to_dict()}")

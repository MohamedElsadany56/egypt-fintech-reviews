"""
Ratings-over-time helpers used by notebooks/02_ratings_over_time.ipynb.

All functions expect the cleaned data from src/cleaning.py and should be given only
rows with in_full_coverage == True, so Arabic and English reviews are both present.
"""

from collections import Counter

import pandas as pd

# Common words that say nothing about the problem, removed before comparing word use.
STOPWORDS = set("""
في من علي على و ال انا مش ما لا يا الي الى اللي ده دي ان او مع كل هو هي بس عن تم لم لو كان
the to and i a is it of my app in for this not on me be you that with have was are they
""".split())


def monthly_stats(df):
    """Average stars and 1-star share per app and month, for all reviews and for written ones.

    'Written' = 3+ words (text_usable). One- and two-word reviews are mostly 5-star ("ممتاز")
    and come in waves when an app asks users to rate it, which can hide real problems.
    """
    def agg(g):
        written = g[g["text_usable"]]
        return pd.Series({
            "reviews": len(g),
            "avg_stars": g["score"].mean(),
            "one_star_share": (g["score"] == 1).mean(),
            "written_reviews": len(written),
            "avg_stars_written": written["score"].mean() if len(written) else float("nan"),
        })
    out = df.groupby(["app", "year_month"]).apply(agg, include_groups=False).reset_index()
    out["month"] = pd.PeriodIndex(out["year_month"], freq="M").to_timestamp()
    return out


def weekly_counts(df):
    """Reviews, 1-star and 5-star counts per app and week, with empty weeks filled as 0."""
    rows = []
    for app, g in df.groupby("app"):
        w = g.assign(one=g["score"].eq(1), five=g["score"].eq(5),
                     short_five=g["score"].eq(5) & (g["word_count"] <= 2))
        w = w.groupby(pd.to_datetime(w["week"])).agg(
            reviews=("score", "size"), one_star=("one", "sum"),
            five_star=("five", "sum"), short_five_star=("short_five", "sum"),
            avg_stars=("score", "mean"))
        full = pd.date_range(w.index.min(), w.index.max(), freq="7D")
        w = w.reindex(full, fill_value=0)
        w.index.name = "week"
        w["app"] = app
        rows.append(w.reset_index())
    return pd.concat(rows, ignore_index=True)


def find_surges(weekly, col, min_count, ratio=3, baseline_weeks=8):
    """Flag weeks where `col` is at least `ratio` x its usual level and at least `min_count`.

    Usual level = median of the previous `baseline_weeks` weeks for that app (floor of 5, so
    quiet apps don't flag every small bump). Using the app's own recent past is fairer than one
    threshold for all apps: InstaPay gets ~600 reviews a month, valU ~60.
    """
    w = weekly.sort_values(["app", "week"]).copy()
    w["baseline"] = (w.groupby("app")[col]
                       .transform(lambda s: s.shift(1).rolling(baseline_weeks, min_periods=4).median()))
    w["times_usual"] = w[col] / w["baseline"].clip(lower=5)
    flagged = w[(w[col] >= min_count) & (w["times_usual"] >= ratio)].copy()

    # Merge back-to-back flagged weeks of the same app into one event.
    flagged["new_event"] = flagged.groupby("app")["week"].diff().ne(pd.Timedelta(days=7))
    flagged["event"] = flagged["new_event"].cumsum()
    events = flagged.groupby("event").agg(
        app=("app", "first"), start=("week", "min"), end=("week", "max"),
        weeks=("week", "size"), count=(col, "sum"), usual_per_week=("baseline", "median"),
        peak_times_usual=("times_usual", "max"), avg_stars=("avg_stars", "mean"))
    events["end"] = events["end"] + pd.Timedelta(days=6)
    return events.reset_index(drop=True)


def reviews_in(df, app, start, end, max_stars=None):
    sel = (df["app"] == app) & (df["at"] >= start) & (df["at"] <= end + pd.Timedelta(days=1))
    if max_stars is not None:
        sel &= df["score"] <= max_stars
    return df[sel]


def rising_words(event_reviews, before_reviews, top=12, min_share=0.04):
    """Words used much more in the event's reviews than in the 90 days before it.

    Share = % of reviews containing the word (each review counts a word once).
    """
    def shares(texts):
        c = Counter()
        for t in texts.fillna(""):
            c.update({w for w in t.split() if len(w) > 2 and w not in STOPWORDS})
        n = max(len(texts), 1)
        return {w: k / n for w, k in c.items()}, c

    ev, ev_counts = shares(event_reviews["content_clean"])
    bf, _ = shares(before_reviews["content_clean"])
    rows = [(w, s, bf.get(w, 0.0)) for w, s in ev.items() if s >= min_share and ev_counts[w] >= 8]
    out = pd.DataFrame(rows, columns=["word", "share_in_event", "share_before"])
    out["increase"] = out["share_in_event"] - out["share_before"]
    return out.sort_values("increase", ascending=False).head(top).reset_index(drop=True)


def version_stats(df, min_reviews=100):
    """Average stars and 1-star share per app version, in release order."""
    v = (df.dropna(subset=["appVersion"])
           .groupby(["app", "appVersion"])
           .agg(reviews=("score", "size"), avg_stars=("score", "mean"),
                one_star_share=("score", lambda s: (s == 1).mean()),
                first_seen=("at", "min"))
           .query("reviews >= @min_reviews")
           .reset_index()
           .sort_values(["app", "first_seen"]))
    v["change_vs_previous"] = v.groupby("app")["avg_stars"].diff()
    return v

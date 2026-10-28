# Sawt El Omala (صوت العملاء)
### What Egyptian users really think about fintech apps

An analysis of real Google Play reviews of five Egyptian fintech apps: **InstaPay, Vodafone Cash, Telda, valU and Fawry**. The project finds what frustrates users most, when ratings dropped and why, and which app gives the best experience, across Arabic, English and Franco-Arabic reviews.

> Status: in progress. Data collection is set up; analysis is next.

---

## Key findings
*(Filled in once the analysis is done. Each finding: one sentence, one number, one chart.)*

1. **Top complaint:** _[topic]_ drives _[X]%_ of 1-star reviews across all apps.
2. **Biggest rating drop:** _[app]_ in _[month/year]_, linked to _[update/outage/fee change]_.
3. **Best experience:** _[app]_ with _[X]_ average rating and the lowest share of negative reviews.
4. **Hidden pain points:** _[X]%_ of 4–5 star reviews still mention a problem.

## Recommendations
*(2–3 per app, each tied to a number from the analysis.)*

| App | Biggest pain point | Recommendation |
| --- | --- | --- |
| InstaPay | | |
| Vodafone Cash | | |
| Telda | | |
| valU | | |
| Fawry | | |

---

## Business questions
1. What are the top complaint topics for each app, and what share of 1-star reviews does each topic cause?
2. When did ratings drop sharply, and does each drop line up with an app update, an outage or a policy change?
3. How does sentiment differ between Arabic, English and Franco-Arabic reviews?
4. Which app has the best overall experience, and what is each app's single biggest fix?

## Data
- **Source:** public Google Play reviews from the Egypt store, collected with [`google-play-scraper`](https://github.com/JoMingyu/google-play-scraper).
- **Collected on:** _[date]_
- **Size:** _[N]_ reviews (Arabic and English requests per app)
- **Privacy:** user names and profile images are not stored.

| Column | Meaning |
| --- | --- |
| `reviewId` | unique review ID |
| `app` | app name |
| `lang_requested` | language requested from the store (`ar` / `en`) |
| `content` | review text |
| `score` | star rating, 1–5 |
| `thumbsUpCount` | how many users found the review helpful |
| `appVersion` | app version the reviewer used |
| `at` | review date |
| `replyContent`, `repliedAt` | company reply and its date |
| `collected_at` | when the review was scraped |

## Method
1. **Collection:** `src/collect_reviews.py` (newest reviews first, Arabic and English, Egypt store).
2. **Cleaning:** remove empty and duplicate reviews, detect Arabic / English / Franco-Arabic, normalize Arabic text.
3. **Ratings over time:** monthly ratings, 1-star spike detection, ratings by app version.
4. **Complaint topics:** keyword dictionary in three languages, validated against 300 hand-labeled reviews (precision and recall per topic).
5. **Sentiment:** CAMeLBERT dialect model for Arabic, RoBERTa for English; mismatches between text and stars.
6. **Comparison:** app scorecard and dashboard.

## Repo structure
```
egypt-fintech-reviews/
├── config/
│   └── apps.json           # apps and their Play Store package IDs
├── src/
│   └── collect_reviews.py  # scraper
├── data/
│   ├── raw/                # scraped CSVs (not committed, re-create with the script)
│   └── processed/          # cleaned and labeled data
├── notebooks/              # 01_cleaning_eda, 02_topics, 03_sentiment ...
├── dashboard/              # Power BI file or Streamlit app
├── images/                 # charts used in this README
└── requirements.txt
```

## How to run
```bash
pip install -r requirements.txt

# 1. Find each app's package ID and paste it into config/apps.json
python src/collect_reviews.py --find-ids

# 2. Quick test with a small number of reviews
python src/collect_reviews.py --apps Telda --max 500

# 3. Full collection
python src/collect_reviews.py
```

## Limitations
- Play Store reviewers are not a random sample of users; unhappy users review more often.
- iOS App Store reviews are not included.
- Keyword topic labels can miss sarcasm and mixed-language slang.
- No ready-made sentiment model exists for Franco-Arabic, so star ratings are used as its sentiment label.

## Tools
Python (pandas, scikit-learn, Hugging Face transformers), google-play-scraper, Power BI / Streamlit.

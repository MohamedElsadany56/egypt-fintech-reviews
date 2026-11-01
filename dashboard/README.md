# Power BI dashboard: build guide

The dashboard is built in **Power BI Desktop** (free, Windows) from the CSV files in `dashboard/data/`,
which `notebooks/05_app_scorecard.ipynb` creates. Building it takes about 1–2 hours the first time.

**Files in this folder**

| File | What it is |
|---|---|
| `data/fact_reviews.csv` | one row per review (71,749), with 0/1 flags so measures can use `SUM` |
| `data/review_topics.csv` | one row per review × complaint topic (a review can have several topics) |
| `data/dim_app.csv` | one row per app: store rating, installs, coverage start, color |
| `data/dim_topic.csv` | the 12 complaint topics and their sort order |
| `data/surge_events.csv` | the 6 complaint surges and their causes |
| `data/recommendations.csv` | my 14 recommendations with their evidence |
| `measures.dax` | every DAX measure, ready to paste |
| `theme.json` | report theme with the project colors |
| `PAGES.md` | page-by-page layout: canvas size, exact position of every visual, wireframes, click-by-click steps |
| `wireframes/` | one wireframe image per page (1280 × 720) |

> **Order:** do Steps 1–3 below (data, measures, relationships), then build the pages with [PAGES.md](PAGES.md).
> Step 4 below is the short version of the same pages.

---

## Step 1. Load the data

1. **Home → Get data → Text/CSV**, choose `data/fact_reviews.csv`.
2. In the preview, set **File Origin = 65001: Unicode (UTF-8)** so the Arabic text displays correctly. Click **Transform Data**.
3. In Power Query, check the column types:
   - `review_date` → **Date**
   - `reply_hours`, `model_score` → **Decimal number**
   - `stars` and every 0/1 flag (`is_one_star`, `is_negative`, `text_usable`, `in_full_coverage`, `has_reply`, `hidden_pain_base`, `hidden_pain_point`, ...) → **Whole number**
   - `review_text`, `app_version`, `review_id` → **Text**

   If your Windows uses a comma as the decimal separator, change the type with **Using Locale… → English (United States)**.
4. Repeat for the other five CSVs (**New Source → Text/CSV**, UTF-8 each time). In `dim_app`, set `coverage_start` to **Date**.
5. **Close & Apply**.

## Step 2. Date table, measures and theme

1. **Modeling → New table**, paste the `Date = ...` block from `measures.dax`. Then **Table tools → Mark as date table** (column: `Date`).
2. **Home → Enter data**, name the table `_Measures`, click **Load**. Then add every measure from `measures.dax` with
   **Modeling → New measure** while `_Measures` is selected. You can delete its empty `Column1` afterwards.
3. Format the measures (select a measure → **Measure tools**):
   - **Percentage, 1 decimal:** `% 1-Star`, `% Negative (1-2 Stars)`, `% of App Reviews`, `% of Negative Reviews (Topic)`, `Hidden Pain %`, `Reply Rate (Negative)`
   - **Decimal, 2 places:** `Avg Stars`, `Avg Stars (3+ Words)`, `Store Rating`, `Gap vs Store Rating`, `Avg Stars Last 6M`, `Avg Stars Prev 6M`, `Trend (Last 6M vs Prev 6M)`
   - **Decimal, 1 place:** `Median Reply Hours`, `Median Reply Days`
   - `Matches Topic Slicer` is a helper (0/1) used only as a filter; no formatting needed
   - **Whole number with thousands separator:** `Reviews`, `One-Star Reviews`, `Negative Reviews`, `Negative Written Reviews`, `Hidden Pain Reviews`
4. **View → Themes → Browse for themes**, choose `theme.json`.

## Step 3. Relationships (Model view)

Drag to create these. All are **one-to-many, single direction**:

| From (one) | To (many) |
|---|---|
| `dim_app[app]` | `fact_reviews[app]` |
| `dim_app[app]` | `surge_events[app]` |
| `dim_app[app]` | `recommendations[app]` |
| `Date[Date]` | `fact_reviews[review_date]` |
| `fact_reviews[review_id]` | `review_topics[review_id]` |
| `dim_topic[topic_id]` | `review_topics[topic_id]` |

Then set sort orders (select the column → **Column tools → Sort by column**):
- `dim_app[app]` sorted by `dim_app[sort_order]`
- `dim_topic[topic]` sorted by `dim_topic[sort_order]`
- `Date[Month]` sorted by `Date[Month Start]`

> Why single direction matters: topic filters must not reach `fact_reviews`, otherwise the denominator of
> `% of Negative Reviews (Topic)` would shrink and every topic would show 100%.

## Step 4. Build the pages

**On every page except "Voice of the customer"**, add a page filter **`fact_reviews[in_full_coverage]` is 1**
(Filters pane → *Filters on this page*). This is the same rule as the notebooks: before each app's coverage start
there are only English reviews. Add an **app slicer** (`dim_app[app]`, style: Tile) at the top of each page and use
**View → Sync slicers** so the choice carries across pages.

### Page 1 · Overview

| Visual | Fields |
|---|---|
| Text box (title) | "Sawt El Omala · What Egyptian users say about 5 fintech apps" + a line with the data date |
| 4 × Card (new card visual) | `Reviews`, `Avg Stars`, `% 1-Star`, `Hidden Pain %` |
| Table (scorecard) | `dim_app[app]`, `Store Rating`, `Avg Stars`, `% 1-Star`, `Trend (Last 6M vs Prev 6M)`, `Hidden Pain %`, `Reply Rate (Negative)`, `Median Reply Days` |
| 100% stacked bar chart | Y-axis `dim_app[app]`, Legend `fact_reviews[stars]`, X-axis `Reviews` |

Formatting:
- Scorecard table: **Conditional formatting → Font color → Rules** on `Trend…`: below 0 = `#C23B3A`, above 0 = `#0CA30C`.
  On `% 1-Star`, use **Background color → Gradient** from `#F4F8FD` (lowest) to `#1C5CAB` (highest).
- Star bar colors (Format → Bars → Colors): 1★ `#C23B3A`, 2★ `#F09A99`, 3★ `#D9D8D3`, 4★ `#86B6EF`, 5★ `#2A78D6`.
  Turn on **Data labels** so the light colors are readable.

### Page 2 · Trends

| Visual | Fields |
|---|---|
| Line chart | X-axis `Date[Month Start]`, Y-axis `Avg Stars` and `Avg Stars (3+ Words)`, **Small multiples** `dim_app[app]` |
| Column chart | X-axis `Date[Week Start]`, Y-axis `One-Star Reviews`, **Small multiples** `dim_app[app]` |
| Table | `surge_events`: `app`, `start_date`, `one_star_reviews`, `times_usual`, `app_version`, `cause` |

Formatting: Small multiples → 1 column so the time axes line up. Line colors: `Avg Stars` `#2A78D6`,
`Avg Stars (3+ Words)` `#EB6834`. Title for the column chart: "Weekly 1-star reviews: InstaPay 1.12.0 was the biggest surge".

### Page 3 · Complaints

| Visual | Fields |
|---|---|
| Matrix (heatmap) | Rows `dim_topic[topic]`, Columns `dim_app[app]`, Values `% of Negative Reviews (Topic)` |
| Clustered bar chart | Y-axis `dim_topic[topic]`, X-axis `% of Negative Reviews (Topic)`, visual filter `fact_reviews[stars]` is 1, title "What 1-star reviews are about (all apps)" |
| Slicer | `fact_reviews[language]` |
| Slicer | `Date[Date]` (style: Between) |

Formatting: Matrix → **Cell elements → Background color → Gradient**, minimum `#F4F8FD`, maximum `#0D366B`
(use **Font color** white with a rule for values ≥ 0.28 so dark cells stay readable). Turn off row and column totals.

### Page 4 · Voice of the customer

| Visual | Fields |
|---|---|
| Slicers | `dim_app[app]`, `dim_topic[topic]`, `fact_reviews[stars]`, `fact_reviews[language]`, `fact_reviews[hidden_pain_point]` |
| Table | `fact_reviews[review_date]`, `dim_app[app]`, `fact_reviews[stars]`, `fact_reviews[review_text]`, `fact_reviews[model_sentiment]` |

Formatting: sort the table by `review_date` descending; turn on **Word wrap** for values; set the `review_text`
column width to ~500 px. Leave the coverage filter off on this page: old reviews are still useful to read.

Two visual filters on the table (Filters pane → *Filters on this visual*):
- `fact_reviews[text_usable]` is 1, so one-word reviews don't fill the table.
- Measure `Matches Topic Slicer` is 1. Without it, the topic slicer does nothing here, because topics don't filter
  `fact_reviews` directly (that's on purpose, see Step 3). With it, picking a topic shows only reviews with that topic.

### Page 5 · Recommendations

| Visual | Fields |
|---|---|
| Table | `recommendations`: `app`, `priority`, `recommendation`, `evidence` |
| Text box | 2–3 lines on which app is best and which needs the most work (from notebook 05's findings) |

Formatting: word wrap on, sort by `app` then `priority`.

## Step 5. Check the numbers

With the page filter `in_full_coverage = 1`, the Overview page should show these values (from notebook 05).
If a number is off, the usual cause is a missing page filter or a relationship set to "Both" directions.

| App | Reviews | Avg Stars | % 1-Star | Trend | Hidden Pain % | Reply Rate (Negative) | App-not-working % of negative |
|---|---|---|---|---|---|---|---|
| InstaPay | 17,637 | 3.62 | 30.1% | +0.11 | 8.6% | 73.4% | 51.3% |
| Fawry | 19,354 | 3.28 | 37.2% | −0.25 | 6.7% | 98.6% | 22.7% |
| Telda | 8,377 | 3.92 | 22.4% | −0.37 | 3.4% | 18.6% | 11.3% |
| valU | 11,148 | 2.90 | 48.4% | −0.72 | 6.1% | 87.5% | 15.3% |
| Vodafone Cash | 715 | 1.92 | 68.5% | (blank) | 21.6% | 94.8% | 47.4% |
| **All apps** | **57,231** | **3.39** | **35.4%** | | **6.6%** | **81.4%** | **28.2%** |

## Step 6. Save and share

1. Save as `dashboard/sawt_el_omala.pbix`.
2. Export each page as an image (**File → Export → Export to PDF**, or a screenshot) and save the Overview and
   Complaints pages as `images/dashboard_overview.png` and `images/dashboard_complaints.png`, so they show in the main README.
3. Optional: **Publish** to Power BI Service (needs a work or school account) and add the link to the main README.
   Without one, the `.pbix` file plus the screenshots on GitHub are enough for a portfolio.

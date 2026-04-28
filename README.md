# Student Performance Analytics: Does a Retake Policy Improve Math Outcomes?

An end-to-end data analysis project using **SQL (SQLite)**, **Python**, and **Tableau** to evaluate whether offering chapter test retakes leads to statistically significant improvement in student math scores.

**Background:** I've been privately tutoring math (Algebra through AP Calculus BC) since 2022. To track student progress, I built [Math Tracker](https://github.com/yejuseol/math-tracker) — a web dashboard where I log unit test scores, chapter-level results, and feedback notes for each student. This project uses the schema and scoring patterns from Math Tracker as the foundation for the dataset. Since the app is still early in deployment, I supplemented real data with synthetic records generated to match observed score distributions and improvement rates from 4 years of tutoring.

All student identifiers are anonymized (`Student_01` … `Student_24`).

---

## Key Findings

### Primary A/B Test — chapters where first attempt < 80%

| Metric | Control (no retake) | Treatment (retake) |
|---|---|---|
| n (chapter-records) | 55 | 69 |
| Mean final score | 66.4% | 70.5% |
| Median final score | 68.0% | 72.8% |

| Test | Statistic | p-value | Decision |
|---|---|---|---|
| Two-sample t-test | t = −1.86 | **0.0326** | Reject H₀ ✓ |
| Mann-Whitney U | U = 1420.5 | **0.0083** | Reject H₀ ✓ |
| Cohen's d | 0.343 | — | Small effect |
| 95% CI on diff | [−0.1, 8.2] pp | — | — |

### Paired analysis — treatment group only

| Metric | Value |
|---|---|
| Retake attempts | 69 |
| Mean first attempt | 61.0% |
| Mean retake score | 70.5% |
| Mean improvement | **+9.5 pp** |
| Paired t-test | p ≈ 0.000 |

### Mastery rate (score ≥ 76%) — full dataset

| Group | Mastery rate |
|---|---|
| Control | 44.2% |
| Treatment | **51.2%** |

---

## Project Structure

```
student-performance-analytics/
├── generate_data.py      # Synthetic data generation (SQLite)
├── sql_analysis.py       # SQL queries + CSV export for Tableau
├── ab_testing.py         # Hypothesis testing & visualizations
├── requirements.txt
├── math_tracker.db       # SQLite database (241 records)
├── figures/              # Output charts (5 figures)
└── tableau_exports/      # CSVs for Tableau dashboard
```

---

## A/B Test Design

**Research question:** Among chapters where a student scored below 80% on the first attempt, do students *with* retake access end up with significantly higher final scores than those *without*?

- **Control** (12 students): no retake — first attempt score is final
- **Treatment** (12 students): retake offered when first attempt < 80%
- Groups are balanced 2:2 within each of the 6 courses to avoid course difficulty as a confounding variable

Both parametric (t-test) and non-parametric (Mann-Whitney U) tests confirm a statistically significant difference (p < 0.05). The paired analysis on the treatment group shows a mean improvement of +9.5 pp from first attempt to retake.

---

## SQL Analysis Highlights

```sql
-- Chapter-level average performance
SELECT c.subject, c.chapter_num, c.chapter_name,
       ROUND(AVG(r.pct), 1) AS avg_pct
FROM test_records r
JOIN chapters c ON r.chapter_id = c.chapter_id
WHERE r.attempt = 1
GROUP BY c.chapter_id
ORDER BY avg_pct ASC;

-- Retake improvement (treatment group only)
SELECT f.pct AS first_pct, r2.pct AS retake_pct,
       ROUND(r2.pct - f.pct, 1) AS improvement
FROM test_records f
JOIN test_records r2
  ON f.student_id = r2.student_id AND f.chapter_id = r2.chapter_id
 AND f.attempt = 1 AND r2.attempt = 2;
```

---

## Visualizations

### Fig 1 — A/B Test: Score Distribution & Boxplot
![fig1](figures/fig1_ab_distribution.png)

### Fig 2 — Monthly Score Trend
![fig2](figures/fig2_score_trend.png)

### Fig 3 — Chapter Difficulty Heatmap
![fig3](figures/fig3_heatmap.png)

### Fig 4 — Retake Improvement Detail
![fig4](figures/fig4_retake_detail.png)

### Fig 5 — Mastery Rate by Group
![fig5](figures/fig5_mastery_rate.png)

---

## Tableau Dashboard

🔗 **[View Interactive Dashboard on Tableau Public](https://public.tableau.com/views/StudentPerformanceAnalytics_17773443084170/Dashboard1)**

---

## Setup

```bash
git clone https://github.com/yejuseol/student-performance-analytics
cd student-performance-analytics
pip install -r requirements.txt

python generate_data.py   # Creates math_tracker.db
python sql_analysis.py    # Runs queries + exports CSVs
python ab_testing.py      # Runs hypothesis tests + saves figures
```

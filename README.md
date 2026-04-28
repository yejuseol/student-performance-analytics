# Student Performance Analytics: Does a Retake Policy Improve Math Outcomes?

An end-to-end data analysis project using **SQL**, **Python (A/B Testing, Statistical Modeling)**, and **Tableau** to evaluate whether offering students a retake opportunity leads to statistically significant improvements in chapter test scores.

> **Context:** Data is based on real tutoring patterns from [Math Tracker](https://github.com/yejuseol/math-tracker) — a student progress dashboard built for a private math tutoring practice — supplemented with realistic synthetic data to enable robust statistical analysis.

---

## Key Findings

| Metric | Control (No Retake) | Treatment (Retake) |
|---|---|---|
| Mean Chapter Score | 71.9% | 77.9% |
| Mastery Rate (≥76%) | 41.9% | 57.0% |
| Sample Size | 86 chapter-scores | 86 chapter-scores |

- **t-test**: p = 0.0011 — statistically significant (α = 0.05)
- **Mann-Whitney U**: p = 0.0016 — confirmed by non-parametric test
- **Cohen's d**: 0.47 — small-to-medium practical effect
- **95% CI on mean difference**: [2.23, 9.85] percentage points

Retake access is associated with a **+6.0 pp improvement** in final chapter scores and a **+15.1 pp increase in mastery rate**.

---

## Project Structure

```
student-performance-analytics/
├── generate_data.py       # Synthetic data generation (SQLite)
├── sql_analysis.py        # SQL queries + CSV export for Tableau
├── ab_testing.py          # Hypothesis testing & visualizations
├── requirements.txt
├── math_tracker.db        # Generated SQLite database
├── figures/               # Output charts
│   ├── fig1_ab_distribution.png
│   ├── fig2_score_trend.png
│   ├── fig3_heatmap.png
│   └── fig4_retake_detail.png
└── tableau_exports/       # CSVs for Tableau dashboard
    ├── students.csv
    ├── chapters.csv
    ├── test_records.csv
    └── ab_best_scores.csv
```

---

## A/B Test Design

### Setup

The retake policy was introduced as a **natural experiment** within a private tutoring practice:

- **Control group** (12 students): Received instruction only. First attempt score = final score.
- **Treatment group** (12 students): Offered a retake if first attempt score was below 80%. Final score = highest attempt.

Groups are **balanced across all 6 subjects** (2 control + 2 treatment per course) to eliminate course difficulty as a confounding variable.

### Research Question

> Among students taking the same subject, does offering retake opportunities lead to statistically higher final chapter scores?

### Hypotheses

- **H₀:** μ_control ≥ μ_treatment (retakes have no effect or decrease scores)
- **H₁:** μ_control < μ_treatment (retakes improve final scores)

### Statistical Tests

| Test | Statistic | p-value | Decision |
|---|---|---|---|
| Two-sample t-test | t = −3.10 | 0.0011 | Reject H₀ |
| Mann-Whitney U | U = 2736.5 | 0.0016 | Reject H₀ |

Both parametric and non-parametric tests confirm the finding. The Shapiro-Wilk test indicated slight non-normality in both groups (p < 0.05), making the Mann-Whitney result particularly important as a robust confirmation.

---

## SQL Analysis Highlights

All analytical queries run against a local SQLite database. Key queries:

**Chapter-level average performance:**
```sql
SELECT c.subject, c.chapter_num, c.chapter_name,
       ROUND(AVG(r.pct), 1) AS avg_pct
FROM test_records r
JOIN chapters c ON r.chapter_id = c.chapter_id
WHERE r.attempt = 1
GROUP BY c.chapter_id
ORDER BY avg_pct ASC;
```

**Control vs Treatment — best score per student-chapter:**
```sql
SELECT s.retake_group,
       COUNT(DISTINCT s.student_id) AS students,
       ROUND(AVG(r.pct), 1)         AS avg_all_pct,
       ROUND(100.0 * SUM(CASE WHEN r.pct >= 76 THEN 1 ELSE 0 END)
             / COUNT(r.record_id), 1) AS mastery_rate_pct
FROM students s
JOIN test_records r ON s.student_id = r.student_id
GROUP BY s.retake_group;
```

**Retake improvement — first attempt vs retake score:**
```sql
SELECT f.pct AS first_pct, r2.pct AS retake_pct,
       ROUND(r2.pct - f.pct, 1) AS improvement
FROM test_records f
JOIN test_records r2
  ON f.student_id = r2.student_id
 AND f.chapter_id = r2.chapter_id
 AND f.attempt = 1 AND r2.attempt = 2;
```

---

## Visualizations

### Figure 1 — Score Distribution & Boxplot by Group
![A/B Distribution](figures/fig1_ab_distribution.png)

### Figure 2 — Monthly Score Trend
![Score Trend](figures/fig2_score_trend.png)

### Figure 3 — Chapter Difficulty Heatmap
![Heatmap](figures/fig3_heatmap.png)

### Figure 4 — Retake Improvement Analysis
![Retake Detail](figures/fig4_retake_detail.png)

---

## Tableau Dashboard

An interactive Tableau Public dashboard was built using the exported CSVs. It includes:

- Overall KPI summary cards (avg score, mastery rate, retake count)
- Control vs Treatment score comparison by subject
- Chapter difficulty heatmap with filter by subject
- Individual student score trends over time
- Retake improvement scatter plot

> 🔗 **[View Tableau Dashboard](https://public.tableau.com)** ← *(link to be added after publishing)*

---

## Data Note

Data is **synthetic but grounded in real tutoring patterns** from a private math tutoring practice spanning 4 years (2022–2026). Score distributions, chapter difficulty levels, and retake improvement rates were calibrated to match observed outcomes:

- AP exam students: typical first-attempt range 60–75%
- Algebra students: typical range 72–90%
- Retake improvement: mean ~10 points with realistic variance

Student names are pseudonymous. No personally identifiable information is included.

---

## Tech Stack

| Layer | Tool |
|---|---|
| Database | SQLite 3 |
| Data Generation | Python (NumPy, pandas) |
| SQL Analysis | SQLite + pandas |
| Statistical Testing | scipy.stats (t-test, Mann-Whitney U, Shapiro-Wilk) |
| Visualization | Matplotlib, Seaborn |
| BI Dashboard | Tableau Public |

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

"""
ab_testing.py
Hypothesis testing: Does offering retake opportunities lead to statistically
significant improvement in final chapter scores?

Design
------
Control   : 12 students — no retake policy (first attempt = final score)
Treatment : 13 students — retake offered when first attempt < 80%

Primary metric  : best chapter score (%) per student-chapter pair
Secondary metric: chapter mastery rate (score >= 76%)

Tests run
---------
1. Two-sample independent t-test (assumes approximate normality)
2. Mann-Whitney U test (non-parametric, robust to skew)
3. Effect size: Cohen's d
4. 95% Confidence interval on mean difference
"""

import sqlite3
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from scipy import stats
import warnings
warnings.filterwarnings("ignore")

# ── Load data ──────────────────────────────────────────────────────────────
conn = sqlite3.connect("math_tracker.db")
df = pd.read_sql_query("""
    SELECT s.student_id, s.name, s.subject, s.retake_group,
           c.chapter_id, c.chapter_name, c.difficulty,
           MAX(r.pct) AS best_pct,
           COUNT(r.record_id) AS attempts,
           CASE WHEN MAX(r.pct) >= 76 THEN 1 ELSE 0 END AS mastered
    FROM students s
    JOIN test_records r ON s.student_id = r.student_id
    JOIN chapters c     ON r.chapter_id = c.chapter_id
    GROUP BY s.student_id, c.chapter_id
""", conn)
conn.close()

control   = df[df["retake_group"] == "control"]["best_pct"].values
treatment = df[df["retake_group"] == "treatment"]["best_pct"].values

# ── Helper: Cohen's d ──────────────────────────────────────────────────────
def cohens_d(a, b):
    pooled_std = np.sqrt((np.std(a, ddof=1)**2 + np.std(b, ddof=1)**2) / 2)
    return (np.mean(b) - np.mean(a)) / pooled_std

# ── 1. Descriptive stats ───────────────────────────────────────────────────
print("=" * 60)
print("  DESCRIPTIVE STATISTICS")
print("=" * 60)
for label, arr in [("Control (no retake)", control), ("Treatment (retake)", treatment)]:
    print(f"\n{label}  (n={len(arr)})")
    print(f"  Mean  : {arr.mean():.2f}%")
    print(f"  Median: {np.median(arr):.2f}%")
    print(f"  Std   : {arr.std(ddof=1):.2f}%")
    print(f"  Min   : {arr.min():.2f}%   Max: {arr.max():.2f}%")

# ── 2. Normality check ─────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("  NORMALITY CHECK (Shapiro-Wilk)")
print("=" * 60)
for label, arr in [("Control", control), ("Treatment", treatment)]:
    stat, p = stats.shapiro(arr)
    verdict = "Normal (p >= 0.05)" if p >= 0.05 else "Non-normal (p < 0.05)"
    print(f"  {label}: W={stat:.4f}, p={p:.4f}  → {verdict}")

# ── 3. Two-sample t-test ───────────────────────────────────────────────────
print("\n" + "=" * 60)
print("  TWO-SAMPLE INDEPENDENT T-TEST")
print("=" * 60)
t_stat, t_p = stats.ttest_ind(control, treatment, alternative="less")
print(f"  H₀: μ_control >= μ_treatment  (retakes have no effect)")
print(f"  H₁: μ_control < μ_treatment   (retakes improve scores)")
print(f"  t-statistic : {t_stat:.4f}")
print(f"  p-value     : {t_p:.4f}")
print(f"  Conclusion  : {'Reject H₀ ✓ (p < 0.05)' if t_p < 0.05 else 'Fail to reject H₀'}")

# ── 4. Mann-Whitney U (non-parametric) ────────────────────────────────────
print("\n" + "=" * 60)
print("  MANN-WHITNEY U TEST (non-parametric)")
print("=" * 60)
u_stat, u_p = stats.mannwhitneyu(control, treatment, alternative="less")
print(f"  U-statistic : {u_stat:.1f}")
print(f"  p-value     : {u_p:.4f}")
print(f"  Conclusion  : {'Reject H₀ ✓ (p < 0.05)' if u_p < 0.05 else 'Fail to reject H₀'}")

# ── 5. Effect size ─────────────────────────────────────────────────────────
d = cohens_d(control, treatment)
magnitude = ("negligible" if abs(d) < 0.2 else
             "small"      if abs(d) < 0.5 else
             "medium"     if abs(d) < 0.8 else "large")
print("\n" + "=" * 60)
print("  EFFECT SIZE")
print("=" * 60)
print(f"  Cohen's d : {d:.4f}  ({magnitude} effect)")
print(f"  Mean diff : {treatment.mean() - control.mean():.2f} percentage points")

# ── 6. 95% Confidence interval on difference ──────────────────────────────
diff = treatment.mean() - control.mean()
se   = np.sqrt(np.var(control, ddof=1)/len(control) + np.var(treatment, ddof=1)/len(treatment))
ci_lo, ci_hi = diff - 1.96*se, diff + 1.96*se
print("\n" + "=" * 60)
print("  95% CONFIDENCE INTERVAL (mean difference: Treatment - Control)")
print("=" * 60)
print(f"  [{ci_lo:.2f}, {ci_hi:.2f}] percentage points")

# ── 7. Mastery rate comparison ─────────────────────────────────────────────
print("\n" + "=" * 60)
print("  MASTERY RATE (score >= 76%)")
print("=" * 60)
for group in ["control", "treatment"]:
    sub = df[df["retake_group"] == group]
    rate = sub["mastered"].mean() * 100
    print(f"  {group.capitalize():12s}: {rate:.1f}%")

# ── 8. Visualizations ─────────────────────────────────────────────────────
import os
os.makedirs("figures", exist_ok=True)

PALETTE = {"control": "#4C72B0", "treatment": "#DD8452"}
LABELS  = {"control": "Control (no retake)", "treatment": "Treatment (retake)"}

# Fig 1: Distribution comparison
fig, axes = plt.subplots(1, 2, figsize=(13, 5))
fig.suptitle("A/B Test: Impact of Retake Policy on Chapter Scores", fontsize=14, fontweight="bold")

ax = axes[0]
for group, color in PALETTE.items():
    data = df[df["retake_group"] == group]["best_pct"]
    ax.hist(data, bins=20, alpha=0.65, color=color, label=LABELS[group], edgecolor="white")
    ax.axvline(data.mean(), color=color, linestyle="--", linewidth=1.8)
ax.axvline(76, color="gray", linestyle=":", linewidth=1.5, label="Mastery threshold (76%)")
ax.set_xlabel("Best Chapter Score (%)", fontsize=11)
ax.set_ylabel("Frequency", fontsize=11)
ax.set_title("Score Distribution by Group", fontsize=12)
ax.legend(fontsize=9)

ax = axes[1]
for i, (group, color) in enumerate(PALETTE.items()):
    data = df[df["retake_group"] == group]["best_pct"]
    ax.boxplot(data, positions=[i], widths=0.5, patch_artist=True,
               boxprops=dict(facecolor=color, alpha=0.7),
               medianprops=dict(color="black", linewidth=2),
               whiskerprops=dict(linewidth=1.5),
               capprops=dict(linewidth=1.5),
               flierprops=dict(marker="o", markerfacecolor=color, markersize=4, alpha=0.5))

ax.set_xticks([0, 1])
ax.set_xticklabels([LABELS[g] for g in PALETTE], fontsize=9)
ax.set_ylabel("Best Chapter Score (%)", fontsize=11)
ax.set_title(f"Boxplot Comparison\n(t-test p={t_p:.4f}, Cohen's d={d:.2f})", fontsize=12)
ax.axhline(76, color="gray", linestyle=":", linewidth=1.5)

plt.tight_layout()
plt.savefig("figures/fig1_ab_distribution.png", dpi=150, bbox_inches="tight")
plt.close()
print("\nSaved: figures/fig1_ab_distribution.png")

# Fig 2: Score trends over time
conn2 = sqlite3.connect("math_tracker.db")
trend = pd.read_sql_query("""
    SELECT SUBSTR(r.test_date, 1, 7) AS month,
           s.retake_group,
           ROUND(AVG(r.pct), 2) AS avg_pct
    FROM test_records r
    JOIN students s ON r.student_id = s.student_id
    GROUP BY month, s.retake_group
    ORDER BY month
""", conn2)
conn2.close()

fig, ax = plt.subplots(figsize=(12, 5))
for group, color in PALETTE.items():
    sub = trend[trend["retake_group"] == group]
    ax.plot(sub["month"], sub["avg_pct"], marker="o", color=color,
            linewidth=2, markersize=6, label=LABELS[group])
ax.axhline(76, color="gray", linestyle=":", linewidth=1.5, label="Mastery threshold")
ax.set_xlabel("Month", fontsize=11)
ax.set_ylabel("Average Score (%)", fontsize=11)
ax.set_title("Monthly Score Trend: Control vs Treatment Group", fontsize=13, fontweight="bold")
ax.legend(fontsize=10)
ax.tick_params(axis="x", rotation=45)
plt.tight_layout()
plt.savefig("figures/fig2_score_trend.png", dpi=150, bbox_inches="tight")
plt.close()
print("Saved: figures/fig2_score_trend.png")

# Fig 3: Chapter-level heatmap (avg score by subject × chapter)
conn3 = sqlite3.connect("math_tracker.db")
heatmap_df = pd.read_sql_query("""
    SELECT c.subject, c.chapter_num,
           ROUND(AVG(r.pct), 1) AS avg_pct
    FROM test_records r
    JOIN chapters c ON r.chapter_id = c.chapter_id
    WHERE r.attempt = 1
    GROUP BY c.subject, c.chapter_num
""", conn3)
conn3.close()

pivot = heatmap_df.pivot(index="subject", columns="chapter_num", values="avg_pct")
fig, ax = plt.subplots(figsize=(12, 5))
sns.heatmap(pivot, annot=True, fmt=".1f", cmap="RdYlGn", vmin=55, vmax=95,
            linewidths=0.5, ax=ax, cbar_kws={"label": "Avg Score (%)"})
ax.set_title("Average First-Attempt Score by Subject & Chapter", fontsize=13, fontweight="bold")
ax.set_xlabel("Chapter Number", fontsize=11)
ax.set_ylabel("")
plt.tight_layout()
plt.savefig("figures/fig3_heatmap.png", dpi=150, bbox_inches="tight")
plt.close()
print("Saved: figures/fig3_heatmap.png")

# Fig 4: Retake improvement distribution
conn4 = sqlite3.connect("math_tracker.db")
retake_df = pd.read_sql_query("""
    SELECT f.pct AS first_pct, r2.pct AS retake_pct,
           (r2.pct - f.pct) AS improvement, c.subject
    FROM test_records f
    JOIN test_records r2
      ON f.student_id = r2.student_id AND f.chapter_id = r2.chapter_id
     AND f.attempt = 1 AND r2.attempt = 2
    JOIN chapters c ON f.chapter_id = c.chapter_id
""", conn4)
conn4.close()

fig, axes = plt.subplots(1, 2, figsize=(12, 5))
fig.suptitle("Retake Analysis (Treatment Group Only)", fontsize=13, fontweight="bold")

axes[0].hist(retake_df["improvement"], bins=20, color=PALETTE["treatment"],
             alpha=0.75, edgecolor="white")
axes[0].axvline(retake_df["improvement"].mean(), color="black",
                linestyle="--", linewidth=2,
                label=f"Mean = {retake_df['improvement'].mean():.1f}pts")
axes[0].set_xlabel("Score Improvement (retake − first attempt)", fontsize=11)
axes[0].set_ylabel("Frequency", fontsize=11)
axes[0].set_title("Distribution of Retake Improvement", fontsize=12)
axes[0].legend()

axes[1].scatter(retake_df["first_pct"], retake_df["retake_pct"],
                alpha=0.55, color=PALETTE["treatment"], edgecolors="white", s=40)
lo, hi = retake_df["first_pct"].min() - 2, 100
axes[1].plot([lo, hi], [lo, hi], "k--", linewidth=1.2, label="No change line")
axes[1].set_xlabel("First Attempt Score (%)", fontsize=11)
axes[1].set_ylabel("Retake Score (%)", fontsize=11)
axes[1].set_title("First Attempt vs Retake Score", fontsize=12)
axes[1].legend()

plt.tight_layout()
plt.savefig("figures/fig4_retake_detail.png", dpi=150, bbox_inches="tight")
plt.close()
print("Saved: figures/fig4_retake_detail.png")

print("\n✓ All analyses complete.")

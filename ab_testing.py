import sqlite3
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import os, warnings
warnings.filterwarnings("ignore")

conn = sqlite3.connect("math_tracker.db")

df_all = pd.read_sql_query("""
    SELECT s.student_id, s.name, s.subject, s.retake_group, s.ability_tier,
           c.chapter_id, c.chapter_name, c.difficulty,
           MIN(r.pct) AS first_pct,
           MAX(r.pct) AS best_pct,
           COUNT(r.record_id) AS attempts,
           CASE WHEN COUNT(r.record_id) > 1 THEN 1 ELSE 0 END AS did_retake,
           CASE WHEN MAX(r.pct) >= 76     THEN 1 ELSE 0 END AS mastered
    FROM students s
    JOIN test_records r ON s.student_id = r.student_id
    JOIN chapters c     ON r.chapter_id = c.chapter_id
    GROUP BY s.student_id, c.chapter_id
""", conn)

df_retake = pd.read_sql_query("""
    SELECT f.student_id, f.pct AS first_pct, r2.pct AS retake_pct,
           (r2.pct - f.pct) AS improvement, c.subject, c.difficulty
    FROM test_records f
    JOIN test_records r2
      ON f.student_id = r2.student_id AND f.chapter_id = r2.chapter_id
     AND f.attempt = 1 AND r2.attempt = 2
    JOIN chapters c ON f.chapter_id = c.chapter_id
""", conn)

conn.close()

PALETTE = {"control": "#4C72B0", "treatment": "#DD8452"}
LABELS  = {"control": "Control (no retake)", "treatment": "Treatment (retake)"}

# Primary subset: only chapters where first attempt < 80%
df_sub = df_all[df_all["first_pct"] < 80].copy()
ctrl = df_sub[df_sub["retake_group"] == "control"]["best_pct"].values
trt  = df_sub[df_sub["retake_group"] == "treatment"]["best_pct"].values


def cohens_d(a, b):
    pool = np.sqrt((np.std(a, ddof=1)**2 + np.std(b, ddof=1)**2) / 2)
    return (b.mean() - a.mean()) / pool


print("=" * 60)
print(f"  PRIMARY ANALYSIS  (first attempt < 80%)")
print(f"  control n={len(ctrl)}, treatment n={len(trt)}")
print("=" * 60)

for label, arr in [("Control", ctrl), ("Treatment", trt)]:
    print(f"\n  {label}: mean={arr.mean():.1f}%  median={np.median(arr):.1f}%  "
          f"std={arr.std(ddof=1):.1f}%")

# Normality
print("\n  Shapiro-Wilk:")
for label, arr in [("Control", ctrl), ("Treatment", trt)]:
    W, p = stats.shapiro(arr)
    print(f"    {label:12s}: p={p:.4f}  {'normal' if p >= 0.05 else 'non-normal'}")

# t-test
t, tp = stats.ttest_ind(ctrl, trt, alternative="less")
print(f"\n  t-test:      t={t:.4f}, p={tp:.4f}  "
      f"→ {'Reject H0 ✓' if tp < 0.05 else 'Fail to reject H0'}")

# Mann-Whitney
U, up = stats.mannwhitneyu(ctrl, trt, alternative="less")
print(f"  Mann-Whitney: U={U:.1f}, p={up:.4f}  "
      f"→ {'Reject H0 ✓' if up < 0.05 else 'Fail to reject H0'}")

# Effect size + CI
d    = cohens_d(ctrl, trt)
diff = trt.mean() - ctrl.mean()
se   = np.sqrt(np.var(ctrl, ddof=1)/len(ctrl) + np.var(trt, ddof=1)/len(trt))
ci_lo, ci_hi = diff - 1.96*se, diff + 1.96*se
mag = "negligible" if abs(d) < 0.2 else "small" if abs(d) < 0.5 else "medium" if abs(d) < 0.8 else "large"
print(f"  Cohen's d:    {d:.3f} ({mag})  |  mean diff: +{diff:.1f} pp")
print(f"  95% CI:       [{ci_lo:.1f}, {ci_hi:.1f}] pp")

# Mastery rate (full dataset)
print("\n  Mastery rate (score >= 76%, full dataset):")
for g in ["control", "treatment"]:
    r = df_all[df_all["retake_group"] == g]["mastered"].mean() * 100
    print(f"    {g.capitalize():12s}: {r:.1f}%")

# Paired: first vs retake (treatment only)
pt, pp = stats.ttest_rel(df_retake["first_pct"], df_retake["retake_pct"],
                          alternative="less")
print(f"\n  Paired t-test (retake group, first vs retake):")
print(f"    n={len(df_retake)}  first={df_retake['first_pct'].mean():.1f}%  "
      f"retake={df_retake['retake_pct'].mean():.1f}%  "
      f"improvement=+{df_retake['improvement'].mean():.1f}pp  p={pp:.4f}")

# ── Figures ────────────────────────────────────────────────────────────────
os.makedirs("figures", exist_ok=True)

# Fig 1 — distribution + boxplot (primary subset)
fig, axes = plt.subplots(1, 2, figsize=(13, 5))
fig.suptitle("A/B Test: Final Scores for Students Who Scored <80% on First Attempt",
             fontsize=13, fontweight="bold")

ax = axes[0]
for g, col in PALETTE.items():
    d_ = df_sub[df_sub["retake_group"] == g]["best_pct"]
    ax.hist(d_, bins=18, alpha=0.65, color=col, label=LABELS[g], edgecolor="white")
    ax.axvline(d_.mean(), color=col, linestyle="--", lw=2)
ax.axvline(76, color="gray", linestyle=":", lw=1.5, label="Mastery threshold (76%)")
ax.set_xlabel("Final Chapter Score (%)", fontsize=11)
ax.set_ylabel("Frequency", fontsize=11)
ax.set_title("Score Distribution", fontsize=11)
ax.legend(fontsize=9)

ax = axes[1]
for i, (g, col) in enumerate(PALETTE.items()):
    ax.boxplot([ctrl, trt][i], positions=[i], widths=0.45, patch_artist=True,
               boxprops=dict(facecolor=col, alpha=0.7),
               medianprops=dict(color="black", lw=2),
               whiskerprops=dict(lw=1.5), capprops=dict(lw=1.5),
               flierprops=dict(marker="o", markerfacecolor=col, ms=4, alpha=0.5))
ax.set_xticks([0, 1])
ax.set_xticklabels([LABELS[g] for g in PALETTE], fontsize=9)
ax.set_ylabel("Final Score (%)", fontsize=11)
ax.set_title(f"Boxplot  |  t-test p={tp:.4f}, Cohen's d={d:.2f}", fontsize=11)
ax.axhline(76, color="gray", linestyle=":", lw=1.5)
plt.tight_layout()
plt.savefig("figures/fig1_ab_distribution.png", dpi=150, bbox_inches="tight")
plt.close()

# Fig 2 — monthly score trend
conn2 = sqlite3.connect("math_tracker.db")
trend = pd.read_sql_query("""
    SELECT SUBSTR(r.test_date, 1, 7) AS month, s.retake_group,
           ROUND(AVG(r.pct), 2) AS avg_pct
    FROM test_records r JOIN students s ON r.student_id = s.student_id
    GROUP BY month, s.retake_group ORDER BY month
""", conn2)
conn2.close()

fig, ax = plt.subplots(figsize=(12, 5))
for g, col in PALETTE.items():
    sub = trend[trend["retake_group"] == g]
    ax.plot(sub["month"], sub["avg_pct"], marker="o", color=col,
            lw=2, ms=6, label=LABELS[g])
ax.axhline(76, color="gray", linestyle=":", lw=1.5, label="Mastery threshold")
ax.set_xlabel("Month", fontsize=11)
ax.set_ylabel("Average Score (%)", fontsize=11)
ax.set_title("Monthly Score Trend — Control vs Treatment", fontsize=13, fontweight="bold")
ax.legend(fontsize=10)
ax.tick_params(axis="x", rotation=45)
plt.tight_layout()
plt.savefig("figures/fig2_score_trend.png", dpi=150, bbox_inches="tight")
plt.close()

# Fig 3 — chapter difficulty heatmap (first attempts only)
conn3 = sqlite3.connect("math_tracker.db")
hm = pd.read_sql_query("""
    SELECT c.subject, c.chapter_num, ROUND(AVG(r.pct), 1) AS avg_pct
    FROM test_records r JOIN chapters c ON r.chapter_id = c.chapter_id
    WHERE r.attempt = 1
    GROUP BY c.subject, c.chapter_num
""", conn3)
conn3.close()

pivot = hm.pivot(index="subject", columns="chapter_num", values="avg_pct")
fig, ax = plt.subplots(figsize=(12, 5))
sns.heatmap(pivot, annot=True, fmt=".1f", cmap="RdYlGn", vmin=52, vmax=96,
            linewidths=0.5, ax=ax, cbar_kws={"label": "Avg First-Attempt Score (%)"})
ax.set_title("Average First-Attempt Score by Subject & Chapter",
             fontsize=13, fontweight="bold")
ax.set_xlabel("Chapter Number", fontsize=11)
ax.set_ylabel("")
plt.tight_layout()
plt.savefig("figures/fig3_heatmap.png", dpi=150, bbox_inches="tight")
plt.close()

# Fig 4 — retake improvement (treatment group only)
fig, axes = plt.subplots(1, 2, figsize=(12, 5))
fig.suptitle("Retake Analysis (Treatment Group Only)", fontsize=13, fontweight="bold")

imp_mean = df_retake["improvement"].mean()
axes[0].hist(df_retake["improvement"], bins=18, color=PALETTE["treatment"],
             alpha=0.75, edgecolor="white")
axes[0].axvline(imp_mean, color="black", linestyle="--", lw=2,
                label=f"Mean = +{imp_mean:.1f} pts")
axes[0].set_xlabel("Score Improvement (retake − first attempt, pp)", fontsize=11)
axes[0].set_ylabel("Frequency", fontsize=11)
axes[0].set_title("Distribution of Retake Improvement", fontsize=12)
axes[0].legend()

axes[1].scatter(df_retake["first_pct"], df_retake["retake_pct"],
                alpha=0.55, color=PALETTE["treatment"], edgecolors="white", s=45)
lo = df_retake["first_pct"].min() - 2
axes[1].plot([lo, 100], [lo, 100], "k--", lw=1.2, label="No-change line")
axes[1].set_xlabel("First Attempt (%)", fontsize=11)
axes[1].set_ylabel("Retake Score (%)", fontsize=11)
axes[1].set_title("First Attempt vs Retake Score", fontsize=12)
axes[1].legend()
plt.tight_layout()
plt.savefig("figures/fig4_retake_detail.png", dpi=150, bbox_inches="tight")
plt.close()

# Fig 5 — mastery rate bar chart
fig, ax = plt.subplots(figsize=(7, 4))
mrates = df_all.groupby("retake_group")["mastered"].mean() * 100
colors = [PALETTE[g] for g in mrates.index]
bars = ax.bar([LABELS[g] for g in mrates.index], mrates.values,
              color=colors, width=0.45, edgecolor="white")
for bar, val in zip(bars, mrates.values):
    ax.text(bar.get_x() + bar.get_width() / 2, val + 0.8,
            f"{val:.1f}%", ha="center", va="bottom",
            fontsize=12, fontweight="bold")
ax.set_ylabel("Chapter Mastery Rate (%)", fontsize=11)
ax.set_title("Mastery Rate (score ≥ 76%) by Group", fontsize=13, fontweight="bold")
ax.set_ylim(0, 75)
ax.axhline(76, color="gray", linestyle=":", lw=1.5)
plt.tight_layout()
plt.savefig("figures/fig5_mastery_rate.png", dpi=150, bbox_inches="tight")
plt.close()

print("\n5 figures saved to figures/")

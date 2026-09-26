"""Step 3 - Charts. Colourblind-safe categorical slots, one axis per chart, labels in ink."""
import pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
SURFACE, INK, INK2, MUTED = "#fcfcfb", "#0b0b0b", "#52514e", "#898781"
GRID, BASELINE = "#e1e0d9", "#c3c2b7"
plt.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Segoe UI", "DejaVu Sans"],
                     "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "axes.edgecolor": BASELINE,
                     "axes.labelcolor": INK2, "text.color": INK, "xtick.color": MUTED, "ytick.color": MUTED,
                     "axes.titlesize": 13, "axes.titleweight": "bold", "font.size": 10})


def style(ax, xgrid=False):
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    ax.grid(axis="x" if xgrid else "y", color=GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)


def titles(ax, t, sub):
    ax.set_title(t, loc="left", pad=32)
    ax.text(0, 1.03, sub, transform=ax.transAxes, color=MUTED, fontsize=9, va="bottom")


def save(fig, name):
    fig.savefig(OUT / name, dpi=150, bbox_inches="tight", facecolor=SURFACE)
    plt.close(fig)
    print("wrote", name)


# 1. Half of viewing is licensed
mix = pd.read_csv(OUT / "viewing_mix_by_segment.csv", index_col=0)
fig, ax = plt.subplots(figsize=(9, 4.8))
x = np.arange(len(mix))
b1 = ax.bar(x, mix["Licensed"], color=BLUE, width=0.62, zorder=3)
b2 = ax.bar(x, mix["Catalog original"], bottom=mix["Licensed"], color=AQUA, width=0.62, zorder=3,
            edgecolor=SURFACE, linewidth=1.5)
b3 = ax.bar(x, mix["New original"], bottom=mix["Licensed"] + mix["Catalog original"], color=ORANGE,
            width=0.62, zorder=3, edgecolor=SURFACE, linewidth=1.5)
style(ax)
ax.set_xticks(x)
ax.set_xticklabels([p[:4] + " " + p[4:] for p in mix.index], color=INK2)
ax.set_ylim(0, 100)
ax.set_ylabel("Share of Netflix hours viewed (%)")
titles(ax, "Half of what Netflix members watch is licensed, not original",
       "Share of hours by title type. Original = Netflix-premiered (release date listed); new = launched that half.")
for i, (l, c, n) in enumerate(zip(mix["Licensed"], mix["Catalog original"], mix["New original"])):
    ax.text(i, l / 2, "{:.0f}%".format(l), ha="center", va="center", color="white", fontweight="bold")
    ax.text(i, l + c / 2, "{:.0f}%".format(c), ha="center", va="center", color="white", fontweight="bold")
    ax.text(i, l + c + n / 2, "{:.0f}%".format(n), ha="center", va="center", color="white", fontweight="bold")
ax.legend([b1, b2, b3], ["Licensed", "Catalog original", "New original"], frameon=False,
          loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=3, labelcolor=INK2)
save(fig, "01_viewing_mix.png")

# 2. Launch decay
dec = pd.read_csv(OUT / "launch_decay.csv").set_index("type")
fig, ax = plt.subplots(figsize=(8.5, 4.6))
stages = ["Launch half", "Next half", "Two halves later"]
vals = [100, dec.loc["All", "median_retained_next_half"] * 100, dec.loc["All", "median_retained_two_halves"] * 100]
ax.plot(stages, vals, marker="o", markersize=9, linewidth=2.4, color=ORANGE, zorder=3)
for i, v in enumerate(vals):
    ax.text(i, v + 5, "{:.0f}".format(v) if i == 0 else "{:.1f}".format(v), ha="center",
            color=INK, fontweight="bold", fontsize=11)
style(ax)
ax.set_ylim(0, 115)
ax.set_ylabel("Daily viewing, launch half = 100")
titles(ax, "A new original loses over 90% of its daily viewing after launch",
       "Median of {:,} Netflix originals, hours per day on service. Shows keep {:.1f}, movies {:.1f} in the next half.".format(
           int(dec.loc["All", "titles"]), dec.loc["Show", "median_retained_next_half"] * 100,
           dec.loc["Movie", "median_retained_next_half"] * 100))
ax.tick_params(axis="x", labelcolor=INK2)
save(fig, "02_launch_decay.png")

# 3. Retention by segment
ret = pd.read_csv(OUT / "retention_by_segment.csv").set_index("segment").loc[
    ["Catalog original", "Licensed", "New original"]]
fig, ax = plt.subplots(figsize=(8.5, 4.4))
cols = [AQUA, BLUE, ORANGE]
ax.barh(ret.index[::-1], ret["avg_hours_kept_pct"][::-1], color=cols[::-1], height=0.55, zorder=3)
style(ax, xgrid=True)
ax.set_xlim(0, 100)
ax.set_xlabel("Hours kept into the next half (%, average of 5 transitions)")
titles(ax, "Library titles hold ~80% of their audience; new originals keep 29%",
       "Titles that fall below Netflix's 50,000-hour reporting line are counted at zero")
for i, seg in enumerate(ret.index[::-1]):
    v = ret.loc[seg, "avg_hours_kept_pct"]
    ax.text(v + 1, i, "{:.0f}%   ({:.0f}% of titles fall off the list)".format(
        v, ret.loc[seg, "avg_dropped_pct"]),
            va="center", color=INK, fontsize=9.5)
ax.tick_params(axis="y", labelcolor=INK2)
save(fig, "03_retention_by_segment.png")

# 4. Concentration (latest half)
panel = pd.read_parquet(ROOT / "data" / "processed" / "panel.parquet")
latest = panel[(panel["period"] == "2026H1") & (panel["hours"] > 0)]
h = np.sort(latest["hours"].to_numpy())[::-1]
cum = np.cumsum(h) / h.sum() * 100
xs = np.arange(1, len(h) + 1) / len(h) * 100
conc = pd.read_csv(OUT / "concentration.csv").set_index("period").loc["2026H1"]
fig, ax = plt.subplots(figsize=(8.5, 4.6))
ax.plot(xs, cum, color=BLUE, linewidth=2.2, zorder=3)
style(ax)
ax.set_xlim(0, 100)
ax.set_ylim(0, 102)
ax.set_xlabel("Share of titles, ranked from most to least watched (%)")
ax.set_ylabel("Cumulative share of hours (%)")
k = int(conc["titles_for_half_of_hours"])
ax.axhline(50, color=BASELINE, linewidth=1, linestyle="--")
ax.annotate("{:,} titles ({:.1f}% of the list)\ndeliver half of all viewing".format(k, k / len(h) * 100),
            xy=(k / len(h) * 100, 50), xytext=(20, 38), fontsize=10, color=INK, fontweight="bold",
            arrowprops=dict(arrowstyle="->", color=INK2))
titles(ax, "A few hundred titles carry the service",
       "H1 2026, {:,} titles. Top 1% = {:.0f}% of hours; top 10% = {:.0f}%.".format(
           len(h), conc["top1pct_share"], conc["top10pct_share"]))
save(fig, "04_concentration.png")

# 5. Forecast accuracy
m = pd.read_csv(OUT / "forecast_metrics.csv")
big = pd.read_csv(OUT / "forecast_metrics_licensed_1m.csv").iloc[0]
fig, ax = plt.subplots(figsize=(8.5, 4.2))
labels = ["Naive: flat retention", "Naive: retention by title type", "Gradient boosting model"]
vals = [m.loc[m["model"].str.startswith("Naive: flat"), "median_abs_pct_error"].iloc[0],
        m.loc[m["model"].str.startswith("Naive: segment"), "median_abs_pct_error"].iloc[0],
        m.loc[m["model"].str.startswith("Gradient"), "median_abs_pct_error"].iloc[0]]
ax.barh(labels, vals, color=[BASELINE, MUTED, BLUE], height=0.55, zorder=3)
style(ax, xgrid=True)
ax.set_xlim(0, 32)
ax.set_xlabel("Median absolute % error, next-half hours (held-out H1 2026)")
titles(ax, "The model beats a strong naive baseline, modestly",
       "On licensed titles with 1M+ hours, median error falls from {:.0f}% to {:.0f}%".format(
           big["segment_naive_mdape"], big["model_mdape"]))
for i, v in enumerate(vals):
    ax.text(v + 0.4, i, "{:.1f}%".format(v), va="center", color=INK, fontweight="bold")
ax.tick_params(axis="y", labelcolor=INK2)
save(fig, "05_forecast_accuracy.png")

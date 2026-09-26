"""
Step 2 - What is a title actually worth to a streaming catalog?

Five questions, each answered from the panel built in build_panel.py:

  1. How concentrated is viewing?            (a few hits, or a deep catalog?)
  2. How much viewing comes from licensed titles vs Netflix originals?
  3. How fast does a new original fade after launch?
  4. How well does each kind of title hold its audience half over half?
  5. Can next-half viewing be predicted well enough to price a licensing deal,
     and does a model beat the naive "same as last time" rule?

REPORTING THRESHOLD
Netflix only lists titles with 50,000+ hours in a half. A title that disappears from
the next report fell below that line - it did not vanish. Retention is therefore
computed with dropped titles counted at zero (a conservative lower bound), and the
share of titles that drop out is reported alongside every retention figure.
"""
import pathlib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import r2_score

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
PERIODS = ["2023H2", "2024H1", "2024H2", "2025H1", "2025H2", "2026H1"]

panel = pd.read_parquet(ROOT / "data" / "processed" / "panel.parquet")
# a handful of rows carry no usable hours figure; they cannot enter log-scale work
N_NO_HOURS = int((panel["hours"] <= 0).sum() + panel["hours"].isna().sum())
panel = panel[panel["hours"] > 0].copy()
panel["key"] = panel["title"] + " || " + panel["type"]


def segment(r):
    if not r["original"]:
        return "Licensed"
    return "New original" if r["launch_half"] else "Catalog original"


panel["segment"] = panel.apply(segment, axis=1)

# ---------------------------------------------------------------------------
# 1. Concentration
# ---------------------------------------------------------------------------
rows = []
for p, g in panel.groupby("period"):
    h = np.sort(g["hours"].to_numpy())[::-1]
    tot = h.sum()
    n = len(h)
    cum = np.cumsum(h) / tot
    lorenz = np.cumsum(np.sort(h)) / tot
    gini = 1 - 2 * lorenz.sum() / n + 1 / n
    rows.append({"period": p, "titles": n,
                 "top1pct_share": h[: max(1, n // 100)].sum() / tot * 100,
                 "top10pct_share": h[: max(1, n // 10)].sum() / tot * 100,
                 "titles_for_half_of_hours": int(np.searchsorted(cum, 0.5) + 1),
                 "gini": gini})
conc = pd.DataFrame(rows)
conc.round(3).to_csv(OUT / "concentration.csv", index=False)

# ---------------------------------------------------------------------------
# 2. Licensed vs original share of viewing
# ---------------------------------------------------------------------------
mix = (panel.groupby(["period", "segment"])["hours"].sum()
            .unstack(fill_value=0))
mix = mix.div(mix.sum(axis=1), axis=0) * 100
mix = mix.reindex(PERIODS)
mix.round(2).to_csv(OUT / "viewing_mix_by_segment.csv")
lic_title_share = panel.groupby("period")["original"].apply(lambda s: (~s).mean() * 100).reindex(PERIODS)

# ---------------------------------------------------------------------------
# 3. Launch decay for new originals, in hours per day on service
# ---------------------------------------------------------------------------
wide_hpd = panel.pivot_table(index="key", columns="period_idx", values="hours_per_day", aggfunc="first")
launch = panel[panel["launch_half"]][["key", "type", "period_idx", "hours_per_day", "days_on_service"]]
# at least 30 days of launch-half exposure, so a 3-day launch window does not
# masquerade as a huge daily rate; and two full halves observable afterwards
launch = launch[(launch["days_on_service"] >= 30) & (launch["period_idx"] <= len(PERIODS) - 3)]
dec_rows = []
for _, r in launch.iterrows():
    l0 = r["hours_per_day"]
    nxt = [wide_hpd.at[r["key"], r["period_idx"] + k] if (r["period_idx"] + k) in wide_hpd.columns else np.nan
           for k in (1, 2)]
    nxt = [0.0 if pd.isna(v) else v for v in nxt]      # dropped below threshold -> 0
    dec_rows.append({"type": r["type"], "l0": l0, "l1": nxt[0], "l2": nxt[1]})
dec = pd.DataFrame(dec_rows)
dec["ret1"] = dec["l1"] / dec["l0"]
dec["ret2"] = dec["l2"] / dec["l0"]
decay = dec.groupby("type").agg(titles=("l0", "size"),
                                median_retained_next_half=("ret1", "median"),
                                median_retained_two_halves=("ret2", "median"),
                                dropped_next_half_pct=("l1", lambda s: (s == 0).mean() * 100)).reset_index()
allrow = pd.DataFrame([{"type": "All", "titles": len(dec),
                        "median_retained_next_half": dec["ret1"].median(),
                        "median_retained_two_halves": dec["ret2"].median(),
                        "dropped_next_half_pct": (dec["l1"] == 0).mean() * 100}])
decay = pd.concat([decay, allrow], ignore_index=True)
decay.round(4).to_csv(OUT / "launch_decay.csv", index=False)

# ---------------------------------------------------------------------------
# 4. Half-over-half retention by segment (aggregate hours kept)
# ---------------------------------------------------------------------------
wide_h = panel.pivot_table(index="key", columns="period_idx", values="hours", aggfunc="first")
seg_at = panel.pivot_table(index="key", columns="period_idx", values="segment", aggfunc="first")
ret_rows = []
for t in range(len(PERIODS) - 1):
    for seg in ["Licensed", "Catalog original", "New original"]:
        keys = seg_at.index[seg_at[t] == seg]
        now = wide_h.loc[keys, t]
        nxt = wide_h.loc[keys, t + 1].fillna(0)
        ret_rows.append({"from": PERIODS[t], "segment": seg, "titles": len(keys),
                         "hours_kept_pct": nxt.sum() / now.sum() * 100,
                         "dropped_pct": (nxt == 0).mean() * 100})
ret = pd.DataFrame(ret_rows)
ret.round(3).to_csv(OUT / "retention_by_segment_period.csv", index=False)
ret_sum = ret.groupby("segment").agg(avg_hours_kept_pct=("hours_kept_pct", "mean"),
                                     avg_dropped_pct=("dropped_pct", "mean")).reset_index()
ret_sum.round(2).to_csv(OUT / "retention_by_segment.csv", index=False)

# ---------------------------------------------------------------------------
# 5. Predicting next-half hours (the "license or pass" input)
#
# A licensing team pricing a deal already knows the title will be on the service:
# that is what they are buying. So the forecast is conditional on the title still
# being listed next half. Whether a title leaves (license expiry, removal) is not in
# this data and is reported separately as a dropout rate, not hidden inside the error.
# ---------------------------------------------------------------------------
feat_rows = []
for t in range(1, len(PERIODS) - 1):          # need t-1 for the lag and t+1 for the target
    cur = panel[panel["period_idx"] == t].set_index("key")
    f = pd.DataFrame({
        "log_hours": np.log10(cur["hours"]),
        "log_hours_lag": np.log10(wide_h[t - 1].reindex(cur.index)),   # NaN if new last half
        "is_show": (cur["type"] == "Show").astype(int),
        "original": cur["original"].astype(int),
        "global": cur["global"].astype(int),
        "launch_half": cur["launch_half"].astype(int),
        "age_years": cur["age_years"],
        "log_runtime": np.log10(cur["runtime_h"].clip(lower=0.1)),
        "segment": cur["segment"],
        "t": t,
        "y_hours": wide_h[t + 1].reindex(cur.index),
        "hours_now": cur["hours"],
    })
    f["growth"] = f["log_hours"] - f["log_hours_lag"]
    feat_rows.append(f)
feats = pd.concat(feat_rows)
feats["stays"] = feats["y_hours"].notna() & (feats["y_hours"] > 0)
dropout = feats.groupby("segment")["stays"].apply(lambda s: (1 - s.mean()) * 100).rename("dropout_pct")

stay = feats[feats["stays"]].copy()
stay["y"] = np.log10(stay["y_hours"])
X_cols = ["log_hours", "log_hours_lag", "growth", "is_show", "original", "global",
          "launch_half", "age_years", "log_runtime"]
train = stay[stay["t"] <= len(PERIODS) - 3]
test = stay[stay["t"] == len(PERIODS) - 2]           # 2025H2 -> 2026H1, fully held out

# absolute-error loss on log hours = a median forecast, matching the error metric
model = HistGradientBoostingRegressor(loss="absolute_error", max_iter=500, learning_rate=0.05,
                                      max_leaf_nodes=31, random_state=7)
model.fit(train[X_cols], train["y"])
pred = model.predict(test[X_cols])

# Two baselines. The second is the one worth beating: it already knows that new
# originals fade and library titles hold, which is most of the signal.
flat = test["log_hours"] + np.median(train["y"] - train["log_hours"])
seg_ret = (train["y"] - train["log_hours"]).groupby(train["segment"]).median()
seg_naive = test["log_hours"] + test["segment"].map(seg_ret)


def mdape(y_log, p_log):
    y_log, p_log = np.asarray(y_log), np.asarray(p_log)
    return float(np.median(np.abs(10 ** p_log - 10 ** y_log) / 10 ** y_log) * 100)


def within(y_log, p_log, pct):
    y_log, p_log = np.asarray(y_log), np.asarray(p_log)
    return float((np.abs(10 ** p_log - 10 ** y_log) / 10 ** y_log <= pct / 100).mean() * 100)


metrics = pd.DataFrame([
    {"model": "Gradient boosting (median loss)", "r2_log": r2_score(test["y"], pred),
     "median_abs_pct_error": mdape(test["y"], pred), "within_25pct": within(test["y"], pred, 25)},
    {"model": "Naive: segment-specific retention", "r2_log": r2_score(test["y"], seg_naive),
     "median_abs_pct_error": mdape(test["y"], seg_naive), "within_25pct": within(test["y"], seg_naive, 25)},
    {"model": "Naive: flat retention", "r2_log": r2_score(test["y"], flat),
     "median_abs_pct_error": mdape(test["y"], flat), "within_25pct": within(test["y"], flat, 25)},
])
metrics["test_titles"] = len(test)
metrics["train_titles"] = len(train)
metrics.round(4).to_csv(OUT / "forecast_metrics.csv", index=False)
dropout.round(2).to_csv(OUT / "dropout_by_segment.csv")

# accuracy on what a licensing team would actually price: licensed titles with 1M+ hours
big_lic = ((test["original"] == 0) & (test["hours_now"] >= 1_000_000)).to_numpy()
big = pd.DataFrame([{
    "segment": "Licensed titles with 1M+ hours",
    "titles": int(big_lic.sum()),
    "model_mdape": mdape(test["y"][big_lic], pred[big_lic]),
    "segment_naive_mdape": mdape(test["y"][big_lic], seg_naive[big_lic]),
    "model_within_25pct": within(test["y"][big_lic], pred[big_lic], 25),
    "segment_naive_within_25pct": within(test["y"][big_lic], seg_naive[big_lic], 25),
}])
big.round(3).to_csv(OUT / "forecast_metrics_licensed_1m.csv", index=False)

# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
pd.set_option("display.width", 200)
print("rows excluded for having no usable hours figure:", N_NO_HOURS)
print("=" * 90)
print("1. CONCENTRATION")
print("=" * 90)
print(conc.round(3).to_string(index=False))
print()
print("=" * 90)
print("2. SHARE OF VIEWING BY SEGMENT (%)   and share of listed titles that are licensed")
print("=" * 90)
print(mix.round(1).to_string())
print("licensed share of titles:", lic_title_share.round(1).to_dict())
print()
print("=" * 90)
print("3. LAUNCH DECAY - new originals, hours per day on service, relative to launch half")
print("=" * 90)
print(decay.round(3).to_string(index=False))
print()
print("=" * 90)
print("4. HOURS KEPT HALF-OVER-HALF, by segment (avg of 5 transitions)")
print("=" * 90)
print(ret_sum.round(1).to_string(index=False))
print()
print("=" * 90)
print("5. FORECASTING NEXT-HALF HOURS, conditional on the title staying listed")
print("   train: 2024H1-2025H1 -> next half; test: 2025H2 -> 2026H1 (held out)")
print("=" * 90)
print(metrics.round(3).to_string(index=False))
print()
print(big.round(1).to_string(index=False))
print()
print("share of titles that fall below the 50,000-hour line next half:")
print(dropout.round(1).to_string())

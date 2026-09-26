"""
Step 1 - Stack Netflix's semiannual engagement reports into one title-by-period panel.

Source: Netflix "What We Watched" reports, H2 2023 through H1 2026 (six half-years,
every title watched 50,000+ hours in the period). H1 2023 is kept only for totals:
it is a single combined sheet with no show/film split, runtime, or views.

ORIGINAL VS LICENSED
Netflix fills "Release Date" for titles it premiered (its own originals and branded
releases) and leaves it blank for licensed library titles. That makes it a usable,
transparent proxy for original vs licensed. It is a proxy, not a label: some
co-productions and regional exclusives will sit on the wrong side of the line.
"""
import pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW, OUT = ROOT / "data" / "raw", ROOT / "data" / "processed"
PERIODS = ["2023H2", "2024H1", "2024H2", "2025H1", "2025H2", "2026H1"]
PERIOD_START = {p: pd.Timestamp("{}-{}-01".format(p[:4], "01" if p.endswith("H1") else "07"))
                for p in PERIODS + ["2023H1"]}


def period_end(p):
    return PERIOD_START[p] + pd.offsets.MonthEnd(6)


def read_sheet(path, sheet):
    df = pd.read_excel(path, sheet_name=sheet, header=5)
    return df.loc[:, [c for c in df.columns if not str(c).startswith("Unnamed")]]


def runtime_hours(x):
    """'7:47' -> 7.78 hours. Netflix footnotes some runtimes with '*' (e.g. '0:44*');
    the asterisk is dropped. Excel sometimes stores the value as a time object.
    Anything else ('*' alone, blank) -> NaN."""
    if hasattr(x, "hour") and hasattr(x, "minute"):
        return x.hour + x.minute / 60
    if not isinstance(x, str):
        return np.nan
    x = x.replace("*", "").strip()
    if ":" not in x:
        return np.nan
    h, m = x.split(":")[:2]
    return int(h) + int(m) / 60 if h.isdigit() and m.isdigit() else np.nan


rows = []
for p in PERIODS:
    path = RAW / "netflix_engagement_{}.xlsx".format(p)
    for sheet in pd.ExcelFile(path).sheet_names:
        df = read_sheet(path, sheet)
        df["type"] = "Show" if sheet in ("TV", "Shows") else "Movie"
        df["period"] = p
        rows.append(df)
panel = pd.concat(rows, ignore_index=True)
panel = panel.rename(columns={"Title": "title", "Available Globally?": "global",
                              "Release Date": "release_date", "Hours Viewed": "hours",
                              "Runtime": "runtime", "Views": "views"})
panel["title"] = panel["title"].astype(str).str.strip()
# Netflix marks some views and runtimes with '*' (not calculable); those become NaN
# rather than zero, so they drop out of view-based metrics instead of distorting them.
for col in ["hours", "views"]:
    panel[col] = pd.to_numeric(panel[col], errors="coerce")
panel["global"] = panel["global"].eq("Yes")
panel["release_date"] = pd.to_datetime(panel["release_date"], errors="coerce")
panel["original"] = panel["release_date"].notna()
panel["runtime_h"] = panel["runtime"].map(runtime_hours)
panel["period_start"] = panel["period"].map(PERIOD_START)
panel["period_end"] = panel["period"].map(period_end)
panel["period_idx"] = panel["period"].map({p: i for i, p in enumerate(PERIODS)})

# Days the title was actually available in this half: a title released on 20 June
# only had 10 days of its launch half. Comparing raw hours across halves would make
# every launch look weak, so decay is measured in hours per day on service.
start = np.maximum(panel["period_start"], panel["release_date"].fillna(panel["period_start"]))
panel["days_on_service"] = (panel["period_end"] - start).dt.days + 1
panel.loc[panel["days_on_service"] <= 0, "days_on_service"] = np.nan
panel["hours_per_day"] = panel["hours"] / panel["days_on_service"]
panel["launch_half"] = (panel["release_date"] >= panel["period_start"]) & \
                       (panel["release_date"] <= panel["period_end"])
panel["age_years"] = (panel["period_end"] - panel["release_date"]).dt.days / 365.25

# Duplicate titles within a period and type (rare re-listings) are summed.
dups = panel.duplicated(["title", "type", "period"], keep=False).sum()
panel = (panel.sort_values("hours", ascending=False)
              .groupby(["title", "type", "period"], as_index=False)
              .agg({"global": "first", "release_date": "first", "original": "first",
                    "hours": "sum", "views": lambda s: s.sum(min_count=1), "runtime_h": "first",
                    "period_start": "first", "period_end": "first", "period_idx": "first",
                    "days_on_service": "first", "hours_per_day": "first",
                    "launch_half": "first", "age_years": "first"}))

panel.to_parquet(OUT / "panel.parquet", index=False)

# Totals, including H1 2023 for the headline series
tot = panel.groupby("period")["hours"].sum() / 1e9
h1 = read_sheet(RAW / "netflix_engagement_2023H1.xlsx", "Engagement")["Hours Viewed"].sum() / 1e9
totals = pd.concat([pd.Series({"2023H1": h1}), tot]).rename("hours_billions").reset_index()
totals.columns = ["period", "hours_billions"]
totals.to_csv(ROOT / "output" / "total_hours_by_period.csv", index=False)

print("title-period rows     {:,}".format(len(panel)))
print("unique titles         {:,}".format(panel[["title", "type"]].drop_duplicates().shape[0]))
print("duplicate rows merged {:,}".format(int(dups)))
print("periods               {}".format(", ".join(PERIODS)))
print()
print(panel.groupby(["period", "type"]).agg(titles=("title", "size"),
                                           hours_b=("hours", lambda s: round(s.sum() / 1e9, 1)),
                                           pct_original=("original", lambda s: round(s.mean() * 100, 1)))
      .to_string())
print()
print("total hours (billions):")
print(totals.round(1).to_string(index=False))

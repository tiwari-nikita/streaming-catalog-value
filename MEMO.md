# What is a title worth to a streaming catalog?

**Analysis memo · September 2026**
**Source:** Netflix *What We Watched* engagement reports, H2 2023 – H1 2026 · 97,736 title-period observations covering 28,694 titles

---

## Bottom line

**Half of everything Netflix members watch is licensed, not original.** In every half-year from H2 2023 to H1 2026, licensed titles supplied 47–51% of hours viewed. New originals, the titles that dominate headlines and marketing budgets, supplied 18–20%.

The two behave completely differently. **A new original loses over 90% of its daily viewing once its launch half ends**, and keeps only 29% of its hours into the following half. Library titles, licensed or original, keep about 80%. Originals win the launch window; the library holds the audience between launches.

## What the data shows

**Viewing is concentrated but not winner-take-all.** Fewer than 5% of listed titles, roughly 715–745 of about 16,000, deliver half of all viewing in each half. The top 1% of titles account for 24–26% of hours.

**Launches are steep and short.** Across 1,368 Netflix originals, median daily viewing in the half after launch is 8.4% of launch-half levels, and 5.4% two halves out. Shows (7.9%) and movies (9.5%) decay almost identically.

**Once past launch, an original behaves like library.** Catalog originals keep 82% of their hours half over half, and licensed titles keep 80%. The cliff belongs to the launch, not to originals as a category.

**Licensed titles churn off the service.** 22% of licensed titles fall below Netflix's 50,000-hour reporting line from one half to the next, 3.6x the rate for catalog originals (6%). The data can't separate license expiry from simple low viewing, but expiry is the obvious driver, and it's a cost originals don't carry.

**Next-half viewing is forecastable, within limits.** A gradient-boosting model predicts next-half hours for titles that stay on the service with a 24.7% median error on a fully held-out half. That beats two naive baselines: 27.2% for "same share as last half" and 26.2% for "the usual share for this title type." On licensed titles with 1M+ hours, the ones a licensing team actually prices, median error falls from 43% to 37%.

## Why the method matters

Three choices keep these numbers honest.

- **Daily viewing, not raw hours.** A title released on June 25 has six days in its launch half. Comparing raw hours across halves would make every late-half launch look like a flop. Decay is measured in hours per day on service, with a 30-day minimum launch window.
- **The reporting threshold is a floor, not a disappearance.** Titles that drop off the next report fell below 50,000 hours. They count as zero, a conservative lower bound, and the dropout rate is reported beside every retention figure instead of hidden inside it.
- **Forecasts are judged against a baseline that already knows the answer shape.** The segment baseline already encodes "launches fade, library holds," which is most of the signal. A model that only beat a flat baseline would be overstating its value.

## So what

1. **Value licensed deals on retained hours, not headline popularity.** Licensed titles keep about 80% of their hours each half, so the next 12 months are worth roughly 1.4x a title's latest half-year of viewing (0.8 + 0.8²), on average. The forecast model supplies the per-title number.
2. **Budget for the launch cliff.** Over 90% of a new original's daily viewing is gone after launch. Marketing and release timing need to capture the launch window, because the title won't earn it back later.
3. **Treat license churn as a planning risk.** With 22% of licensed titles dropping off each half, renewal timing is a catalog-management problem, not a legal footnote.
4. **Don't overpay for forecast precision.** A simple rule by title type gets most of the way there. The model's gain is real but modest; it's worth using on high-value licensing decisions, not as a black box for everything.

## Limitations

- "Original" is inferred from whether Netflix lists a release date. Co-productions and regional exclusives will sometimes sit on the wrong side of that line.
- Hours are not revenue. The reports carry no license fees or production budgets, so this values titles in viewing, not dollars.
- Six half-years is a short panel. The launch-decay estimate uses originals released through H1 2025, so it doesn't yet reflect 2026 release strategy.
- Netflix moves to annual reports from 2027, so this may be the last half-yearly series of its kind.

"""Step 0 - Download Netflix's seven engagement reports from Netflix's own file host and
check each against the SHA-256 recorded when this analysis was built. The raw files are
not committed to the repository: Netflix publishes them without a stated reuse licence,
so the repo links to the source instead of redistributing it."""
import hashlib
import pathlib
import urllib.request

RAW = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
BASE = "https://assets.ctfassets.net/4cd45et68cgf/"
FILES = {
    "2023H1": ("1HyknFM84ISQpeua6TjM7A/97a0a393098937a8f29c9d29c48dbfa8/What_We_Watched_A_Netflix_Engagement_Report_2023Jan-Jun.xlsx",
               "c6fd33eb4c243e6e18d81a248ad71a28e8ccc3d0dd2b1fbc9f8538c649d28637"),
    "2023H2": ("inuAnzotdsAEgbInGLzH5/1be323ba419b2af3a96bffa29acc31a3/What_We_Watched_A_Netflix_Engagement_Report_2023Jul-Dec.xlsx",
               "ea536b6e1f3771ba662e57a72ab847efd0200b3e4adb93a2f7d3e2b133f5b655"),
    "2024H1": ("2PoZlfdc46dH2gQvI8eUzI/9db5840720c47acfcf7b89ffe2402860/What_We_Watched_A_Netflix_Engagement_Report_2024Jan-Jun.xlsx",
               "2803512229889f91b51c214b9494b7a55799767d63e3f5cf2c142b1917a18d62"),
    "2024H2": ("6XSmoEjBjVMPRtYybT9d1E/8c0b0b2645b8712d5597b0bdbe0d64e2/What_We_Watched_A_Netflix_Engagement_Report_2024Jul-Dec.xlsx",
               "3030e3630fb0ff90d8d84b9cda3c22c83f4e9e356d4f1742bda729bfa2fc738c"),
    "2025H1": ("mplcXj5ulHDfbCPCr0f0I/5dbb6ec09f03df89706476e380e9b8bd/What_We_Watched_A_Netflix_Engagement_Report_2025Jan-Jun.xlsx",
               "7208fc0207818f961652748d19500221b1d3edce8999b83e0f954f27fb31e8dd"),
    "2025H2": ("2vdDPGLKA0XX2cjF2APJFn/7f1c367b39ed73a6a588751d3c5d0252/What_We_Watched_A_Netflix_Engagement_Report_2025Jul-Dec__6_.xlsx",
               "a06b0f510264336ad31f29a0ed4aaa51247374dcaa8aee780bbecf50227635cb"),
    "2026H1": ("40WGcHJa9vRua31kU6Gbz5/43b15c7fbd6924392fc80e885839e39f/Netflix-s_What_We_Watched_Report_2026Jan-Jun__1_.xlsx",
               "bcfda87e87d09d923472a1e1b30d5c7c799457aacba41310a9d223e834fe2f5f"),
}

RAW.mkdir(parents=True, exist_ok=True)
for period, (path, expected) in FILES.items():
    dest = RAW / "netflix_engagement_{}.xlsx".format(period)
    if not dest.exists():
        urllib.request.urlretrieve(BASE + path, dest)
    actual = hashlib.sha256(dest.read_bytes()).hexdigest()
    status = "ok" if actual == expected else "CHANGED UPSTREAM"
    print("  {:<8} {:<40} {}".format(period, dest.name, status))
    if actual != expected:
        raise SystemExit("Netflix revised {} since this analysis was built; results may differ.".format(period))

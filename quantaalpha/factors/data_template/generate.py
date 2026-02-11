"""
Generate daily price-volume HDF5 files for factor mining.

- daily_pv_all.h5   : ALL A-share stocks, full date range (2015-01-01 ~ end)
- daily_pv_debug.h5 : first 30 stocks (for fast CoSTEER evaluation)

NOTE: The h5 files intentionally contain **full A-share** data.  Factor
expressions (including cross-sectional operators like RANK / CS_RANK) are
computed over the entire market.  Downstream backtest code filters to the
configured market (e.g. csi300) via qlib instrument pools.
"""

import os

import qlib

_provider = os.environ.get(
    "QLIB_DATA_DIR",
    os.environ.get("QLIB_PROVIDER_URI", "~/.qlib/qlib_data/cn_data"),
)
qlib.init(provider_uri=_provider)
from qlib.data import D  # noqa: E402

# ---------------------------------------------------------------------------
# 1. Full A-share data  →  daily_pv_all.h5
# ---------------------------------------------------------------------------
START = "2015-01-01"
END = "2025-12-26"

instruments = D.instruments("all")
fields = ["$open", "$close", "$high", "$low", "$volume"]

data = (
    D.features(instruments, fields, freq="day", start_time=START, end_time=END)
    .swaplevel()
    .sort_index()
)

# Derived column used by some factor expressions
data["$return"] = data.groupby(level=0)["$close"].pct_change().fillna(0)

print(f"[daily_pv_all] all A-shares | {START} ~ {END}")
print(f"  rows: {len(data)}, instruments: {data.index.get_level_values('instrument').nunique()}")
print(data.tail())

data.to_hdf("./daily_pv_all.h5", key="data")

# ---------------------------------------------------------------------------
# 2. Debug subset (first 30 stocks)  →  daily_pv_debug.h5
# ---------------------------------------------------------------------------
DEBUG_N = 30
all_instruments = data.index.get_level_values("instrument").unique()
debug_instruments = all_instruments[:DEBUG_N]
debug_data = data.loc[debug_instruments].sort_index()

print(f"\n[daily_pv_debug] first {DEBUG_N} stocks")
print(f"  rows: {len(debug_data)}, instruments: {debug_data.index.get_level_values('instrument').nunique()}")
print(debug_data.tail())

debug_data.to_hdf("./daily_pv_debug.h5", key="data")


import qlib
from qlib.data import D
import pandas as pd

# Initialize Qlib with US data
qlib.init(provider_uri='/home/tjxy/.qlib/qlib_data/us_data', region='us')

potential_benchmarks = ['spx', '^GSPC', 'SPY', 'SPX', 'INX']
print("Checking US Benchmarks...")

for benchmark in potential_benchmarks:
    try:
        data = D.features([benchmark], ['$close'], start_time='2020-01-01', end_time='2020-01-10')
        if not data.empty:
            print(f"Found valid benchmark: {benchmark}")
        else:
            print(f"Benchmark {benchmark} returned empty data.")
    except Exception as e:
        print(f"Error checking {benchmark}: {e}")

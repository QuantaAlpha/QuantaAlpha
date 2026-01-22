import json
import os

input_file = '/home/tjxy/quantagent/AlphaAgent/all_factors_library_QA_liwei_csi500_best_deepseek_aliyun_123.json'
output_file = '/home/tjxy/quantagent/AlphaAgent/all_factors_library_QA_liwei_csi500_top150.json'

print(f"Loading {input_file}...")
with open(input_file, 'r') as f:
    data = json.load(f)

factors = data.get('factors', {})
print(f"Total factors found: {len(factors)}")

# Extract factors with their Rank IC
factor_list = []
for fid, fdata in factors.items():
    results = fdata.get('backtest_results', {})
    rank_ic = results.get('Rank IC')
    
    if rank_ic is not None:
        factor_list.append({
            'id': fid,
            'rank_ic': float(rank_ic),
            'data': fdata
        })
    else:
        print(f"Warning: Factor {fid} has no Rank IC")

# Sort by Rank IC descending
factor_list.sort(key=lambda x: x['rank_ic'], reverse=True)

# Select top 150
top_150 = factor_list[:150]
print(f"Selected top {len(top_150)} factors.")

if len(top_150) > 0:
    print(f"Top 1 Rank IC: {top_150[0]['rank_ic']}")
    print(f"Top 150 Rank IC: {top_150[-1]['rank_ic']}")

# Construct new JSON
new_data = data.copy()
new_data['factors'] = {item['id']: item['data'] for item in top_150}
new_data['metadata']['total_factors'] = len(top_150)
new_data['metadata']['description'] = "Top 150 factors selected by Rank IC from original library."

print(f"Saving to {output_file}...")
with open(output_file, 'w') as f:
    json.dump(new_data, f, indent=2)

print("Done.")

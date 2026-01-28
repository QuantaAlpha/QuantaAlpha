import os
import yaml
import json
import subprocess
from pathlib import Path
import pandas as pd
import time

# Configuration
CONFIG_TEMPLATE_PATH = "QuantaAlpha/backtest_v2/config_csi500.yaml"
OUTPUT_BASE_DIR = "backtest_v2_results_batch"
RUN_SCRIPT = "QuantaAlpha/backtest_v2/run_backtest.py"

EXPERIMENTS = [
    # CSI500
    {
        "name": "csi500_alpha158_20",
        "market": "csi500",
        "benchmark": "sh000905",
        "factor_source": "alpha158_20",
        "topk": 50, # Default TopK
        "description": "CSI500 + Alpha158(20)"
    },
    {
        "name": "csi500_alpha158",
        "market": "csi500",
        "benchmark": "sh000905",
        "factor_source": "alpha158",
        "topk": 50,
        "description": "CSI500 + Alpha158(All)"
    },
    {
        "name": "csi500_alpha360",
        "market": "csi500",
        "benchmark": "sh000905",
        "factor_source": "alpha360",
        "topk": 50,
        "description": "CSI500 + Alpha360"
    },
    # CSI300
    {
        "name": "csi300_alpha158_20",
        "market": "csi300",
        "benchmark": "sh000300",
        "factor_source": "alpha158_20",
        "topk": 50,
        "description": "CSI300 + Alpha158(20)"
    },
    {
        "name": "csi300_alpha158",
        "market": "csi300",
        "benchmark": "sh000300",
        "factor_source": "alpha158",
        "topk": 50,
        "description": "CSI300 + Alpha158(All)"
    },
    {
        "name": "csi300_alpha360",
        "market": "csi300",
        "benchmark": "sh000300",
        "factor_source": "alpha360",
        "topk": 50,
        "description": "CSI300 + Alpha360"
    }
]

def load_template():
    with open(CONFIG_TEMPLATE_PATH, 'r') as f:
        return yaml.safe_load(f)

def run_experiment(exp_config):
    print(f"\n{'='*60}")
    print(f"Running Experiment: {exp_config['description']}")
    print(f"{'='*60}")
    
    # 1. Prepare Config
    config = load_template()
    
    exp_name = exp_config['name']
    output_dir = os.path.join(OUTPUT_BASE_DIR, exp_name)
    
    # Update config
    config['experiment']['name'] = exp_name
    config['experiment']['output_dir'] = output_dir
    
    # Factor Source
    config['factor_source'] = {
        "type": exp_config['factor_source']
    }
    
    # Data & Benchmark
    config['data']['market'] = exp_config['market']
    config['backtest']['backtest']['benchmark'] = exp_config['benchmark']
    
    # Strategy TopK (if needed)
    # config['backtest']['strategy']['kwargs']['topk'] = exp_config['topk']
    
    # Disable LLM and Cache (Use standard Qlib flow)
    config['llm']['enabled'] = False
    # Ensure n_jobs is set reasonably (LGBM handles parallelism internally usually)
    # But Qlib data loading might use n_jobs.
    # We set to 8 to be safe.
    config['factor_calculation']['n_jobs'] = 8 
    
    # Save temporary config
    temp_config_path = f"temp_config_{exp_name}.yaml"
    with open(temp_config_path, 'w') as f:
        yaml.dump(config, f)
        
    # 2. Run Backtest
    cmd = ["python", RUN_SCRIPT, "-c", temp_config_path]
    log_file = f"run_{exp_name}.log"
    
    start_time = time.time()
    with open(log_file, "w") as outfile:
        result = subprocess.run(cmd, stdout=outfile, stderr=subprocess.STDOUT)
    
    duration = time.time() - start_time
    print(f"  Finished in {duration:.2f}s. Exit Code: {result.returncode}")
    
    # 3. Collect Metrics
    metrics_path = os.path.join(output_dir, "backtest_metrics.json")
    metrics = {}
    if os.path.exists(metrics_path):
        try:
            with open(metrics_path, 'r') as f:
                data = json.load(f)
                metrics = data.get("metrics", {})
                print("  Metrics loaded successfully.")
        except Exception as e:
            print(f"  Error loading metrics: {e}")
    else:
        print("  Metrics file not found.")
        
    # Cleanup
    if os.path.exists(temp_config_path):
        os.remove(temp_config_path)
        
    return {
        "Experiment": exp_config['description'],
        "Market": exp_config['market'],
        "Factors": exp_config['factor_source'],
        **metrics
    }

import concurrent.futures

def main():
    results = []
    
    # Ensure output dir exists
    Path(OUTPUT_BASE_DIR).mkdir(parents=True, exist_ok=True)
    
    # Run in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        future_to_exp = {executor.submit(run_experiment, exp): exp for exp in EXPERIMENTS}
        
        for future in concurrent.futures.as_completed(future_to_exp):
            exp = future_to_exp[future]
            try:
                res = future.result()
                results.append(res)
            except Exception as e:
                print(f"Error running {exp['name']}: {e}")
            
    # Print Summary
    print("\n\n" + "="*80)
    print("BATCH EXPERIMENT RESULTS")
    print("="*80)
    
    df = pd.DataFrame(results)
    # Reorder columns
    cols = ["Experiment", "IC", "ICIR", "Rank IC", "Rank ICIR", "annualized_return", "information_ratio", "max_drawdown", "calmar_ratio"]
    # Filter cols that exist
    cols = [c for c in cols if c in df.columns]
    
    print(df[cols].to_markdown(index=False))
    
    # Save summary
    df.to_csv(os.path.join(OUTPUT_BASE_DIR, "batch_summary.csv"), index=False)
    print(f"\nSummary saved to {os.path.join(OUTPUT_BASE_DIR, 'batch_summary.csv')}")

if __name__ == "__main__":
    main()

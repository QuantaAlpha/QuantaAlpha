import os
import yaml
import json
import subprocess
from pathlib import Path
import pandas as pd
import time
import concurrent.futures

# Configuration
CONFIG_TEMPLATE_PATH = "AlphaAgent/backtest_v2/config_sp500.yaml"
OUTPUT_BASE_DIR = "backtest_v2_results_sp500"
RUN_SCRIPT = "AlphaAgent/backtest_v2/run_backtest.py"

EXPERIMENTS = [
    # SP500
    {
        "name": "sp500_alpha158_20",
        "market": "sp500",
        "benchmark": "spx",
        "factor_source": "alpha158_20",
        "topk": 50,
        "description": "SP500 + Alpha158(20)"
    },
    {
        "name": "sp500_alpha158",
        "market": "sp500",
        "benchmark": "spx",
        "factor_source": "alpha158",
        "topk": 50,
        "description": "SP500 + Alpha158(All)"
    },
    {
        "name": "sp500_alpha360",
        "market": "sp500",
        "benchmark": "spx",
        "factor_source": "alpha360",
        "topk": 50,
        "description": "SP500 + Alpha360"
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
    
    # Ensure independent cache for each experiment to avoid conflicts
    config['factor_calculation'] = config.get('factor_calculation', {})
    config['factor_calculation']['cache_dir'] = f"factor_cache_{exp_name}"
    
    # Disable LLM and Cache (Use standard Qlib flow)
    config['llm']['enabled'] = False
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

def main():
    results = []
    
    # Ensure output dir exists
    Path(OUTPUT_BASE_DIR).mkdir(parents=True, exist_ok=True)
    
    # Run in parallel
    # Reducing workers to 3 to avoid overloading if data loading is heavy
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
    print("BATCH EXPERIMENT RESULTS (SP500)")
    print("="*80)
    
    df = pd.DataFrame(results)
    # Reorder columns
    cols = ["Experiment", "IC", "ICIR", "Rank IC", "Rank ICIR", "annualized_return", "information_ratio", "max_drawdown", "calmar_ratio"]
    # Filter cols that exist
    cols = [c for c in cols if c in df.columns]
    
    if not df.empty and len(cols) > 0:
        print(df[cols].to_markdown(index=False))
        # Save summary
        df.to_csv(os.path.join(OUTPUT_BASE_DIR, "batch_summary.csv"), index=False)
        print(f"\nSummary saved to {os.path.join(OUTPUT_BASE_DIR, 'batch_summary.csv')}")
    else:
        print("No results to display.")

if __name__ == "__main__":
    main()


import yaml
import os
import subprocess
import json
import sys
from pathlib import Path

def run_sp500_benchmarks():
    base_config_path = "/home/tjxy/quantagent/QuantaAlpha/backtest_v2/config_sp500.yaml"
    
    # Load base config
    if not os.path.exists(base_config_path):
        print(f"Error: Base config {base_config_path} not found.")
        return

    with open(base_config_path, 'r') as f:
        base_config = yaml.safe_load(f)
    
    # Benchmarks to run
    benchmarks = [
        "alpha158_20",
        "alpha158",
        "alpha360"
    ]
    
    results = {}
    
    for benchmark in benchmarks:
        print(f"\n{'='*50}")
        print(f"Running SP500 Benchmark: {benchmark}")
        print(f"{'='*50}\n")
        
        # Create config for this benchmark
        config = base_config.copy()
        
        # 1. Update Experiment Settings
        exp_name = f"backtest_v2_sp500_{benchmark}"
        output_dir = f"backtest_v2_results_sp500_{benchmark}"
        
        config['experiment']['name'] = exp_name
        config['experiment']['output_dir'] = output_dir
        config['experiment']['output_metrics_file'] = "backtest_metrics.json"
        
        # 2. Update Factor Source
        if 'factor_source' not in config:
            config['factor_source'] = {}
        config['factor_source']['type'] = benchmark
        # Remove custom settings
        if 'custom' in config['factor_source']:
            del config['factor_source']['custom']
            
        # 3. Update Cache Directory (ISOLATION)
        cache_dir = f"/mnt/DATA/quantagent/QuantaAlpha/factor_cache_sp500_{benchmark}"
        if 'llm' not in config:
            config['llm'] = {}
        config['llm']['cache_dir'] = cache_dir
        
        # 4. Factor Calculation Output (ISOLATION)
        if 'factor_calculation' not in config:
            config['factor_calculation'] = {}
        config['factor_calculation']['output_dir'] = f"/mnt/DATA/quantagent/QuantaAlpha/computed_factors_sp500_{benchmark}"
        
        # 5. Ensure Benchmark is correct (spx)
        if 'backtest' not in config:
            config['backtest'] = {} # Usually in 'backtest' -> 'backtest' -> 'benchmark' or just 'benchmark' depending on how backtest_runner handles it
        # But wait, config_sp500.yaml structure might be different. 
        # Looking at config_csi500.yaml, benchmark is usually passed to Qlib config.
        # Let's explicitly set benchmark in config['data'] or wherever it's used.
        # My backtest_runner.py reads config and sets up Qlib.
        # Let's ensure 'benchmark' is set in 'data' section if supported, or verify runner logic.
        # Actually, in Qlib standard config, benchmark is part of 'port_analysis_config' -> 'strategy' -> 'benchmark'.
        # But my runner seems to handle 'benchmark' argument or config field.
        # Let's trust the runner handles 'benchmark' if I set it in the right place.
        # In `config_csi500.yaml`, we set benchmark: sh000905.
        # Here we want benchmark: spx.
        # I'll update the config file to have 'benchmark': 'spx' in the 'backtest' section if it exists, or verify where it is.
        # Looking at config_sp500.yaml read earlier:
        # It didn't have a 'backtest' section with benchmark.
        # I should add it.
        if 'backtest' not in config:
            config['backtest'] = {}
        if 'backtest' in config['backtest']: # Nested?
             config['backtest']['backtest']['benchmark'] = 'spx'
        else:
             config['backtest']['benchmark'] = 'spx'

        # Save temporary config
        temp_config_path = f"/home/tjxy/quantagent/QuantaAlpha/backtest_v2/config_sp500_{benchmark}.yaml"
        with open(temp_config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
            
        print(f"Created config: {temp_config_path}")
        print(f"Cache dir: {cache_dir}")
        print(f"Output dir: {output_dir}")
        
        # Run Backtest
        cmd = [
            "python", 
            "QuantaAlpha/backtest_v2/run_backtest.py",
            "-c", temp_config_path
        ]
        
        log_file = f"run_sp500_{benchmark}.log"
        print(f"Starting backtest, logs at {log_file}...")
        
        with open(log_file, 'w') as log_f:
            process = subprocess.Popen(
                cmd, 
                stdout=log_f, 
                stderr=subprocess.STDOUT,
                cwd="/home/tjxy/quantagent"
            )
            process.wait()
            
        if process.returncode != 0:
            print(f"❌ Error running {benchmark}. Check {log_file}.")
            results[benchmark] = "Failed"
        else:
            print(f"✓ {benchmark} completed successfully.")
            
            # Read metrics
            metrics_file = Path(f"/home/tjxy/quantagent/{output_dir}/backtest_metrics.json")
            if metrics_file.exists():
                with open(metrics_file, 'r') as f:
                    metrics = json.load(f)
                    results[benchmark] = metrics.get('metrics', {})
            else:
                 results[benchmark] = "Metrics file missing"

    # Save summary
    with open("sp500_benchmarks_summary.json", 'w') as f:
        json.dump(results, f, indent=4)
        
    print("\nSP500 Benchmarks Summary Saved.")

if __name__ == "__main__":
    run_sp500_benchmarks()

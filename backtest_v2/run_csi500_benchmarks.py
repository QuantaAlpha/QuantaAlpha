
import yaml
import os
import subprocess
import json
import sys
from pathlib import Path

def run_csi500_benchmarks():
    base_config_path = "/home/tjxy/quantagent/AlphaAgent/backtest_v2/config_csi500.yaml"
    
    # Load base config
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
        print(f"Running CSI500 Benchmark: {benchmark}")
        print(f"{'='*50}\n")
        
        # Create config for this benchmark
        config = base_config.copy()
        
        # 1. Update Experiment Settings
        exp_name = f"backtest_v2_csi500_{benchmark}"
        output_dir = f"backtest_v2_results_csi500_{benchmark}"
        
        config['experiment']['name'] = exp_name
        config['experiment']['output_dir'] = output_dir
        config['experiment']['output_metrics_file'] = "backtest_metrics.json"
        
        # 2. Update Factor Source
        if 'factor_source' not in config:
            config['factor_source'] = {}
        config['factor_source']['type'] = benchmark
        # Remove custom settings to avoid confusion (though runner handles it)
        if 'custom' in config['factor_source']:
            del config['factor_source']['custom']
            
        # 3. Update Cache Directory (ISOLATION)
        # Use a dedicated cache directory for each benchmark to prevent contamination
        cache_dir = f"/mnt/DATA/quantagent/AlphaAgent/factor_cache_csi500_{benchmark}"
        if 'llm' not in config:
            config['llm'] = {}
        config['llm']['cache_dir'] = cache_dir
        
        # 4. Factor Calculation Output (ISOLATION)
        if 'factor_calculation' not in config:
            config['factor_calculation'] = {}
        config['factor_calculation']['output_dir'] = f"/mnt/DATA/quantagent/AlphaAgent/computed_factors_csi500_{benchmark}"

        # Save temporary config
        temp_config_path = f"/home/tjxy/quantagent/AlphaAgent/backtest_v2/config_csi500_{benchmark}.yaml"
        with open(temp_config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
            
        print(f"Created config: {temp_config_path}")
        print(f"Cache dir: {cache_dir}")
        print(f"Output dir: {output_dir}")
        
        # Run Backtest
        cmd = [
            "python", 
            "AlphaAgent/backtest_v2/run_backtest.py",
            "-c", temp_config_path
        ]
        
        log_file = f"run_csi500_{benchmark}.log"
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
                print(f"⚠️ Metrics file not found: {metrics_file}")
                results[benchmark] = "Metrics Missing"

    # Print Summary
    print("\n\n")
    print("="*60)
    print("CSI500 Benchmark Results (Independent Cache)")
    print("="*60)
    
    for benchmark, res in results.items():
        print(f"\nFactor Library: {benchmark}")
        if isinstance(res, dict):
            # Print key metrics
            print(f"  IC:           {res.get('IC', 'N/A')}")
            print(f"  ICIR:         {res.get('ICIR', 'N/A')}")
            print(f"  Rank IC:      {res.get('Rank IC', 'N/A')}")
            print(f"  Rank ICIR:    {res.get('Rank ICIR', 'N/A')}")
            print(f"  Ann. Return:  {res.get('annualized_return', 'N/A')}")
            print(f"  Info Ratio:   {res.get('information_ratio', 'N/A')}")
            print(f"  Max Drawdown: {res.get('max_drawdown', 'N/A')}")
            print(f"  Calmar Ratio: {res.get('calmar_ratio', 'N/A')}")
        else:
            print(f"  Status: {res}")
    print("="*60)

if __name__ == "__main__":
    run_csi500_benchmarks()

#!/usr/bin/env python3
"""
回测工具入口脚本

使用方式:
    # 使用 Alpha158(20) 因子库
    quantaalpha backtest --factor-source alpha158_20
    
    # 使用自定义因子库
    quantaalpha backtest --factor-source custom --factor-json /path/to/factors.json
    
    # 或直接运行
    python -m quantaalpha.backtest.run_backtest -c configs/backtest.yaml --factor-source alpha158_20
"""

import argparse
import logging
import sys
from pathlib import Path

# 添加项目路径 (从 quantaalpha/backtest/ 向上三级到项目根目录)
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

# 加载 .env 文件
from dotenv import load_dotenv
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file)
    print(f"✓ 已加载环境变量: {env_file}")
else:
    print(f"⚠ 未找到 .env 文件: {env_file}，将使用系统环境变量")

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description='Backtest V2 - 全功能回测工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 使用 Alpha158(20) 基础因子
  python run_backtest.py -c config.yaml --factor-source alpha158_20
  
  # 使用自定义因子库
  python run_backtest.py -c config.yaml --factor-source custom \
      --factor-json /path/to/factor_data/quality/high_quality_1.json
  
  # 使用组合因子（官方 + 自定义）
  python run_backtest.py -c config.yaml --factor-source combined \
      --factor-json /path/to/factors1.json --factor-json /path/to/factors2.json
        """
    )
    
    # 必需参数
    parser.add_argument(
        '-c', '--config',
        type=str,
        required=True,
        help='配置文件路径 (YAML格式)'
    )
    
    # 因子源参数
    parser.add_argument(
        '-s', '--factor-source',
        type=str,
        choices=['alpha158', 'alpha158_20', 'alpha360', 'custom', 'combined'],
        default=None,
        help='因子源类型 (覆盖配置文件设置)'
    )
    
    parser.add_argument(
        '-j', '--factor-json',
        type=str,
        action='append',
        default=None,
        help='自定义因子库 JSON 文件路径 (可多次指定)'
    )
    
    # 实验参数
    parser.add_argument(
        '-e', '--experiment',
        type=str,
        default=None,
        help='实验名称 (覆盖配置文件设置)'
    )
    
    # 调试参数
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='显示详细日志'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='仅加载因子，不执行回测'
    )
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # 检查配置文件
    config_path = Path(args.config)
    if not config_path.exists():
        logger.error(f"配置文件不存在: {config_path}")
        sys.exit(1)
    
    # 验证因子源
    if args.factor_source == 'custom' and not args.factor_json:
        parser.error("使用 --factor-source custom 时必须指定 --factor-json 参数")
    if args.factor_source == 'combined' and not args.factor_json:
        parser.error("使用 --factor-source combined 时必须指定 --factor-json 参数")
    
    try:
        from quantaalpha.backtest.runner import BacktestRunner
        
        runner = BacktestRunner(str(config_path))
        
        if args.dry_run:
            # 仅加载因子，不执行回测
            print("\n📋 Dry Run 模式 - 仅加载因子\n")
            
            from quantaalpha.backtest.factor_loader import FactorLoader
            
            # 更新配置
            if args.factor_source:
                runner.config['factor_source']['type'] = args.factor_source
            if args.factor_json:
                runner.config['factor_source']['custom']['json_files'] = args.factor_json
            
            loader = FactorLoader(runner.config)
            qlib_factors, custom_factors = loader.load_factors()
            
            print(f"\n📊 因子加载结果:")
            print(f"  Qlib 兼容因子: {len(qlib_factors)} 个")
            print(f"  需要 LLM 计算的因子: {len(custom_factors)} 个")
            
            if args.verbose:
                print("\n  Qlib 兼容因子列表:")
                for name in list(qlib_factors.keys())[:10]:
                    print(f"    - {name}")
                if len(qlib_factors) > 10:
                    print(f"    ... 还有 {len(qlib_factors) - 10} 个因子")
                
                if custom_factors:
                    print("\n  需要 LLM 计算的因子列表:")
                    for factor in custom_factors[:5]:
                        print(f"    - {factor.get('factor_name', 'unknown')}")
                    if len(custom_factors) > 5:
                        print(f"    ... 还有 {len(custom_factors) - 5} 个因子")
        else:
            # 执行完整回测
            runner.run(
                factor_source=args.factor_source,
                factor_json=args.factor_json,
                experiment_name=args.experiment
            )
            
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断")
        sys.exit(130)
    except Exception as e:
        logger.error(f"\n❌ 回测失败: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()


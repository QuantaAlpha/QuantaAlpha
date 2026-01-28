#!/bin/bash
# 快速运行回测工具

cd /home/tjxy/quantagent/QuantaAlpha
source ../venv/bin/activate

echo "=========================================="
echo "独立回测工具 - 快速运行"
echo "=========================================="
echo ""

# 检查参数
if [ "$#" -eq 0 ]; then
    echo "使用方法:"
    echo "  bash run_backtest.sh alpha158       # 使用Alpha158(20)基础因子"
    echo "  bash run_backtest.sh custom         # 使用自定义因子库（高质量因子，限50个）"
    echo "  bash run_backtest.sh custom-all     # 使用所有自定义因子"
    echo ""
    exit 0
fi

MODE=$1

case $MODE in
    alpha158)
        echo "📊 模式: Alpha158(20) 基础因子库"
        python backtest_tool/backtest_tool.py \
            -c backtest_tool/backtest_tool_default.yaml \
            -s alpha158_20 \
            -e "Alpha158_20_$(date +%Y%m%d_%H%M)"
        ;;
    
    custom)
        echo "📊 模式: 自定义高质量因子（最多50个）"
        python backtest_tool/backtest_tool.py \
            -c backtest_tool/backtest_tool_default.yaml \
            -s custom \
            -l all_factors_library.json \
            -q high_quality \
            -n 50 \
            -e "Custom_High_Quality_50_$(date +%Y%m%d_%H%M)"
        ;;
    
    custom-all)
        echo "📊 模式: 所有自定义高质量因子"
        python backtest_tool/backtest_tool.py \
            -c backtest_tool/backtest_tool_default.yaml \
            -s custom \
            -l all_factors_library.json \
            -q high_quality valid \
            -e "Custom_All_Quality_$(date +%Y%m%d_%H%M)"
        ;;
    
    *)
        echo "❌ 未知模式: $MODE"
        echo "支持的模式: alpha158, custom, custom-all"
        exit 1
        ;;
esac

echo ""
echo "=========================================="
echo "回测完成！"
echo "=========================================="


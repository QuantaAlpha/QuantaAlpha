#!/bin/bash
# 批量回测脚本 - AA Top80 RankIC 因子 (Claude, DeepSeek, GPT)
# 对三个模型的 Top80 RankIC 因子库进行回测，并汇总结果

cd /home/tjxy/quantagent

# 激活虚拟环境
echo "🔧 激活虚拟环境..."
source venv/bin/activate

cd QuantaAlpha

# 配置文件
CONFIG="backtest_v2/config.yaml"

# 结果输出目录
OUTPUT_DIR="backtest_v2_results/AA_top80_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUTPUT_DIR"

# 定义要回测的因子库列表
FACTOR_LIBS=(
    "/home/tjxy/quantagent/QuantaAlpha/factor_library/AA_top80_RankIC_AA_claude_123_csi300.json"
    "/home/tjxy/quantagent/QuantaAlpha/factor_library/AA_top80_RankIC_AA_deepseek_123_csi300.json"
    "/home/tjxy/quantagent/QuantaAlpha/factor_library/AA_top80_RankIC_AA_gpt_123_csi300.json"
)

# 对应的简短名称
NAMES=(
    "Claude"
    "DeepSeek"
    "GPT"
)

echo "========================================"
echo "   批量回测 - AA Top80 RankIC"
echo "========================================"
echo "配置文件: $CONFIG"
echo "因子库数量: ${#FACTOR_LIBS[@]}"
echo "结果目录: $OUTPUT_DIR"
echo ""

# 记录开始时间
START_TIME=$(date +%s)

# 成功/失败计数
SUCCESS=0
FAILED=0

# 依次回测每个因子库
for i in "${!FACTOR_LIBS[@]}"; do
    FACTOR_JSON="${FACTOR_LIBS[$i]}"
    FACTOR_NAME=$(basename "$FACTOR_JSON" .json)
    SHORT_NAME="${NAMES[$i]}"
    
    echo ""
    echo "========================================"
    echo "[$((i+1))/${#FACTOR_LIBS[@]}] 回测: $SHORT_NAME"
    echo "========================================"
    echo "文件: $FACTOR_JSON"
    echo ""
    
    # 检查文件是否存在
    if [ ! -f "$FACTOR_JSON" ]; then
        echo "❌ 错误: 因子库文件不存在!"
        ((FAILED++))
        continue
    fi
    
    # 执行回测
    python backtest_v2/run_backtest.py \
        -c "$CONFIG" \
        --factor-source custom \
        --factor-json "$FACTOR_JSON" 2>&1 | tee "$OUTPUT_DIR/log_${SHORT_NAME}.txt"
    
    # 检查执行结果
    if [ $? -eq 0 ]; then
        echo "✅ $SHORT_NAME 回测完成"
        ((SUCCESS++))
        
        # 复制结果文件
        ACTUAL_RESULT="backtest_v2_results/${FACTOR_NAME}_backtest_metrics.json"
        if [ -f "$ACTUAL_RESULT" ]; then
            cp "$ACTUAL_RESULT" "$OUTPUT_DIR/result_${SHORT_NAME}.json"
            echo "  ✓ 复制结果: $ACTUAL_RESULT"
        else
            echo "  ⚠️ 结果文件不存在: $ACTUAL_RESULT"
        fi
    else
        echo "❌ $SHORT_NAME 回测失败"
        ((FAILED++))
    fi
done

# 计算总耗时
END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
ELAPSED_MIN=$((ELAPSED / 60))
ELAPSED_SEC=$((ELAPSED % 60))

echo ""
echo "========================================"
echo "        批量回测完成"
echo "========================================"
echo "成功: $SUCCESS"
echo "失败: $FAILED"
echo "总耗时: ${ELAPSED_MIN}分${ELAPSED_SEC}秒"
echo ""
echo "📁 结果目录: $OUTPUT_DIR"
echo ""

# 汇总结果
echo "========================================"
echo "        结果汇总"
echo "========================================"

python3 << EOF
import json
from pathlib import Path

output_dir = Path("$OUTPUT_DIR")
names = ["Claude", "DeepSeek", "GPT"]
results = []

print(f"{'Model':<12} {'因子数':>8} {'RankIC':>12} {'RankICIR':>12} {'年化收益':>12} {'IR':>12} {'MDD':>12}")
print("-" * 90)

for name in names:
    result_file = output_dir / f"result_{name}.json"
    if result_file.exists():
        try:
            with open(result_file, 'r') as f:
                data = json.load(f)
            
            num_factors = data.get('num_factors', 'N/A')
            metrics = data.get('metrics', {})
            ric = metrics.get('Rank IC')
            ricir = metrics.get('Rank ICIR')
            ret = metrics.get('annualized_return')
            ir = metrics.get('information_ratio')
            mdd = metrics.get('max_drawdown')
            
            ric_str = f"{ric:.6f}" if ric is not None else "N/A"
            ricir_str = f"{ricir:.4f}" if ricir is not None else "N/A"
            ret_str = f"{ret:.4f}" if ret is not None else "N/A"
            ir_str = f"{ir:.4f}" if ir is not None else "N/A"
            mdd_str = f"{mdd:.4f}" if mdd is not None else "N/A"
            
            print(f"{name:<12} {num_factors:>8} {ric_str:>12} {ricir_str:>12} {ret_str:>12} {ir_str:>12} {mdd_str:>12}")
            
            results.append({
                'model': name,
                'num_factors': num_factors,
                'Rank_IC': ric,
                'Rank_ICIR': ricir,
                'annualized_return': ret,
                'information_ratio': ir,
                'max_drawdown': mdd
            })
        except Exception as e:
            print(f"{name:<12} {'N/A':>8} 读取失败: {e}")
    else:
        print(f"{name:<12} {'N/A':>8} 文件不存在")

# 保存汇总
summary_file = output_dir / "summary.json"
with open(summary_file, 'w') as f:
    json.dump(results, f, indent=2)
print(f"\n📊 汇总已保存到: {summary_file}")
EOF


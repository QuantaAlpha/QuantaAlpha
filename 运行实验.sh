#!/bin/bash
# AlphaAgent 实验运行脚本

cd /home/tjxy/quantagent

# 激活虚拟环境
echo "🔧 激活虚拟环境..."
source venv/bin/activate

# 检查 alphaagent 是否可用
if ! command -v alphaagent &> /dev/null; then
    echo "❌ 错误: alphaagent 命令未找到"
    echo "请先安装 AlphaAgent:"
    echo "  cd AlphaAgent && pip install -e ."
    exit 1
fi

echo "✅ 虚拟环境已激活"
echo "📦 Python: $(python --version)"
echo "📍 AlphaAgent: $(which alphaagent)"
echo ""

# 进入 AlphaAgent 目录
cd AlphaAgent

# 运行实验
# 默认从配置文件读取参数：alphaagent/app/qlib_rd_loop/run_config.yaml
CONFIG_PATH=${CONFIG_PATH:-"alphaagent/app/qlib_rd_loop/run_config.yaml"}
STEP_N=${STEP_N:-""}

# 回测配置说明
# 数据时间范围: 2016-01-01 ~ 2025-12-31
# 训练集: 2016-01-01 ~ 2020-12-31
# 验证集: 2021-01-01 ~ 2021-12-31
# 测试集: 2022-01-01 ~ 2025-12-31
# 回测时间: 2022-01-01 ~ 2025-12-31 (在测试集上进行回测)
# 配置文件位置:
#   - alphaagent/scenarios/qlib/experiment/factor_template/conf.yaml
#   - alphaagent/scenarios/qlib/experiment/factor_template/conf_cn_combined_kdd_ver.yaml

echo "🚀 开始运行实验..."
echo "📄 配置文件: ${CONFIG_PATH}"
echo "📅 回测时间: 2022-01-01 ~ 2025-12-31"
echo "----------------------------------------"
if [ -n "${STEP_N}" ]; then
  alphaagent mine --direction "$1" --step_n "${STEP_N}" --config_path "${CONFIG_PATH}"
else
  alphaagent mine --direction "$1" --config_path "${CONFIG_PATH}"
fi


#!/bin/bash
# QuantaAlpha 主实验运行脚本
#
# 用法：
#   ./run.sh "初始方向"                       # 默认实验
#   ./run.sh "初始方向" "后缀"                # 指定因子库后缀
#   CONFIG=configs/experiment.yaml ./run.sh "方向"
#
# 示例：
#   ./run.sh "价量因子挖掘"
#   ./run.sh "动量反转因子" "exp_momentum"

# =============================================================================
# 定位项目根目录
# =============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

# =============================================================================
# 加载 .env 配置文件
# =============================================================================
if [ -f "${SCRIPT_DIR}/.env" ]; then
    set -a
    source "${SCRIPT_DIR}/.env"
    set +a
else
    echo "错误: 未找到 .env 配置文件"
    echo "请先执行: cp configs/.env.example .env"
    exit 1
fi

# =============================================================================
# 激活 conda 环境
# =============================================================================
eval "$(conda shell.bash hook)" 2>/dev/null
conda activate "${CONDA_ENV_NAME:-quantaalpha}" 2>/dev/null

if [ $? -ne 0 ]; then
    source activate "${CONDA_ENV_NAME:-quantaalpha}" 2>/dev/null
fi

if ! command -v quantaalpha &> /dev/null; then
    echo "错误: quantaalpha 命令未找到，请先安装: pip install -e ."
    exit 1
fi

echo "Python: $(python --version)"
echo "QuantaAlpha: $(which quantaalpha)"
echo ""

# =============================================================================
# 实验隔离
# =============================================================================
CONFIG_PATH=${CONFIG_PATH:-"configs/experiment.yaml"}

if [ -z "${EXPERIMENT_ID}" ]; then
    EXPERIMENT_ID="exp_$(date +%Y%m%d_%H%M%S)"
fi
export EXPERIMENT_ID

RESULTS_BASE="${DATA_RESULTS_DIR:-./data/results}"

if [ "${EXPERIMENT_ID}" != "shared" ]; then
    export WORKSPACE_PATH="${RESULTS_BASE}/workspace_${EXPERIMENT_ID}"
    export PICKLE_CACHE_FOLDER_PATH_STR="${RESULTS_BASE}/pickle_cache_${EXPERIMENT_ID}"
    mkdir -p "${WORKSPACE_PATH}" "${PICKLE_CACHE_FOLDER_PATH_STR}"
    echo "实验ID: ${EXPERIMENT_ID}"
    echo "工作空间: ${WORKSPACE_PATH}"
fi

# =============================================================================
# 校验 Qlib 数据
# =============================================================================
QLIB_DATA="${QLIB_DATA_DIR:-}"
if [ -z "${QLIB_DATA}" ]; then
    echo "错误: 未配置 QLIB_DATA_DIR，请在 .env 中设置 Qlib 数据路径"
    echo "示例: QLIB_DATA_DIR=/path/to/qlib/cn_data"
    exit 1
fi
if [ ! -d "${QLIB_DATA}" ]; then
    echo "错误: Qlib 数据目录不存在: ${QLIB_DATA}"
    echo "请检查 .env 中 QLIB_DATA_DIR 的路径是否正确"
    exit 1
fi
# 校验关键子目录
for subdir in calendars features instruments; do
    if [ ! -d "${QLIB_DATA}/${subdir}" ]; then
        echo "错误: Qlib 数据目录缺少 ${subdir}/ 子目录: ${QLIB_DATA}"
        echo "有效的 Qlib 数据目录应包含 calendars/、features/、instruments/ 子目录"
        exit 1
    fi
done
echo "Qlib 数据校验通过: ${QLIB_DATA}"

# 确保 Qlib 数据符号链接
if [ -n "${QLIB_DATA}" ]; then
    QLIB_SYMLINK_DIR="$HOME/.qlib/qlib_data"
    if [ ! -L "${QLIB_SYMLINK_DIR}/cn_data" ] || [ "$(readlink -f ${QLIB_SYMLINK_DIR}/cn_data 2>/dev/null)" != "$(readlink -f ${QLIB_DATA})" ]; then
        mkdir -p "${QLIB_SYMLINK_DIR}"
        ln -sfn "${QLIB_DATA}" "${QLIB_SYMLINK_DIR}/cn_data"
    fi
fi

# =============================================================================
# 解析参数并运行
# =============================================================================
DIRECTION="$1"
LIBRARY_SUFFIX="$2"

if [ -n "${LIBRARY_SUFFIX}" ]; then
    export FACTOR_LIBRARY_SUFFIX="${LIBRARY_SUFFIX}"
fi

echo ""
echo "开始运行实验..."
echo "配置: ${CONFIG_PATH}"
echo "数据: ${QLIB_DATA}"
echo "结果: ${RESULTS_BASE}"
echo "----------------------------------------"

if [ -n "${STEP_N}" ]; then
    quantaalpha mine --direction "${DIRECTION}" --step_n "${STEP_N}" --config_path "${CONFIG_PATH}"
else
    quantaalpha mine --direction "${DIRECTION}" --config_path "${CONFIG_PATH}"
fi

#!/bin/bash

# QuantaAlpha AI V2 启动脚本
# 同时启动 FastAPI 后端 + Vite 前端开发服务器

echo "🚀 启动 QuantaAlpha AI V2..."
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# =============================================================================
# 检查 Node.js
# =============================================================================
if ! command -v node &> /dev/null; then
    echo "❌ 错误: 未找到 Node.js"
    echo "请先安装 Node.js: https://nodejs.org/"
    exit 1
fi
echo "✅ Node.js: $(node --version)"

# =============================================================================
# 激活 conda 环境（使用与主实验相同的 quantaalpha 环境）
# =============================================================================
eval "$(conda shell.bash hook)" 2>/dev/null
CONDA_ENV="${CONDA_ENV_NAME:-quantaalpha}"
conda activate "${CONDA_ENV}" 2>/dev/null

if [ $? -ne 0 ]; then
    source activate "${CONDA_ENV}" 2>/dev/null
fi

if ! python -c "import quantaalpha" 2>/dev/null; then
    echo "❌ 错误: quantaalpha 包未安装"
    echo "请先运行: conda activate ${CONDA_ENV} && cd ${PROJECT_ROOT} && pip install -e ."
    exit 1
fi
echo "✅ Python: $(python --version) (conda env: ${CONDA_ENV})"

# =============================================================================
# 加载 .env 配置
# =============================================================================
if [ -f "${PROJECT_ROOT}/.env" ]; then
    set -a
    source "${PROJECT_ROOT}/.env"
    set +a
    echo "✅ 已加载 .env 配置"
else
    echo "⚠️  未找到 .env 文件，后端将使用默认配置"
fi

# =============================================================================
# 安装前端依赖
# =============================================================================
cd "${SCRIPT_DIR}"
if [ ! -d "node_modules" ]; then
    echo ""
    echo "📦 安装前端依赖..."
    npm install
    if [ $? -ne 0 ]; then
        echo "❌ 前端依赖安装失败"
        exit 1
    fi
    echo "✅ 前端依赖安装完成"
fi

# =============================================================================
# 安装后端依赖（在 conda 环境中）
# =============================================================================
pip install fastapi uvicorn websockets python-multipart 2>/dev/null | grep -v "already satisfied"

# =============================================================================
# 启动后端
# =============================================================================
echo ""
echo "🔧 启动后端服务 (端口 8000)..."
cd "${SCRIPT_DIR}"
python backend/app.py &
BACKEND_PID=$!

# 等待后端启动
sleep 3

# 检查后端是否启动成功
if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
    echo "✅ 后端服务启动成功"
else
    echo "❌ 后端启动失败，请检查日志"
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

# =============================================================================
# 启动前端
# =============================================================================
echo ""
echo "🎨 启动前端服务 (端口 3000)..."
cd "${SCRIPT_DIR}"
npm run dev &
FRONTEND_PID=$!

sleep 3

echo ""
echo "============================================"
echo "✅ 所有服务启动完成!"
echo ""
echo "📍 访问地址:"
echo "   前端:     http://localhost:3000"
echo "   后端 API: http://localhost:8000"
echo "   API 文档: http://localhost:8000/docs"
echo ""
echo "按 Ctrl+C 停止所有服务"
echo "============================================"
echo ""

# 捕获退出信号
cleanup() {
    echo ""
    echo "🛑 停止服务..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    echo "✅ 已停止所有服务"
    exit 0
}
trap cleanup SIGINT SIGTERM

# 等待子进程
wait

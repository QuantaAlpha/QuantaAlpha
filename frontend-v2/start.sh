#!/bin/bash

# QuantaAlpha AI V2 启动脚本
# 同时启动 FastAPI 后端 + Vite 前端开发服务器
# 多用户共享服务器场景：如果服务已在运行，复用现有服务而非互相杀掉

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
echo "📦 检查/安装后端 Python 依赖..."
pip install -q fastapi uvicorn websockets python-multipart python-dotenv pyyaml 2>/dev/null || true
echo "✅ 后端依赖就绪"

# =============================================================================
# 获取本机 IP（用于多用户访问提示）
# =============================================================================
HOST_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
if [ -z "$HOST_IP" ]; then
    HOST_IP="localhost"
fi

# =============================================================================
# 检测并启动后端（复用已有服务 or 重新启动）
# =============================================================================
BACKEND_PID=""
BACKEND_REUSED=false

echo ""
echo "🔍 检测后端服务 (端口 8000)..."
if curl -s --connect-timeout 2 http://localhost:8000/api/health > /dev/null 2>&1; then
    echo "✅ 后端服务已在运行中 (端口 8000)，复用现有服务"
    BACKEND_REUSED=true
    BACKEND_PID=$(lsof -ti:8000 2>/dev/null | head -1)
else
    # 清理可能占用端口但未正常服务的残留进程
    OLD_PID=$(lsof -ti:8000 2>/dev/null)
    if [ -n "$OLD_PID" ]; then
        echo "⚠️  端口 8000 被占用但服务异常，清理残留进程 (PID: $OLD_PID)..."
        kill $OLD_PID 2>/dev/null
        sleep 1
        kill -9 $OLD_PID 2>/dev/null 2>&1
    fi

    echo "🔧 启动后端服务 (端口 8000)..."
    cd "${SCRIPT_DIR}"
    python backend/app.py &
    BACKEND_PID=$!

    # 等待后端启动
    sleep 3

    if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
        echo "✅ 后端服务启动成功 (PID: $BACKEND_PID)"
    else
        echo "❌ 后端启动失败，请检查日志"
        kill $BACKEND_PID 2>/dev/null
        exit 1
    fi
fi

# =============================================================================
# 检测并启动前端（复用已有服务 or 重新启动）
# =============================================================================
FRONTEND_PID=""
FRONTEND_REUSED=false

echo ""
echo "🔍 检测前端服务 (端口 3000)..."
if curl -s --connect-timeout 2 http://localhost:3000 > /dev/null 2>&1; then
    echo "✅ 前端服务已在运行中 (端口 3000)，复用现有服务"
    FRONTEND_REUSED=true
    FRONTEND_PID=$(lsof -ti:3000 2>/dev/null | head -1)
else
    # 清理可能占用端口但未正常服务的残留进程
    OLD_PID=$(lsof -ti:3000 2>/dev/null)
    if [ -n "$OLD_PID" ]; then
        echo "⚠️  端口 3000 被占用但服务异常，清理残留进程 (PID: $OLD_PID)..."
        kill $OLD_PID 2>/dev/null
        sleep 1
        kill -9 $OLD_PID 2>/dev/null 2>&1
    fi

    echo "🎨 启动前端服务 (端口 3000)..."
    cd "${SCRIPT_DIR}"
    npm run dev &
    FRONTEND_PID=$!
    sleep 3
fi

echo ""
echo "============================================"
echo "✅ 所有服务启动完成!"
echo ""
echo "📍 访问地址:"
echo "   本机:     http://localhost:3000"
if [ "$HOST_IP" != "localhost" ]; then
echo "   局域网:   http://${HOST_IP}:3000"
fi
echo "   后端 API: http://localhost:8000"
echo "   API 文档: http://localhost:8000/docs"
echo ""
if [ "$BACKEND_REUSED" = true ] || [ "$FRONTEND_REUSED" = true ]; then
echo "ℹ️  部分服务为复用已有进程（多用户共享模式）"
echo "   Ctrl+C 仅停止本脚本启动的服务，不影响其他用户"
fi
echo ""
echo "按 Ctrl+C 停止服务"
echo "============================================"
echo ""

# 捕获退出信号 — 只杀自己启动的进程，不杀复用的
cleanup() {
    echo ""
    echo "🛑 停止服务..."
    if [ "$BACKEND_REUSED" = false ] && [ -n "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null
        echo "  已停止后端 (PID: $BACKEND_PID)"
    else
        echo "  后端为共享服务，保持运行"
    fi
    if [ "$FRONTEND_REUSED" = false ] && [ -n "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null
        echo "  已停止前端 (PID: $FRONTEND_PID)"
    else
        echo "  前端为共享服务，保持运行"
    fi
    echo "✅ 完成"
    exit 0
}
trap cleanup SIGINT SIGTERM

# 等待子进程
wait

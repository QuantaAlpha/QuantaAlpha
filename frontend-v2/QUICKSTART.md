# QuantaAlpha Web Dashboard - 快速开始指南

## 🎯 项目概览

基于 **React + FastAPI** 的对话式 AI 驱动量化因子挖掘平台 Web 看板。

### ✨ 主要特性
1. **自然语言输入** - 用对话方式描述需求，无需编程
2. **实时进度展示** - 阶段识别、进度条、日志流
3. **实时回测结果** - IC 指标、收益率、回撤实时更新
4. **交互式可视化** - 净值曲线、回撤分析、因子分布
5. **因子库管理** - 浏览、搜索、筛选已挖掘的因子
6. **系统配置** - 统一管理 API Key、Qlib 路径、默认参数

### 📐 架构设计

```
┌─────────────────────────────────────────────────────────┐
│                    用户浏览器                            │
│  ┌──────────────────────────────────────────────────┐  │
│  │         React 前端 (localhost:3000)              │  │
│  │  - 因子挖掘 (对话式输入 + 实时图表)              │  │
│  │  - 因子库 (浏览/搜索/筛选)                       │  │
│  │  - 独立回测 (选库 → 运行 → 结果)                │  │
│  │  - 系统设置 (API/路径/参数)                      │  │
│  └──────────────────────────────────────────────────┘  │
│            ↕ HTTP REST API + WebSocket                  │
│  ┌──────────────────────────────────────────────────┐  │
│  │       FastAPI 后端 (localhost:8000)              │  │
│  │  - REST API (任务管理、因子库读取)               │  │
│  │  - WebSocket (实时日志/进度推送)                  │  │
│  │  - 子进程调用 quantaalpha CLI                    │  │
│  └──────────────────────────────────────────────────┘  │
│            ↕ subprocess                                  │
│  ┌──────────────────────────────────────────────────┐  │
│  │        QuantaAlpha 核心 (quantaalpha CLI)        │  │
│  │  - 因子挖掘 (quantaalpha mine)                   │  │
│  │  - 独立回测 (quantaalpha.backtest.run_backtest)  │  │
│  │  - 因子库 (all_factors_library*.json)            │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## 🚀 快速启动

### 前提条件

- 已完成主项目安装（`pip install -e .`）
- 已配置 `.env` 文件
- Node.js 18+

### 方法 1: 一键启动（推荐）

```bash
conda activate quantaalpha   # 或你的 conda 环境名
cd frontend-v2
bash start.sh
```

脚本会自动：
- ✅ 检查 Node.js 和 Python 环境
- ✅ 安装前端依赖 (`npm install`)
- ✅ 安装后端依赖 (`pip install`)
- ✅ 启动后端服务 (端口 8000)
- ✅ 启动前端服务 (端口 3000)

### 方法 2: 手动启动

**终端 1 - 后端:**
```bash
conda activate quantaalpha
cd frontend-v2
pip install -r backend/requirements.txt
python backend/app.py
```

**终端 2 - 前端:**
```bash
cd frontend-v2
npm install
npm run dev
```

### 访问应用

- 🌐 **前端界面**: http://localhost:3000
- 🔧 **API 文档**: http://localhost:8000/docs
- 📊 **健康检查**: http://localhost:8000/api/health

## 💡 使用流程

### 1️⃣ 因子挖掘

1. 点击顶部 **"因子挖掘"** 菜单
2. 在底部输入框输入需求，例如：`请帮我挖掘动量类因子`
3. 点击 ⚙️ 调整高级配置（可选）
4. 点击 🚀 开始执行
5. 观察左侧进度和右侧图表实时更新

### 2️⃣ 查看因子库

1. 点击顶部 **"因子库"** 菜单
2. 浏览所有已挖掘的因子
3. 使用搜索框或质量筛选按钮
4. 点击因子卡片查看详情

### 3️⃣ 独立回测

1. 点击顶部 **"回测"** 菜单
2. 选择因子库 JSON 文件
3. 选择回测模式（Custom / Combined）
4. 查看回测结果指标

### 4️⃣ 系统设置

1. 点击顶部 **"设置"** 菜单
2. 配置 API Key、Qlib 数据路径等
3. 点击 **"保存配置"**

## 🔌 API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| POST | `/api/v1/mining/start` | 启动因子挖掘 |
| GET | `/api/v1/mining/{taskId}` | 获取挖掘任务状态 |
| DELETE | `/api/v1/mining/{taskId}` | 取消挖掘任务 |
| POST | `/api/v1/backtest/start` | 启动独立回测 |
| GET | `/api/v1/backtest/{taskId}` | 获取回测任务状态 |
| GET | `/api/v1/factors` | 分页查询因子库 |
| GET | `/api/v1/factors/libraries` | 列出所有因子库文件 |
| GET | `/api/v1/factors/cache-status` | 因子缓存状态 |
| POST | `/api/v1/factors/warm-cache` | 预热因子缓存 |
| GET | `/api/v1/system/config` | 获取系统配置 |
| PUT | `/api/v1/system/config` | 更新系统配置 |
| WS | `/ws/mining/{taskId}` | WebSocket 实时推送 |

### WebSocket 消息类型
- `progress` - 进度更新
- `log` - 日志条目
- `metrics` - 指标更新
- `result` - 最终结果
- `heartbeat` - 心跳保活

## 🐛 常见问题

### 前端启动报错 "Cannot find module"
```bash
rm -rf node_modules package-lock.json
npm install
```

### 后端启动报错 "Address already in use"
```bash
lsof -ti:8000 | xargs kill -9
python backend/app.py
```

### WebSocket 连接失败
- 确认后端运行在 8000 端口
- 检查浏览器控制台是否有 CORS 错误
- Vite 代理配置会自动转发 `/ws` 到后端

### 因子库页面为空
- 需要先运行因子挖掘实验生成 `all_factors_library*.json`
- 或通过挖掘页面启动一次实验

## 📦 项目结构

```
frontend-v2/
├── src/
│   ├── components/
│   │   ├── ui/                    # 基础 UI 组件
│   │   ├── layout/Layout.tsx      # 统一布局（Header + 导航）
│   │   ├── ChatInput.tsx          # 底部对话式输入框
│   │   ├── LiveCharts.tsx         # 实时图表
│   │   ├── ProgressSidebar.tsx    # 进度侧栏
│   │   └── ParticleBackground.tsx # 粒子动画背景
│   ├── pages/
│   │   ├── HomePage.tsx           # 因子挖掘页
│   │   ├── FactorLibraryPage.tsx  # 因子库页
│   │   ├── BacktestPage.tsx       # 独立回测页
│   │   └── SettingsPage.tsx       # 系统设置页
│   ├── context/TaskContext.tsx     # 全局状态管理
│   ├── services/api.ts            # API 客户端
│   ├── types/index.ts             # TypeScript 类型定义
│   ├── App.tsx                    # 路由入口
│   └── main.tsx                   # 应用入口
├── backend/
│   ├── app.py                     # FastAPI 后端（REST + WebSocket）
│   └── requirements.txt           # Python 后端依赖
├── start.sh                       # 一键启动脚本
├── package.json                   # 前端依赖
├── vite.config.ts                 # Vite 配置（代理 /api → 8000）
└── tailwind.config.js             # TailwindCSS 配置
```

## 📊 技术栈

- **前端**: React 18 + TypeScript + Vite + TailwindCSS + Recharts
- **后端**: FastAPI + Python 3.10+ + WebSocket
- **状态管理**: React Context + React Query
- **样式**: TailwindCSS + 自定义 CSS（深色主题）

---

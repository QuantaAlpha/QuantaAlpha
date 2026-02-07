# QuantaAlpha AI V2 - 全新设计 🚀

> 🎨 **高级美观** | 📊 **实时可视化** | 🤖 **AI 驱动** | ⚡ **极速调试** | 📚 **因子管理** | ⚙️ **配置中心**

## ✨ 最新更新 (v2.1)

### 🆕 新增功能
- **⚙️ 配置管理页面** - 统一管理 API Key、Qlib 路径、默认参数
- **📚 因子库页面** - 浏览、搜索、筛选已挖掘的因子
- **💾 本地缓存** - localStorage 持久化配置和因子数据
- **🧭 顶部导航** - 快速切换因子挖掘、因子库、设置

## 🎯 核心特性

### 1️⃣ 因子挖掘 (主页)
- **对话式交互** - 底部输入框，自然语言描述需求
- **实时可视化** - 净值、回撤、IC 曲线流式更新
- **进度追踪** - 左侧进度条 + 时间线 + 实时日志
- **快速仿真** - 300ms/tick，6-8秒完成演示

### 2️⃣ 因子库 📚
- **卡片展示** - 因子名称、表达式、质量标签、指标
- **智能筛选** - 按质量(高/中/低)筛选
- **全文搜索** - 搜索名称、表达式、描述
- **详情查看** - 点击卡片查看完整信息
- **数据导出** - 一键导出 JSON 文件
- **统计看板** - 总数、高质量数、中等数、低质量数

### 3️⃣ 系统设置 ⚙️
- **LLM 配置** - API Key、URL、模型选择
- **Qlib 配置** - 数据路径设置
- **默认参数** - 并行方向数、进化轮次、市场选择
- **高级选项** - 并行执行、质量门控开关
- **配置管理** - 保存/重置功能

## 🖥️ 界面导航

```
┌─────────────────────────────────────────────────────┐
│  ✨ Header (Fixed Top)                               │
│  [Logo] QuantaAlpha AI    [因子挖掘][因子库][设置] │
├─────────────────────────────────────────────────────┤
│                                                       │
│  📄 当前页面内容                                      │
│  - 因子挖掘: 欢迎页 / 执行视图 + 底部输入框         │
│  - 因子库: 因子卡片 + 筛选搜索                       │
│  - 设置: 配置表单                                     │
│                                                       │
└─────────────────────────────────────────────────────┘
```

## 🚀 快速开始

### 一键启动
```bash
cd frontend-v2
./start.sh
```

### 手动启动
```bash
# 终端 1 - 后端（在已激活 quantaalpha conda 环境的前提下）
cd frontend-v2
pip install -r backend/requirements.txt
python backend/app.py

# 终端 2 - 前端
cd frontend-v2
npm install
npm run dev
```

### 访问
- 🌐 **前端**: http://localhost:3000
- 🔧 **API 文档**: http://localhost:8000/docs

## 📖 使用指南

### 1️⃣ 首次配置

1. 点击顶部 **"设置"** 菜单
2. 填写 **API Key** (必填)
3. 配置 **Qlib 数据路径** (必填)
4. 调整默认参数 (可选)
5. 点击 **"保存配置"**

### 2️⃣ 开始挖掘

1. 点击顶部 **"因子挖掘"** 返回主页
2. 在底部输入框输入需求，例如:
   ```
   请帮我挖掘动量类因子，重点关注短期反转效应和成交量配合
   ```
3. 点击 **⚙️** 调整高级配置 (可选)
4. 点击 **🚀** 开始执行
5. 观察左侧进度和右侧图表实时更新

### 3️⃣ 查看因子库

1. 点击顶部 **"因子库"** 菜单
2. 查看所有已挖掘的因子
3. 使用搜索框或质量筛选按钮
4. 点击因子卡片查看详情
5. 点击 **"导出"** 下载 JSON 文件

## 💾 数据存储

### localStorage 缓存
- **配置数据**: `quantaalpha_config`
- **因子数据**: `quantaalpha_factors`

### 数据格式

**配置 (quantaalpha_config)**:
```json
{
  "apiKey": "sk-...",
  "apiUrl": "https://api.openai.com/v1",
  "modelName": "gpt-4",
  "qlibDataPath": "~/.qlib/qlib_data/cn_data",
  "defaultNumDirections": 2,
  "defaultMaxRounds": 7,
  "defaultMarket": "csi500",
  "parallelExecution": true,
  "qualityGateEnabled": true,
  "backtestTimeout": 600
}
```

**因子 (quantaalpha_factors)**:
```json
[
  {
    "factorId": "factor_1",
    "factorName": "Factor_1_动量类",
    "factorExpression": "RANK(TS_MEAN($close / DELAY($close, 10), 5) * $volume)",
    "factorDescription": "这是一个动量类因子，结合了价格动量和成交量特征",
    "quality": "high",
    "ic": 0.0627,
    "icir": 0.639,
    "rankIc": 0.0582,
    "rankIcir": 0.612,
    "round": 1,
    "direction": "动量类",
    "createdAt": "2026-02-05T10:30:00.000Z"
  }
]
```

## 🎨 页面详情

### 因子挖掘页面
- **欢迎屏幕**: 3个特性卡片 + 底部输入框
- **执行视图**: 左侧进度 + 右侧图表 + 底部输入框
- **图表组件**: 4个指标卡片 + 净值曲线 + 回撤分析 + IC时序 + 质量分布

### 因子库页面
- **顶部统计**: 总数、高质量、中等、低质量
- **筛选栏**: 搜索框 + 质量按钮
- **因子卡片**: 名称、质量标签、描述、表达式、指标、时间
- **详情弹窗**: 完整信息 + 大号指标展示

### 设置页面
- **LLM 配置**: API Key (可隐藏) + URL + 模型
- **Qlib 配置**: 数据路径
- **默认参数**: 4个数值输入
- **高级选项**: 2个开关
- **操作按钮**: 重置 + 保存

## 🔧 自定义配置

### 调整仿真速度
```typescript
// src/pages/HomePage.tsx 第 154 行
}, 300); // 改为 500 或 1000 更慢
```

### 调整粒子数量
```typescript
// src/components/ParticleBackground.tsx 第 18 行
const particleCount = 50; // 改为 30 更流畅
```

### 修改默认配置
```typescript
// src/pages/SettingsPage.tsx 第 16-28 行
const DEFAULT_CONFIG: SystemConfig = {
  // 修改这里的默认值
};
```

## 📦 项目结构

```
frontend-v2/
├── src/
│   ├── components/
│   │   ├── ui/                    # 基础组件
│   │   ├── layout/
│   │   │   └── Layout.tsx         # 统一布局 ⭐ NEW
│   │   ├── ChatInput.tsx          # 底部对话框
│   │   ├── LiveCharts.tsx         # 实时图表
│   │   ├── ProgressSidebar.tsx    # 进度侧栏
│   │   └── ParticleBackground.tsx # 粒子背景
│   ├── pages/
│   │   ├── HomePage.tsx           # 因子挖掘页
│   │   ├── FactorLibraryPage.tsx  # 因子库页 ⭐ NEW
│   │   └── SettingsPage.tsx       # 设置页 ⭐ NEW
│   ├── App.tsx                    # 应用入口 ⭐ NEW
│   └── main.tsx
└── backend/
    └── app.py                     # FastAPI 服务
```

## 🎯 功能清单

### 已实现 ✅
- [x] 对话式因子挖掘
- [x] 实时图表展示
- [x] 进度追踪
- [x] 粒子背景动画
- [x] 毛玻璃效果
- [x] 渐变边框
- [x] 配置管理
- [x] 因子库展示
- [x] 本地缓存
- [x] 导航菜单
- [x] 搜索筛选
- [x] 数据导出

### 待实现 🚧
- [ ] 真实后端集成
- [ ] WebSocket 实时推送
- [ ] 因子详细分析
- [ ] 历史任务记录
- [ ] 多任务并行
- [ ] 用户认证
- [ ] 暗色/亮色主题切换

## 🐛 故障排查

### 配置无法保存
- 检查浏览器是否禁用 localStorage
- 清除浏览器缓存后重试
- 打开开发者工具查看控制台错误

### 因子库为空
- 首次使用会生成 30 个示例因子
- 点击 "刷新" 按钮重新加载
- 检查 localStorage 中的 `quantaalpha_factors`

### 导航菜单不显示
- 确保在主页之外的页面
- 检查浏览器窗口宽度
- 刷新页面

## 📊 技术栈

- **前端框架**: React 18 + TypeScript
- **构建工具**: Vite
- **样式方案**: TailwindCSS + 自定义 CSS
- **图表库**: Recharts
- **图标库**: Lucide React
- **状态管理**: React Hooks + localStorage
- **后端**: FastAPI + Python 3.9+

## 🎉 特色功能

### 1. 配置持久化
所有配置保存在浏览器 localStorage，刷新不丢失

### 2. 因子缓存
挖掘的因子自动缓存，可随时查看历史结果

### 3. 智能搜索
支持因子名称、表达式、描述全文搜索

### 4. 质量分类
自动按 RankICIR 分类为高/中/低质量

### 5. 一键导出
导出 JSON 格式，包含完整因子信息

## 📞 反馈与支持

遇到问题？
1. 检查浏览器控制台 (F12)
2. 查看后端日志
3. 参考 QUICKSTART.md

---

**🎨 更美观 | 📊 更直观 | ⚡ 更快速 | 🚀 更高级 | 📚 更完善**

Made with ❤️ by QuantaAlpha Team

import React from 'react';
import { ChatInput } from '@/components/ChatInput';
import { Layout } from '@/components/layout/Layout';
import type { PageId } from '@/components/layout/Layout';
import { useTaskContext } from '@/context/TaskContext';

// -------------------------------------------------------------------
// Component
// -------------------------------------------------------------------

interface HomePageProps {
  onNavigate?: (page: PageId) => void;
}

export const HomePage: React.FC<HomePageProps> = ({ onNavigate }) => {
  const {
    backendAvailable,
    miningTask: task,
    startMining,
    stopMining,
  } = useTaskContext();

  return (
    <Layout
      currentPage="home"
      onNavigate={onNavigate || (() => {})}
      showNavigation={!!onNavigate}
    >
        {/* Welcome Screen - leave some space at the bottom to avoid overlapping with fixed input area */}
        <div className="flex flex-col items-center justify-center min-h-[60vh] pb-8 animate-fade-in-up">
          <div className="text-center mb-10">
            <h2 className="text-4xl font-bold mb-4 bg-gradient-to-r from-primary via-purple-500 to-pink-500 bg-clip-text text-transparent">
              欢迎使用 QuantaAlpha
            </h2>
            <p className="text-lg text-muted-foreground">
              用自然语言描述需求，AI 自动挖掘高质量量化因子
            </p>
            {backendAvailable === false && (
              <p className="text-sm text-warning mt-2">
                后端未连接，将使用模拟数据演示
              </p>
            )}
            {backendAvailable === true && (
              <p className="text-sm text-success mt-2">
                已连接后端服务
              </p>
            )}
          </div>

          {/* Feature Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl w-full mb-10">
            <div className="glass rounded-2xl p-6 card-hover text-center cursor-pointer" onClick={() => onNavigate?.('home')}>
              <div className="text-4xl mb-3">🤖</div>
              <h3 className="font-semibold mb-2">AI 因子挖掘</h3>
              <p className="text-sm text-muted-foreground">
                LLM 自动理解需求，生成因子假设并进化优化
              </p>
            </div>
            <div className="glass rounded-2xl p-6 card-hover text-center cursor-pointer" onClick={() => onNavigate?.('library')}>
              <div className="text-4xl mb-3">📊</div>
              <h3 className="font-semibold mb-2">因子库管理</h3>
              <p className="text-sm text-muted-foreground">
                浏览、筛选、分析已挖掘的所有因子
              </p>
            </div>
            <div className="glass rounded-2xl p-6 card-hover text-center cursor-pointer" onClick={() => onNavigate?.('backtest')}>
              <div className="text-4xl mb-3">🚀</div>
              <h3 className="font-semibold mb-2">独立回测</h3>
              <p className="text-sm text-muted-foreground">
                选择因子库进行全周期样本外回测评估
              </p>
            </div>
          </div>

          {/* System Info Panel */}
          <div className="w-full max-w-4xl glass rounded-2xl p-6 text-sm space-y-3">
            <h4 className="font-semibold text-foreground mb-3 flex items-center gap-2">
              <span className="text-lg">💡</span> 使用须知
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-2 text-muted-foreground">

              <div className="flex items-start gap-2">
                <span className="text-primary mt-0.5">&#9679;</span>
                <span><strong className="text-foreground">默认市场：</strong>CSI 300（沪深300）市场股票数据</span>
              </div>
              <div className="flex items-start gap-2">
                <span className="text-primary mt-0.5">&#9679;</span>
                <span><strong className="text-foreground">挖掘时间段：</strong>训练集 2016-2020，验证集 2021（初步回测在验证集上进行）</span>
              </div>
              <div className="flex items-start gap-2">
                <span className="text-primary mt-0.5">&#9679;</span>
                <span><strong className="text-foreground">独立回测：</strong>测试集 2022-01-01 ~ 2025-12-26（评估样本外表现）</span>
              </div>
              <div className="flex items-start gap-2">
                <span className="text-primary mt-0.5">&#9679;</span>
                <span><strong className="text-foreground">资源消耗：</strong>LLM Token / 时间消耗与<strong className="text-foreground">（进化轮次 x 并行方向数）</strong>成正比</span>
              </div>
              <div className="flex items-start gap-2">
                <span className="text-primary mt-0.5">&#9679;</span>
                <span><strong className="text-foreground">基础因子：</strong>主实验中新因子与 4 个基础因子（开盘收益率、成交量比率、振幅收益率、日收益率）组合后回测</span>
              </div>
            </div>
          </div>
        </div>

      {/* Bottom Chat Input - Always visible on Home Page for starting new tasks */}
      <ChatInput
        onSubmit={startMining}
        onStop={stopMining}
        isRunning={task?.status === 'running'}
      />
    </Layout>
  );
};

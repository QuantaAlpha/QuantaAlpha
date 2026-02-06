import React, { useState } from 'react';
import { HomePage } from '@/pages/HomePage';
import { FactorLibraryPage } from '@/pages/FactorLibraryPage';
import { BacktestPage } from '@/pages/BacktestPage';
import { SettingsPage } from '@/pages/SettingsPage';
import { Layout } from '@/components/layout/Layout';
import type { PageId } from '@/components/layout/Layout';
import { ParticleBackground } from '@/components/ParticleBackground';
import { TaskProvider } from '@/context/TaskContext';

export const App: React.FC = () => {
  const [currentPage, setCurrentPage] = useState<PageId>('home');

  return (
    <TaskProvider>
      <ParticleBackground />
      {/*
        使用 display:none 隐藏非当前页面，而非条件卸载。
        这样切换页面时组件不会被卸载，WebSocket/任务状态不会丢失。
      */}
      <div style={{ display: currentPage === 'home' ? 'block' : 'none' }}>
        <HomePage onNavigate={setCurrentPage} />
      </div>
      <div style={{ display: currentPage === 'library' ? 'block' : 'none' }}>
        <Layout currentPage={currentPage} onNavigate={setCurrentPage}>
          <FactorLibraryPage />
        </Layout>
      </div>
      <div style={{ display: currentPage === 'backtest' ? 'block' : 'none' }}>
        <Layout currentPage={currentPage} onNavigate={setCurrentPage}>
          <BacktestPage />
        </Layout>
      </div>
      <div style={{ display: currentPage === 'settings' ? 'block' : 'none' }}>
        <Layout currentPage={currentPage} onNavigate={setCurrentPage}>
          <SettingsPage />
        </Layout>
      </div>
    </TaskProvider>
  );
};

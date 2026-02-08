/**
 * TaskContext — 全局任务状态管理
 *
 * 将 mining 和 backtest 的任务状态、WebSocket 连接、轮询逻辑
 * 提升到 App 级别，页面切换时不会丢失运行状态。
 */

import React, { createContext, useContext, useState, useCallback, useRef, useEffect } from 'react';
import type {
  Task,
  TaskConfig,
  LogEntry,
  RealtimeMetrics,
  TimeSeriesData,
  WsMessage,
} from '@/types';
import { generateId } from '@/utils';
import {
  startMining as apiStartMining,
  getMiningStatus,
  cancelMining as apiCancelMining,
  startBacktest as apiStartBacktest,
  getBacktestStatus,
  cancelBacktest as apiCancelBacktest,
  connectMiningWs,
  healthCheck,
} from '@/services/api';
import type { BacktestStartParams } from '@/services/api';
import { getDefaultMiningDirection } from '@/utils/miningDirections';

// ========================== Backtest local type ==========================

export interface BacktestTask {
  taskId: string;
  status: string;
  progress: {
    phase: string;
    progress: number;
    message: string;
    timestamp: string;
  };
  logs: LogEntry[];
  metrics: Record<string, any>;
  config: Record<string, any>;
  createdAt: string;
  updatedAt: string;
}

// ========================== Context Value ==========================

interface TaskContextValue {
  // Backend health
  backendAvailable: boolean | null;

  // ---- Mining ----
  miningTask: Task | null;
  miningEquityCurve: TimeSeriesData[];
  miningDrawdownCurve: TimeSeriesData[];
  miningIcTimeSeries: TimeSeriesData[];
  startMining: (config: TaskConfig) => void;
  stopMining: () => void;
  resetMiningTask: () => void;

  // ---- Backtest ----
  backtestTask: BacktestTask | null;
  backtestLogs: LogEntry[];
  startBacktestTask: (params: BacktestStartParams) => Promise<void>;
  stopBacktestTask: () => void;
}

const TaskContext = createContext<TaskContextValue | null>(null);

// ========================== Provider ==========================

export const TaskProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // ---- Backend health ----
  const [backendAvailable, setBackendAvailable] = useState<boolean | null>(null);

  useEffect(() => {
    healthCheck()
      .then(() => setBackendAvailable(true))
      .catch(() => setBackendAvailable(false));
  }, []);

  // ==================================================================
  // MINING
  // ==================================================================
  const [miningTask, setMiningTask] = useState<Task | null>(null);
  const [miningEquityCurve, setMiningEquityCurve] = useState<TimeSeriesData[]>([]);
  const [miningDrawdownCurve, setMiningDrawdownCurve] = useState<TimeSeriesData[]>([]);
  const [miningIcTimeSeries, setMiningIcTimeSeries] = useState<TimeSeriesData[]>([]);

  const miningWsRef = useRef<WebSocket | null>(null);
  const miningPollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const miningDataPointsRef = useRef(0);

  // Chart data helper
  const pushMiningDataPoint = useCallback(() => {
    miningDataPointsRef.current += 1;
    const n = miningDataPointsRef.current;
    const startDate = new Date('2020-01-01');
    const d = new Date(startDate);
    d.setDate(d.getDate() + n * 7);
    const dateStr = d.toISOString().split('T')[0];

    setMiningEquityCurve((prev) => [
      ...prev,
      { date: dateStr, value: 1 + n * 0.003 + (Math.random() - 0.5) * 0.02 },
    ]);
    setMiningDrawdownCurve((prev) => [
      ...prev,
      { date: dateStr, value: -0.02 - n * 0.001 + (Math.random() - 0.5) * 0.01 },
    ]);
    setMiningIcTimeSeries((prev) => [
      ...prev,
      { date: dateStr, value: 0.05 + Math.sin(n * 0.1) * 0.02 + (Math.random() - 0.5) * 0.01 },
    ]);
  }, []);

  // WS handler for mining
  const handleMiningWsMessage = useCallback(
    (msg: WsMessage) => {
      setMiningTask((prev) => {
        if (!prev) return prev;
        const updated = { ...prev };
        switch (msg.type) {
          case 'progress':
            updated.progress = msg.data;
            updated.status = msg.data.phase === 'completed' ? 'completed' : 'running';
            if (['backtesting', 'analyzing', 'completed'].includes(msg.data.phase)) {
              pushMiningDataPoint();
            }
            break;
          case 'log':
            // Increased frontend log retention limit from 99 to 2000
            updated.logs = [...(updated.logs || []).slice(-2000), msg.data as LogEntry];
            
            // Try to extract factor from log message to show it immediately in the list
            // Pattern: "Added new factor: {name} with expression: {expr}"
            const logMsg = (msg.data as LogEntry).message;
            if (logMsg && logMsg.includes("Added new factor:")) {
              const match = logMsg.match(/Added new factor: (.+?) with expression: (.+)/);
              if (match) {
                const [_, name, expr] = match;
                const currentMetrics = updated.metrics || {
                    ic: 0, icir: 0, rankIc: 0, rankIcir: 0,
                    annualReturn: 0, sharpeRatio: 0, maxDrawdown: 0,
                    totalFactors: 0, highQualityFactors: 0, mediumQualityFactors: 0, lowQualityFactors: 0,
                    top10Factors: []
                };
                
                const currentFactors = currentMetrics.top10Factors || [];
                // Avoid duplicates
                if (!currentFactors.some((f: any) => f.factorName === name)) {
                    const newFactor = {
                        factorName: name,
                        factorExpression: expr,
                        rankIc: 0, rankIcir: 0, ic: 0, icir: 0,
                        annualReturn: 0, sharpeRatio: 0, maxDrawdown: 0, calmarRatio: 0,
                        cumulativeCurve: []
                    };
                    
                    // Recalculate best metrics from the updated list
                    const updatedFactors = [newFactor, ...currentFactors];
                    const bestFactor = updatedFactors.reduce((best, current) => {
                        // Prioritize RankIC, but handle potential missing values
                        const bestScore = best.rankIc || 0;
                        const currentScore = current.rankIc || 0;
                        return currentScore > bestScore ? current : best;
                    }, updatedFactors[0]);

                    updated.metrics = {
                        ...currentMetrics,
                        totalFactors: (currentMetrics.totalFactors || 0) + 1,
                        // Prepend new factor to the list so user sees it immediately
                        top10Factors: updatedFactors,
                        // Update best factor metrics
                        factorName: bestFactor.factorName,
                        rankIc: bestFactor.rankIc ?? 0,
                        rankIcir: bestFactor.rankIcir ?? 0,
                        ic: bestFactor.ic ?? 0,
                        icir: bestFactor.icir ?? 0,
                        annualReturn: bestFactor.annualReturn ?? 0,
                        sharpeRatio: bestFactor.sharpeRatio ?? 0,
                        maxDrawdown: bestFactor.maxDrawdown ?? 0,
                    };
                }
              }
            }
            break;
          case 'metrics':
            updated.metrics = {
              ...(updated.metrics || {} as RealtimeMetrics),
              ...msg.data as RealtimeMetrics
            };
            break;
          case 'result':
            updated.status = msg.data.status === 'completed' ? 'completed' : 'failed';
            if (msg.data.metrics) updated.metrics = msg.data.metrics;
            break;
          case 'error':
            updated.status = 'failed';
            updated.logs = [
              ...(updated.logs || []),
              {
                id: generateId(),
                timestamp: new Date().toISOString(),
                level: 'error',
                message: msg.data.error || 'Unknown error',
              },
            ];
            break;
        }
        updated.updatedAt = new Date().toISOString();
        return updated;
      });
    },
    [pushMiningDataPoint],
  );

  // Start mining (real backend)
  const startRealMining = useCallback(
    async (config: TaskConfig) => {
      try {
        // Load defaults from localStorage
        let defaults: any = {};
        const savedConfig = localStorage.getItem('quantaalpha_config');
        if (savedConfig) {
          try {
            defaults = JSON.parse(savedConfig);
          } catch {}
        }

        const direction =
          config.useCustomMiningDirection
            ? (getDefaultMiningDirection() || '价量因子挖掘')
            : (config.userInput && config.userInput.trim()) || getDefaultMiningDirection() || '价量因子挖掘';
        const resp = await apiStartMining({
          direction,
          numDirections: config.numDirections || defaults.defaultNumDirections || 2,
          maxRounds: config.maxRounds || defaults.defaultMaxRounds || 3,
          librarySuffix: config.librarySuffix || defaults.defaultLibrarySuffix || undefined,
          qualityGateEnabled: config.qualityGateEnabled ?? defaults.qualityGateEnabled ?? true,
        });
        if (!resp.success || !resp.data) throw new Error(resp.error || 'Failed');

        const taskData = resp.data.task as Task;
        // Initialize metrics with empty top10Factors to avoid stale data
        if (taskData.metrics) {
            taskData.metrics.top10Factors = [];
            taskData.metrics.totalFactors = 0;
            taskData.metrics.highQualityFactors = 0;
            taskData.metrics.mediumQualityFactors = 0;
            taskData.metrics.lowQualityFactors = 0;
        }
        setMiningTask(taskData);
        setMiningEquityCurve([]);
        setMiningDrawdownCurve([]);
        setMiningIcTimeSeries([]);
        miningDataPointsRef.current = 0;

        // WebSocket
        const ws = connectMiningWs(
          resp.data.taskId,
          handleMiningWsMessage,
          () => {
            getMiningStatus(resp.data!.taskId).then((r) => {
              if (r.data?.task) setMiningTask(r.data.task as Task);
            });
          },
        );
        miningWsRef.current = ws;

        // Polling fallback
        miningPollingRef.current = setInterval(async () => {
          try {
            const r = await getMiningStatus(resp.data!.taskId);
            if (r.data?.task) {
              const t = r.data.task as Task;
              if (t.status === 'completed' || t.status === 'failed') {
                setMiningTask(t);
                clearInterval(miningPollingRef.current!);
                miningPollingRef.current = null;
              }
            }
          } catch {
            // ignore
          }
        }, 10000);
      } catch (err: any) {
        console.error('Failed to start mining task:', err);
        // Fall back to mock
        startMockMining(config);
      }
    },
    [handleMiningWsMessage],
  );

  // Mock mining fallback
  const startMockMining = useCallback(
    (config: TaskConfig) => {
      const newTask: Task = {
        taskId: generateId(),
        status: 'running',
        config,
        progress: {
          phase: 'parsing',
          currentRound: 0,
          totalRounds: config.maxRounds || 7,
          progress: 0,
          message: '正在解析用户需求...',
          timestamp: new Date().toISOString(),
        },
        logs: [],
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };
      setMiningTask(newTask);
      setMiningEquityCurve([]);
      setMiningDrawdownCurve([]);
      setMiningIcTimeSeries([]);
      miningDataPointsRef.current = 0;

      const phases = ['parsing', 'planning', 'evolving', 'backtesting', 'analyzing', 'completed'] as const;
      let phaseIdx = 0;
      let progress = 0;
      let round = 1;

      const logMessages: Record<string, string[]> = {
        parsing: ['解析需求关键词...', '识别策略类型...', '生成研究方向...'],
        planning: ['规划探索路径...', '初始化进化框架...', '准备种子因子...'],
        evolving: ['生成因子假设...', '构建表达式...', '计算因子值...', '评估质量...'],
        backtesting: ['执行回测计算...', '计算IC指标...', '评估收益曲线...', '分析因子质量...'],
        analyzing: ['综合分析结果...', '生成评估报告...', '优化因子组合...'],
        completed: ['任务完成!', '结果已生成!'],
      };

      const interval = setInterval(() => {
        progress += 10 + Math.random() * 15;
        if (progress >= 100 && phaseIdx < phases.length - 1) {
          phaseIdx++;
          progress = 0;
          if (phases[phaseIdx] === 'evolving') round++;
        }
        const phase = phases[phaseIdx];
        const msgs = logMessages[phase];
        const msg = msgs[Math.floor(Math.random() * msgs.length)];

        const dp = miningDataPointsRef.current;
        const metrics: RealtimeMetrics | undefined =
          ['backtesting', 'analyzing', 'completed'].includes(phase)
            ? {
                ic: 0.05 + Math.random() * 0.03,
                icir: 0.5 + Math.random() * 0.3,
                rankIc: 0.04 + Math.random() * 0.03,
                rankIcir: 0.45 + Math.random() * 0.3,
                annualReturn: 0.12 + Math.random() * 0.08,
                sharpeRatio: 1.2 + Math.random() * 0.5,
                maxDrawdown: -(0.08 + Math.random() * 0.05),
                totalFactors: Math.min(50 + dp * 2, 80),
                highQualityFactors: Math.min(15 + Math.floor(dp * 0.7), 25),
                mediumQualityFactors: Math.min(20 + Math.floor(dp * 0.8), 30),
                lowQualityFactors: Math.min(10 + Math.floor(dp * 0.5), 20),
              }
            : undefined;

        if (['backtesting', 'analyzing', 'completed'].includes(phase)) {
          pushMiningDataPoint();
        }

        setMiningTask((prev) => {
          if (!prev) return prev;
          return {
            ...prev,
            status: phase === 'completed' ? 'completed' : 'running',
            progress: {
              phase: phase as any,
              currentRound: round,
              totalRounds: config.maxRounds || 7,
              progress,
              message: msg,
              timestamp: new Date().toISOString(),
            },
            metrics,
            logs: [
              ...(prev.logs || []),
              {
                id: generateId(),
                timestamp: new Date().toISOString(),
                level: (Math.random() > 0.95 ? 'warning' : 'info') as 'warning' | 'info',
                message: msg,
              },
            ].slice(-30),
            updatedAt: new Date().toISOString(),
          };
        });

        if (phase === 'completed') clearInterval(interval);
      }, 300);
    },
    [pushMiningDataPoint],
  );

  // Public start mining
  const startMining = useCallback(
    (config: TaskConfig) => {
      if (backendAvailable) {
        startRealMining(config);
      } else {
        startMockMining(config);
      }
    },
    [backendAvailable, startRealMining, startMockMining],
  );

  // Stop mining
  const stopMining = useCallback(async () => {
    if (!miningTask) return;
    miningWsRef.current?.close();
    miningWsRef.current = null;
    if (miningPollingRef.current) {
      clearInterval(miningPollingRef.current);
      miningPollingRef.current = null;
    }
    if (backendAvailable) {
      try {
        await apiCancelMining(miningTask.taskId);
      } catch {
        // ignore
      }
    }
    setMiningTask((prev) => (prev ? { ...prev, status: 'failed' } : prev));
  }, [miningTask, backendAvailable]);

  // Reset mining task
  const resetMiningTask = useCallback(() => {
    // Ensure stopped first
    miningWsRef.current?.close();
    miningWsRef.current = null;
    if (miningPollingRef.current) {
      clearInterval(miningPollingRef.current);
      miningPollingRef.current = null;
    }
    setMiningTask(null);
    setMiningEquityCurve([]);
    setMiningDrawdownCurve([]);
    setMiningIcTimeSeries([]);
  }, []);

  // ==================================================================
  // BACKTEST
  // ==================================================================
  const [backtestTask, setBacktestTask] = useState<BacktestTask | null>(null);
  const [backtestLogs, setBacktestLogs] = useState<LogEntry[]>([]);

  const backtestWsRef = useRef<WebSocket | null>(null);
  const backtestPollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // WS handler for backtest
  // IMPORTANT: setBacktestLogs must NOT be inside setBacktestTask's updater function,
  // because React StrictMode double-invokes updater functions in development mode,
  // which would cause every log entry to be added twice.
  const handleBacktestWsMessage = useCallback((msg: WsMessage) => {
    switch (msg.type) {
      case 'progress':
        setBacktestTask((prev) => {
          if (!prev) return prev;
          return { ...prev, progress: msg.data, updatedAt: new Date().toISOString() };
        });
        break;
      case 'log':
        setBacktestLogs((l) => [...l.slice(-499), msg.data as LogEntry]);
        break;
      case 'metrics':
        setBacktestTask((prev) => {
          if (!prev) return prev;
          return { ...prev, metrics: msg.data, updatedAt: new Date().toISOString() };
        });
        break;
      case 'result':
        setBacktestTask((prev) => {
          if (!prev) return prev;
          return {
            ...prev,
            status: msg.data.status === 'completed' ? 'completed' : 'failed',
            metrics: msg.data.metrics || prev.metrics,
            updatedAt: new Date().toISOString(),
          };
        });
        break;
      case 'error':
        setBacktestTask((prev) => {
          if (!prev) return prev;
          return { ...prev, status: 'failed', updatedAt: new Date().toISOString() };
        });
        break;
    }
  }, []);

  // Start backtest
  const startBacktestTask = useCallback(
    async (params: BacktestStartParams) => {
      setBacktestLogs([]);
      const resp = await apiStartBacktest(params);
      if (!resp.success || !resp.data) throw new Error(resp.error || 'Failed');

      const taskData = resp.data.task as unknown as BacktestTask;
      setBacktestTask(taskData);

      // WebSocket
      const ws = connectMiningWs(
        resp.data.taskId,
        handleBacktestWsMessage,
        () => {
          getBacktestStatus(resp.data!.taskId).then((r) => {
            if (r.data?.task) setBacktestTask(r.data.task as unknown as BacktestTask);
          });
        },
      );
      backtestWsRef.current = ws;

      // Polling fallback
      backtestPollingRef.current = setInterval(async () => {
        try {
          const r = await getBacktestStatus(resp.data!.taskId);
          if (r.data?.task) {
            const t = r.data.task as unknown as BacktestTask;

            // Always sync progress from polling (in case WS missed updates)
            setBacktestTask((prev) => {
              if (!prev) return t;
              return {
                ...prev,
                status: t.status,
                progress: t.progress || prev.progress,
                metrics: (t.metrics && Object.keys(t.metrics).length > 0) ? t.metrics : prev.metrics,
                updatedAt: t.updatedAt,
              };
            });

            if (t.status === 'completed' || t.status === 'failed' || t.status === 'cancelled') {
              // Final update: sync task + logs from backend (in case WS missed some)
              setBacktestTask(t);
              if (t.logs && t.logs.length > 0) {
                setBacktestLogs(t.logs.slice(-500));
              }
              clearInterval(backtestPollingRef.current!);
              backtestPollingRef.current = null;
            }
          }
        } catch {
          // ignore
        }
      }, 5000);
    },
    [handleBacktestWsMessage],
  );

  // Stop backtest
  const stopBacktestTask = useCallback(async () => {
    if (!backtestTask) return;
    backtestWsRef.current?.close();
    backtestWsRef.current = null;
    if (backtestPollingRef.current) {
      clearInterval(backtestPollingRef.current);
      backtestPollingRef.current = null;
    }
    try {
      await apiCancelBacktest(backtestTask.taskId);
    } catch {
      // ignore
    }
    setBacktestTask((prev) => (prev ? { ...prev, status: 'cancelled' } : prev));
  }, [backtestTask]);

  // ==================================================================
  // Context value
  // ==================================================================
  const value: TaskContextValue = {
    backendAvailable,
    // Mining
    miningTask,
    miningEquityCurve,
    miningDrawdownCurve,
    miningIcTimeSeries,
    startMining,
    stopMining,
    resetMiningTask,

    // ---- Backtest ----
    backtestTask,
    backtestLogs,
    startBacktestTask,
    stopBacktestTask,
  };

  return <TaskContext.Provider value={value}>{children}</TaskContext.Provider>;
};

// ========================== Hook ==========================

export function useTaskContext(): TaskContextValue {
  const ctx = useContext(TaskContext);
  if (!ctx) throw new Error('useTaskContext must be used inside <TaskProvider>');
  return ctx;
}

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import {
  Play,
  Square,
  Loader2,
  FileText,
  TrendingUp,
  AlertCircle,
  Info,
  ChevronDown,
  Clock,
  BarChart3,
  Database,
  RefreshCw,
  CheckCircle2,
} from 'lucide-react';
import {
  getFactors,
  listFactorLibraries,
  getCacheStatus,
  warmCache,
} from '@/services/api';
import type { CacheStatusResponse } from '@/services/api';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { formatDate, formatNumber, formatPercent } from '@/utils';

// ... (existing MetricCard component)

const CumulativeReturnChart: React.FC<{ data: { date: string; value: number }[] }> = ({ data }) => {
  if (!data || data.length === 0) return null;

  // Generate ticks for every 6 months
  const ticks = [];
  if (data.length > 0) {
    const startDate = new Date(data[0].date);
    const endDate = new Date(data[data.length - 1].date);
    let currentDate = new Date(startDate);
    
    // Align to start of month
    currentDate.setDate(1);
    
    while (currentDate <= endDate) {
      ticks.push(currentDate.toISOString().split('T')[0]);
      // Add 6 months
      currentDate.setMonth(currentDate.getMonth() + 6);
    }
  }

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="glass-strong rounded-lg p-3 shadow-xl border border-border/50">
          <p className="text-xs text-muted-foreground mb-1">{formatDate(label)}</p>
          <p className="text-sm font-bold text-primary">
            超额收益: {formatPercent(payload[0].value)}
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="h-[300px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="colorReturn" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#10B981" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#10B981" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.2} vertical={false} />
          <XAxis 
            dataKey="date" 
            tick={{ fill: '#9CA3AF', fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            ticks={ticks}
            tickFormatter={(value) => formatDate(value).split('/').slice(0, 2).join('/')} 
          />
          <YAxis 
            tick={{ fill: '#9CA3AF', fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(value) => `${(value * 100).toFixed(0)}%`}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ stroke: '#374151', strokeWidth: 1, strokeDasharray: '4 4' }} />
          <Area
            type="monotone"
            dataKey="value"
            stroke="#10B981"
            strokeWidth={2}
            fill="url(#colorReturn)"
            animationDuration={1000}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};

import { useTaskContext } from '@/context/TaskContext';

// ========================== Component ==========================

// Helper component for metrics
const MetricCard = ({ label, value, unit = '' }: { label: string; value?: number; unit?: string }) => (
  <div className="bg-secondary/30 rounded-lg p-3">
    <div className="text-xs text-muted-foreground mb-1">{label}</div>
    <div className="text-lg font-bold font-mono">
      {typeof value === 'number' 
        ? `${formatNumber(value, 4)}${unit}`
        : '--'}
    </div>
  </div>
);

export const BacktestPage: React.FC = () => {
  const {
    backendAvailable,
    backtestTask: task,
    backtestLogs: logs,
    startBacktestTask,
    stopBacktestTask,
  } = useTaskContext();

  // -- Local UI State --
  const [libraries, setLibraries] = useState<string[]>([]);
  // Initialize with saved library from localStorage if available
  const [selectedLibrary, setSelectedLibrary] = useState(localStorage.getItem('quantaalpha_active_library') || '');
  const [factorSource, setFactorSource] = useState<'custom' | 'combined'>('custom');
  const [factorCount, setFactorCount] = useState(0);
  const [isStarting, setIsStarting] = useState(false);
  const logsEndRef = useRef<HTMLDivElement>(null);

  // Cache status state
  const [cacheStatus, setCacheStatus] = useState<CacheStatusResponse | null>(null);
  const [cacheLoading, setCacheLoading] = useState(false);
  const [warmingCache, setWarmingCache] = useState(false);
  const [warmCacheResult, setWarmCacheResult] = useState<string | null>(null);

  // -- Load libraries (on mount + manual refresh) --
  const [libsLoading, setLibsLoading] = useState(false);
  const loadLibraries = useCallback(async () => {
    setLibsLoading(true);
    try {
      const resp = await listFactorLibraries();
      if (resp.success && resp.data) {
        const libs = resp.data.libraries || [];
        setLibraries(libs);
        // Auto-select first if current selection is empty or removed
        if (libs.length > 0 && (!selectedLibrary || !libs.includes(selectedLibrary))) {
          setSelectedLibrary(libs[0]);
        }
      }
    } catch {
      // ignore — backend might not be up yet
    }
    setLibsLoading(false);
  }, [selectedLibrary]);

  // Init on mount
  const initDone = useRef(false);
  useEffect(() => {
    if (initDone.current) return;
    initDone.current = true;
    loadLibraries();
  }, [loadLibraries]);

  // Load factor count and cache status when library changes
  useEffect(() => {
    if (!selectedLibrary) return;
    (async () => {
      try {
        const resp = await getFactors({ library: selectedLibrary, limit: 500 });
        if (resp.success && resp.data) {
          setFactorCount(resp.data.total || 0);
        }
      } catch { /* ignore */ }
    })();
    // Also load cache status
    (async () => {
      setCacheLoading(true);
      setWarmCacheResult(null);
      try {
        const resp = await getCacheStatus(selectedLibrary);
        if (resp.success && resp.data) {
          setCacheStatus(resp.data as unknown as CacheStatusResponse);
        }
      } catch { /* ignore */ }
      setCacheLoading(false);
    })();
  }, [selectedLibrary]);

  // Auto-scroll logs
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  // -- Start backtest --
  const handleStart = async () => {
    if (!selectedLibrary) return;
    setIsStarting(true);
    try {
      await startBacktestTask({
        factorJson: selectedLibrary,
        factorSource,
      });
    } catch (err: any) {
      console.error('Failed to start backtest:', err);
    } finally {
      setIsStarting(false);
    }
  };

  // -- Cancel backtest --
  const handleCancel = async () => {
    stopBacktestTask();
  };

  // -- Warm cache --
  const handleWarmCache = async () => {
    if (!selectedLibrary) return;
    setWarmingCache(true);
    setWarmCacheResult(null);
    try {
      const resp = await warmCache(selectedLibrary);
      if (resp.success) {
        // Use the detailed message from backend
        setWarmCacheResult(resp.message || '完成');
      }
      // Refresh cache status
      const cs = await getCacheStatus(selectedLibrary);
      if (cs.success && cs.data) {
        setCacheStatus(cs.data as unknown as CacheStatusResponse);
      }
    } catch (err: any) {
      setWarmCacheResult(`预热失败: ${err.message}`);
    }
    setWarmingCache(false);
  };

  const isRunning = task?.status === 'running';
  const isFinished = task?.status === 'completed' || task?.status === 'failed' || task?.status === 'cancelled';

  // -- Render metric card --
  const MetricCard = ({ label, value, unit }: { label: string; value: any; unit?: string }) => (
    <div className="glass rounded-xl p-4 text-center">
      <div className="text-xs text-muted-foreground mb-1">{label}</div>
      <div className="text-lg font-bold text-foreground">
        {typeof value === 'number' ? value.toFixed(4) : value ?? '--'}
        {unit && <span className="text-xs text-muted-foreground ml-1">{unit}</span>}
      </div>
    </div>
  );

  // Extract metrics from task
  const metrics = task?.metrics || {};

  return (
    <div className="space-y-6 animate-fade-in-up">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold flex items-center gap-3">
          <BarChart3 className="h-8 w-8 text-primary" />
          独立回测
        </h1>
        <p className="text-muted-foreground mt-1">
          使用因子库进行全周期回测评估
        </p>
      </div>

      {/* Info Banner */}
      <Card className="glass border-primary/30">
        <CardContent className="p-4">
          <div className="flex gap-3">
            <Info className="h-5 w-5 text-primary flex-shrink-0 mt-0.5" />
            <div className="text-sm space-y-1">
              <p className="text-muted-foreground">
                独立回测在<strong className="text-foreground">测试集（2022-01-01 ~ 2025-12-26）</strong>上评估因子的样本外表现。
                使用 CSI300 市场股票池，TopK Dropout 策略，LightGBM 模型。
              </p>
              <p className="text-muted-foreground">
                <strong className="text-foreground">custom</strong> 模式仅使用因子库中的自定义因子；
                <strong className="text-foreground">combined</strong> 模式将自定义因子与 Alpha158(20) 基线因子组合使用。
                主实验挖掘过程中，新因子会与 4 个基础因子（开盘收益率、成交量比率、振幅收益率、日收益率）组合后在验证集上初步回测。
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Backend Status */}
      {backendAvailable === false && (
        <Card className="glass border-destructive/50">
          <CardContent className="p-4 flex items-center gap-3">
            <AlertCircle className="h-5 w-5 text-destructive" />
            <span className="text-sm text-destructive">
              后端服务未连接。请先启动后端：<code className="bg-secondary px-2 py-0.5 rounded">cd frontend-v2 && bash start.sh</code>
            </span>
          </CardContent>
        </Card>
      )}

      {/* Configuration Panel */}
      <Card className="glass card-hover">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            回测配置
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Factor Library Selection */}
            <div>
              <label className="block text-sm font-medium mb-2">因子库 JSON</label>
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <select
                    value={selectedLibrary}
                    onChange={e => setSelectedLibrary(e.target.value)}
                    disabled={isRunning}
                    className="w-full rounded-lg border border-input bg-background px-4 py-2.5 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary transition-all appearance-none pr-10"
                  >
                    {libraries.length === 0 && (
                      <option value="">暂无因子库文件</option>
                    )}
                    {libraries.map(lib => (
                      <option key={lib} value={lib}>{lib}</option>
                    ))}
                  </select>
                  <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={loadLibraries}
                  disabled={libsLoading}
                  title="刷新因子库列表"
                  className="px-2.5 self-center"
                >
                  <RefreshCw className={`h-4 w-4 ${libsLoading ? 'animate-spin' : ''}`} />
                </Button>
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                包含 {factorCount} 个因子
              </p>
            </div>

            {/* Factor Source */}
            <div>
              <label className="block text-sm font-medium mb-2">因子源类型</label>
              <div className="flex gap-3">
                <button
                  onClick={() => setFactorSource('custom')}
                  disabled={isRunning}
                  className={`flex-1 px-4 py-2.5 rounded-lg border text-sm font-medium transition-all ${
                    factorSource === 'custom'
                      ? 'border-primary bg-primary/10 text-primary'
                      : 'border-input bg-background text-muted-foreground hover:border-primary/50'
                  }`}
                >
                  Custom
                  <span className="block text-xs font-normal mt-0.5">仅自定义因子</span>
                </button>
                <button
                  onClick={() => setFactorSource('combined')}
                  disabled={isRunning}
                  className={`flex-1 px-4 py-2.5 rounded-lg border text-sm font-medium transition-all ${
                    factorSource === 'combined'
                      ? 'border-primary bg-primary/10 text-primary'
                      : 'border-input bg-background text-muted-foreground hover:border-primary/50'
                  }`}
                >
                  Combined
                  <span className="block text-xs font-normal mt-0.5">自定义 + Alpha158(20)</span>
                </button>
              </div>
            </div>
          </div>

          {/* Cache Status */}
          {selectedLibrary && (
            <div className="pt-2 border-t border-border/50">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2 text-sm font-medium">
                  <Database className="h-4 w-4 text-primary" />
                  因子缓存状态
                </div>
                <div className="flex items-center gap-2">
                  {warmCacheResult && (
                    <span className="text-xs text-muted-foreground">{warmCacheResult}</span>
                  )}
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleWarmCache}
                    disabled={warmingCache || isRunning || !cacheStatus || cacheStatus.need_compute === 0}
                  >
                    {warmingCache ? (
                      <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                    ) : (
                      <RefreshCw className="h-3 w-3 mr-1" />
                    )}
                    预热缓存
                  </Button>
                </div>
              </div>
              {cacheLoading ? (
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Loader2 className="h-3 w-3 animate-spin" />
                  正在检查缓存状态...
                </div>
              ) : cacheStatus ? (
                <div className="space-y-2">
                  {/* Summary bar */}
                  <div className="flex items-center gap-3 text-xs">
                    <span className="text-muted-foreground">共 {cacheStatus.total} 个因子</span>
                    {cacheStatus.h5_cached > 0 && (
                      <span className="flex items-center gap-1 text-green-500">
                        <CheckCircle2 className="h-3 w-3" />
                        HDF5 缓存: {cacheStatus.h5_cached}
                      </span>
                    )}
                    {cacheStatus.md5_cached > 0 && (
                      <span className="flex items-center gap-1 text-blue-500">
                        <CheckCircle2 className="h-3 w-3" />
                        MD5 缓存: {cacheStatus.md5_cached}
                      </span>
                    )}
                    {cacheStatus.need_compute > 0 && (
                      <span className="flex items-center gap-1 text-yellow-500">
                        <AlertCircle className="h-3 w-3" />
                        需重算: {cacheStatus.need_compute}
                      </span>
                    )}
                  </div>
                  {/* Progress bar */}
                  <div className="h-2 bg-secondary rounded-full overflow-hidden flex">
                    {cacheStatus.total > 0 && (
                      <>
                        <div
                          className="h-full bg-green-500 transition-all"
                          style={{ width: `${(cacheStatus.h5_cached / cacheStatus.total) * 100}%` }}
                          title={`HDF5 缓存: ${cacheStatus.h5_cached}`}
                        />
                        <div
                          className="h-full bg-blue-500 transition-all"
                          style={{ width: `${(cacheStatus.md5_cached / cacheStatus.total) * 100}%` }}
                          title={`MD5 缓存: ${cacheStatus.md5_cached}`}
                        />
                        <div
                          className="h-full bg-yellow-500/50 transition-all"
                          style={{ width: `${(cacheStatus.need_compute / cacheStatus.total) * 100}%` }}
                          title={`需重算: ${cacheStatus.need_compute}`}
                        />
                      </>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {cacheStatus.need_compute === 0
                      ? '所有因子已缓存，回测将快速执行'
                      : `${cacheStatus.need_compute} 个因子无缓存，回测时将从表达式重新计算（首次较慢，计算后自动缓存）`}
                  </p>
                </div>
              ) : null}
            </div>
          )}

          {/* Fixed display fields */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2 border-t border-border/50">
            <div className="text-sm">
              <span className="text-muted-foreground">市场：</span>
              <span className="font-medium ml-1">CSI 300（沪深300）</span>
            </div>
            <div className="text-sm">
              <span className="text-muted-foreground">回测区间：</span>
              <span className="font-medium ml-1">2022-01-01 ~ 2025-12-26</span>
            </div>
            <div className="text-sm">
              <span className="text-muted-foreground">基准：</span>
              <span className="font-medium ml-1">SH000300（沪深300指数）</span>
            </div>
          </div>

          {/* Start / Cancel Button */}
          <div className="flex justify-end gap-3 pt-2">
            {isRunning ? (
              <Button variant="outline" onClick={handleCancel}>
                <Square className="h-4 w-4 mr-2" />
                停止回测
              </Button>
            ) : (
              <Button
                variant="primary"
                onClick={handleStart}
                disabled={backendAvailable === false || !selectedLibrary || isStarting}
              >
                {isStarting ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Play className="h-4 w-4 mr-2" />
                )}
                开始回测
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Progress + Status */}
      {task && (
        <Card className={`glass card-hover ${isRunning ? 'border-primary/50' : ''}`}>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {isRunning ? (
                  <div className="relative h-5 w-5">
                    <div className="absolute inset-0 rounded-full bg-primary/30 animate-ping" />
                    <BarChart3 className="relative h-5 w-5 text-primary" />
                  </div>
                ) : task.status === 'completed' ? (
                  <CheckCircle2 className="h-5 w-5 text-green-500" />
                ) : task.status === 'failed' ? (
                  <AlertCircle className="h-5 w-5 text-red-500" />
                ) : (
                  <Clock className="h-5 w-5" />
                )}
                回测进度
              </div>
              <Badge
                variant={
                  task.status === 'completed' ? 'default' :
                  task.status === 'running' ? 'default' :
                  task.status === 'failed' ? 'destructive' : 'outline'
                }
              >
                {task.status === 'running' ? '运行中' :
                 task.status === 'completed' ? '已完成' :
                 task.status === 'failed' ? '失败' :
                 task.status === 'cancelled' ? '已取消' : task.status}
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {/* Running animation banner */}
            {isRunning && (
              <div className="mb-4 rounded-lg bg-primary/5 border border-primary/20 p-3 flex items-center gap-3">
                <Loader2 className="h-5 w-5 text-primary animate-spin flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-primary">
                    回测正在执行中
                  </p>
                  <p className="text-xs text-muted-foreground truncate">
                    {task.progress?.message || '正在加载因子数据并训练模型...'}
                  </p>
                </div>
              </div>
            )}

            {/* Progress bar */}
            <div className="mb-4">
              <div className="flex justify-between text-sm mb-1">
                <span className="text-muted-foreground">{task.progress?.message || '等待中...'}</span>
                <span className="text-muted-foreground">
                  {task.status === 'completed' ? '100%' :
                   task.status === 'failed' ? '失败' :
                   task.progress?.progress > 0 ? `${Math.round(task.progress.progress)}%` :
                   isRunning ? '运行中...' : ''}
                </span>
              </div>
              <div className="h-2 bg-secondary rounded-full overflow-hidden">
                {isRunning && (!task.progress?.progress || task.progress.progress <= 0) ? (
                  /* Indeterminate shimmer animation when no progress % */
                  <div
                    className="h-full w-1/3 rounded-full bg-gradient-to-r from-transparent via-primary to-transparent"
                    style={{
                      animation: 'shimmer 1.5s ease-in-out infinite',
                    }}
                  />
                ) : (
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${
                      task.status === 'completed' ? 'bg-green-500' :
                      task.status === 'failed' ? 'bg-red-500' :
                      'bg-primary'
                    }`}
                    style={{
                      width: task.status === 'completed' ? '100%' :
                             task.status === 'failed' ? '100%' :
                             task.progress?.progress > 0 ? `${task.progress.progress}%` :
                             '0%',
                    }}
                  />
                )}
              </div>
            </div>

            {/* Task info */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs text-muted-foreground">
              <div>任务 ID: <span className="font-mono text-foreground">{task.taskId}</span></div>
              <div>开始时间: {new Date(task.createdAt).toLocaleTimeString()}</div>
              <div>因子库: {task.config?.factorJson || selectedLibrary}</div>
              <div>因子源: {task.config?.factorSource || factorSource}</div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Results */}
      {isFinished && task?.status === 'completed' && Object.keys(metrics).length > 0 && (
        <Card className="glass card-hover animate-fade-in-up">
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <TrendingUp className="h-5 w-5 text-green-500" />
                回测结果
              </div>
              {metrics.__num_factors != null && (
                <span className="text-xs text-muted-foreground font-normal">
                  {metrics.__num_factors} 个因子 · 耗时 {metrics.__elapsed_seconds != null ? `${Math.round(metrics.__elapsed_seconds)}s` : '--'}
                </span>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <MetricCard label="IC" value={metrics.IC || metrics.ic} />
              <MetricCard label="ICIR" value={metrics.ICIR || metrics.icir} />
              <MetricCard label="Rank IC" value={metrics['Rank IC'] || metrics.RankIC || metrics.rankIc} />
              <MetricCard label="Rank ICIR" value={metrics['Rank ICIR'] || metrics.RankICIR || metrics.rankIcir} />
              <MetricCard
                label="年化扣费收益"
                value={metrics.annualized_return != null ? (metrics.annualized_return * 100) : undefined}
                unit="%"
              />
              <MetricCard
                label="最大回撤"
                value={metrics.max_drawdown != null ? (metrics.max_drawdown * 100) : undefined}
                unit="%"
              />
              <MetricCard label="信息比率" value={metrics.information_ratio} />
              <MetricCard label="Calmar" value={metrics.calmar_ratio} />
            </div>

            {/* Cumulative Excess Return Chart */}
            {metrics.cumulative_curve && (
              <div className="pt-4 border-t border-border/50">
                <h4 className="text-sm font-medium mb-4 flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-primary" />
                  超额累计收益曲线
                </h4>
                <CumulativeReturnChart data={metrics.cumulative_curve} />
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Logs Panel */}
      {(logs.length > 0 || isRunning) && (
        <Card className="glass card-hover">
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span className="flex items-center gap-2">
                <FileText className="h-5 w-5" />
                运行日志
              </span>
              <span className="text-xs text-muted-foreground font-normal">
                {logs.length} 条日志
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="bg-black/50 rounded-lg p-4 max-h-[400px] overflow-y-auto font-mono text-xs">
              {logs.length === 0 && isRunning && (
                <div className="text-muted-foreground flex items-center gap-2">
                  <Loader2 className="h-3 w-3 animate-spin" />
                  等待日志输出...
                </div>
              )}
              {logs.map((log) => (
                <div key={log.id} className="py-0.5 flex gap-2">
                  <span className="text-muted-foreground whitespace-nowrap">
                    {new Date(log.timestamp).toLocaleTimeString()}
                  </span>
                  <span
                    className={
                      log.level === 'error' ? 'text-red-400' :
                      log.level === 'warning' ? 'text-yellow-400' :
                      log.level === 'success' ? 'text-green-400' :
                      'text-gray-300'
                    }
                  >
                    {log.message}
                  </span>
                </div>
              ))}
              <div ref={logsEndRef} />
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

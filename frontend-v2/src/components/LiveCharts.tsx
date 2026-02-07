import React, { useMemo, useRef, useEffect } from 'react';
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { TimeSeriesData, RealtimeMetrics, LogEntry } from '@/types';
import { formatNumber, formatPercent, formatDate, formatDateTime } from '@/utils';
import { TrendingUp, Activity, BarChart3, Target } from 'lucide-react';

interface LiveChartsProps {
  equityCurve: TimeSeriesData[];
  drawdownCurve: TimeSeriesData[];
  metrics: RealtimeMetrics | null;
  isRunning: boolean;
  logs: LogEntry[];
}

export const LiveCharts: React.FC<LiveChartsProps> = ({
  equityCurve,
  drawdownCurve,
  metrics,
  isRunning,
  logs,
}) => {
  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const getLogIcon = (level: LogEntry['level']) => {
    switch (level) {
      case 'success': return '✅';
      case 'error': return '❌';
      case 'warning': return '⚠️';
      default: return '•';
    }
  };

  const getLogColor = (level: LogEntry['level']) => {
    switch (level) {
      case 'success': return 'text-success';
      case 'error': return 'text-destructive';
      case 'warning': return 'text-warning';
      default: return 'text-muted-foreground';
    }
  };

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="glass-strong rounded-lg p-3 shadow-xl">
          <p className="text-xs text-muted-foreground mb-1">{formatDate(label)}</p>
          <p className="text-sm font-bold text-primary">
            {payload[0].name}: {formatNumber(payload[0].value, 4)}
          </p>
        </div>
      );
    }
    return null;
  };

  const QualityTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="glass-strong rounded-lg p-3 shadow-xl">
          <p className="text-sm font-bold text-primary">
            {label}: {payload[0].value}
          </p>
        </div>
      );
    }
    return null;
  };

  const StatCard = ({ icon: Icon, label, value, trend, color }: any) => (
    <div className="glass rounded-xl p-4 card-hover">
      <div className="flex items-start justify-between mb-2">
        <div className={`p-2 rounded-lg ${color} bg-opacity-20`}>
          <Icon className={`h-5 w-5 ${color}`} />
        </div>
        {trend !== undefined && (
          <Badge variant={trend > 0 ? 'success' : 'destructive'} className="text-xs">
            {trend > 0 ? '+' : ''}{formatPercent(trend, 1)}
          </Badge>
        )}
      </div>
      <div className="text-xs text-muted-foreground mb-1">{label}</div>
      <div className="text-2xl font-bold">{value}</div>
    </div>
  );

  const qualityData = useMemo(() => {
    if (!metrics) return [];
    return [
      { name: '高质量', value: metrics.highQualityFactors || 0, fill: '#10B981' },
      { name: '中等', value: metrics.mediumQualityFactors || 0, fill: '#F59E0B' },
      { name: '低质量', value: metrics.lowQualityFactors || 0, fill: '#EF4444' },
    ];
  }, [metrics]);

  return (
    <div className="space-y-4">
      {/* Key Metrics Row */}
      {metrics && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 animate-fade-in-up">
          <StatCard
            icon={TrendingUp}
            label="年化收益"
            value={formatPercent(metrics.annualReturn)}
            trend={metrics.annualReturn}
            color="text-success"
          />
          <StatCard
            icon={Activity}
            label="RankIC"
            value={formatNumber(metrics.rankIc, 4)}
            color="text-primary"
          />
          <StatCard
            icon={BarChart3}
            label="夏普比率"
            value={formatNumber(metrics.sharpeRatio, 2)}
            color="text-warning"
          />
          <StatCard
            icon={Target}
            label="最大回撤"
            value={formatPercent(metrics.maxDrawdown)}
            trend={metrics.maxDrawdown}
            color="text-destructive"
          />
        </div>
      )}

      {/* Main Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        
        {/* Real-time Logs (Full Width) */}
        <Card className="glass card-hover animate-fade-in-left lg:col-span-2">
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              实时日志
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[300px] overflow-y-auto rounded-lg bg-yellow-50 p-3 font-mono text-xs space-y-1 border border-yellow-100">
              {logs.length === 0 ? (
                <div className="flex h-full items-center justify-center text-muted-foreground">
                  等待日志输出...
                </div>
              ) : (
                <>
                  {logs.map((log) => (
                    <div key={log.id} className="flex gap-2 items-start animate-fade-in-up">
                      <span className="text-muted-foreground shrink-0">
                        {formatDateTime(log.timestamp).split(' ')[1]}
                      </span>
                      <span className="shrink-0">{getLogIcon(log.level)}</span>
                      <span className={getLogColor(log.level)}>{log.message}</span>
                    </div>
                  ))}
                  <div ref={logsEndRef} />
                </>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Equity Curve (Left) */}
        <Card className="glass card-hover animate-fade-in-left">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                <div className="h-2 w-2 rounded-full bg-primary animate-pulse" />
                净值曲线
              </CardTitle>
              {isRunning && (
                <Badge variant="default" className="animate-pulse">实时更新</Badge>
              )}
            </div>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={240}>
              <AreaChart data={equityCurve}>
                <defs>
                  <linearGradient id="colorEquity" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#3B82F6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
                <XAxis
                  dataKey="date"
                  tick={{ fill: '#9CA3AF', fontSize: 11 }}
                  tickFormatter={(value) => formatDate(value).split('/').slice(1).join('/')}
                />
                <YAxis
                  tick={{ fill: '#9CA3AF', fontSize: 11 }}
                  tickFormatter={(value) => formatNumber(value, 2)}
                />
                <Tooltip content={<CustomTooltip />} />
                <Area
                  type="monotone"
                  dataKey="value"
                  stroke="#3B82F6"
                  strokeWidth={2.5}
                  fill="url(#colorEquity)"
                  animationDuration={300}
                />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Drawdown Curve (Right) */}
        <Card className="glass card-hover animate-fade-in-right">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                <div className="h-2 w-2 rounded-full bg-destructive animate-pulse" />
                回撤分析
              </CardTitle>
              {metrics && (
                <span className="text-xs text-muted-foreground">
                  最大: {formatPercent(metrics.maxDrawdown)}
                </span>
              )}
            </div>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={240}>
              <AreaChart data={drawdownCurve}>
                <defs>
                  <linearGradient id="colorDrawdown" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#EF4444" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#EF4444" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
                <XAxis
                  dataKey="date"
                  tick={{ fill: '#9CA3AF', fontSize: 11 }}
                  tickFormatter={(value) => formatDate(value).split('/').slice(1).join('/')}
                />
                <YAxis
                  tick={{ fill: '#9CA3AF', fontSize: 11 }}
                  tickFormatter={(value) => formatPercent(value)}
                />
                <Tooltip content={<CustomTooltip />} />
                <Area
                  type="monotone"
                  dataKey="value"
                  stroke="#EF4444"
                  strokeWidth={2.5}
                  fill="url(#colorDrawdown)"
                  animationDuration={300}
                />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Quality Distribution (Bottom, Full Width) */}
        <Card className="glass card-hover animate-fade-in-up lg:col-span-2">
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <div className="h-2 w-2 rounded-full bg-success animate-pulse" />
              因子质量分布
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={qualityData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
                <XAxis dataKey="name" tick={{ fill: '#9CA3AF', fontSize: 11 }} />
                <YAxis tick={{ fill: '#9CA3AF', fontSize: 11 }} />
                <Tooltip content={<QualityTooltip />} />
                <Bar dataKey="value" radius={[4, 4, 0, 0]} animationDuration={500} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

      </div>
    </div>
  );
};

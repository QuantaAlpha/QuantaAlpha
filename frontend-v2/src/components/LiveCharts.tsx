import React, { useMemo } from 'react';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { TimeSeriesData, RealtimeMetrics } from '@/types';
import { formatNumber, formatPercent, formatDate } from '@/utils';
import { TrendingUp, Activity, BarChart3, Target } from 'lucide-react';

interface LiveChartsProps {
  equityCurve: TimeSeriesData[];
  drawdownCurve: TimeSeriesData[];
  icTimeSeries: TimeSeriesData[];
  metrics: RealtimeMetrics | null;
  isRunning: boolean;
}

export const LiveCharts: React.FC<LiveChartsProps> = ({
  equityCurve,
  drawdownCurve,
  icTimeSeries,
  metrics,
  isRunning,
}) => {
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
        {/* Equity Curve */}
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

        {/* Drawdown Curve */}
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

        {/* IC Time Series */}
        <Card className="glass card-hover animate-fade-in-left lg:col-span-2">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                <div className="h-2 w-2 rounded-full bg-success animate-pulse" />
                IC 时序分析
              </CardTitle>
              {metrics && (
                <div className="flex gap-3 text-xs">
                  <span className="text-muted-foreground">
                    IC: <span className="text-foreground font-mono">{formatNumber(metrics.ic, 4)}</span>
                  </span>
                  <span className="text-muted-foreground">
                    ICIR: <span className="text-foreground font-mono">{formatNumber(metrics.icir, 3)}</span>
                  </span>
                </div>
              )}
            </div>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={icTimeSeries}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
                <XAxis
                  dataKey="date"
                  tick={{ fill: '#9CA3AF', fontSize: 11 }}
                  tickFormatter={(value) => formatDate(value).split('/').slice(1).join('/')}
                />
                <YAxis
                  tick={{ fill: '#9CA3AF', fontSize: 11 }}
                  tickFormatter={(value) => formatNumber(value, 3)}
                />
                <Tooltip content={<CustomTooltip />} />
                <Line
                  type="monotone"
                  dataKey="value"
                  stroke="#10B981"
                  strokeWidth={2}
                  dot={false}
                  animationDuration={300}
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Factor Quality Distribution */}
      {metrics && (
        <Card className="glass card-hover animate-fade-in-up">
          <CardHeader className="pb-3">
            <CardTitle className="text-base">因子质量分布</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">总因子数</span>
                <span className="text-2xl font-bold">{metrics.totalFactors}</span>
              </div>

              {/* Quality Bar */}
              <div className="relative h-8 rounded-full overflow-hidden bg-secondary/30">
                <div
                  className="absolute left-0 top-0 h-full bg-success transition-all duration-500"
                  style={{ width: `${(metrics.highQualityFactors / metrics.totalFactors) * 100}%` }}
                />
                <div
                  className="absolute left-0 top-0 h-full bg-warning transition-all duration-500"
                  style={{
                    left: `${(metrics.highQualityFactors / metrics.totalFactors) * 100}%`,
                    width: `${(metrics.mediumQualityFactors / metrics.totalFactors) * 100}%`,
                  }}
                />
                <div
                  className="absolute left-0 top-0 h-full bg-destructive transition-all duration-500"
                  style={{
                    left: `${((metrics.highQualityFactors + metrics.mediumQualityFactors) / metrics.totalFactors) * 100}%`,
                    width: `${(metrics.lowQualityFactors / metrics.totalFactors) * 100}%`,
                  }}
                />
              </div>

              {/* Quality Labels */}
              <div className="grid grid-cols-3 gap-3 text-xs">
                <div className="flex items-center gap-2">
                  <div className="h-3 w-3 rounded-full bg-success" />
                  <span className="text-muted-foreground">高质量</span>
                  <span className="ml-auto font-bold text-success">{metrics.highQualityFactors}</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="h-3 w-3 rounded-full bg-warning" />
                  <span className="text-muted-foreground">中等</span>
                  <span className="ml-auto font-bold text-warning">{metrics.mediumQualityFactors}</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="h-3 w-3 rounded-full bg-destructive" />
                  <span className="text-muted-foreground">低质量</span>
                  <span className="ml-auto font-bold text-destructive">{metrics.lowQualityFactors}</span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

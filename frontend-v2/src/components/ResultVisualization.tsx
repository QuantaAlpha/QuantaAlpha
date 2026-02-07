import React from 'react';
import {
  LineChart,
  Line,
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
import { BacktestResult } from '@/types';
import { formatNumber, formatPercent, formatDate } from '@/utils';

interface ResultVisualizationProps {
  result: BacktestResult | null;
}

export const ResultVisualization: React.FC<ResultVisualizationProps> = ({ result }) => {
  if (!result) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>📊 最终结果展示</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex h-[400px] items-center justify-center text-muted-foreground">
            等待任务完成...
          </div>
        </CardContent>
      </Card>
    );
  }

  const qualityData = [
    { name: '高质量', value: result.qualityDistribution.high, fill: '#10B981' },
    { name: '中等', value: result.qualityDistribution.medium, fill: '#F59E0B' },
    { name: '低质量', value: result.qualityDistribution.low, fill: '#EF4444' },
  ];

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>📊 最终结果展示</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            {/* 净值曲线 */}
            <div>
              <h4 className="mb-3 text-sm font-medium">净值曲线</h4>
              <ResponsiveContainer width="100%" height={250}>
                <AreaChart data={result.equityCurve}>
                  <defs>
                    <linearGradient id="colorEquity" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#3B82F6" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis
                    dataKey="date"
                    tick={{ fill: '#9CA3AF', fontSize: 12 }}
                    tickFormatter={(value) => formatDate(value)}
                  />
                  <YAxis
                    tick={{ fill: '#9CA3AF', fontSize: 12 }}
                    tickFormatter={(value) => formatNumber(value, 2)}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1F2937',
                      border: '1px solid #374151',
                      borderRadius: '0.5rem',
                    }}
                    labelFormatter={(value) => formatDate(value)}
                    formatter={(value: number) => [formatNumber(value, 2), '净值']}
                  />
                  <Area
                    type="monotone"
                    dataKey="value"
                    stroke="#3B82F6"
                    strokeWidth={2}
                    fill="url(#colorEquity)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            {/* 回撤曲线 */}
            <div>
              <h4 className="mb-3 text-sm font-medium">回撤分析</h4>
              <ResponsiveContainer width="100%" height={250}>
                <AreaChart data={result.drawdownCurve}>
                  <defs>
                    <linearGradient id="colorDrawdown" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#EF4444" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#EF4444" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis
                    dataKey="date"
                    tick={{ fill: '#9CA3AF', fontSize: 12 }}
                    tickFormatter={(value) => formatDate(value)}
                  />
                  <YAxis
                    tick={{ fill: '#9CA3AF', fontSize: 12 }}
                    tickFormatter={(value) => formatPercent(value)}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1F2937',
                      border: '1px solid #374151',
                      borderRadius: '0.5rem',
                    }}
                    labelFormatter={(value) => formatDate(value)}
                    formatter={(value: number) => [formatPercent(value), '回撤']}
                  />
                  <Area
                    type="monotone"
                    dataKey="value"
                    stroke="#EF4444"
                    strokeWidth={2}
                    fill="url(#colorDrawdown)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            {/* IC 时序 */}
            <div>
              <h4 className="mb-3 text-sm font-medium">IC 时序</h4>
              <ResponsiveContainer width="100%" height={250}>
                <LineChart data={result.icTimeSeries}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis
                    dataKey="date"
                    tick={{ fill: '#9CA3AF', fontSize: 12 }}
                    tickFormatter={(value) => formatDate(value)}
                  />
                  <YAxis tick={{ fill: '#9CA3AF', fontSize: 12 }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1F2937',
                      border: '1px solid #374151',
                      borderRadius: '0.5rem',
                    }}
                    labelFormatter={(value) => formatDate(value)}
                    formatter={(value: number) => [formatNumber(value, 4), 'IC']}
                  />
                  <Line
                    type="monotone"
                    dataKey="value"
                    stroke="#10B981"
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>

            {/* 因子质量分布 */}
            <div>
              <h4 className="mb-3 text-sm font-medium">因子质量分布</h4>
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={qualityData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis dataKey="name" tick={{ fill: '#9CA3AF', fontSize: 12 }} />
                  <YAxis tick={{ fill: '#9CA3AF', fontSize: 12 }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1F2937',
                      border: '1px solid #374151',
                      borderRadius: '0.5rem',
                    }}
                    formatter={(value: number) => [value, '数量']}
                  />
                  <Bar dataKey="value" radius={[8, 8, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 因子列表 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">🎯 生成因子列表 (Top 10)</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="pb-2 text-left font-medium text-muted-foreground">因子名称</th>
                  <th className="pb-2 text-left font-medium text-muted-foreground">质量</th>
                  <th className="pb-2 text-right font-medium text-muted-foreground">RankIC</th>
                  <th className="pb-2 text-right font-medium text-muted-foreground">RankICIR</th>
                  <th className="pb-2 text-left font-medium text-muted-foreground">轮次</th>
                </tr>
              </thead>
              <tbody>
                {result.factors.slice(0, 10).map((factor) => (
                  <tr key={factor.factorId} className="border-b border-border/50">
                    <td className="py-3">
                      <div>
                        <div className="font-medium">{factor.factorName}</div>
                        <div className="mt-1 text-xs text-muted-foreground">
                          {factor.factorExpression.substring(0, 50)}...
                        </div>
                      </div>
                    </td>
                    <td className="py-3">
                      <span
                        className={`inline-block rounded-full px-2 py-1 text-xs font-medium ${
                          factor.quality === 'high'
                            ? 'bg-success/20 text-success'
                            : factor.quality === 'medium'
                            ? 'bg-warning/20 text-warning'
                            : 'bg-destructive/20 text-destructive'
                        }`}
                      >
                        {factor.quality === 'high' ? '高' : factor.quality === 'medium' ? '中' : '低'}
                      </span>
                    </td>
                    <td className="py-3 text-right font-mono">{formatNumber(factor.rankIc, 4)}</td>
                    <td className="py-3 text-right font-mono">{formatNumber(factor.rankIcir, 3)}</td>
                    <td className="py-3 text-muted-foreground">Round {factor.round}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

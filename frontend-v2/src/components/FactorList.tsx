import React from 'react';
import {
  AreaChart,
  Area,
  ResponsiveContainer,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { HoverCard, HoverCardContent, HoverCardTrigger } from "@/components/ui/HoverCard";
import { RealtimeMetrics } from '@/types';
import { formatNumber, formatPercent } from '@/utils';
import { TrendingUp } from 'lucide-react';

interface FactorListProps {
  metrics: RealtimeMetrics | null;
}

export const FactorList: React.FC<FactorListProps> = ({ metrics }) => {
  const truncate = (str: string, max: number) => {
    if (!str) return '';
    return str.length > max ? str.substring(0, max) + '...' : str;
  };

  return (
    <Card className="glass card-hover animate-fade-in-up w-full">
      <CardHeader className="pb-3">
        <CardTitle className="text-base flex items-center gap-2">
          <div className="h-2 w-2 rounded-full bg-purple-500 animate-pulse" />
          当前因子库 RankIC Top 10
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border/50">
                <th className="py-3 px-4 text-left font-medium text-muted-foreground w-1/6">因子名</th>
                <th className="py-3 px-4 text-left font-medium text-muted-foreground w-1/4">公式</th>
                <th className="py-3 px-4 text-right font-medium text-muted-foreground">IC</th>
                <th className="py-3 px-4 text-right font-medium text-muted-foreground">RankIC</th>
                <th className="py-3 px-4 text-right font-medium text-muted-foreground">ICIR</th>
                <th className="py-3 px-4 text-right font-medium text-muted-foreground">RankICIR</th>
                 <th className="py-3 px-4 text-right font-medium text-muted-foreground">ARR</th>
                 <th className="py-3 px-4 text-right font-medium text-muted-foreground">MDD</th>
                 <th className="py-3 px-4 text-right font-medium text-muted-foreground">Sharpe</th>
               </tr>
             </thead>
             <tbody>
              {metrics?.top10Factors && metrics.top10Factors.length > 0 ? (
                metrics.top10Factors.map((factor, index) => (
                  <HoverCard key={index} openDelay={200}>
                    <HoverCardTrigger asChild>
                      <tr className="group hover:bg-muted/50 transition-colors border-b border-border/50 last:border-0 cursor-help">
                        <td className="py-3 px-4 font-medium max-w-[150px] truncate" title={factor.factorName}>
                          {truncate(factor.factorName, 15)}
                        </td>
                        <td className="py-3 px-4 font-mono text-xs text-muted-foreground max-w-[200px] truncate">
                          {truncate(factor.factorExpression, 30)}
                        </td>
                        <td className="py-3 px-4 text-right font-mono">{formatNumber(factor.ic, 4)}</td>
                        <td className="py-3 px-4 text-right font-mono font-bold text-primary">{formatNumber(factor.rankIc, 4)}</td>
                        <td className="py-3 px-4 text-right font-mono">{formatNumber(factor.icir, 2)}</td>
                        <td className="py-3 px-4 text-right font-mono">{formatNumber(factor.rankIcir, 2)}</td>
                        <td className="py-3 px-4 text-right font-mono text-success">{formatPercent(factor.annualReturn || 0)}</td>
                        <td className="py-3 px-4 text-right font-mono text-destructive">{formatPercent(factor.maxDrawdown || 0)}</td>
                        <td className="py-3 px-4 text-right font-mono">{formatNumber(factor.sharpeRatio || 0, 2)}</td>
                      </tr>
                    </HoverCardTrigger>
                    <HoverCardContent 
                      className="w-[400px] glass-strong p-4 shadow-xl border border-primary/20" 
                      side="top" 
                      align="center"
                      sideOffset={10}
                      collisionPadding={20}
                      avoidCollisions={true}
                      style={{ zIndex: 1000 }}
                    >
                      <div className="space-y-4">
                        <div>
                          <div className="flex items-center justify-between mb-2">
                            <h4 className="font-bold text-primary text-base">{factor.factorName}</h4>
                            <div className="px-2 py-0.5 rounded-full bg-primary/10 text-primary text-xs font-medium border border-primary/20">
                               Score: {formatNumber(factor.rankIc * 100, 1)}
                            </div>
                          </div>
                          <div className="p-3 bg-secondary/40 rounded-lg font-mono text-xs break-all border border-border/50 text-foreground/90 shadow-inner">
                            {factor.factorExpression}
                          </div>
                        </div>
                        
                        <div className="grid grid-cols-2 gap-3 p-3 bg-background/40 rounded-lg border border-border/30">
                          <div>
                            <span className="text-xs text-muted-foreground block mb-0.5">年化收益 (ARR)</span>
                            <span className="font-bold text-success text-sm">{formatPercent(factor.annualReturn || 0)}</span>
                          </div>
                          <div>
                            <span className="text-xs text-muted-foreground block mb-0.5">夏普比率 (Sharpe)</span>
                            <span className="font-bold text-sm">{formatNumber(factor.sharpeRatio || 0, 2)}</span>
                          </div>
                          <div>
                            <span className="text-xs text-muted-foreground block mb-0.5">最大回撤 (MDD)</span>
                            <span className="font-bold text-destructive text-sm">{formatPercent(factor.maxDrawdown || 0)}</span>
                          </div>
                          <div>
                            <span className="text-xs text-muted-foreground block mb-0.5">卡玛比率 (CR)</span>
                            <span className="font-bold text-primary text-sm">{formatNumber(factor.calmarRatio || 0, 2)}</span>
                          </div>
                        </div>

                      </div>
                    </HoverCardContent>
                  </HoverCard>
                ))
              ) : (
                <tr>
                  <td colSpan={9} className="py-8 text-center text-muted-foreground">
                    暂无因子数据
                  </td>
                </tr>
              )}

            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
};

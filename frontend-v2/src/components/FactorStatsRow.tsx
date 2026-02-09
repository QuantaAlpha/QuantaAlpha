import React, { useMemo } from 'react';
import { Layers, TrendingUp, BarChart3 } from 'lucide-react';
import { RealtimeMetrics } from '@/types';
import { formatPercent, formatNumber } from '@/utils';
import { Badge } from '@/components/ui/Badge';

interface FactorStatsRowProps {
  metrics: RealtimeMetrics | null;
  onBacktest?: () => void;
}

export const FactorStatsRow: React.FC<FactorStatsRowProps> = ({ metrics, onBacktest }) => {
  const qualityData = useMemo(() => {
    if (!metrics) return [];
    return [
      { name: '高质量', value: metrics.highQualityFactors || 0, fill: '#10B981' },
      { name: '中等', value: metrics.mediumQualityFactors || 0, fill: '#F59E0B' },
      { name: '低质量', value: metrics.lowQualityFactors || 0, fill: '#EF4444' },
    ];
  }, [metrics]);

  const StatCard = ({ icon: Icon, label, value, trend, color, className }: any) => (
    <div className={`glass rounded-xl p-4 card-hover h-[140px] flex flex-col justify-between ${className}`}>
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
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4 animate-fade-in-up w-full">
      {/* Total Factors Card */}
      <StatCard
         icon={Layers}
         label="因子总数量"
         value={metrics ? metrics.totalFactors : 0}
         color="text-primary"
         className="shadow-lg border-primary/10"
      />

      {qualityData.map((item) => (
         <StatCard
           key={item.name}
           icon={TrendingUp}
           label={`${item.name}因子数量`}
           value={item.value}
           color={item.name === '高质量' ? 'text-success' : item.name === '中等' ? 'text-warning' : 'text-destructive'}
           className="shadow-lg border-primary/10"
         />
      ))}
      
      {/* Quick Backtest Button */}
       <div 
          className="h-[140px] flex flex-col justify-center items-center cursor-pointer hover:scale-[1.05] transition-all group relative"
          onClick={onBacktest}
       >
          <div className="p-4 rounded-full bg-primary text-primary-foreground shadow-lg mb-3 z-10 group-hover:shadow-xl group-hover:bg-primary/90 transition-all duration-300">
            <BarChart3 className="h-6 w-6" />
          </div>
          <div className="text-sm font-bold text-foreground/80 group-hover:text-primary transition-colors">一键回测</div>
       </div>
    </div>
  );
};

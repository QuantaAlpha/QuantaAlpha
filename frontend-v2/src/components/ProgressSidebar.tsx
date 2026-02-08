import React from 'react';
import { Card, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { ExecutionProgress } from '@/types';
import { Sparkles, Brain, TrendingUp, CheckCircle2 } from 'lucide-react';

interface ProgressSidebarProps {
  progress: ExecutionProgress;
}

const phaseConfig = {
  parsing: { icon: Sparkles, label: '解析需求', color: 'text-blue-400' },
  planning: { icon: Brain, label: '规划方向', color: 'text-purple-400' },
  evolving: { icon: TrendingUp, label: '进化中', color: 'text-yellow-400' },
  backtesting: { icon: TrendingUp, label: '回测中', color: 'text-green-400' },
  analyzing: { icon: Brain, label: '分析结果', color: 'text-cyan-400' },
  completed: { icon: CheckCircle2, label: '完成', color: 'text-success' },
};

export const ProgressSidebar: React.FC<ProgressSidebarProps> = ({ progress }) => {
  const currentPhase = phaseConfig[progress.phase];
  const Icon = currentPhase.icon;

  return (
    <div className="space-y-4">
      {/* Phase Status */}
      <Card className="glass card-hover animate-fade-in-left h-[140px]">
        <CardContent className="p-4 h-full flex flex-col justify-center">
          <div className="flex items-center gap-3 mb-4">
            <div className={`p-3 rounded-xl bg-secondary/50 ${currentPhase.color}`}>
              <Icon className="h-6 w-6 animate-pulse" />
            </div>
            <div className="flex-1">
              <div className="text-sm font-medium mb-1">{currentPhase.label}</div>
              <div className="text-xs text-muted-foreground">
                Round {progress.currentRound}/{progress.totalRounds}
              </div>
            </div>
            <Badge variant="default" className="animate-pulse">
              {progress.progress.toFixed(0)}%
            </Badge>
          </div>

          {/* Progress Bar */}
          <div className="relative h-2 rounded-full overflow-hidden bg-secondary/30 mb-2">
            <div
              className="absolute left-0 top-0 h-full progress-gradient transition-all duration-500"
              style={{ width: `${progress.progress}%` }}
            />
          </div>
        </CardContent>
      </Card>

      {/* Timeline */}
      <Card className="glass card-hover animate-fade-in-left h-[400px]" style={{ animationDelay: '0.1s' }}>
        <CardContent className="p-4 h-full flex flex-col">
          <div className="text-sm font-medium mb-4">执行时间线</div>
          <div className="flex-1 flex flex-col justify-between relative">
            {/* Vertical Connecting Line */}
            <div className="absolute left-[15px] top-4 bottom-4 w-[2px] bg-gradient-to-b from-secondary/50 via-secondary to-secondary/50" />
            
            {Object.entries(phaseConfig).map(([phase, config]) => {
              const isActive = phase === progress.phase;
              const isPassed = Object.keys(phaseConfig).indexOf(phase) < Object.keys(phaseConfig).indexOf(progress.phase);
              const PhaseIcon = config.icon;

              return (
                <div key={phase} className="flex items-center gap-4 relative z-10 bg-background/50 backdrop-blur-[2px] rounded-lg p-1 -ml-1">
                  <div
                    className={`flex h-8 w-8 items-center justify-center rounded-full border-2 transition-all ${
                      isActive
                        ? 'border-primary bg-primary text-primary-foreground shadow-[0_0_10px_rgba(59,130,246,0.5)] scale-110'
                        : isPassed
                        ? 'border-success bg-success/10 text-success'
                        : 'border-muted bg-background text-muted-foreground'
                    }`}
                  >
                    {isPassed ? (
                      <CheckCircle2 className="h-4 w-4" />
                    ) : (
                      <PhaseIcon className={`h-4 w-4 ${isActive ? 'animate-pulse' : ''}`} />
                    )}
                  </div>
                  <div className="flex-1">
                    <div className={`text-sm transition-colors ${isActive ? 'font-bold text-primary' : isPassed ? 'text-foreground' : 'text-muted-foreground'}`}>
                      {config.label}
                    </div>
                  </div>
                  {isActive && (
                    <div className="flex items-center gap-2">
                      <span className="relative flex h-3 w-3">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-3 w-3 bg-primary"></span>
                      </span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

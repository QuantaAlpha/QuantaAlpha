import React, { useEffect, useRef } from 'react';
import { Card, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { ExecutionProgress, LogEntry } from '@/types';
import { formatDateTime } from '@/utils';
import { Sparkles, Brain, TrendingUp, CheckCircle2 } from 'lucide-react';

interface ProgressSidebarProps {
  progress: ExecutionProgress;
  logs: LogEntry[];
}

const phaseConfig = {
  parsing: { icon: Sparkles, label: '解析需求', color: 'text-blue-400' },
  planning: { icon: Brain, label: '规划方向', color: 'text-purple-400' },
  evolving: { icon: TrendingUp, label: '进化中', color: 'text-yellow-400' },
  backtesting: { icon: TrendingUp, label: '回测中', color: 'text-green-400' },
  analyzing: { icon: Brain, label: '分析结果', color: 'text-cyan-400' },
  completed: { icon: CheckCircle2, label: '完成', color: 'text-success' },
};

export const ProgressSidebar: React.FC<ProgressSidebarProps> = ({ progress, logs }) => {
  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const currentPhase = phaseConfig[progress.phase];
  const Icon = currentPhase.icon;

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

  return (
    <div className="space-y-4">
      {/* Phase Status */}
      <Card className="glass card-hover animate-fade-in-left">
        <CardContent className="p-4">
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

          <p className="text-xs text-muted-foreground">{progress.message}</p>
        </CardContent>
      </Card>

      {/* Timeline */}
      <Card className="glass card-hover animate-fade-in-left" style={{ animationDelay: '0.1s' }}>
        <CardContent className="p-4">
          <div className="text-sm font-medium mb-3">执行时间线</div>
          <div className="space-y-3">
            {Object.entries(phaseConfig).map(([phase, config], idx) => {
              const isActive = phase === progress.phase;
              const isPassed = Object.keys(phaseConfig).indexOf(phase) < Object.keys(phaseConfig).indexOf(progress.phase);
              const PhaseIcon = config.icon;

              return (
                <div key={phase} className="flex items-center gap-3">
                  <div
                    className={`flex h-8 w-8 items-center justify-center rounded-full transition-all ${
                      isActive
                        ? 'bg-primary text-primary-foreground scale-110'
                        : isPassed
                        ? 'bg-success/20 text-success'
                        : 'bg-secondary/30 text-muted-foreground'
                    }`}
                  >
                    {isPassed ? (
                      <CheckCircle2 className="h-4 w-4" />
                    ) : (
                      <PhaseIcon className={`h-4 w-4 ${isActive ? 'animate-pulse' : ''}`} />
                    )}
                  </div>
                  <div className="flex-1">
                    <div className={`text-sm ${isActive ? 'font-medium' : ''}`}>
                      {config.label}
                    </div>
                  </div>
                  {isActive && (
                    <div className="h-2 w-2 rounded-full bg-primary animate-pulse" />
                  )}
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Logs */}
      <Card className="glass card-hover animate-fade-in-left" style={{ animationDelay: '0.2s' }}>
        <CardContent className="p-4">
          <div className="text-sm font-medium mb-3">实时日志</div>
          <div className="h-[200px] overflow-y-auto rounded-lg bg-secondary/20 p-3 font-mono text-xs space-y-1">
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
    </div>
  );
};

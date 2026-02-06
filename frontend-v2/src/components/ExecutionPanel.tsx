import React, { useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Progress } from '@/components/ui/Progress';
import { ExecutionProgress, LogEntry } from '@/types';
import { formatDateTime } from '@/utils';

interface ExecutionPanelProps {
  progress: ExecutionProgress;
  logs: LogEntry[];
}

const phaseLabels: Record<string, string> = {
  parsing: '🤔 解析需求',
  planning: '📋 规划方向',
  evolving: '🧬 进化中',
  backtesting: '📊 回测中',
  analyzing: '🔍 分析结果',
  completed: '✅ 完成',
};

const phaseColors: Record<string, 'default' | 'success' | 'warning'> = {
  parsing: 'default',
  planning: 'default',
  evolving: 'warning',
  backtesting: 'warning',
  analyzing: 'default',
  completed: 'success',
};

export const ExecutionPanel: React.FC<ExecutionPanelProps> = ({ progress, logs }) => {
  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const getLogIcon = (level: LogEntry['level']) => {
    switch (level) {
      case 'success':
        return '✅';
      case 'error':
        return '❌';
      case 'warning':
        return '⚠️';
      default:
        return '📝';
    }
  };

  const getLogColor = (level: LogEntry['level']) => {
    switch (level) {
      case 'success':
        return 'text-success';
      case 'error':
        return 'text-destructive';
      case 'warning':
        return 'text-warning';
      default:
        return 'text-muted-foreground';
    }
  };

  return (
    <Card className="h-full">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">🔄 执行进度</CardTitle>
          <Badge variant={phaseColors[progress.phase]}>
            {phaseLabels[progress.phase]}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* 进度信息 */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">
              Round {progress.currentRound}/{progress.totalRounds}
            </span>
            <span className="font-medium">{progress.progress.toFixed(0)}%</span>
          </div>
          <Progress value={progress.progress} />
          <p className="text-xs text-muted-foreground">{progress.message}</p>
        </div>

        {/* 日志流 */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-medium">实时日志</h4>
            <span className="text-xs text-muted-foreground">
              最近 {logs.length} 条
            </span>
          </div>
          <div className="h-[300px] overflow-y-auto rounded-md border border-border bg-secondary/20 p-3 font-mono text-xs">
            {logs.length === 0 ? (
              <div className="flex h-full items-center justify-center text-muted-foreground">
                等待日志输出...
              </div>
            ) : (
              <div className="space-y-1">
                {logs.map((log) => (
                  <div key={log.id} className="flex gap-2">
                    <span className="text-muted-foreground">
                      {formatDateTime(log.timestamp).split(' ')[1]}
                    </span>
                    <span>{getLogIcon(log.level)}</span>
                    <span className={getLogColor(log.level)}>{log.message}</span>
                  </div>
                ))}
                <div ref={logsEndRef} />
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

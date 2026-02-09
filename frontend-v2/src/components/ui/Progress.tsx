import React from 'react';
import { cn } from '@/utils';

interface ProgressProps {
  value: number; // 0-100
  className?: string;
  showLabel?: boolean;
}

export const Progress: React.FC<ProgressProps> = ({ value, className, showLabel = false }) => {
  const clampedValue = Math.min(Math.max(value, 0), 100);

  return (
    <div className={cn('w-full', className)}>
      <div className="relative h-2 w-full overflow-hidden rounded-full bg-secondary">
        <div
          className="h-full bg-primary transition-all duration-300 ease-in-out"
          style={{ width: `${clampedValue}%` }}
        />
      </div>
      {showLabel && (
        <div className="mt-1 text-right text-xs text-muted-foreground">
          {clampedValue.toFixed(0)}%
        </div>
      )}
    </div>
  );
};

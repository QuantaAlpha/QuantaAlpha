import React from 'react';
import { cn } from '@/utils';

interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'success' | 'warning' | 'destructive' | 'outline';
  children: React.ReactNode;
}

export const Badge = React.forwardRef<HTMLDivElement, BadgeProps>(
  ({ className, variant = 'default', children, ...props }, ref) => {
    const variants = {
      default: 'bg-primary/20 text-primary border-primary/50',
      success: 'bg-success/20 text-success border-success/50',
      warning: 'bg-warning/20 text-warning border-warning/50',
      destructive: 'bg-destructive/20 text-destructive border-destructive/50',
      outline: 'border-border text-foreground',
    };

    return (
      <div
        ref={ref}
        className={cn(
          'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors',
          variants[variant],
          className
        )}
        {...props}
      >
        {children}
      </div>
    );
  }
);

Badge.displayName = 'Badge';

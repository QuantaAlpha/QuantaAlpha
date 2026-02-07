import React from 'react';
import { Sparkles, Database, BarChart3, Settings as SettingsIcon } from 'lucide-react';

export type PageId = 'home' | 'library' | 'backtest' | 'settings';

interface LayoutProps {
  children: React.ReactNode;
  currentPage: PageId;
  onNavigate: (page: PageId) => void;
  showNavigation?: boolean;
}

export const Layout: React.FC<LayoutProps> = ({
  children,
  currentPage,
  onNavigate,
  showNavigation = true,
}) => {
  const navItems = [
    { id: 'home' as const, label: '因子挖掘', icon: Sparkles },
    { id: 'library' as const, label: '因子库', icon: Database },
    { id: 'backtest' as const, label: '回测', icon: BarChart3 },
    { id: 'settings' as const, label: '设置', icon: SettingsIcon },
  ];

  return (
    <div className="min-h-screen bg-background gradient-mesh">
      {/* Header */}
      <header className="fixed top-0 left-0 right-0 z-40 glass-strong border-b border-border/50">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="relative">
                <div className="absolute inset-0 bg-primary blur-xl opacity-50 animate-pulse" />
                <div className="relative flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-purple-600 shadow-lg">
                  <Sparkles className="h-6 w-6 text-white" />
                </div>
              </div>
              <div>
                <h1 className="text-xl font-bold neon-text">QuantaAlpha</h1>
                <p className="text-xs text-muted-foreground">智能因子挖掘平台 V2</p>
              </div>
            </div>

            {/* Navigation */}
            {showNavigation && (
              <nav className="flex items-center gap-2">
                {navItems.map((item) => {
                  const Icon = item.icon;
                  const isActive = currentPage === item.id;
                  return (
                    <button
                      key={item.id}
                      onClick={() => onNavigate(item.id)}
                      className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-all ${
                        isActive
                          ? 'bg-primary text-primary-foreground'
                          : 'text-muted-foreground hover:text-foreground hover:bg-secondary/50'
                      }`}
                    >
                      <Icon className="h-4 w-4" />
                      <span className="text-sm font-medium">{item.label}</span>
                    </button>
                  );
                })}
              </nav>
            )}
          </div>
        </div>
      </header>

      {/* Main Content — pb-48 ensures content is never hidden behind the fixed ChatInput */}
      <main className="pt-24 pb-48">
        <div className="container mx-auto px-6">{children}</div>
      </main>
    </div>
  );
};

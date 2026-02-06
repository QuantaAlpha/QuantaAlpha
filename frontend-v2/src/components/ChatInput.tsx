import React, { useState, useRef, useEffect } from 'react';
import { Send, Settings, Sparkles, Loader2, Square } from 'lucide-react';
import { TaskConfig } from '@/types';

interface ChatInputProps {
  onSubmit: (config: TaskConfig) => void;
  onStop?: () => void;
  isRunning?: boolean;
}

export const ChatInput: React.FC<ChatInputProps> = ({ onSubmit, onStop, isRunning = false }) => {
  const [input, setInput] = useState('');
  const [showSettings, setShowSettings] = useState(false);
  const [config, setConfig] = useState<Partial<TaskConfig>>({
    numDirections: 2,
    maxRounds: 3,
    market: 'csi300',
    parallelExecution: true,
    qualityGateEnabled: true,
    librarySuffix: '',
  });
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const examplePrompts = [
    '💹 挖掘动量类因子，关注短期反转和成交量配合',
    '💰 探索价值成长组合，考虑行业中性化',
    '📊 基于技术指标构建因子，重点RSI和MACD',
  ];

  const handleSubmit = () => {
    if (!input.trim() || isRunning) return;
    const suffix = config.librarySuffix?.trim() || undefined;
    onSubmit({
      userInput: input.trim(),
      ...config,
      librarySuffix: suffix,
    } as TaskConfig);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 120) + 'px';
    }
  }, [input]);

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 pb-6">
      <div className="container mx-auto px-6">
        {/* Settings Panel */}
        {showSettings && !isRunning && (
          <div className="glass-strong rounded-2xl p-4 mb-3 animate-fade-in-up">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div>
                <label className="block text-xs text-muted-foreground mb-1">
                  并行方向数
                </label>
                <input
                  type="number"
                  value={config.numDirections}
                  onChange={(e) =>
                    setConfig({ ...config, numDirections: parseInt(e.target.value) })
                  }
                  className="w-full rounded-lg border border-border/50 bg-background/50 px-3 py-1.5 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary transition-all"
                  min={1}
                  max={10}
                />
              </div>

              <div>
                <label className="block text-xs text-muted-foreground mb-1">
                  进化轮次
                </label>
                <input
                  type="number"
                  value={config.maxRounds}
                  onChange={(e) =>
                    setConfig({ ...config, maxRounds: parseInt(e.target.value) })
                  }
                  className="w-full rounded-lg border border-border/50 bg-background/50 px-3 py-1.5 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary transition-all"
                  min={1}
                  max={20}
                />
              </div>

              <div>
                <label className="block text-xs text-muted-foreground mb-1">
                  市场选择
                </label>
                <select
                  value={config.market}
                  onChange={(e) =>
                    setConfig({ ...config, market: e.target.value as 'csi300' | 'csi500' | 'sp500' })
                  }
                  className="w-full rounded-lg border border-border/50 bg-background/50 px-3 py-1.5 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary transition-all"
                >
                  <option value="csi300">CSI 300</option>
                  <option value="csi500">CSI 500</option>
                </select>
              </div>

              <div className="flex items-end">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={config.qualityGateEnabled}
                    onChange={(e) =>
                      setConfig({ ...config, qualityGateEnabled: e.target.checked })
                    }
                    className="h-4 w-4 rounded border-border/50 text-primary focus:ring-primary"
                  />
                  <span className="text-xs text-muted-foreground">质量门控</span>
                </label>
              </div>
            </div>

            {/* 因子库名称 —— 独立一行 */}
            <div className="mt-3">
              <label className="block text-xs text-muted-foreground mb-1">
                因子库名称
                <span className="ml-1 text-[10px] opacity-60">（选填，留空则默认 all_factors_library.json）</span>
              </label>
              <div className="flex items-center gap-2">
                <span className="text-xs text-muted-foreground whitespace-nowrap">all_factors_library_</span>
                <input
                  type="text"
                  value={config.librarySuffix ?? ''}
                  onChange={(e) => {
                    // 只允许字母、数字、下划线、中划线
                    const val = e.target.value.replace(/[^a-zA-Z0-9_\-]/g, '');
                    setConfig({ ...config, librarySuffix: val });
                  }}
                  placeholder="例如 momentum_v1"
                  className="flex-1 rounded-lg border border-border/50 bg-background/50 px-3 py-1.5 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary transition-all"
                />
                <span className="text-xs text-muted-foreground whitespace-nowrap">.json</span>
              </div>
            </div>
          </div>
        )}

        {/* Example Prompts */}
        {!input && !isRunning && (
          <div className="flex gap-2 mb-3 overflow-x-auto pb-2 scrollbar-hide">
            {examplePrompts.map((prompt, idx) => (
              <button
                key={idx}
                onClick={() => setInput(prompt)}
                className="glass rounded-xl px-4 py-2 text-sm text-muted-foreground hover:text-foreground hover:scale-105 transition-all whitespace-nowrap flex items-center gap-2 card-hover"
              >
                <Sparkles className="h-3 w-3" />
                {prompt}
              </button>
            ))}
          </div>
        )}

        {/* Main Input */}
        <div className="gradient-border">
          <div className="gradient-border-content">
            <div className="glass-strong rounded-xl p-4">
              <div className="flex items-end gap-3">
                <div className="flex-1">
                  <textarea
                    ref={textareaRef}
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder={isRunning ? "实验运行中...可以切换到其他页面，任务不会中断" : "描述你的因子挖掘需求... (Shift+Enter 换行，Enter 发送)"}
                    disabled={isRunning}
                    className="w-full bg-transparent text-base placeholder:text-muted-foreground focus:outline-none resize-none"
                    rows={1}
                    style={{ maxHeight: '120px' }}
                  />
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setShowSettings(!showSettings)}
                    className={`p-2.5 rounded-lg transition-all ${
                      showSettings
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-secondary/50 text-muted-foreground hover:text-foreground hover:bg-secondary'
                    }`}
                    title="高级设置"
                  >
                    <Settings className="h-5 w-5" />
                  </button>

                  {isRunning && onStop ? (
                    <button
                      onClick={onStop}
                      className="p-2.5 rounded-lg bg-red-500 text-white hover:bg-red-600 transition-all hover:scale-105 active:scale-95"
                      title="中断实验"
                    >
                      <Square className="h-5 w-5" />
                    </button>
                  ) : (
                    <button
                      onClick={handleSubmit}
                      disabled={!input.trim() || isRunning}
                      className="p-2.5 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-all hover:scale-105 active:scale-95"
                      title="发送 (Enter)"
                    >
                      <Send className="h-5 w-5" />
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

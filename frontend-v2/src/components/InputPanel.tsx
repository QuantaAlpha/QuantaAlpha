import React, { useState } from 'react';
import { Settings } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/Card';
import { Textarea } from '@/components/ui/Textarea';
import { Button } from '@/components/ui/Button';
import { TaskConfig } from '@/types';

interface InputPanelProps {
  onSubmit: (config: TaskConfig) => void;
  isRunning: boolean;
}

export const InputPanel: React.FC<InputPanelProps> = ({ onSubmit, isRunning }) => {
  const [userInput, setUserInput] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [config, setConfig] = useState<Partial<TaskConfig>>({
    numDirections: 2,
    maxRounds: 7,
    market: 'csi500',
    parallelExecution: true,
    qualityGateEnabled: true,
  });

  const handleSubmit = () => {
    if (!userInput.trim()) return;
    onSubmit({
      userInput: userInput.trim(),
      ...config,
    } as TaskConfig);
  };

  const examplePrompts = [
    '请帮我挖掘动量类因子，重点关注短期反转效应和成交量配合',
    '探索价值因子与成长因子的组合策略，考虑行业中性化',
    '基于技术指标构建因子，重点关注RSI和MACD的组合',
  ];

  return (
    <Card className="w-full">
      <CardContent className="p-6">
        <div className="space-y-4">
          {/* 主输入框 */}
          <div>
            <label className="mb-2 block text-sm font-medium">
              💬 描述你的因子挖掘需求
            </label>
            <Textarea
              value={userInput}
              onChange={(e) => setUserInput(e.target.value)}
              placeholder="用自然语言描述你想要挖掘的因子类型、策略思路或研究方向..."
              className="min-h-[120px] resize-none text-base"
              disabled={isRunning}
            />
          </div>

          {/* 示例提示 */}
          {!userInput && (
            <div className="space-y-2">
              <p className="text-xs text-muted-foreground">💡 示例:</p>
              <div className="space-y-1">
                {examplePrompts.map((prompt, idx) => (
                  <button
                    key={idx}
                    onClick={() => setUserInput(prompt)}
                    className="block w-full rounded-md bg-secondary/50 px-3 py-2 text-left text-xs text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* 高级配置 */}
          <div>
            <button
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="flex items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-foreground"
            >
              <Settings className="h-4 w-4" />
              高级配置
              <span className="text-xs">
                {showAdvanced ? '▲' : '▼'}
              </span>
            </button>

            {showAdvanced && (
              <div className="mt-4 grid grid-cols-2 gap-4 rounded-md border border-border bg-secondary/20 p-4">
                <div>
                  <label className="mb-1 block text-xs text-muted-foreground">
                    并行方向数
                  </label>
                  <input
                    type="number"
                    value={config.numDirections}
                    onChange={(e) =>
                      setConfig({ ...config, numDirections: parseInt(e.target.value) })
                    }
                    className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm"
                    min={1}
                    max={10}
                  />
                </div>

                <div>
                  <label className="mb-1 block text-xs text-muted-foreground">
                    进化轮次
                  </label>
                  <input
                    type="number"
                    value={config.maxRounds}
                    onChange={(e) =>
                      setConfig({ ...config, maxRounds: parseInt(e.target.value) })
                    }
                    className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm"
                    min={1}
                    max={20}
                  />
                </div>

                <div>
                  <label className="mb-1 block text-xs text-muted-foreground">
                    市场选择
                  </label>
                  <select
                    value={config.market}
                    onChange={(e) =>
                      setConfig({ ...config, market: e.target.value as 'csi500' | 'sp500' })
                    }
                    className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm"
                  >
                    <option value="csi500">CSI 500 (中证500)</option>
                    <option value="sp500">S&P 500</option>
                  </select>
                </div>

                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="qualityGate"
                    checked={config.qualityGateEnabled}
                    onChange={(e) =>
                      setConfig({ ...config, qualityGateEnabled: e.target.checked })
                    }
                    className="h-4 w-4 rounded border-input"
                  />
                  <label htmlFor="qualityGate" className="text-xs text-muted-foreground">
                    启用质量门控
                  </label>
                </div>
              </div>
            )}
          </div>

          {/* 操作按钮 */}
          <div className="flex gap-3">
            <Button
              variant="primary"
              size="lg"
              onClick={handleSubmit}
              disabled={!userInput.trim() || isRunning}
              className="flex-1"
            >
              {isRunning ? (
                <>
                  <span className="mr-2 inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                  执行中...
                </>
              ) : (
                <>🚀 开始执行</>
              )}
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Settings, Save, RotateCcw, Eye, EyeOff, Check, X, AlertCircle, Loader2 } from 'lucide-react';
import { getSystemConfig, updateSystemConfig, healthCheck } from '@/services/api';

interface SystemConfig {
  // LLM
  apiKey: string;
  apiUrl: string;
  modelName: string;
  // Qlib
  qlibDataPath: string;
  resultsDir: string;
  // Parameters
  defaultNumDirections: number;
  defaultMaxRounds: number;
  defaultMarket: 'csi300' | 'csi500' | 'sp500';
  // Advanced
  parallelExecution: boolean;
  qualityGateEnabled: boolean;
  backtestTimeout: number;
}

const DEFAULT_CONFIG: SystemConfig = {
  apiKey: '',
  apiUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
  modelName: 'deepseek-v3',
  qlibDataPath: '',
  resultsDir: '',
  defaultNumDirections: 2,
  defaultMaxRounds: 3,
  defaultMarket: 'csi300',
  parallelExecution: false,
  qualityGateEnabled: true,
  backtestTimeout: 600,
};

export const SettingsPage: React.FC = () => {
  const [config, setConfig] = useState<SystemConfig>(DEFAULT_CONFIG);
  const [showApiKey, setShowApiKey] = useState(false);
  const [isSaved, setIsSaved] = useState(false);
  const [isDirty, setIsDirty] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [backendStatus, setBackendStatus] = useState<'checking' | 'online' | 'offline'>('checking');
  const [factorLibraries, setFactorLibraries] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Load config from backend on mount
  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    setIsLoading(true);
    setError(null);

    // Check backend health
    try {
      await healthCheck();
      setBackendStatus('online');
    } catch {
      setBackendStatus('offline');
    }

    // Load config
    try {
      const resp = await getSystemConfig();
      if (resp.success && resp.data) {
        const env = resp.data.env || {};
        setConfig({
          apiKey: env.OPENAI_API_KEY || '',
          apiUrl: env.OPENAI_BASE_URL || DEFAULT_CONFIG.apiUrl,
          modelName: env.CHAT_MODEL || DEFAULT_CONFIG.modelName,
          qlibDataPath: env.QLIB_DATA_DIR || '',
          resultsDir: env.DATA_RESULTS_DIR || '',
          defaultNumDirections: 2,
          defaultMaxRounds: 3,
          defaultMarket: 'csi300',
          parallelExecution: false,
          qualityGateEnabled: true,
          backtestTimeout: 600,
        });
        setFactorLibraries(resp.data.factorLibraries || []);
      }
    } catch (err: any) {
      console.error('Failed to load config:', err);
      // Fallback to localStorage
      const saved = localStorage.getItem('quantaalpha_config');
      if (saved) {
        try {
          setConfig(JSON.parse(saved));
        } catch {
          // use defaults
        }
      }
      setError('无法从后端加载配置，显示的是本地缓存配置');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    setError(null);

    // Always save to localStorage as backup
    localStorage.setItem('quantaalpha_config', JSON.stringify(config));

    // Try to save to backend
    try {
      const update: Record<string, string> = {};
      if (config.apiKey && !config.apiKey.includes('...')) {
        update.OPENAI_API_KEY = config.apiKey;
      }
      if (config.apiUrl) update.OPENAI_BASE_URL = config.apiUrl;
      if (config.modelName) {
        update.CHAT_MODEL = config.modelName;
        update.REASONING_MODEL = config.modelName;
      }
      if (config.qlibDataPath) update.QLIB_DATA_DIR = config.qlibDataPath;
      if (config.resultsDir) update.DATA_RESULTS_DIR = config.resultsDir;

      if (Object.keys(update).length > 0) {
        await updateSystemConfig(update);
      }
    } catch (err: any) {
      console.warn('Failed to save to backend, saved locally:', err);
    }

    setIsSaved(true);
    setIsDirty(false);
    setIsSaving(false);
    setTimeout(() => setIsSaved(false), 2000);
  };

  const handleReset = () => {
    if (confirm('确定要重置为默认配置吗？')) {
      setConfig(DEFAULT_CONFIG);
      setIsDirty(true);
    }
  };

  const updateConfigField = (key: keyof SystemConfig, value: any) => {
    setConfig((prev) => ({ ...prev, [key]: value }));
    setIsDirty(true);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[40vh]">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-3 text-muted-foreground">加载配置中...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in-up">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-3">
            <Settings className="h-8 w-8 text-primary" />
            系统配置
          </h1>
          <p className="text-muted-foreground mt-1">
            配置 API、数据路径和默认参数
          </p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" onClick={handleReset}>
            <RotateCcw className="h-4 w-4 mr-2" />
            重置
          </Button>
          <Button variant="primary" onClick={handleSave} disabled={!isDirty || isSaving}>
            {isSaving ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Save className="h-4 w-4 mr-2" />
            )}
            保存配置
          </Button>
        </div>
      </div>

      {/* Status Banners */}
      {isSaved && (
        <div className="glass rounded-lg p-4 flex items-center gap-3 bg-success/10 border-success/50 animate-fade-in-down">
          <Check className="h-5 w-5 text-success" />
          <span className="text-success">配置已保存</span>
        </div>
      )}
      {isDirty && !isSaved && (
        <div className="glass rounded-lg p-4 flex items-center gap-3 bg-warning/10 border-warning/50 animate-fade-in-down">
          <X className="h-5 w-5 text-warning" />
          <span className="text-warning">有未保存的更改</span>
        </div>
      )}
      {error && (
        <div className="glass rounded-lg p-4 flex items-center gap-3 bg-warning/10 border-warning/50">
          <AlertCircle className="h-5 w-5 text-warning flex-shrink-0" />
          <span className="text-sm text-warning">{error}</span>
        </div>
      )}

      {/* Backend Status */}
      <Card className="glass card-hover">
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div
                className={`h-3 w-3 rounded-full ${
                  backendStatus === 'online'
                    ? 'bg-success animate-pulse'
                    : backendStatus === 'offline'
                    ? 'bg-destructive'
                    : 'bg-warning animate-pulse'
                }`}
              />
              <span className="text-sm">
                后端服务：
                {backendStatus === 'online' ? '已连接' : backendStatus === 'offline' ? '未连接' : '检测中'}
              </span>
            </div>
            {factorLibraries.length > 0 && (
              <span className="text-xs text-muted-foreground">
                因子库文件: {factorLibraries.length} 个
              </span>
            )}
          </div>
        </CardContent>
      </Card>

      {/* LLM Configuration */}
      <Card className="glass card-hover">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            🤖 LLM 配置
            <Badge variant="default">必填</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2">
              API Key <span className="text-destructive">*</span>
            </label>
            <div className="flex gap-2">
              <input
                type={showApiKey ? 'text' : 'password'}
                value={config.apiKey}
                onChange={(e) => updateConfigField('apiKey', e.target.value)}
                placeholder="sk-..."
                className="flex-1 rounded-lg border border-input bg-background px-4 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary transition-all"
              />
              <Button
                variant="outline"
                onClick={() => setShowApiKey(!showApiKey)}
                className="px-3"
              >
                {showApiKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </Button>
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              OpenAI 兼容 API Key（DashScope、OpenAI 等）
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">API URL</label>
            <input
              type="text"
              value={config.apiUrl}
              onChange={(e) => updateConfigField('apiUrl', e.target.value)}
              placeholder="https://dashscope.aliyuncs.com/compatible-mode/v1"
              className="w-full rounded-lg border border-input bg-background px-4 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary transition-all"
            />
            <p className="text-xs text-muted-foreground mt-1">
              支持 DashScope、OpenAI 等 OpenAI 兼容 API
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">模型名称</label>
            <select
              value={config.modelName}
              onChange={(e) => updateConfigField('modelName', e.target.value)}
              className="w-full rounded-lg border border-input bg-background px-4 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary transition-all"
            >
              <option value="deepseek-v3">DeepSeek V3</option>
              <option value="deepseek-r1">DeepSeek R1</option>
              <option value="qwen-max">Qwen Max</option>
              <option value="qwen-plus">Qwen Plus</option>
              <option value="gpt-4">GPT-4</option>
              <option value="gpt-4-turbo">GPT-4 Turbo</option>
              <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
            </select>
          </div>
        </CardContent>
      </Card>

      {/* Data Path Configuration */}
      <Card className="glass card-hover">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            📊 数据路径配置
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2">
              Qlib 数据路径 <span className="text-destructive">*</span>
            </label>
            <input
              type="text"
              value={config.qlibDataPath}
              onChange={(e) => updateConfigField('qlibDataPath', e.target.value)}
              placeholder="/path/to/qlib/cn_data"
              className="w-full rounded-lg border border-input bg-background px-4 py-2 text-sm font-mono focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary transition-all"
            />
            <p className="text-xs text-muted-foreground mt-1">
              包含 calendars/、features/、instruments/ 子目录的 Qlib 数据路径
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">
              输出目录
            </label>
            <input
              type="text"
              value={config.resultsDir}
              onChange={(e) => updateConfigField('resultsDir', e.target.value)}
              placeholder="/path/to/results"
              className="w-full rounded-lg border border-input bg-background px-4 py-2 text-sm font-mono focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary transition-all"
            />
            <p className="text-xs text-muted-foreground mt-1">
              实验结果、缓存、日志的输出根目录
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Default Parameters */}
      <Card className="glass card-hover">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            ⚙️ 默认参数
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-2">并行方向数</label>
              <input
                type="number"
                value={config.defaultNumDirections}
                onChange={(e) => updateConfigField('defaultNumDirections', parseInt(e.target.value))}
                min={1}
                max={10}
                className="w-full rounded-lg border border-input bg-background px-4 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary transition-all"
              />
              <p className="text-xs text-muted-foreground mt-1">
                同时探索的研究方向数量 (1-10)
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">进化轮次</label>
              <input
                type="number"
                value={config.defaultMaxRounds}
                onChange={(e) => updateConfigField('defaultMaxRounds', parseInt(e.target.value))}
                min={1}
                max={20}
                className="w-full rounded-lg border border-input bg-background px-4 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary transition-all"
              />
              <p className="text-xs text-muted-foreground mt-1">
                因子进化的迭代次数 (1-20)
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">默认市场</label>
              <select
                value={config.defaultMarket}
                onChange={(e) => updateConfigField('defaultMarket', e.target.value)}
                className="w-full rounded-lg border border-input bg-background px-4 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary transition-all"
              >
                <option value="csi300">CSI 300 (沪深300)</option>
                <option value="csi500">CSI 500 (中证500)</option>
                <option value="sp500">S&P 500</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">回测超时 (秒)</label>
              <input
                type="number"
                value={config.backtestTimeout}
                onChange={(e) => updateConfigField('backtestTimeout', parseInt(e.target.value))}
                min={60}
                max={3600}
                className="w-full rounded-lg border border-input bg-background px-4 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary transition-all"
              />
              <p className="text-xs text-muted-foreground mt-1">
                单次回测最大执行时间 (60-3600)
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Advanced Options */}
      <Card className="glass card-hover">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            🔧 高级选项
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <label className="flex items-center gap-3 cursor-pointer group">
            <input
              type="checkbox"
              checked={config.parallelExecution}
              onChange={(e) => updateConfigField('parallelExecution', e.target.checked)}
              className="h-5 w-5 rounded border-input text-primary focus:ring-primary"
            />
            <div className="flex-1">
              <div className="font-medium group-hover:text-primary transition-colors">
                并行执行
              </div>
              <div className="text-xs text-muted-foreground">
                多个方向同时执行，提升效率
              </div>
            </div>
          </label>

          <label className="flex items-center gap-3 cursor-pointer group">
            <input
              type="checkbox"
              checked={config.qualityGateEnabled}
              onChange={(e) => updateConfigField('qualityGateEnabled', e.target.checked)}
              className="h-5 w-5 rounded border-input text-primary focus:ring-primary"
            />
            <div className="flex-1">
              <div className="font-medium group-hover:text-primary transition-colors">
                质量门控
              </div>
              <div className="text-xs text-muted-foreground">
                自动过滤低质量因子，保证结果质量
              </div>
            </div>
          </label>
        </CardContent>
      </Card>

      {/* Info Card */}
      <Card className="glass border-primary/50">
        <CardContent className="p-4">
          <div className="flex gap-3">
            <div className="text-2xl">💡</div>
            <div className="flex-1 text-sm">
              <div className="font-medium mb-1">配置说明</div>
              <ul className="space-y-1 text-muted-foreground">
                <li>• 配置会同时保存到后端 .env 文件和浏览器本地</li>
                <li>• API Key 会被部分遮蔽显示，修改时输入新的完整 Key</li>
                <li>• 路径配置需要指向服务器上的实际路径（后端仅支持 Linux）</li>
                <li>• 修改后需重启实验才能生效</li>
                <li>• 默认市场为 CSI300（沪深300），数据需覆盖 2016-2025 年</li>
                <li>• LLM Token 消耗与 <strong>进化轮次 x 并行方向数</strong> 成正比，建议首次实验使用 2 方向 x 3 轮次</li>
                <li>• 主实验时间段：训练集 2016-2020，验证集 2021；独立回测测试集 2022-2025</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* System Requirements Card */}
      <Card className="glass border-warning/30">
        <CardContent className="p-4">
          <div className="flex gap-3">
            <div className="text-2xl">⚠️</div>
            <div className="flex-1 text-sm">
              <div className="font-medium mb-1">系统要求</div>
              <ul className="space-y-1 text-muted-foreground">
                <li>• <strong>操作系统：</strong>当前版本仅支持 Linux。Windows 和 macOS 支持将在未来版本提供</li>
                <li>• <strong>Python：</strong>3.10+（推荐使用 Conda 管理环境）</li>
                <li>• <strong>磁盘空间：</strong>Qlib 数据约 30-50 GB，建议预留 100 GB 用于实验缓存</li>
                <li>• <strong>内存：</strong>建议 32 GB+（LightGBM 训练 + 因子计算）</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

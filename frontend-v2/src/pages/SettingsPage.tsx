import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Settings, Save, RotateCcw, Eye, EyeOff, Check, X, AlertCircle, Loader2, Database, Sliders, Box, Cpu, Compass, Shuffle } from 'lucide-react';
import { getSystemConfig, updateSystemConfig, healthCheck } from '@/services/api';
import { REFERENCE_MINING_DIRECTIONS, getDirectionLabel, type MiningDirectionItem } from '@/utils/miningDirections';

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
  defaultLibrarySuffix: string;
  // Mining direction: use selected directions / random
  miningDirectionMode: 'selected' | 'random';
  selectedMiningDirectionIndices: number[];
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
  parallelExecution: true,
  qualityGateEnabled: true,
  backtestTimeout: 600,
  defaultLibrarySuffix: '',
  miningDirectionMode: 'selected',
  selectedMiningDirectionIndices: [0, 1, 2],
};

type SettingsTab = 'api' | 'data' | 'params' | 'directions';

export const SettingsPage: React.FC = () => {
  const [config, setConfig] = useState<SystemConfig>(DEFAULT_CONFIG);
  const [activeTab, setActiveTab] = useState<SettingsTab>('api');
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
        const saved = localStorage.getItem('quantaalpha_config');
        let miningDirectionMode = DEFAULT_CONFIG.miningDirectionMode;
        let selectedMiningDirectionIndices = DEFAULT_CONFIG.selectedMiningDirectionIndices;
        if (saved) {
          try {
            const parsed = JSON.parse(saved);
            if (parsed.miningDirectionMode) miningDirectionMode = parsed.miningDirectionMode;
            if (Array.isArray(parsed.selectedMiningDirectionIndices)) selectedMiningDirectionIndices = parsed.selectedMiningDirectionIndices;
          } catch { /* use defaults */ }
        }
        setConfig({
          apiKey: env.OPENAI_API_KEY || '',
          apiUrl: env.OPENAI_BASE_URL || DEFAULT_CONFIG.apiUrl,
          modelName: env.CHAT_MODEL || DEFAULT_CONFIG.modelName,
          qlibDataPath: env.QLIB_DATA_DIR || '',
          resultsDir: env.DATA_RESULTS_DIR || '',
          defaultNumDirections: 2,
          defaultMaxRounds: 3,
          defaultMarket: 'csi300',
          parallelExecution: true,
          qualityGateEnabled: true,
          backtestTimeout: 600,
          defaultLibrarySuffix: '',
          miningDirectionMode,
          selectedMiningDirectionIndices,
        });
        setFactorLibraries(resp.data.factorLibraries || []);
      }
    } catch (err: any) {
      console.error('Failed to load config:', err);
      // Fallback to localStorage
      const saved = localStorage.getItem('quantaalpha_config');
      if (saved) {
        try {
          const parsed = JSON.parse(saved);
          setConfig({
            ...DEFAULT_CONFIG,
            ...parsed,
            selectedMiningDirectionIndices: Array.isArray(parsed.selectedMiningDirectionIndices)
              ? parsed.selectedMiningDirectionIndices
              : DEFAULT_CONFIG.selectedMiningDirectionIndices,
          });
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

  const TabButton = ({ id, label, icon: Icon }: { id: SettingsTab; label: string; icon: any }) => (
    <button
      onClick={() => setActiveTab(id)}
      className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-all ${
        activeTab === id
          ? 'bg-primary text-primary-foreground shadow-lg scale-105'
          : 'text-muted-foreground hover:bg-secondary/50 hover:text-foreground'
      }`}
    >
      <Icon className="h-4 w-4" />
      <span className="font-medium">{label}</span>
    </button>
  );

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
            管理 API 连接、数据源及实验参数
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

      {/* Tabs Navigation */}
      <div className="flex gap-2 p-1 bg-secondary/20 rounded-xl w-fit flex-wrap">
        <TabButton id="api" label="配置 API" icon={Cpu} />
        <TabButton id="data" label="数据路径" icon={Database} />
        <TabButton id="params" label="默认参数" icon={Sliders} />
        <TabButton id="directions" label="挖掘方向" icon={Compass} />
      </div>

      {/* Tab Content */}
      <div className="grid grid-cols-1 gap-6">
        
        {/* API Configuration Tab */}
        {activeTab === 'api' && (
          <Card className="glass card-hover animate-fade-in-up">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                🤖 LLM 模型配置
                <Badge variant="default">核心</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
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
                  支持 OpenAI 兼容格式的 API Key（如 DashScope, DeepSeek 等）
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">API Base URL</label>
                <input
                  type="text"
                  value={config.apiUrl}
                  onChange={(e) => updateConfigField('apiUrl', e.target.value)}
                  placeholder="https://dashscope.aliyuncs.com/compatible-mode/v1"
                  className="w-full rounded-lg border border-input bg-background px-4 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary transition-all"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  LLM 服务端点地址
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">模型名称</label>
                <input
                  type="text"
                  value={config.modelName}
                  onChange={(e) => updateConfigField('modelName', e.target.value)}
                  placeholder="请输入模型名称，如 deepseek-v3"
                  className="w-full rounded-lg border border-input bg-background px-4 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary transition-all"
                />
              </div>

              {/* Connection Status */}
              <div className="pt-4 border-t border-border/50">
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
                    后端连接状态：
                    {backendStatus === 'online' ? <span className="text-success font-medium">已连接</span> : 
                     backendStatus === 'offline' ? <span className="text-destructive font-medium">未连接</span> : 
                     '检测中...'}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Data Path Configuration Tab */}
        {activeTab === 'data' && (
          <Card className="glass card-hover animate-fade-in-up">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                📊 数据存储路径
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div>
                <label className="block text-sm font-medium mb-2">
                  Qlib 数据目录 <span className="text-destructive">*</span>
                </label>
                <div className="flex items-center gap-2">
                  <Database className="h-4 w-4 text-muted-foreground" />
                  <input
                    type="text"
                    value={config.qlibDataPath}
                    onChange={(e) => updateConfigField('qlibDataPath', e.target.value)}
                    placeholder="/path/to/qlib/cn_data"
                    className="flex-1 rounded-lg border border-input bg-background px-4 py-2 text-sm font-mono focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary transition-all"
                  />
                </div>
                <p className="text-xs text-muted-foreground mt-1 ml-6">
                  需包含 calendars/, features/, instruments/ 等 Qlib 标准数据子目录
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">
                  实验结果输出目录
                </label>
                <div className="flex items-center gap-2">
                  <Box className="h-4 w-4 text-muted-foreground" />
                  <input
                    type="text"
                    value={config.resultsDir}
                    onChange={(e) => updateConfigField('resultsDir', e.target.value)}
                    placeholder="/path/to/results"
                    className="flex-1 rounded-lg border border-input bg-background px-4 py-2 text-sm font-mono focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary transition-all"
                  />
                </div>
                <p className="text-xs text-muted-foreground mt-1 ml-6">
                  用于存放挖掘出的因子、回测报告及日志文件
                </p>
              </div>

              {factorLibraries.length > 0 && (
                <div className="bg-secondary/20 rounded-lg p-4 mt-4">
                  <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                    <Check className="h-4 w-4 text-success" />
                    已识别的因子库
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {factorLibraries.map((lib, idx) => (
                      <Badge key={idx} variant="outline" className="bg-background/50">
                        {lib}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Default Parameters Tab */}
        {activeTab === 'params' && (
          <Card className="glass card-hover animate-fade-in-up">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                ⚙️ 实验默认参数
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
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
                    单次实验同时探索的独立方向数量 (1-10)
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
                    因子自我进化和优化的最大迭代次数 (1-20)
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
                  <p className="text-xs text-muted-foreground mt-1">
                    切换市场需要本地计算相应的h5文件，默认提供csi300
                  </p>
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
                    单次回测最大执行时间 (秒)
                  </p>
                </div>

                <div className="md:col-span-2">
                  <label className="block text-sm font-medium mb-2">默认因子库名称后缀</label>
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-muted-foreground font-mono">all_factors_library_</span>
                    <input
                      type="text"
                      value={config.defaultLibrarySuffix}
                      onChange={(e) => {
                        const val = e.target.value.replace(/[^a-zA-Z0-9_\-]/g, '');
                        updateConfigField('defaultLibrarySuffix', val);
                      }}
                      placeholder="例如 momentum_v1 (留空则无后缀)"
                      className="flex-1 rounded-lg border border-input bg-background px-4 py-2 text-sm font-mono focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary transition-all"
                    />
                    <span className="text-sm text-muted-foreground font-mono">.json</span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    生成的因子将保存到此文件。支持字母、数字、下划线。
                  </p>
                </div>
              </div>

              <div className="pt-4 border-t border-border/50 space-y-4">
                <h4 className="text-sm font-medium">高级控制</h4>
                
                <label className="flex items-center gap-3 cursor-pointer group p-3 rounded-lg border border-border/50 hover:bg-secondary/20 transition-all">
                  <input
                    type="checkbox"
                    checked={config.parallelExecution}
                    onChange={(e) => updateConfigField('parallelExecution', e.target.checked)}
                    className="h-5 w-5 rounded border-input text-primary focus:ring-primary"
                  />
                  <div className="flex-1">
                    <div className="font-medium group-hover:text-primary transition-colors">
                      启用并行执行
                    </div>
                    <div className="text-xs text-muted-foreground">
                      允许多个挖掘方向同时运行，显著加快实验速度，但会增加系统负载
                    </div>
                  </div>
                </label>

                <label className="flex items-center gap-3 cursor-pointer group p-3 rounded-lg border border-border/50 hover:bg-secondary/20 transition-all">
                  <input
                    type="checkbox"
                    checked={config.qualityGateEnabled}
                    onChange={(e) => updateConfigField('qualityGateEnabled', e.target.checked)}
                    className="h-5 w-5 rounded border-input text-primary focus:ring-primary"
                  />
                  <div className="flex-1">
                    <div className="font-medium group-hover:text-primary transition-colors">
                      启用质量门控
                    </div>
                    <div className="text-xs text-muted-foreground">
                      自动检测并过滤低质量因子，防止其进入下一轮迭代，保证最终结果质量
                    </div>
                  </div>
                </label>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Mining Direction Tab */}
        {activeTab === 'directions' && (
          <Card className="glass card-hover animate-fade-in-up">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Compass className="h-5 w-5" />
                挖掘方向（参考 Alpha158(20)）
              </CardTitle>
              <p className="text-sm text-muted-foreground mt-1">
                选择作为默认参考的挖掘方向；启动任务时可从中选用或随机一条
              </p>
            </CardHeader>
            <CardContent className="space-y-6">
              <div>
                <label className="block text-sm font-medium mb-3">使用方式</label>
                <div className="flex flex-wrap gap-4">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      name="miningDirectionMode"
                      checked={config.miningDirectionMode === 'selected'}
                      onChange={() => updateConfigField('miningDirectionMode', 'selected')}
                      className="h-4 w-4 text-primary focus:ring-primary"
                    />
                    <span>使用下方选中的方向（启动时从选中中取一条或按业务逻辑使用）</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      name="miningDirectionMode"
                      checked={config.miningDirectionMode === 'random'}
                      onChange={() => updateConfigField('miningDirectionMode', 'random')}
                      className="h-4 w-4 text-primary focus:ring-primary"
                    />
                    <span className="flex items-center gap-1.5">
                      <Shuffle className="h-4 w-4" />
                      随机（从选中方向中随机选一条）
                    </span>
                  </label>
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-3">
                  <label className="text-sm font-medium">参考方向（可多选）</label>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        updateConfigField(
                          'selectedMiningDirectionIndices',
                          REFERENCE_MINING_DIRECTIONS.map((_: MiningDirectionItem, i: number) => i)
                        );
                      }}
                    >
                      全选
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => updateConfigField('selectedMiningDirectionIndices', [])}
                    >
                      取消全选
                    </Button>
                  </div>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-[320px] overflow-y-auto rounded-lg border border-border/50 bg-secondary/10 p-3">
                  {REFERENCE_MINING_DIRECTIONS.map((item: MiningDirectionItem, idx: number) => {
                    const label = getDirectionLabel(item);
                    return (
                      <label
                        key={idx}
                        className="flex items-center gap-2 p-2 rounded-lg hover:bg-secondary/20 cursor-pointer"
                      >
                        <input
                          type="checkbox"
                          checked={config.selectedMiningDirectionIndices.includes(idx)}
                          onChange={(e) => {
                            const next = e.target.checked
                              ? [...config.selectedMiningDirectionIndices, idx].sort((a, b) => a - b)
                              : config.selectedMiningDirectionIndices.filter((i) => i !== idx);
                            updateConfigField('selectedMiningDirectionIndices', next);
                          }}
                          className="h-4 w-4 rounded border-input text-primary focus:ring-primary"
                        />
                        <span className="text-sm truncate flex-1" title={label}>
                          {label}
                        </span>
                      </label>
                    );
                  })}
                </div>
                <p className="text-xs text-muted-foreground mt-2">
                  已选 {config.selectedMiningDirectionIndices.length} / {REFERENCE_MINING_DIRECTIONS.length} 项。
                </p>
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Info Footer */}
      <Card className="glass border-primary/20 bg-primary/5">
        <CardContent className="p-4 flex gap-3">
          <div className="text-xl">💡</div>
          <div className="text-sm text-muted-foreground">
            <p className="mb-1 font-medium text-foreground">配置提示</p>
            <p>所有配置修改后会自动保存至后端环境文件及本地浏览器缓存。涉及 API 或路径的修改，建议在保存后重启相关服务以确保生效。</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

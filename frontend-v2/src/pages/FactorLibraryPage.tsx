import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Factor, FactorQuality } from '@/types';
import { formatNumber, getQualityBadgeClass } from '@/utils';
import { getFactors, getFactorDetail } from '@/services/api';
import {
  Database,
  Search,
  Download,
  RefreshCw,
  TrendingUp,
  Code,
  Calendar,
  BarChart3,
  AlertCircle,
} from 'lucide-react';

export const FactorLibraryPage: React.FC = () => {
  const [factors, setFactors] = useState<Factor[]>([]);
  const [filteredFactors, setFilteredFactors] = useState<Factor[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [qualityFilter, setQualityFilter] = useState<FactorQuality | 'all'>('all');
  const [selectedFactor, setSelectedFactor] = useState<any | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [libraries, setLibraries] = useState<string[]>([]);
  const [selectedLibrary, setSelectedLibrary] = useState<string>('');
  const [metadata, setMetadata] = useState<any>(null);

  useEffect(() => {
    loadFactors();
  }, [selectedLibrary]);

  useEffect(() => {
    filterFactors();
  }, [factors, searchQuery, qualityFilter]);

  const loadFactors = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const resp = await getFactors({
        library: selectedLibrary || undefined,
        limit: 500,
      });
      if (resp.success && resp.data) {
        const apiFactors: Factor[] = resp.data.factors.map((f: any) => {
          const bt = f.backtestResults || {};
          return {
            factorId: f.factorId || '',
            factorName: f.factorName || 'Unknown',
            factorExpression: f.factorExpression || '',
            factorDescription: f.factorDescription || '',
            quality: (f.quality || 'low') as FactorQuality,
            // Prioritize specific metrics from backtest results to match detail view
            ic: (typeof bt['IC'] === 'number' ? bt['IC'] : (f.ic || bt['1day.excess_return_without_cost.information_coefficient'] || 0)),
            icir: (typeof bt['ICIR'] === 'number' ? bt['ICIR'] : (f.icir || bt['1day.excess_return_without_cost.information_coefficient_ir'] || 0)),
            rankIc: (typeof bt['Rank IC'] === 'number' ? bt['Rank IC'] : (f.rankIc || bt['rank_ic'] || bt['1day.excess_return_without_cost.rank_ic'] || 0)),
            rankIcir: (typeof bt['Rank ICIR'] === 'number' ? bt['Rank ICIR'] : (f.rankIcir || bt['rank_ic_ir'] || bt['1day.excess_return_without_cost.rank_ic_ir'] || 0)),
            round: f.round || 0,
            direction: String(f.direction ?? ''),
            createdAt: f.createdAt || new Date().toISOString(),
            // Extra fields from API
            backtestResults: f.backtestResults,
            factorFormulation: f.factorFormulation,
            annualReturn: f.annualReturn,
            maxDrawdown: f.maxDrawdown,
            sharpeRatio: f.sharpeRatio,
          };
        });
        setFactors(apiFactors);
        setLibraries(resp.data.libraries || []);
        setMetadata(resp.data.metadata || null);
      }
    } catch (err: any) {
      console.error('Failed to load factors from API:', err);
      setError('无法连接后端服务。请确保后端已启动 (python backend/app.py)');
      // Fallback to mock data
      loadMockFactors();
    } finally {
      setIsLoading(false);
    }
  }, [selectedLibrary]);

  const loadMockFactors = () => {
    const cached = localStorage.getItem('quantaalpha_factors');
    if (cached) {
      try {
        setFactors(JSON.parse(cached));
      } catch {
        setFactors(generateMockFactors());
      }
    } else {
      const mock = generateMockFactors();
      setFactors(mock);
      localStorage.setItem('quantaalpha_factors', JSON.stringify(mock));
    }
  };

  const filterFactors = () => {
    let filtered = factors;
    if (qualityFilter !== 'all') {
      filtered = filtered.filter((f) => f.quality === qualityFilter);
    }
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (f) =>
          f.factorName.toLowerCase().includes(query) ||
          f.factorExpression.toLowerCase().includes(query) ||
          f.factorDescription.toLowerCase().includes(query)
      );
    }
    setFilteredFactors(filtered);
  };

  const handleExport = () => {
    const dataStr = JSON.stringify(factors, null, 2);
    const blob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `factors_${new Date().toISOString().split('T')[0]}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const handleSelectFactor = async (factor: Factor) => {
    // Try to load full detail from API
    try {
      const resp = await getFactorDetail(factor.factorId);
      if (resp.success && resp.data?.factor) {
        setSelectedFactor({ ...factor, ...resp.data.factor });
        return;
      }
    } catch {
      // fallback
    }
    setSelectedFactor(factor);
  };

  const stats = {
    total: factors.length,
    high: factors.filter((f) => f.quality === 'high').length,
    medium: factors.filter((f) => f.quality === 'medium').length,
    low: factors.filter((f) => f.quality === 'low').length,
  };

  return (
    <div className="space-y-6 animate-fade-in-up">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-3">
            <Database className="h-8 w-8 text-primary" />
            因子库
          </h1>
          <p className="text-muted-foreground mt-1">
            浏览和管理挖掘的因子
            {metadata?.total_factors != null && (
              <span className="ml-2 text-xs">
                (更新于 {metadata.last_updated ? new Date(metadata.last_updated).toLocaleString('zh-CN') : '未知'})
              </span>
            )}
          </p>
        </div>
        <div className="flex gap-3">
          {libraries.length > 1 && (
            <select
              value={selectedLibrary}
              onChange={(e) => setSelectedLibrary(e.target.value)}
              className="rounded-lg border border-input bg-background px-3 py-2 text-sm"
            >
              <option value="">最新因子库</option>
              {libraries.map((lib) => (
                <option key={lib} value={lib}>{lib}</option>
              ))}
            </select>
          )}
          <Button variant="outline" onClick={loadFactors} disabled={isLoading}>
            <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
            刷新
          </Button>
          <Button variant="primary" onClick={handleExport}>
            <Download className="h-4 w-4 mr-2" />
            导出
          </Button>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="glass rounded-lg p-4 flex items-center gap-3 bg-warning/10 border-warning/50">
          <AlertCircle className="h-5 w-5 text-warning flex-shrink-0" />
          <span className="text-sm text-warning">{error}</span>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="glass card-hover">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-muted-foreground">总因子数</div>
                <div className="text-2xl font-bold mt-1">{stats.total}</div>
              </div>
              <div className="p-3 rounded-lg bg-primary/20">
                <BarChart3 className="h-6 w-6 text-primary" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="glass card-hover">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-muted-foreground">高质量</div>
                <div className="text-2xl font-bold mt-1 text-success">{stats.high}</div>
              </div>
              <div className="p-3 rounded-lg bg-success/20">
                <TrendingUp className="h-6 w-6 text-success" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="glass card-hover">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-muted-foreground">中等质量</div>
                <div className="text-2xl font-bold mt-1 text-warning">{stats.medium}</div>
              </div>
              <div className="p-3 rounded-lg bg-warning/20">
                <BarChart3 className="h-6 w-6 text-warning" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="glass card-hover">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-muted-foreground">低质量</div>
                <div className="text-2xl font-bold mt-1 text-destructive">{stats.low}</div>
              </div>
              <div className="p-3 rounded-lg bg-destructive/20">
                <BarChart3 className="h-6 w-6 text-destructive" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card className="glass">
        <CardContent className="p-4">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="搜索因子名称、表达式或描述..."
                  className="w-full pl-10 pr-4 py-2 rounded-lg border border-input bg-background text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary transition-all"
                />
              </div>
            </div>
            <div className="flex gap-2">
              <Button
                variant={qualityFilter === 'all' ? 'primary' : 'outline'}
                size="sm"
                onClick={() => setQualityFilter('all')}
              >
                全部 ({stats.total})
              </Button>
              <Button
                variant={qualityFilter === 'high' ? 'primary' : 'outline'}
                size="sm"
                onClick={() => setQualityFilter('high')}
              >
                高质量 ({stats.high})
              </Button>
              <Button
                variant={qualityFilter === 'medium' ? 'primary' : 'outline'}
                size="sm"
                onClick={() => setQualityFilter('medium')}
              >
                中等 ({stats.medium})
              </Button>
              <Button
                variant={qualityFilter === 'low' ? 'primary' : 'outline'}
                size="sm"
                onClick={() => setQualityFilter('low')}
              >
                低质量 ({stats.low})
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Factor List */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {filteredFactors.map((factor) => (
          <Card
            key={factor.factorId}
            className="glass card-hover cursor-pointer"
            onClick={() => handleSelectFactor(factor)}
          >
            <CardHeader className="pb-3">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <CardTitle className="text-base">{factor.factorName}</CardTitle>
                  <div className="flex items-center gap-2 mt-2">
                    <Badge className={getQualityBadgeClass(factor.quality)}>
                      {factor.quality === 'high' ? '高' : factor.quality === 'medium' ? '中' : '低'}
                    </Badge>
                    {factor.round > 0 && (
                      <span className="text-xs text-muted-foreground">
                        Round {factor.round}
                      </span>
                    )}
                    {factor.direction && (
                      <span className="text-xs text-muted-foreground">
                        方向 {factor.direction}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-sm text-muted-foreground line-clamp-2">
                {factor.factorDescription}
              </p>
              <div className="rounded-lg bg-secondary/30 p-3">
                <div className="flex items-center gap-2 mb-2">
                  <Code className="h-3 w-3 text-muted-foreground" />
                  <span className="text-xs text-muted-foreground">表达式</span>
                </div>
                <code className="text-xs font-mono line-clamp-2">
                  {factor.factorExpression}
                </code>
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div>
                  <span className="text-muted-foreground">IC: </span>
                  <span className="font-mono font-medium">{formatNumber(factor.ic, 4)}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">RankIC: </span>
                  <span className="font-mono font-medium">{formatNumber(factor.rankIc, 4)}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">ICIR: </span>
                  <span className="font-mono font-medium">{formatNumber(factor.icir, 3)}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">RankICIR: </span>
                  <span className="font-mono font-medium">{formatNumber(factor.rankIcir, 3)}</span>
                </div>
              </div>
              {factor.createdAt && (
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Calendar className="h-3 w-3" />
                  {new Date(factor.createdAt).toLocaleString('zh-CN')}
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Empty State */}
      {filteredFactors.length === 0 && !isLoading && (
        <Card className="glass">
          <CardContent className="p-12 text-center">
            <Database className="h-16 w-16 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium mb-2">暂无因子</h3>
            <p className="text-sm text-muted-foreground">
              {searchQuery || qualityFilter !== 'all'
                ? '没有符合筛选条件的因子'
                : '开始挖掘因子后，结果将显示在这里'}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Factor Detail Modal */}
      {selectedFactor && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-6"
          onClick={() => setSelectedFactor(null)}
        >
          <Card
            className="glass-strong max-w-3xl w-full max-h-[80vh] overflow-y-auto animate-scale-in"
            onClick={(e: React.MouseEvent) => e.stopPropagation()}
          >
            <CardHeader>
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <CardTitle className="text-xl">
                    {selectedFactor.factorName || selectedFactor.factor_name}
                  </CardTitle>
                  <div className="flex items-center gap-2 mt-2">
                    <Badge className={getQualityBadgeClass(selectedFactor.quality || 'medium')}>
                      {selectedFactor.quality === 'high'
                        ? '高质量'
                        : selectedFactor.quality === 'medium'
                        ? '中等质量'
                        : '低质量'}
                    </Badge>
                  </div>
                </div>
                <Button variant="ghost" onClick={() => setSelectedFactor(null)}>
                  ✕
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Description */}
              <div>
                <h4 className="text-sm font-medium mb-2">因子描述</h4>
                <p className="text-sm text-muted-foreground">
                  {selectedFactor.factorDescription || selectedFactor.factor_description || '无描述'}
                </p>
              </div>

              {/* Expression */}
              <div>
                <h4 className="text-sm font-medium mb-2">因子表达式</h4>
                <div className="rounded-lg bg-secondary/30 p-4">
                  <code className="text-sm font-mono break-all">
                    {selectedFactor.factorExpression || selectedFactor.factor_expression || ''}
                  </code>
                </div>
              </div>

              {/* Formulation */}
              {(selectedFactor.factorFormulation || selectedFactor.factor_formulation) && (
                <div>
                  <h4 className="text-sm font-medium mb-2">数学公式</h4>
                  <div className="rounded-lg bg-secondary/30 p-4">
                    <code className="text-sm font-mono break-all">
                      {selectedFactor.factorFormulation || selectedFactor.factor_formulation}
                    </code>
                  </div>
                </div>
              )}

              {/* Backtest Results */}
              {(selectedFactor.backtestResults || selectedFactor.backtest_results) && (
                <div>
                  <h4 className="text-sm font-medium mb-2">回测指标</h4>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                    {Object.entries(
                      selectedFactor.backtestResults || selectedFactor.backtest_results || {}
                    ).map(([key, val]) => (
                      <div key={key} className="rounded-lg bg-secondary/30 p-3">
                        <div className="text-xs text-muted-foreground truncate" title={key}>
                          {key}
                        </div>
                        <div className="text-sm font-bold font-mono mt-1">
                          {typeof val === 'number' ? formatNumber(val, 4) : String(val)}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Meta */}
              <div>
                <h4 className="text-sm font-medium mb-2">元信息</h4>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">因子ID:</span>
                    <span className="font-mono">
                      {selectedFactor.factorId || selectedFactor.factor_id || ''}
                    </span>
                  </div>
                  {(selectedFactor.createdAt || selectedFactor.added_at) && (
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">创建时间:</span>
                      <span>
                        {new Date(
                          selectedFactor.createdAt || selectedFactor.added_at
                        ).toLocaleString('zh-CN')}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
};

// Generate mock factors for demo when backend is unavailable
function generateMockFactors(): Factor[] {
  const qualities: FactorQuality[] = ['high', 'medium', 'low'];
  const directions = ['动量类', '价值类', '成长类', '技术指标'];
  const factors: Factor[] = [];
  for (let i = 0; i < 30; i++) {
    factors.push({
      factorId: `factor_${i + 1}`,
      factorName: `Factor_${i + 1}_${directions[i % 4]}`,
      factorExpression: `RANK(TS_MEAN($close / DELAY($close, ${10 + i}), ${5 + i}) * $volume)`,
      factorDescription: `这是一个${directions[i % 4]}因子，结合了价格动量和成交量特征`,
      quality: qualities[i % 3],
      ic: 0.03 + Math.random() * 0.05,
      icir: 0.3 + Math.random() * 0.5,
      rankIc: 0.025 + Math.random() * 0.05,
      rankIcir: 0.25 + Math.random() * 0.5,
      round: Math.floor(i / 5) + 1,
      direction: directions[i % 4],
      createdAt: new Date(Date.now() - i * 86400000).toISOString(),
    });
  }
  return factors;
}

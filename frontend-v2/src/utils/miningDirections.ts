/**
 * Reference mining directions list and default direction parsing (consistent with "Mining Direction" in settings)
 * Each direction can attach up to 3 factors' "short name", "expression", "meaning", displayed on hover
 */

export interface FactorHint {
  shortName: string;
  expression: string;
  meaning: string;
}

export interface MiningDirectionItem {
  label: string;
  /** Up to 3 factors, displayed when hovering over the direction */
  factors?: FactorHint[];
}

/** Reference mining directions (Alpha158(20) style, can be added/deleted/modified as needed; factors can be filled from original_direction_CN.json) */
export const REFERENCE_MINING_DIRECTIONS: MiningDirectionItem[] = [
  {
    label: '价量关系与开盘收益率',
    factors: [
      { shortName: 'KMID', expression: '(close-open)/open', meaning: '开盘收益率' },
      { shortName: 'KUP', expression: '(high-max(open,close))/open', meaning: '上影线相对开盘' },
      { shortName: 'KLOW', expression: '(min(open,close)-low)/open', meaning: '下影线相对开盘' },
    ],
  },
  { label: '短期动量与收益率', factors: [] },
  { label: '成交量比率与放量确认', factors: [] },
  { label: '波动率与价格稳定性', factors: [] },
  { label: '振幅与高低价区间', factors: [] },
  { label: 'RSV 与超买超卖', factors: [] },
  { label: '均线比率与趋势', factors: [] },
  { label: '影线比例与 K 线形态', factors: [] },
  { label: '实体比例与多空力量', factors: [] },
  { label: '收益率波动与风险', factors: [] },
  { label: '高低价相对位置', factors: [] },
  { label: '量价背离与确认', factors: [] },
  { label: '多周期动量组合', factors: [] },
  { label: '成交量标准化特征', factors: [] },
  { label: '价格相对均线位置', factors: [] },
];

/** Get direction label (compatible with object or string) */
export function getDirectionLabel(item: MiningDirectionItem): string {
  return typeof item === 'string' ? item : item.label;
}

interface StoredMiningDirectionConfig {
  miningDirectionMode?: 'selected' | 'random';
  selectedMiningDirectionIndices?: number[];
}

/** Get a default mining direction from saved config (one of the selected list, or a random one) */
export function getDefaultMiningDirection(): string {
  try {
    const raw = localStorage.getItem('quantaalpha_config');
    if (!raw) return '';
    const config = JSON.parse(raw) as StoredMiningDirectionConfig;
    const indices = config?.selectedMiningDirectionIndices ?? [];
    const list = REFERENCE_MINING_DIRECTIONS;
    if (!list.length || !indices.length) return '';
    const validIndices = indices.filter((i) => i >= 0 && i < list.length);
    if (!validIndices.length) return '';
    if (config?.miningDirectionMode === 'random') {
      const idx = validIndices[Math.floor(Math.random() * validIndices.length)];
      return getDirectionLabel(list[idx]);
    }
    return getDirectionLabel(list[validIndices[0]]);
  } catch {
    return '';
  }
}

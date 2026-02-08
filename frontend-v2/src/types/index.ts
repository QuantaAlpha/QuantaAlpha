// 任务状态
export type TaskStatus = 'idle' | 'running' | 'completed' | 'failed';

// 执行阶段
export type ExecutionPhase =
  | 'parsing'      // 解析需求
  | 'planning'     // 规划方向
  | 'evolving'     // 进化中
  | 'backtesting'  // 回测中
  | 'analyzing'    // 分析结果
  | 'completed';   // 完成

// 因子质量等级
export type FactorQuality = 'high' | 'medium' | 'low';

// 任务配置
export interface TaskConfig {
  // 基础配置
  userInput: string;
  /** 为 true 时使用「设置 → 挖掘方向」中的选项（选中/随机），忽略输入框内容 */
  useCustomMiningDirection?: boolean;
  numDirections?: number;
  maxRounds?: number;
  librarySuffix?: string;

  // LLM 配置
  apiKey?: string;
  apiUrl?: string;
  modelName?: string;

  // 回测配置
  market?: 'csi300' | 'csi500' | 'sp500';
  startDate?: string;
  endDate?: string;

  // 高级配置
  parallelExecution?: boolean;
  qualityGateEnabled?: boolean;
  backtestTimeout?: number;
}

// 实时指标
export interface RealtimeMetrics {
  // IC 指标
  ic: number;
  icir: number;
  rankIc: number;
  rankIcir: number;
  
  // Optional factor name if available (e.g. best factor)
  factorName?: string;
  
  // Top 10 factors list
  top10Factors?: Array<{
    factorName: string;
    factorExpression: string;
    rankIc: number;
    rankIcir: number;
    ic: number;
    icir: number;
    annualReturn?: number;
    sharpeRatio?: number;
    maxDrawdown?: number;
    calmarRatio?: number;
    cumulativeCurve?: Array<{date: string, value: number}>;
  }>;

  // 收益指标
  annualReturn: number;
  sharpeRatio: number;
  maxDrawdown: number;

  // 因子统计
  totalFactors: number;
  highQualityFactors: number;
  mediumQualityFactors: number;
  lowQualityFactors: number;
}

// 执行进度
export interface ExecutionProgress {
  phase: ExecutionPhase;
  currentRound: number;
  totalRounds: number;
  progress: number; // 0-100
  message: string;
  timestamp: string;
}

// 日志条目
export interface LogEntry {
  id: string;
  timestamp: string;
  level: 'info' | 'warning' | 'error' | 'success';
  message: string;
}

// 因子信息
export interface Factor {
  factorId: string;
  factorName: string;
  factorExpression: string;
  factorDescription: string;
  quality: FactorQuality;

  // 回测指标
  ic: number;
  icir: number;
  rankIc: number;
  rankIcir: number;

  // 元数据
  round: number;
  direction: string;
  createdAt: string;
}

// 回测结果
export interface BacktestResult {
  // 整体指标
  metrics: RealtimeMetrics;

  // 时间序列数据
  equityCurve: TimeSeriesData[];
  drawdownCurve: TimeSeriesData[];
  icTimeSeries: TimeSeriesData[];

  // 因子列表
  factors: Factor[];

  // 质量分布
  qualityDistribution: {
    high: number;
    medium: number;
    low: number;
  };
}

// 时间序列数据点
export interface TimeSeriesData {
  date: string;
  value: number;
}

// 任务信息
export interface Task {
  taskId: string;
  status: TaskStatus;
  config: TaskConfig;
  progress: ExecutionProgress;
  metrics?: RealtimeMetrics;
  result?: BacktestResult;
  logs: LogEntry[];
  createdAt: string;
  updatedAt: string;
}

// API 响应
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

// WebSocket 消息类型
export type WsMessageType =
  | 'progress'
  | 'metrics'
  | 'log'
  | 'result'
  | 'error';

// WebSocket 消息
export interface WsMessage {
  type: WsMessageType;
  taskId: string;
  data: any;
  timestamp: string;
}

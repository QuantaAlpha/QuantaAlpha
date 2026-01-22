#!/usr/bin/env python3
"""
因子加载器 - 支持多种因子源

支持:
1. Qlib 官方因子库: alpha158, alpha158(20), alpha360
2. 自定义因子库 (JSON格式)
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger(__name__)


# 不规范表达式的模式 - 用于自动过滤不可回测的因子
INVALID_EXPRESSION_PATTERNS = [
    r'LET\s*\(',          # LET(...) 变量定义
    r'\bIF\s*\(',         # IF(...) 条件语句
    r'//',                # // 注释
    r';\s*\n',            # 分号换行（多语句）
    r'\b[a-z_]+\s*=\s*[^=]',  # 变量赋值 (如 roc60 = ...)
    r'#\s+[A-Za-z]',      # # 注释
    r'\bAND\b',           # AND 关键字
    r'\bOR\b',            # OR 关键字
    r'\bNULL\b',          # NULL 关键字
    r'\$[a-z_]+_df',      # 不存在的 dataframe 引用 (如 $sector_etf_df)
    r'\$[a-z_]+_[a-z]+_[a-z]+_df',  # 嵌套 dataframe 引用
    r"df\['",             # pandas 风格引用 (如 df['$volume'])
    r'\bsector\b',        # 不支持的 sector 变量
    r'\bCORRELATION\b',   # 非标准函数名 (应该是 TS_CORR)
    r'\bTS_DELTA\b',      # 非标准函数名 (应该是 DELTA)
    r'\$accruals',        # 不存在的基本面数据
    r'\$analyst',         # 不存在的分析师数据
    r'\$disclosure',      # 不存在的披露数据
]


def is_valid_expression(expr: str) -> bool:
    """
    检查因子表达式是否规范（可解析）
    
    Args:
        expr: 因子表达式
        
    Returns:
        bool: 表达式是否有效
    """
    if not expr or not isinstance(expr, str):
        return False
    
    for pattern in INVALID_EXPRESSION_PATTERNS:
        if re.search(pattern, expr, re.MULTILINE | re.IGNORECASE):
            return False
    
    return True


def check_cache_exists(cache_location: dict) -> bool:
    """
    检查缓存文件是否存在
    
    Args:
        cache_location: 缓存位置信息
        
    Returns:
        bool: 缓存文件是否存在
    """
    if not cache_location:
        return False
    
    h5_path = cache_location.get("result_h5_path", "")
    if not h5_path:
        return False
    
    return Path(h5_path).exists()


class FactorLoader:
    """因子加载器"""
    
    # Alpha158(20) 核心因子
    ALPHA158_20_FACTORS = {
        "ROC0": "($close-$open)/$open",
        "ROC1": "$close/Ref($close, 1)-1",
        "ROC5": "($close-Ref($close, 5))/Ref($close, 5)",
        "ROC10": "($close-Ref($close, 10))/Ref($close, 10)",
        "ROC20": "($close-Ref($close, 20))/Ref($close, 20)",
        "VRATIO5": "$volume/Mean($volume, 5)",
        "VRATIO10": "$volume/Mean($volume, 10)",
        "VSTD5_RATIO": "Std($volume, 5)/Mean($volume, 5)",
        "RANGE": "($high-$low)/$open",
        "VOLATILITY5": "Std($close, 5)/$close",
        "VOLATILITY10": "Std($close, 10)/$close",
        "RET_VOL5": "Std($close/Ref($close, 1)-1, 5)",
        "RSV5": "($close-Min($low, 5))/(Max($high, 5)-Min($low, 5)+1e-12)",
        "RSV10": "($close-Min($low, 10))/(Max($high, 10)-Min($low, 10)+1e-12)",
        "HIGH_RATIO5": "$close/Max($high, 5)-1",
        "LOW_RATIO5": "$close/Min($low, 5)-1",
        "SHADOW_RATIO": "($high-$close)/($close-$low+1e-12)",
        "BODY_RATIO": "($close-$open)/($high-$low+1e-12)",
        "MA_RATIO5_10": "Mean($close, 5)/Mean($close, 10)-1",
        "MA_RATIO10_20": "Mean($close, 10)/Mean($close, 20)-1",
    }
    
    # Alpha158 完整因子库 (158个因子)
    ALPHA158_FACTORS = {
        # K线形态因子
        "KMID": "($close-$open)/$open",
        "KLEN": "($high-$low)/$open",
        "KMID2": "($close-$open)/($high-$low+1e-12)",
        "KUP": "($high-Greater($open, $close))/$open",
        "KUP2": "($high-Greater($open, $close))/($high-$low+1e-12)",
        "KLOW": "(Less($open, $close)-$low)/$open",
        "KLOW2": "(Less($open, $close)-$low)/($high-$low+1e-12)",
        "KSFT": "(2*$close-$high-$low)/$open",
        "KSFT2": "(2*$close-$high-$low)/($high-$low+1e-12)",
        
        # 基础价格因子
        "OPEN0": "$open/$close",
        "HIGH0": "$high/$close",
        "LOW0": "$low/$close",
        "VWAP0": "$vwap/$close",
        
        # ROC因子
        "ROC5": "Ref($close, 5)/$close",
        "ROC10": "Ref($close, 10)/$close",
        "ROC20": "Ref($close, 20)/$close",
        "ROC30": "Ref($close, 30)/$close",
        "ROC60": "Ref($close, 60)/$close",
        
        # MA因子
        "MA5": "Mean($close, 5)/$close",
        "MA10": "Mean($close, 10)/$close",
        "MA20": "Mean($close, 20)/$close",
        "MA30": "Mean($close, 30)/$close",
        "MA60": "Mean($close, 60)/$close",
        
        # STD因子
        "STD5": "Std($close, 5)/$close",
        "STD10": "Std($close, 10)/$close",
        "STD20": "Std($close, 20)/$close",
        "STD30": "Std($close, 30)/$close",
        "STD60": "Std($close, 60)/$close",
        
        # BETA因子
        "BETA5": "Slope($close, 5)/$close",
        "BETA10": "Slope($close, 10)/$close",
        "BETA20": "Slope($close, 20)/$close",
        "BETA30": "Slope($close, 30)/$close",
        "BETA60": "Slope($close, 60)/$close",
        
        # RSQR因子
        "RSQR5": "Rsquare($close, 5)",
        "RSQR10": "Rsquare($close, 10)",
        "RSQR20": "Rsquare($close, 20)",
        "RSQR30": "Rsquare($close, 30)",
        "RSQR60": "Rsquare($close, 60)",
        
        # RESI因子
        "RESI5": "Resi($close, 5)/$close",
        "RESI10": "Resi($close, 10)/$close",
        "RESI20": "Resi($close, 20)/$close",
        "RESI30": "Resi($close, 30)/$close",
        "RESI60": "Resi($close, 60)/$close",
        
        # MAX因子
        "MAX5": "Max($high, 5)/$close",
        "MAX10": "Max($high, 10)/$close",
        "MAX20": "Max($high, 20)/$close",
        "MAX30": "Max($high, 30)/$close",
        "MAX60": "Max($high, 60)/$close",
        
        # MIN因子
        "MIN5": "Min($low, 5)/$close",
        "MIN10": "Min($low, 10)/$close",
        "MIN20": "Min($low, 20)/$close",
        "MIN30": "Min($low, 30)/$close",
        "MIN60": "Min($low, 60)/$close",
        
        # QTLU因子
        "QTLU5": "Quantile($close, 5, 0.8)/$close",
        "QTLU10": "Quantile($close, 10, 0.8)/$close",
        "QTLU20": "Quantile($close, 20, 0.8)/$close",
        "QTLU30": "Quantile($close, 30, 0.8)/$close",
        "QTLU60": "Quantile($close, 60, 0.8)/$close",
        
        # QTLD因子
        "QTLD5": "Quantile($close, 5, 0.2)/$close",
        "QTLD10": "Quantile($close, 10, 0.2)/$close",
        "QTLD20": "Quantile($close, 20, 0.2)/$close",
        "QTLD30": "Quantile($close, 30, 0.2)/$close",
        "QTLD60": "Quantile($close, 60, 0.2)/$close",
        
        # RANK因子
        "RANK5": "Rank($close, 5)",
        "RANK10": "Rank($close, 10)",
        "RANK20": "Rank($close, 20)",
        "RANK30": "Rank($close, 30)",
        "RANK60": "Rank($close, 60)",
        
        # RSV因子
        "RSV5": "($close-Min($low, 5))/(Max($high, 5)-Min($low, 5)+1e-12)",
        "RSV10": "($close-Min($low, 10))/(Max($high, 10)-Min($low, 10)+1e-12)",
        "RSV20": "($close-Min($low, 20))/(Max($high, 20)-Min($low, 20)+1e-12)",
        "RSV30": "($close-Min($low, 30))/(Max($high, 30)-Min($low, 30)+1e-12)",
        "RSV60": "($close-Min($low, 60))/(Max($high, 60)-Min($low, 60)+1e-12)",
        
        # IMAX因子
        "IMAX5": "IdxMax($high, 5)/5",
        "IMAX10": "IdxMax($high, 10)/10",
        "IMAX20": "IdxMax($high, 20)/20",
        "IMAX30": "IdxMax($high, 30)/30",
        "IMAX60": "IdxMax($high, 60)/60",
        
        # IMIN因子
        "IMIN5": "IdxMin($low, 5)/5",
        "IMIN10": "IdxMin($low, 10)/10",
        "IMIN20": "IdxMin($low, 20)/20",
        "IMIN30": "IdxMin($low, 30)/30",
        "IMIN60": "IdxMin($low, 60)/60",
        
        # IMXD因子
        "IMXD5": "(IdxMax($high, 5)-IdxMin($low, 5))/5",
        "IMXD10": "(IdxMax($high, 10)-IdxMin($low, 10))/10",
        "IMXD20": "(IdxMax($high, 20)-IdxMin($low, 20))/20",
        "IMXD30": "(IdxMax($high, 30)-IdxMin($low, 30))/30",
        "IMXD60": "(IdxMax($high, 60)-IdxMin($low, 60))/60",
        
        # CORR因子
        "CORR5": "Corr($close, Log($volume+1), 5)",
        "CORR10": "Corr($close, Log($volume+1), 10)",
        "CORR20": "Corr($close, Log($volume+1), 20)",
        "CORR30": "Corr($close, Log($volume+1), 30)",
        "CORR60": "Corr($close, Log($volume+1), 60)",
        
        # CORD因子
        "CORD5": "Corr($close/Ref($close,1), Log($volume/Ref($volume, 1)+1), 5)",
        "CORD10": "Corr($close/Ref($close,1), Log($volume/Ref($volume, 1)+1), 10)",
        "CORD20": "Corr($close/Ref($close,1), Log($volume/Ref($volume, 1)+1), 20)",
        "CORD30": "Corr($close/Ref($close,1), Log($volume/Ref($volume, 1)+1), 30)",
        "CORD60": "Corr($close/Ref($close,1), Log($volume/Ref($volume, 1)+1), 60)",
        
        # CNTP因子
        "CNTP5": "Mean($close>Ref($close, 1), 5)",
        "CNTP10": "Mean($close>Ref($close, 1), 10)",
        "CNTP20": "Mean($close>Ref($close, 1), 20)",
        "CNTP30": "Mean($close>Ref($close, 1), 30)",
        "CNTP60": "Mean($close>Ref($close, 1), 60)",
        
        # CNTN因子
        "CNTN5": "Mean($close<Ref($close, 1), 5)",
        "CNTN10": "Mean($close<Ref($close, 1), 10)",
        "CNTN20": "Mean($close<Ref($close, 1), 20)",
        "CNTN30": "Mean($close<Ref($close, 1), 30)",
        "CNTN60": "Mean($close<Ref($close, 1), 60)",
        
        # CNTD因子
        "CNTD5": "Mean($close>Ref($close, 1), 5)-Mean($close<Ref($close, 1), 5)",
        "CNTD10": "Mean($close>Ref($close, 1), 10)-Mean($close<Ref($close, 1), 10)",
        "CNTD20": "Mean($close>Ref($close, 1), 20)-Mean($close<Ref($close, 1), 20)",
        "CNTD30": "Mean($close>Ref($close, 1), 30)-Mean($close<Ref($close, 1), 30)",
        "CNTD60": "Mean($close>Ref($close, 1), 60)-Mean($close<Ref($close, 1), 60)",
        
        # SUMP因子
        "SUMP5": "Sum(Greater($close-Ref($close, 1), 0), 5)/(Sum(Abs($close-Ref($close, 1)), 5)+1e-12)",
        "SUMP10": "Sum(Greater($close-Ref($close, 1), 0), 10)/(Sum(Abs($close-Ref($close, 1)), 10)+1e-12)",
        "SUMP20": "Sum(Greater($close-Ref($close, 1), 0), 20)/(Sum(Abs($close-Ref($close, 1)), 20)+1e-12)",
        "SUMP30": "Sum(Greater($close-Ref($close, 1), 0), 30)/(Sum(Abs($close-Ref($close, 1)), 30)+1e-12)",
        "SUMP60": "Sum(Greater($close-Ref($close, 1), 0), 60)/(Sum(Abs($close-Ref($close, 1)), 60)+1e-12)",
        
        # SUMN因子
        "SUMN5": "Sum(Greater(Ref($close, 1)-$close, 0), 5)/(Sum(Abs($close-Ref($close, 1)), 5)+1e-12)",
        "SUMN10": "Sum(Greater(Ref($close, 1)-$close, 0), 10)/(Sum(Abs($close-Ref($close, 1)), 10)+1e-12)",
        "SUMN20": "Sum(Greater(Ref($close, 1)-$close, 0), 20)/(Sum(Abs($close-Ref($close, 1)), 20)+1e-12)",
        "SUMN30": "Sum(Greater(Ref($close, 1)-$close, 0), 30)/(Sum(Abs($close-Ref($close, 1)), 30)+1e-12)",
        "SUMN60": "Sum(Greater(Ref($close, 1)-$close, 0), 60)/(Sum(Abs($close-Ref($close, 1)), 60)+1e-12)",
        
        # SUMD因子
        "SUMD5": "(Sum(Greater($close-Ref($close, 1), 0), 5)-Sum(Greater(Ref($close, 1)-$close, 0), 5))/(Sum(Abs($close-Ref($close, 1)), 5)+1e-12)",
        "SUMD10": "(Sum(Greater($close-Ref($close, 1), 0), 10)-Sum(Greater(Ref($close, 1)-$close, 0), 10))/(Sum(Abs($close-Ref($close, 1)), 10)+1e-12)",
        "SUMD20": "(Sum(Greater($close-Ref($close, 1), 0), 20)-Sum(Greater(Ref($close, 1)-$close, 0), 20))/(Sum(Abs($close-Ref($close, 1)), 20)+1e-12)",
        "SUMD30": "(Sum(Greater($close-Ref($close, 1), 0), 30)-Sum(Greater(Ref($close, 1)-$close, 0), 30))/(Sum(Abs($close-Ref($close, 1)), 30)+1e-12)",
        "SUMD60": "(Sum(Greater($close-Ref($close, 1), 0), 60)-Sum(Greater(Ref($close, 1)-$close, 0), 60))/(Sum(Abs($close-Ref($close, 1)), 60)+1e-12)",
        
        # VMA因子
        "VMA5": "Mean($volume, 5)/($volume+1e-12)",
        "VMA10": "Mean($volume, 10)/($volume+1e-12)",
        "VMA20": "Mean($volume, 20)/($volume+1e-12)",
        "VMA30": "Mean($volume, 30)/($volume+1e-12)",
        "VMA60": "Mean($volume, 60)/($volume+1e-12)",
        
        # VSTD因子
        "VSTD5": "Std($volume, 5)/($volume+1e-12)",
        "VSTD10": "Std($volume, 10)/($volume+1e-12)",
        "VSTD20": "Std($volume, 20)/($volume+1e-12)",
        "VSTD30": "Std($volume, 30)/($volume+1e-12)",
        "VSTD60": "Std($volume, 60)/($volume+1e-12)",
        
        # WVMA因子
        "WVMA5": "Std(Abs($close/Ref($close, 1)-1)*$volume, 5)/(Mean(Abs($close/Ref($close, 1)-1)*$volume, 5)+1e-12)",
        "WVMA10": "Std(Abs($close/Ref($close, 1)-1)*$volume, 10)/(Mean(Abs($close/Ref($close, 1)-1)*$volume, 10)+1e-12)",
        "WVMA20": "Std(Abs($close/Ref($close, 1)-1)*$volume, 20)/(Mean(Abs($close/Ref($close, 1)-1)*$volume, 20)+1e-12)",
        "WVMA30": "Std(Abs($close/Ref($close, 1)-1)*$volume, 30)/(Mean(Abs($close/Ref($close, 1)-1)*$volume, 30)+1e-12)",
        "WVMA60": "Std(Abs($close/Ref($close, 1)-1)*$volume, 60)/(Mean(Abs($close/Ref($close, 1)-1)*$volume, 60)+1e-12)",
        
        # VSUMP因子
        "VSUMP5": "Sum(Greater($volume-Ref($volume, 1), 0), 5)/(Sum(Abs($volume-Ref($volume, 1)), 5)+1e-12)",
        "VSUMP10": "Sum(Greater($volume-Ref($volume, 1), 0), 10)/(Sum(Abs($volume-Ref($volume, 1)), 10)+1e-12)",
        "VSUMP20": "Sum(Greater($volume-Ref($volume, 1), 0), 20)/(Sum(Abs($volume-Ref($volume, 1)), 20)+1e-12)",
        "VSUMP30": "Sum(Greater($volume-Ref($volume, 1), 0), 30)/(Sum(Abs($volume-Ref($volume, 1)), 30)+1e-12)",
        "VSUMP60": "Sum(Greater($volume-Ref($volume, 1), 0), 60)/(Sum(Abs($volume-Ref($volume, 1)), 60)+1e-12)",
        
        # VSUMN因子
        "VSUMN5": "Sum(Greater(Ref($volume, 1)-$volume, 0), 5)/(Sum(Abs($volume-Ref($volume, 1)), 5)+1e-12)",
        "VSUMN10": "Sum(Greater(Ref($volume, 1)-$volume, 0), 10)/(Sum(Abs($volume-Ref($volume, 1)), 10)+1e-12)",
        "VSUMN20": "Sum(Greater(Ref($volume, 1)-$volume, 0), 20)/(Sum(Abs($volume-Ref($volume, 1)), 20)+1e-12)",
        "VSUMN30": "Sum(Greater(Ref($volume, 1)-$volume, 0), 30)/(Sum(Abs($volume-Ref($volume, 1)), 30)+1e-12)",
        "VSUMN60": "Sum(Greater(Ref($volume, 1)-$volume, 0), 60)/(Sum(Abs($volume-Ref($volume, 1)), 60)+1e-12)",
        
        # VSUMD因子
        "VSUMD5": "(Sum(Greater($volume-Ref($volume, 1), 0), 5)-Sum(Greater(Ref($volume, 1)-$volume, 0), 5))/(Sum(Abs($volume-Ref($volume, 1)), 5)+1e-12)",
        "VSUMD10": "(Sum(Greater($volume-Ref($volume, 1), 0), 10)-Sum(Greater(Ref($volume, 1)-$volume, 0), 10))/(Sum(Abs($volume-Ref($volume, 1)), 10)+1e-12)",
        "VSUMD20": "(Sum(Greater($volume-Ref($volume, 1), 0), 20)-Sum(Greater(Ref($volume, 1)-$volume, 0), 20))/(Sum(Abs($volume-Ref($volume, 1)), 20)+1e-12)",
        "VSUMD30": "(Sum(Greater($volume-Ref($volume, 1), 0), 30)-Sum(Greater(Ref($volume, 1)-$volume, 0), 30))/(Sum(Abs($volume-Ref($volume, 1)), 30)+1e-12)",
        "VSUMD60": "(Sum(Greater($volume-Ref($volume, 1), 0), 60)-Sum(Greater(Ref($volume, 1)-$volume, 0), 60))/(Sum(Abs($volume-Ref($volume, 1)), 60)+1e-12)",
    }
    
    def __init__(self, config: Dict):
        """
        初始化因子加载器
        
        Args:
            config: 配置字典
        """
        self.config = config
        self.factor_source_config = config.get('factor_source', {})
        
    def load_factors(self) -> Tuple[Dict[str, str], List[Dict]]:
        """
        加载因子
        
        Returns:
            Tuple[Dict[str, str], List[Dict]]: 
                - qlib_compatible_factors: Qlib兼容的因子 {name: expression}
                - custom_factors: 需要自定义计算的因子列表
        """
        source_type = self.factor_source_config.get('type', 'alpha158_20')
        
        logger.info(f"📊 加载因子源: {source_type}")
        
        if source_type == 'alpha158':
            return self._load_alpha158(), []
        elif source_type == 'alpha158_20':
            return self._load_alpha158_20(), []
        elif source_type == 'alpha360':
            return self._load_alpha360(), []
        elif source_type == 'custom':
            return self._load_custom_factors()
        elif source_type == 'combined':
            return self._load_combined_factors()
        else:
            raise ValueError(f"不支持的因子源类型: {source_type}")
    
    def _load_alpha158_20(self) -> Dict[str, str]:
        """加载 Alpha158(20) 因子"""
        logger.info(f"  ✓ 加载 Alpha158(20) 因子库: {len(self.ALPHA158_20_FACTORS)} 个因子")
        return self.ALPHA158_20_FACTORS.copy()
    
    def _load_alpha158(self) -> Dict[str, str]:
        """加载 Alpha158 因子"""
        logger.info(f"  ✓ 加载 Alpha158 因子库: {len(self.ALPHA158_FACTORS)} 个因子")
        return self.ALPHA158_FACTORS.copy()
    
    def _load_alpha360(self) -> Dict[str, str]:
        """
        加载 Qlib 官方 Alpha360 因子
        
        Alpha360 包含过去 60 天的原始价格数据序列，共 360 个因子：
        - CLOSE0 ~ CLOSE59: 60个收盘价因子
        - OPEN0 ~ OPEN59: 60个开盘价因子
        - HIGH0 ~ HIGH59: 60个最高价因子
        - LOW0 ~ LOW59: 60个最低价因子
        - VWAP0 ~ VWAP59: 60个成交量加权平均价因子
        - VOLUME0 ~ VOLUME59: 60个成交量因子
        
        所有价格因子都除以当日收盘价进行归一化，成交量因子除以当日成交量进行归一化。
        参考 Qlib 源码: qlib/contrib/data/loader.py Alpha360DL.get_feature_config()
        """
        alpha360_factors = {}
        
        # CLOSE: 过去60天的收盘价 (归一化)
        for i in range(59, 0, -1):
            alpha360_factors[f"CLOSE{i}"] = f"Ref($close, {i})/$close"
        alpha360_factors["CLOSE0"] = "$close/$close"
        
        # OPEN: 过去60天的开盘价 (归一化)
        for i in range(59, 0, -1):
            alpha360_factors[f"OPEN{i}"] = f"Ref($open, {i})/$close"
        alpha360_factors["OPEN0"] = "$open/$close"
        
        # HIGH: 过去60天的最高价 (归一化)
        for i in range(59, 0, -1):
            alpha360_factors[f"HIGH{i}"] = f"Ref($high, {i})/$close"
        alpha360_factors["HIGH0"] = "$high/$close"
        
        # LOW: 过去60天的最低价 (归一化)
        for i in range(59, 0, -1):
            alpha360_factors[f"LOW{i}"] = f"Ref($low, {i})/$close"
        alpha360_factors["LOW0"] = "$low/$close"
        
        # VWAP: 过去60天的成交量加权平均价 (归一化)
        for i in range(59, 0, -1):
            alpha360_factors[f"VWAP{i}"] = f"Ref($vwap, {i})/$close"
        alpha360_factors["VWAP0"] = "$vwap/$close"
        
        # VOLUME: 过去60天的成交量 (归一化)
        for i in range(59, 0, -1):
            alpha360_factors[f"VOLUME{i}"] = f"Ref($volume, {i})/($volume+1e-12)"
        alpha360_factors["VOLUME0"] = "$volume/($volume+1e-12)"
        
        logger.info(f"  ✓ 加载 Alpha360 因子库: {len(alpha360_factors)} 个因子")
        return alpha360_factors
    
    def _load_custom_factors(self) -> Tuple[Dict[str, str], List[Dict]]:
        """
        加载自定义因子库
        
        所有自定义因子都走自定义计算流程 (使用 expr_parser + function_lib)
        不再区分 Qlib 兼容与否
        
        Returns:
            Tuple[Dict[str, str], List[Dict]]:
                - qlib_compatible: 空字典 (所有因子走自定义计算)
                - custom_factors: 所有因子列表
        """
        custom_config = self.factor_source_config.get('custom', {})
        json_files = custom_config.get('json_files', [])
        quality_filter = custom_config.get('quality_filter')
        max_factors = custom_config.get('max_factors')
        
        custom_factors = []
        
        for json_file in json_files:
            file_path = Path(json_file)
            if not file_path.exists():
                logger.warning(f"  ⚠ 因子库文件不存在: {json_file}")
                continue
            
            factors = self._parse_all_factors_from_json(file_path, quality_filter)
            custom_factors.extend(factors)
        
        # 限制因子数量
        if max_factors and len(custom_factors) > max_factors:
            custom_factors = custom_factors[:max_factors]
        
        logger.info(f"  ✓ 加载自定义因子: {len(custom_factors)} 个 (使用自定义计算器)")
        
        # 返回空的 qlib_compatible，所有因子走自定义计算
        return {}, custom_factors
    
    def _parse_all_factors_from_json(self, file_path: Path, 
                                     quality_filter: Optional[str] = None) -> List[Dict]:
        """
        解析 JSON 文件中的所有因子
        
        自动过滤不可回测的因子（无缓存且表达式无效的因子会被跳过）
        
        Args:
            file_path: JSON文件路径
            quality_filter: 质量过滤器
            
        Returns:
            List[Dict]: 因子列表，包含 cache_location 字段（如果存在）
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        factors = data.get('factors', {})
        result = []
        
        # 统计
        stats = {
            'total': 0,
            'loaded': 0,
            'skipped_invalid': 0,
            'from_cache': 0,
        }
        
        for factor_id, factor_info in factors.items():
            stats['total'] += 1
            
            # 质量过滤
            if quality_filter:
                factor_quality = factor_info.get('quality', '')
                if factor_quality != quality_filter:
                    continue
            
            factor_name = factor_info.get('factor_name', factor_id)
            factor_expr = factor_info.get('factor_expression', '')
            cache_location = factor_info.get('cache_location')
            
            if not factor_expr:
                continue
            
            # 检查缓存是否存在
            has_cache = check_cache_exists(cache_location)
            
            # 只使用有缓存的因子，跳过需要重新计算的
            if not has_cache:
                stats['skipped_invalid'] += 1
                logger.debug(f"    跳过无缓存因子: {factor_name}")
                continue
            
            stats['from_cache'] += 1
            
            factor_dict = {
                'factor_id': factor_id,
                'factor_name': factor_name,
                'factor_expression': factor_expr,
                'factor_description': factor_info.get('factor_description', ''),
            }
            
            # 包含 cache_location 字段（如果存在）
            if cache_location:
                factor_dict['cache_location'] = cache_location
            
            result.append(factor_dict)
            stats['loaded'] += 1
        
        # 输出过滤统计
        if stats['skipped_invalid'] > 0:
            logger.info(f"    ⚠ 跳过 {stats['skipped_invalid']} 个无缓存因子")
        logger.info(f"    📁 {stats['from_cache']} 个因子从缓存加载")
        
        return result
    
    def _load_combined_factors(self) -> Tuple[Dict[str, str], List[Dict]]:
        """加载组合因子（官方 + 自定义）"""
        combined_config = self.factor_source_config.get('combined', {})
        official_source = combined_config.get('official_source', 'alpha158_20')
        include_custom = combined_config.get('include_custom', True)
        
        # 加载官方因子
        if official_source == 'alpha158':
            qlib_compatible = self._load_alpha158()
        elif official_source == 'alpha158_20':
            qlib_compatible = self._load_alpha158_20()
        elif official_source == 'alpha360':
            qlib_compatible = self._load_alpha360()
        else:
            qlib_compatible = {}
        
        needs_llm = []
        
        # 加载自定义因子
        if include_custom:
            custom_compatible, custom_llm = self._load_custom_factors()
            qlib_compatible.update(custom_compatible)
            needs_llm.extend(custom_llm)
        
        logger.info(f"  ✓ 组合因子: {len(qlib_compatible)} 个Qlib兼容, {len(needs_llm)} 个需要LLM计算")
        return qlib_compatible, needs_llm
    
    def _parse_factor_json(self, file_path: Path, 
                          quality_filter: Optional[str] = None) -> Tuple[Dict[str, str], List[Dict]]:
        """
        解析因子 JSON 文件
        
        Args:
            file_path: JSON文件路径
            quality_filter: 质量过滤器
            
        Returns:
            Tuple[Dict[str, str], List[Dict]]: (qlib兼容因子, 需要LLM计算的因子)
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        factors = data.get('factors', {})
        qlib_compatible = {}
        needs_llm = []
        
        for factor_id, factor_info in factors.items():
            # 质量过滤
            if quality_filter:
                factor_quality = factor_info.get('quality', '')
                if factor_quality != quality_filter:
                    continue
            
            factor_name = factor_info.get('factor_name', factor_id)
            factor_expr = factor_info.get('factor_expression', '')
            
            if not factor_expr:
                continue
            
            # 检查是否Qlib兼容
            if self._is_qlib_compatible(factor_expr):
                # 尝试转换表达式
                converted = self._convert_to_qlib_expression(factor_expr)
                if converted:
                    qlib_compatible[factor_name] = converted
                else:
                    needs_llm.append({
                        'factor_id': factor_id,
                        'factor_name': factor_name,
                        'factor_expression': factor_expr,
                        'factor_description': factor_info.get('factor_description', ''),
                        'variables': factor_info.get('variables', {})
                    })
            else:
                needs_llm.append({
                    'factor_id': factor_id,
                    'factor_name': factor_name,
                    'factor_expression': factor_expr,
                    'factor_description': factor_info.get('factor_description', ''),
                    'variables': factor_info.get('variables', {})
                })
        
        return qlib_compatible, needs_llm
    
    def _is_qlib_compatible(self, expr: str) -> bool:
        """
        检查表达式是否与 Qlib 兼容
        
        Qlib 不支持的操作符列表
        """
        unsupported_patterns = [
            'ZSCORE(', 'RANK(', 'TS_ZSCORE(', 'TS_RANK(',
            'DELAY(', 'DELTA(', 'DECAYLINEAR(',
            'REGBETA(', 'REGRESI(', 'SEQUENCE(',
            'SUMIF(', 'COUNTIF(', 'FILTER(',
            'POW(', 'SIGN(', 'INV(',
            'RSI(', 'MACD(', 'BB_',
            'EMA(', 'WMA(', 'SMA(',
            'TS_CORR(', 'TS_COVARIANCE(',
            'TS_MAD(', 'TS_QUANTILE(', 'TS_PCTCHANGE(',
            'HIGHDAY(', 'LOWDAY(', 'SUMAC(',
            'TS_ARGMAX(', 'TS_ARGMIN(',
            '?', ':'  # 条件表达式
        ]
        
        expr_upper = expr.upper()
        for pattern in unsupported_patterns:
            if pattern.upper() in expr_upper:
                return False
        
        return True
    
    def _convert_to_qlib_expression(self, expr: str) -> Optional[str]:
        """
        将自定义表达式转换为 Qlib 兼容表达式
        
        Args:
            expr: 原始表达式
            
        Returns:
            Optional[str]: 转换后的表达式，如果无法转换则返回 None
        """
        # 简单的转换规则
        conversions = {
            'TS_MEAN': 'Mean',
            'TS_STD': 'Std',
            'TS_VAR': 'Var',
            'TS_MAX': 'Max',
            'TS_MIN': 'Min',
            'TS_SUM': 'Sum',
            '$return': '($close/Ref($close,1)-1)',
        }
        
        result = expr
        for old, new in conversions.items():
            result = result.replace(old, new)
        
        # 再次检查是否兼容
        if self._is_qlib_compatible(result):
            return result
        
        return None
    
    def get_factor_info(self) -> Dict[str, Any]:
        """获取因子信息摘要"""
        source_type = self.factor_source_config.get('type', 'alpha158_20')
        
        if source_type == 'alpha158':
            return {
                'type': 'alpha158',
                'count': len(self.ALPHA158_FACTORS),
                'description': 'Qlib Alpha158 因子库'
            }
        elif source_type == 'alpha158_20':
            return {
                'type': 'alpha158_20',
                'count': len(self.ALPHA158_20_FACTORS),
                'description': 'Qlib Alpha158(20) 核心因子库'
            }
        elif source_type == 'alpha360':
            return {
                'type': 'alpha360',
                'count': 'dynamic',
                'description': 'Qlib Alpha360 扩展因子库'
            }
        elif source_type == 'custom':
            return {
                'type': 'custom',
                'json_files': self.factor_source_config.get('custom', {}).get('json_files', []),
                'description': '自定义因子库'
            }
        else:
            return {
                'type': source_type,
                'description': '未知因子源'
            }


import numpy as np
import pandas as pd
import operator
from joblib import Parallel, delayed


def datatype_adapter(func):
    def wrapper(*args):
        # 对于单个输入，若是np array，则转成df
        if len(args) == 1 and isinstance(args[0], np.ndarray):
            # 转换NumPy数组到DataFrame
            new_args = (pd.DataFrame(args[0]),)
            # 执行函数并转回NumPy数组
            result = func(*new_args)
            return result
        # 对于单个输入，若是float，则转成df再转回float
        if len(args) == 1 and isinstance(args[0], (float, int)):
            new_args = (pd.DataFrame([args[0]]),)
            result = func(*new_args)
            return float(result.iloc[0])
        # 对于典型输入，func(df, p) or func(df)
        if (len(args) == 2 and isinstance(args[0], np.ndarray) and not isinstance(args[1], np.ndarray)):
            # 转换NumPy数组到DataFrame
            new_args = (pd.DataFrame(args[0]), args[1])
            # 执行函数并转回NumPy数组
            result = func(*new_args)
        elif (len(args) == 2 and isinstance(args[1], np.ndarray) and not isinstance(args[0], np.ndarray)):
            # 转换NumPy数组到DataFrame
            new_args = (args[0], pd.DataFrame(args[1]))
            # 执行函数并转回NumPy数组
            result = func(*new_args)
        else:
            result = func(*args)
        return result

    return wrapper

@datatype_adapter
def DELTA(df:pd.DataFrame, p:int=1):
    return df.groupby('instrument').transform(lambda x: x.diff(periods=p))

@datatype_adapter
def RANK(df:pd.DataFrame):
    """计算横截面排序"""
    return df.groupby('datetime').rank(pct=True)

@datatype_adapter
def MEAN(df:pd.DataFrame):
    """计算横截面平均值"""
    return df.groupby('datetime').mean()

@datatype_adapter
def STD(df:pd.DataFrame):
    """计算横截面标准差"""
    return df.groupby('datetime').std()

@datatype_adapter
def SKEW(df:pd.DataFrame):
    """计算横截面偏度"""
    from scipy.stats import skew as scipy_skew
    return df.groupby('datetime').transform(lambda x: scipy_skew(x.dropna(), nan_policy='omit') if len(x.dropna()) >= 3 else np.nan)

@datatype_adapter
def KURT(df:pd.DataFrame):
    """计算横截面峰度"""
    from scipy.stats import kurtosis
    # 使用 transform 保持原始索引结构
    def calc_kurt(group):
        k = kurtosis(group.dropna(), fisher=True, nan_policy='omit')
        return pd.Series(k, index=group.index)
    return df.groupby('datetime').transform(lambda x: kurtosis(x.dropna(), fisher=True, nan_policy='omit') if len(x.dropna()) >= 4 else np.nan)

@datatype_adapter
def MAX(df:pd.DataFrame):
    """计算横截面最大值"""
    return df.groupby('datetime').max()

@datatype_adapter
def MIN(df:pd.DataFrame):
    """计算横截面最小值"""
    return df.groupby('datetime').min()

@datatype_adapter
def MEDIAN(df:pd.DataFrame):
    """计算横截面中位数"""
    return df.groupby('datetime').median()


@datatype_adapter
def TS_KURT(df:pd.DataFrame, p:int=5):
    """计算时间序列的滚动峰度 (Rolling Kurtosis)"""
    from scipy.stats import kurtosis
    def rolling_kurt(x):
        return x.rolling(p, min_periods=min(4, p)).apply(
            lambda arr: kurtosis(arr, fisher=True, nan_policy='omit') if len(arr.dropna()) >= 4 else np.nan,
            raw=False
        )
    return df.groupby('instrument').transform(rolling_kurt)

@datatype_adapter
def TS_SKEW(df:pd.DataFrame, p:int=5):
    """计算时间序列的滚动偏度 (Rolling Skewness)"""
    from scipy.stats import skew as scipy_skew
    def rolling_skew(x):
        return x.rolling(p, min_periods=min(3, p)).apply(
            lambda arr: scipy_skew(arr, nan_policy='omit') if len(arr.dropna()) >= 3 else np.nan,
            raw=False
        )
    return df.groupby('instrument').transform(rolling_skew)

@datatype_adapter
def TS_RANK(df:pd.DataFrame, p:int=5):
    """计算时间序列的百分比排名"""
    return df.groupby('instrument').transform(lambda x: x.rolling(p, min_periods=1).rank(pct=True))

@datatype_adapter
def TS_MAX(df:pd.DataFrame, p:int=5):
    """计算时间序列的最大值"""
    return df.groupby('instrument').transform(lambda x: x.rolling(p, min_periods=1).max())

@datatype_adapter
def TS_MIN(df:pd.DataFrame, p:int=5):
    """计算时间序列的最小值"""
    return df.groupby('instrument').transform(lambda x: x.rolling(p, min_periods=1).min())

@datatype_adapter
def TS_MEAN(df:pd.DataFrame, p:int=5):
    """计算时间序列的平均值"""
    return df.groupby('instrument').transform(lambda x: x.rolling(p, min_periods=1).mean())

@datatype_adapter
def TS_MEDIAN(df:pd.DataFrame, p:int=5):
    """计算时间序列的中位数"""
    return df.groupby('instrument').transform(lambda x: x.rolling(p, min_periods=1).median())

@datatype_adapter
def PERCENTILE(df: pd.DataFrame, q: float, p: int = None):
    """
    计算给定数据的分位数。

    参数:
        df (pd.DataFrame): 输入数据，可以是 DataFrame 或 NumPy 数组。
        q (float): 分位数，范围在 [0, 1] 之间。
        p (int): 滚动窗口大小，如果提供，则计算滚动分位数。

    返回:
        pd.DataFrame: 包含分位数的 DataFrame。
    """
    assert 0 <= q <= 1, "分位数 q 必须在 [0, 1] 之间"
    
    if p is not None:
        # 如果有滚动窗口大小，计算滚动分位数
        return df.groupby('instrument').transform(lambda x: x.rolling(p, min_periods=1).quantile(q))
    else:
        # 如果没有滚动窗口大小，直接计算分位数
        return df.groupby('instrument').transform(lambda x: x.quantile(q))



@datatype_adapter
def TS_SUM(df:pd.DataFrame, p:int=5):
    """计算时间序列的累加和"""
    return df.groupby('instrument').transform(lambda x: x.rolling(p, min_periods=1).sum())


@datatype_adapter
def TS_ARGMAX(df: pd.DataFrame, p: int = 5):
    """计算过去p天内最大值出现的位置距今天数"""
    def rolling_argmax(window):
        return len(window) - window.argmax() - 1
    return df.groupby('instrument').transform(lambda x: x.rolling(p, min_periods=1).apply(rolling_argmax, raw=True))

@datatype_adapter
def TS_ARGMIN(df: pd.DataFrame, p: int = 5):
    """计算过去p天内最小值出现的位置距今天数"""
    def rolling_argmin(window):
        return len(window) - window.argmin() - 1
    return df.groupby('instrument').transform(lambda x: x.rolling(p, min_periods=1).apply(rolling_argmin, raw=True))



def MAX(x:pd.DataFrame, y:pd.DataFrame, z:pd.DataFrame=None):
    """计算多个DataFrame之间的最大值"""
    if z is None:
        return np.maximum(x, y)
    else:
        return np.maximum(np.maximum(x, y), z)




def MIN(x:pd.DataFrame, y:pd.DataFrame, z:pd.DataFrame=None):
    """计算多个DataFrame之间的最小值""" 
    if z is None:
        return np.minimum(x, y)
    else:
        return np.minimum(np.minimum(x, y), z)
    


@datatype_adapter
def ABS(df:pd.DataFrame):
    """计算DataFrame中每个元素的绝对值"""   
    return df.groupby('instrument').transform(lambda x: x.abs())    

@datatype_adapter
def DELAY(df:pd.DataFrame, p:int=1):
    """将数据延迟p个周期"""
    assert p >= 0, ValueError("DELAY的时长不能小于0，否则将会造成数据窥测")
    return df.groupby('instrument').transform(lambda x: x.shift(p))


def TS_CORR(df1:pd.Series, df2: np.ndarray | pd.Series, p:int=5):
    """计算两个序列的滚动相关性"""
    # 如果 df2 是 numpy.ndarray，使用固定窗口方法
    if isinstance(df2, np.ndarray):
        # 如果 p 不等于数组长度，使用数组长度作为窗口大小
        if p != len(df2):
            p = len(df2)
        def corr(window):
            x = window
            y = df2[:len(window)]
            # 计算均值
            mean_x = np.mean(x)
            mean_y = np.mean(y)
            
            # 计算协方差和标准差
            cov = np.sum((x - mean_x) * (y - mean_y))
            std_x = np.sqrt(np.sum((x - mean_x) ** 2))
            std_y = np.sqrt(np.sum((y - mean_y) ** 2))
            
            # 计算相关系数
            if std_x == 0 or std_y == 0:
                return 0.0
            return cov / (std_x * std_y)
        
        return df1.groupby('instrument').transform(lambda x: x.rolling(p, min_periods=2).apply(corr, raw=True))
    # 如果 df2 是 pd.Series 或 pd.DataFrame，使用 DataFrame 方法
    elif isinstance(df2, (pd.Series, pd.DataFrame)):
        def rolling_corr(group, df2, p):
            # 获取当前分组的 instrument
            instrument = group.name
            # 从 df2 中提取对应的 instrument 数据
            if isinstance(df2, pd.DataFrame) and 'instrument' in df2.index.names:
                df2_group = df2.xs(instrument, level='instrument')
            elif isinstance(df2, pd.Series) and 'instrument' in df2.index.names:
                df2_group = df2.xs(instrument, level='instrument')
            else:
                # 如果 df2 没有 instrument 索引，直接使用 df2
                df2_group = df2
            # 计算滚动相关性
            return group.rolling(p, min_periods=2).corr(df2_group)

        # 使用 groupby 和 apply 来计算每个 instrument 的滚动相关性
        result = df1.groupby('instrument').apply(lambda x: rolling_corr(x, df2, p))
        # 由于 apply 会改变索引结构，我们需要将其恢复为原始结构
        result = result.reset_index(level=0, drop=True).sort_index()
        return result
    else:
        raise TypeError(f"TS_CORR 不支持 df2 的类型: {type(df2)}")


def TS_COVARIANCE(df1:pd.DataFrame, df2:pd.DataFrame, p:int=5):  
    """计算两个序列的滚动协方差"""
    # 如果 df2 是 numpy.ndarray，使用固定窗口方法
    if isinstance(df2, np.ndarray):
        # 如果 p 不等于数组长度，使用数组长度作为窗口大小
        if p != len(df2):
            p = len(df2)
        def cov(window):
            return np.cov(window, df2[:len(window)])[0, 1] if len(window) > 1 else 0.0
        return df1.groupby('instrument').transform(lambda x: x.rolling(p, min_periods=2).apply(cov, raw=True))
    # 如果 df2 是 pd.Series 或 pd.DataFrame，使用 DataFrame 方法
    elif isinstance(df2, (pd.Series, pd.DataFrame)):
        def rolling_cov(group, df2, p):
            # 获取当前分组的 instrument
            instrument = group.name
            # 从 df2 中提取对应的 instrument 数据
            if isinstance(df2, pd.DataFrame) and 'instrument' in df2.index.names:
                df2_group = df2.xs(instrument, level='instrument')
            elif isinstance(df2, pd.Series) and 'instrument' in df2.index.names:
                df2_group = df2.xs(instrument, level='instrument')
            else:
                # 如果 df2 没有 instrument 索引，直接使用 df2
                df2_group = df2
            # 计算滚动协方差
            return group.rolling(p, min_periods=2).cov(df2_group)

        # 使用 groupby 和 apply 来计算每个 instrument 的滚动协方差
        result = df1.groupby('instrument').apply(lambda x: rolling_cov(x, df2, p))
        # 由于 apply 会改变索引结构，我们需要将其恢复为原始结构
        result = result.reset_index(level=0, drop=True).sort_index()
        return result
    else:
        raise TypeError(f"TS_COVARIANCE 不支持 df2 的类型: {type(df2)}")

@datatype_adapter
def TS_STD(df:pd.DataFrame, p:int=20):
    """计算时间序列的滚动标准差(Standard Deviation)"""
    return df.groupby('instrument').transform(lambda x: x.rolling(p, min_periods=1).std())





@datatype_adapter
def TS_VAR(df: pd.DataFrame, p: int = 5, ddof: int = 1):
    """计算时间序列的滚动方差(Variance)"""
    return df.groupby('instrument').transform(
        lambda x: x.rolling(p, min_periods=1).var(ddof=ddof)
    )

@datatype_adapter
def SIGN(df: pd.DataFrame):
    """计算DataFrame中每个元素的符号"""
    return np.sign(df)

@datatype_adapter
def SMA(df:pd.DataFrame, m:float=None, n:float=None):
    """
    计算简单移动平均线(Simple Moving Average)
    
    参数:
        df (pd.DataFrame): 输入数据
        m (float, optional): 移动平均的周期数
        n (float, optional): 移动平均的权重
    Y_{i+1} = m/n*X_i + (1 - m/n)*Y_i
    """
        
    if isinstance(m, int) and m >= 1 and n is None:
        return df.groupby('instrument').transform(lambda x: x.rolling(m, min_periods=1).mean())
    else:
        return df.groupby('instrument').transform(lambda x: x.ewm(alpha=n/m).mean())

@datatype_adapter
def EMA(df:pd.DataFrame, p):
    """
    计算指数移动平均线(Exponential Moving Average)
    
    参数:
        df (pd.DataFrame): 输入数据
        p (int): 移动平均的周期数

    返回:
        pd.DataFrame: 指数移动平均线结果
    """
    return df.groupby('instrument').transform(lambda x: x.ewm(span=int(p), min_periods=1).mean())
    
@datatype_adapter
def WMA(df:pd.DataFrame, p:int=20):
    """
    计算加权移动平均线(Weighted Moving Average)
    
    参数:
        df (pd.DataFrame): 输入数据
        p (int): 移动平均的周期数
        
    返回:
        pd.DataFrame: 加权移动平均线结果
    """
    # 计算权重，最近的数据（i=0）有最大的权重
    weights = [0.9**i for i in range(p)][::-1]
    def calculate_wma(window):
        return (window * weights[:len(window)]).sum() / sum(weights[:len(window)])

    # 应用权重计算滑动WMA
    return df.groupby('instrument').transform(lambda x: x.rolling(window=p, min_periods=1).apply(calculate_wma, raw=True))

@datatype_adapter
def COUNT(cond:pd.DataFrame, p:int=20):
    """
    计算条件计数
    
    参数:
        cond (pd.DataFrame): 条件数据
        p (int): 滚动窗口大小
    
    返回:
        pd.DataFrame: 条件计数结果
    """
    return cond.groupby('instrument').transform(lambda x: x.rolling(p, min_periods=1).sum())

@datatype_adapter
def SUMIF(df:pd.DataFrame, p:int, cond:pd.DataFrame):
    """
    计算满足条件的序列的滚动和
    
    参数:
        df (pd.DataFrame): 输入数据
        p (int): 滚动窗口大小
        cond (pd.DataFrame): 条件数据
    
    返回:
        pd.DataFrame: 满足条件的序列的滚动和
    """
    return (df * cond).groupby('instrument').transform(lambda x: x.rolling(p, min_periods=1).sum())

@datatype_adapter
def FILTER(df:pd.DataFrame, cond:pd.DataFrame):
    """
    根据条件过滤序列，保留满足条件的元素，不满足条件的元素置为0
    
    参数:
        df (pd.DataFrame): 输入数据
        cond (pd.DataFrame): 条件数据
    
    返回:
        pd.DataFrame: 根据条件过滤后的序列
    """
    return df.mul(cond)
    

@datatype_adapter
def PROD(df:pd.DataFrame, p:int=5):
    """
    计算序列的滚动乘积
    
    参数:
        df (pd.DataFrame): 输入数据
        p (int): 滚动窗口大小
    
    返回:
        pd.DataFrame: 滚动乘积结果
    """

    # 使用rolling方法创建一个滑动窗口，然后应用累乘
    if isinstance(p, int):
        return df.groupby('instrument').transform(lambda x: x.rolling(p, min_periods=1).apply(lambda x: x.prod(), raw=True))
    else:
        return df.mul(p)    

@datatype_adapter
def DECAYLINEAR(df:pd.DataFrame, p:int=5):
    """
    计算序列的线性衰减加权平均
    
    参数:
        df (pd.DataFrame): 输入数据
        p (int): 滚动窗口大小
    
    返回:
        pd.DataFrame: 线性衰减加权平均结果
    """
    assert isinstance(p, int), ValueError(f"DECAYLINEAR仅接收正整数参数n，接收到{type(p).__name__}")
    decay_weights = np.arange(1, p+1, 1)
    decay_weights = decay_weights / decay_weights.sum()
    
    def calculate_deycaylinear(window):
        return (window * decay_weights[:len(window)]).sum()
    
    return df.groupby('instrument').transform(lambda x: x.rolling(p, min_periods=1).apply(calculate_deycaylinear, raw=True))

@datatype_adapter
def HIGHDAY(df:pd.DataFrame, p:int=5):
    """
    计算序列中最大值出现的位置距今天数
    
    参数:
        df (pd.DataFrame): 输入数据
        p (int): 滚动窗口大小
    
    返回:
        pd.DataFrame: 最大值出现的位置距今天数
    """
    assert isinstance(p, int), ValueError(f"HIGHDAY仅接收正整数参数n，接收到{type(p).__name__}")
    def highday(window):
        return len(window) - window.argmax(axis=0)
    return df.groupby('instrument').transform(lambda x: x.rolling(p, min_periods=1).apply(highday, raw=True))

@datatype_adapter
def LOWDAY(df:pd.DataFrame, p:int=5):
    """
    计算序列中最小值出现的位置距今天数
    
    参数:
        df (pd.DataFrame): 输入数据
        p (int): 滚动窗口大小
    
    返回:
        pd.DataFrame: 最小值出现的位置距今天数
    """
    assert isinstance(p, int), ValueError(f"LOWDAY仅接收正整数参数n，接收到{type(p).__name__}")
    def lowday(window):
        return len(window) - window.argmin(axis=0)
    return df.groupby('instrument').transform(lambda x: x.rolling(p, min_periods=1).apply(lowday, raw=True))
    

def SEQUENCE(n):
    """
    生成一个从1到n的等差数列
    
    参数:
        n (int): 数列的长度
    """
    assert isinstance(n, int), ValueError(f"SEQUENCE(n)仅接收正整数参数n，接收到{type(n).__name__}")
    return np.linspace(1, n, n, dtype=np.float32)

@datatype_adapter
def SUMAC(df:pd.DataFrame, p:int=10):
    """
    计算序列的滚动累加和
    
    参数:
        df (pd.DataFrame): 输入数据
        p (int): 滚动窗口大小
    
    返回:
        pd.DataFrame: 滚动累加和结果
    """
    assert isinstance(p, int), ValueError(f"SUMAC仅接收正整数参数n，接收到{type(p).__name__}")
    return df.groupby('instrument').transform(lambda x: x.rolling(p, min_periods=1).sum())



def calculate_beta(y, x):
    """计算回归系数（beta）"""
    X = np.vstack([x, np.ones(len(x))]).T
    beta, _ = np.linalg.lstsq(X, y, rcond=None)[0]
    return beta

def rolling_beta(df1_group, df2_group, p):
    """对 df1 和 df2 的滚动窗口计算 beta"""
    result = np.empty(len(df1_group))
    result[:] = np.nan  # 初始化结果为 NaN

    # 滚动计算 beta
    for i in range(p - 1, len(df1_group)):
        window_y = df1_group.iloc[i - p + 1 : i + 1].values
        window_x = df2_group.iloc[:p].values if df1_group.shape != df2_group.shape else df2_group.iloc[i - p + 1 : i + 1].values
        result[i] = calculate_beta(window_y, window_x)

    # 返回与输入数据索引一致的 Series
    return pd.Series(result, index=df1_group.index)


def REGBETA(df1: pd.DataFrame, df2: pd.DataFrame, p: int = 5, n_jobs: int = -1):
    """
    计算 df1 和 df2 的滚动回归系数（beta）
    
    参数:
        df1 (pd.DataFrame): 第一个 DataFrame，包含目标变量。
        df2 (pd.DataFrame): 第二个 DataFrame，包含解释变量。
        p (int): 滚动窗口大小。
        n_jobs (int): 并行计算的 CPU 核心数。
    
    返回:
        pd.Series: 滚动回归系数结果。
    """
    assert not (isinstance(df2, np.ndarray) and isinstance(df1, np.ndarray)), "df1与df2不能同时是np.ndarray，至少有一个需要是dataframe，例如$close。"
    if isinstance(df2, np.ndarray) or isinstance(df1, np.ndarray):
        if isinstance(df1, np.ndarray):
            df3 = df1
            df1 = df2
            df2 = df3
            p = min(len(df2), p)
            df2 = pd.Series(df2)
        # 填充缺失值
        df1 = df1.fillna(0)
        
        # 获取分组后的数据
        df1_groups = list(df1.groupby('instrument'))
        df2 = pd.Series(df2[:p])
        
        # 使用 joblib 进行并行计算
        results = Parallel(n_jobs=n_jobs)(
            delayed(rolling_beta)(df1_group, df2, p)
            for _, df1_group in df1_groups
        )
        
        # 将结果合并为一个 Series，并确保索引一致
        result = pd.concat(results)
        result = result.sort_index()  # 按索引排序
        return result
    
    else:
        # 确保 df1 和 df2 的索引一致
        assert df1.index.equals(df2.index), "df1 和 df2 的索引必须对齐"
        
        # 填充缺失值
        df1 = df1.fillna(0)
        df2 = df2.fillna(0)
        
        # 获取分组后的数据
        df1_groups = list(df1.groupby('instrument'))
        df2_groups = list(df2.groupby('instrument'))
        
        # 确保分组顺序一致
        if len(df1_groups) != len(df2_groups):
            raise ValueError("df1 和 df2 的分组数量不一致，请检查数据。")
        
        # 使用 joblib 进行并行计算
        results = Parallel(n_jobs=n_jobs)(
            delayed(rolling_beta)(df1_group, df2_group, p)
            for (_, df1_group), (_, df2_group) in zip(df1_groups, df2_groups)
        )
        
        # 将结果合并为一个 Series，并确保索引一致
        result = pd.concat(results)
        result = result.sort_index()  # 按索引排序
        return result



def calculate_residuals(y, x):
    """计算残差（实际值 - 预测值）"""
    # 添加常数项以计算截距
    X = np.vstack([x, np.ones(len(x))]).T
    # 使用最小二乘法计算回归系数
    beta, intercept = np.linalg.lstsq(X, y, rcond=None)[0]
    # 计算预测值
    y_pred = beta * x + intercept
    # 计算残差（实际值 - 预测值）
    residuals = y - y_pred
    return residuals[-1]  # 返回最后一个残差值（滚动窗口的最新值）

def rolling_residuals(df1_group, df2_group, p):
    """对 df1 和 df2 的滚动窗口计算残差"""
    result = np.empty(len(df1_group))
    result[:] = np.nan  # 初始化结果为 NaN

    # 滚动计算残差
    for i in range(p - 1, len(df1_group)):
        window_y = df1_group.iloc[i - p + 1 : i + 1].values
        window_x = df2_group.iloc[:p].values if df1_group.shape != df2_group.shape else df2_group.iloc[i - p + 1 : i + 1].values
        result[i] = calculate_residuals(window_y, window_x)

    # 返回与输入数据索引一致的 Series
    return pd.Series(result, index=df1_group.index)


def REGRESI(df1: pd.DataFrame, df2: pd.DataFrame, p: int = 5, n_jobs: int = -1):
    """
    计算 df1 和 df2 的滚动残差
    
    参数:
        df1 (pd.DataFrame): 第一个 DataFrame，包含目标变量。
        df2 (pd.DataFrame): 第二个 DataFrame，包含解释变量。
        p (int): 滚动窗口大小。
        n_jobs (int): 并行计算的 CPU 核心数。
    
    返回:
        pd.Series: 滚动残差结果。
    """
    
    assert not (isinstance(df2, np.ndarray) and isinstance(df1, np.ndarray)), "df1与df2不能同时是np.ndarray，至少有一个需要是dataframe，例如$close。"
    if isinstance(df2, np.ndarray) or isinstance(df1, np.ndarray):
        if isinstance(df1, np.ndarray):
            df3 = df1
            df1 = df2
            df2 = df3
            p = min(len(df2), p)
        # 填充缺失值
        df1 = df1.fillna(0)
        df2 = pd.Series(df2[:p])
        
        # 获取分组后的数据
        df1_groups = list(df1.groupby('instrument'))
        
        # 使用 joblib 进行并行计算
        results = Parallel(n_jobs=n_jobs)(
            delayed(rolling_residuals)(df1_group, df2, p)
            for _, df1_group in df1_groups
        )
        
        # 将结果合并为一个 Series，并确保索引一致
        result = pd.concat(results)
        result = result.sort_index()  # 按索引排序
        return result
    
    else:
        # 处理 df2 只有 datetime 索引的情况（例如来自 MEAN 等截面函数）
        # 如果 df1 是 MultiIndex 而 df2 不是，需要将 df2 广播到与 df1 相同的结构
        if isinstance(df1.index, pd.MultiIndex) and not isinstance(df2.index, pd.MultiIndex):
            # df2 只有 datetime 索引（来自截面函数如 MEAN），需要广播到 (datetime, instrument) MultiIndex
            # 获取 df1 的 datetime 层级值
            datetime_level = df1.index.get_level_values('datetime')
            # 将 df2 的索引对齐到 df1 的 datetime 层级
            df2_aligned = df2.reindex(datetime_level, method='ffill')
            # 创建与 df1 相同的 MultiIndex
            df2_aligned.index = df1.index
            df2 = df2_aligned
        elif not df1.index.equals(df2.index):
            # 如果索引结构不同，尝试对齐
            if isinstance(df1.index, pd.MultiIndex) and isinstance(df2.index, pd.MultiIndex):
                # 两个都是 MultiIndex，尝试对齐
                try:
                    df2 = df2.reindex(df1.index)
                except Exception:
                    assert df1.index.equals(df2.index), "df1 和 df2 的索引必须对齐"
            else:
                assert df1.index.equals(df2.index), "df1 和 df2 的索引必须对齐"
        
        # 填充缺失值
        df1 = df1.fillna(0)
        df2 = df2.fillna(0)
        
        # 获取分组后的数据
        df1_groups = list(df1.groupby('instrument'))
        
        # 如果 df2 已经是 MultiIndex 且与 df1 对齐，按 instrument 分组
        if isinstance(df2.index, pd.MultiIndex) and 'instrument' in df2.index.names:
            df2_groups = list(df2.groupby('instrument'))
            # 确保分组顺序一致
            if len(df1_groups) != len(df2_groups):
                raise ValueError("df1 和 df2 的分组数量不一致，请检查数据。")
            # 使用 joblib 进行并行计算
            results = Parallel(n_jobs=n_jobs)(
                delayed(rolling_residuals)(df1_group, df2_group, p)
                for (_, df1_group), (_, df2_group) in zip(df1_groups, df2_groups)
            )
        else:
            # df2 是截面数据（只有 datetime），对每个 instrument 使用相同的 df2
            # 这种情况不应该发生，因为我们已经在上面的逻辑中处理了
            results = Parallel(n_jobs=n_jobs)(
                delayed(rolling_residuals)(df1_group, df2, p)
                for _, df1_group in df1_groups
            )
        
        # 将结果合并为一个 Series，并确保索引一致
        result = pd.concat(results)
        result = result.sort_index()  # 按索引排序
        return result

        
### 数学运算
@datatype_adapter
def EXP(df:pd.DataFrame):
    """
    计算序列的指数值
    
    参数:
        df (pd.DataFrame): 输入数据
        
    返回:
        pd.DataFrame: 指数值结果
    """
    return df.apply(np.exp)

@datatype_adapter
def SQRT(df: pd.DataFrame):
    """计算序列的平方根"""
    if isinstance(df, int):
        return np.sqrt(df)
    return df.apply(np.sqrt)

@datatype_adapter
def LOG(df:pd.DataFrame):
    """计算序列的自然对数"""
    if isinstance(df, int):
        return np.log(df)
    return (df+1).apply(np.log)

@datatype_adapter
def INV(df: pd.DataFrame):
    """计算序列的倒数 (1/x)"""
    return 1 / df

@datatype_adapter
def POW(df:pd.DataFrame, n:int):
    """计算序列的幂"""
    return np.power(df, n)

def FLOOR(df:pd.DataFrame):
    """计算序列的向下取整"""
    return df.apply(np.floor)

@datatype_adapter
def TS_ZSCORE(df: pd.DataFrame, p:int=5):
    assert isinstance(p, int), ValueError(f"TS_ZSCORE仅接收正整数参数n，接收到{type(p).__name__}")
    # assert isinstance(df, pd.DataFrame), ValueError(f"TS_ZSCORE仅接收pd.DataFrame作为A的类型，接收到{type(df).__name__}")
    return (df - df.groupby('instrument').transform(lambda x: x.rolling(p, min_periods=1).mean())) / df.groupby('instrument').transform(lambda x: x.rolling(p, min_periods=1).std())

@datatype_adapter
def ZSCORE(df):
    # 在每个因子截面上计算平均值和标准差
    mean = df.groupby('datetime').mean()
    std = df.groupby('datetime').std()
    
    # 计算z-score: (X - μ) / σ
    zscore = (df - mean) / std
    return zscore

@datatype_adapter
def SCALE(df: pd.DataFrame, target_sum: float = 1.0):
    """
    将序列标准化使其绝对值之和等于target_sum
    """
    # 计算当前绝对值之和
    abs_sum = ABS(df).groupby('datetime').sum()
    # 进行缩放
    return df.multiply(target_sum).div(abs_sum, axis=0)


@datatype_adapter
def TS_MAD(df: pd.DataFrame, p: int = 5):
    """
    计算时间序列的滚动中位数绝对偏差(Median Absolute Deviation)
    
    MAD = median(|X_i - median(X)|)
    
    参数:
        df (pd.DataFrame): 输入数据
        p (int): 滚动窗口大小
        
    返回:
        pd.DataFrame: 滚动MAD结果
    """
    def rolling_mad(window):
        # 计算窗口内的中位数
        median_val = np.median(window)
        # 计算每个值与中位数的绝对偏差
        abs_dev = np.abs(window - median_val)
        # 返回这些偏差的中位数
        return np.median(abs_dev)
    
    return df.groupby('instrument').transform(
        lambda x: x.rolling(p, min_periods=1).apply(rolling_mad, raw=True)
    )


@datatype_adapter
def TS_QUANTILE(df: pd.DataFrame, p: int = 5, q: float = 0.5):
    """
    计算时间序列的滚动分位数
    
    参数:
        df (pd.DataFrame): 输入数据
        p (int): 滚动窗口大小
        q (float): 分位数，范围在[0, 1]之间
        
    返回:
        pd.DataFrame: 滚动分位数结果
    """
    assert 0 <= q <= 1, "分位数 q 必须在 [0, 1] 之间"
    return df.groupby('instrument').transform(lambda x: x.rolling(p, min_periods=1).quantile(q))

@datatype_adapter
def TS_PCTCHANGE(df: pd.DataFrame, p: int = 1):
    """
    计算时间序列的百分比变化
    
    参数:
        df (pd.DataFrame): 输入数据
        p (int): 计算间隔，默认为1（相邻期）
        
    返回:
        pd.DataFrame: 百分比变化结果
    """
    return df.groupby('instrument').transform(lambda x: x.pct_change(periods=p, fill_method=None).fillna(0))


def ADD(df1, df2):
    """加法运算，自动处理索引对齐"""
    return _arithmetic_with_alignment(df1, df2, np.add)

def SUBTRACT(df1, df2):
    """减法运算，自动处理索引对齐"""
    return _arithmetic_with_alignment(df1, df2, np.subtract)

def MULTIPLY(df1, df2):
    """乘法运算，自动处理索引对齐"""
    return _arithmetic_with_alignment(df1, df2, np.multiply)

def DIVIDE(df1, df2):
    """除法运算，自动处理索引对齐"""
    return _arithmetic_with_alignment(df1, df2, np.divide)

def _arithmetic_with_alignment(df1, df2, op_func):
    """
    算术运算，自动处理索引对齐
    
    参数:
        df1: 第一个操作数
        df2: 第二个操作数
        op_func: 算术操作函数（np.add, np.subtract 等）
    
    返回:
        运算结果的 Series/DataFrame
    """
    # 如果都是标量，直接运算
    if not isinstance(df1, (pd.DataFrame, pd.Series)) and not isinstance(df2, (pd.DataFrame, pd.Series)):
        return op_func(df1, df2)
    
    # 如果一个是标量，另一个是 DataFrame/Series，numpy 会自动广播
    if not isinstance(df1, (pd.DataFrame, pd.Series)):
        return op_func(df1, df2)
    if not isinstance(df2, (pd.DataFrame, pd.Series)):
        return op_func(df1, df2)
    
    # 两个都是 DataFrame/Series，需要处理索引对齐
    # 如果 df1 是 MultiIndex 而 df2 不是，需要将 df2 广播到与 df1 相同的结构
    if isinstance(df1.index, pd.MultiIndex) and not isinstance(df2.index, pd.MultiIndex):
        # df2 只有 datetime 索引（来自截面函数如 MEAN, MEDIAN），需要广播到 (datetime, instrument) MultiIndex
        datetime_level = df1.index.get_level_values('datetime')
        # 将 df2 的索引对齐到 df1 的 datetime 层级
        if isinstance(df2, pd.DataFrame):
            df2_aligned = df2.reindex(datetime_level, method='ffill')
        else:  # Series
            df2_aligned = df2.reindex(datetime_level, method='ffill')
        # 创建与 df1 相同的 MultiIndex
        df2_aligned.index = df1.index
        df2 = df2_aligned
    elif not isinstance(df1.index, pd.MultiIndex) and isinstance(df2.index, pd.MultiIndex):
        # df1 只有 datetime 索引，df2 是 MultiIndex，需要将 df1 广播
        datetime_level = df2.index.get_level_values('datetime')
        if isinstance(df1, pd.DataFrame):
            df1_aligned = df1.reindex(datetime_level, method='ffill')
        else:  # Series
            df1_aligned = df1.reindex(datetime_level, method='ffill')
        df1_aligned.index = df2.index
        df1 = df1_aligned
    elif not df1.index.equals(df2.index):
        # 两个索引结构不同，尝试对齐
        try:
            if isinstance(df1.index, pd.MultiIndex) and isinstance(df2.index, pd.MultiIndex):
                # 两个都是 MultiIndex，尝试对齐
                df2 = df2.reindex(df1.index)
            else:
                # 尝试直接对齐
                df2 = df2.reindex(df1.index)
        except Exception:
            # 如果对齐失败，尝试使用 pandas 的自动对齐
            pass
    
    # 执行算术运算
    try:
        result = op_func(df1, df2)
    except (ValueError, TypeError) as e:
        # 如果还是失败，强制对齐索引
        if 'identically-labeled' in str(e) or 'Can only compare' in str(e) or 'index' in str(e).lower():
            # 强制对齐索引
            if isinstance(df1.index, pd.MultiIndex) and isinstance(df2.index, pd.MultiIndex):
                df2 = df2.reindex(df1.index, fill_value=0)
            elif isinstance(df1.index, pd.MultiIndex):
                datetime_level = df1.index.get_level_values('datetime')
                df2 = df2.reindex(datetime_level, method='ffill')
                df2.index = df1.index
            result = op_func(df1, df2)
        else:
            raise
    
    return result
    
def AND(df1, df2):
    """逻辑与运算，自动处理索引对齐"""
    df1_aligned, df2_aligned = _align_for_operation(df1, df2)
    return np.bitwise_and(df1_aligned.astype(np.bool_), df2_aligned.astype(np.bool_))

def OR(df1, df2):
    """逻辑或运算，自动处理索引对齐"""
    df1_aligned, df2_aligned = _align_for_operation(df1, df2)
    return np.bitwise_or(df1_aligned.astype(np.bool_), df2_aligned.astype(np.bool_))

def WHERE(condition, true_value, false_value):
    """
    条件表达式，自动处理索引对齐
    
    参数:
        condition: 条件表达式（布尔值）
        true_value: 条件为真时的值
        false_value: 条件为假时的值
    
    返回:
        根据条件选择的值
    """
    
    # 对齐所有三个参数的索引
    # 确定目标索引（优先使用 condition 的索引）
    if isinstance(condition, (pd.DataFrame, pd.Series)):
        target_index = condition.index
    elif isinstance(true_value, (pd.DataFrame, pd.Series)):
        target_index = true_value.index
    elif isinstance(false_value, (pd.DataFrame, pd.Series)):
        target_index = false_value.index
    else:
        # 都是标量，直接使用 np.where
        return np.where(condition, true_value, false_value)
    
    # 对齐 true_value 和 false_value 到 target_index
    if isinstance(true_value, (pd.DataFrame, pd.Series)) and not true_value.index.equals(target_index):
        if isinstance(target_index, pd.MultiIndex) and not isinstance(true_value.index, pd.MultiIndex):
            datetime_level = target_index.get_level_values('datetime')
            true_value = true_value.reindex(datetime_level, method='ffill')
            true_value.index = target_index
        else:
            true_value = true_value.reindex(target_index, fill_value=0)
    
    if isinstance(false_value, (pd.DataFrame, pd.Series)) and not false_value.index.equals(target_index):
        if isinstance(target_index, pd.MultiIndex) and not isinstance(false_value.index, pd.MultiIndex):
            datetime_level = target_index.get_level_values('datetime')
            false_value = false_value.reindex(datetime_level, method='ffill')
            false_value.index = target_index
        else:
            false_value = false_value.reindex(target_index, fill_value=0)
    
    # 对齐 condition
    if isinstance(condition, (pd.DataFrame, pd.Series)) and not condition.index.equals(target_index):
        condition = condition.reindex(target_index, fill_value=False)
    
    # 执行条件选择
    result = np.where(condition, true_value, false_value)
    
    # 如果结果是数组，转换为 Series
    if isinstance(result, np.ndarray) and isinstance(target_index, pd.MultiIndex):
        result = pd.Series(result, index=target_index)
    elif isinstance(result, np.ndarray) and isinstance(target_index, pd.Index):
        result = pd.Series(result, index=target_index)
    
    return result

def _align_for_operation(df1, df2):
    """
    对齐两个 DataFrame/Series 的索引，用于二元运算
    
    参数:
        df1: 第一个操作数
        df2: 第二个操作数
    
    返回:
        (df1_aligned, df2_aligned): 对齐后的两个操作数
    """
    # 如果都是标量，直接返回
    if not isinstance(df1, (pd.DataFrame, pd.Series)) and not isinstance(df2, (pd.DataFrame, pd.Series)):
        return df1, df2
    
    # 如果一个是标量，另一个是 DataFrame/Series，直接返回（numpy 会自动广播）
    if not isinstance(df1, (pd.DataFrame, pd.Series)):
        return df1, df2
    if not isinstance(df2, (pd.DataFrame, pd.Series)):
        return df1, df2
    
    # 两个都是 DataFrame/Series，需要处理索引对齐
    # 如果 df1 是 MultiIndex 而 df2 不是，需要将 df2 广播到与 df1 相同的结构
    if isinstance(df1.index, pd.MultiIndex) and not isinstance(df2.index, pd.MultiIndex):
        # df2 只有 datetime 索引（来自截面函数如 MEAN, MEDIAN），需要广播到 (datetime, instrument) MultiIndex
        datetime_level = df1.index.get_level_values('datetime')
        # 将 df2 的索引对齐到 df1 的 datetime 层级
        if isinstance(df2, pd.DataFrame):
            df2_aligned = df2.reindex(datetime_level, method='ffill')
        else:  # Series
            df2_aligned = df2.reindex(datetime_level, method='ffill')
        # 创建与 df1 相同的 MultiIndex
        df2_aligned.index = df1.index
        return df1, df2_aligned
    elif not isinstance(df1.index, pd.MultiIndex) and isinstance(df2.index, pd.MultiIndex):
        # df1 只有 datetime 索引，df2 是 MultiIndex，需要将 df1 广播
        datetime_level = df2.index.get_level_values('datetime')
        if isinstance(df1, pd.DataFrame):
            df1_aligned = df1.reindex(datetime_level, method='ffill')
        else:  # Series
            df1_aligned = df1.reindex(datetime_level, method='ffill')
        df1_aligned.index = df2.index
        return df1_aligned, df2
    elif not df1.index.equals(df2.index):
        # 两个索引结构不同，尝试对齐
        try:
            if isinstance(df1.index, pd.MultiIndex) and isinstance(df2.index, pd.MultiIndex):
                # 两个都是 MultiIndex，尝试对齐
                df2_aligned = df2.reindex(df1.index)
                return df1, df2_aligned
            else:
                # 尝试直接对齐
                df2_aligned = df2.reindex(df1.index)
                return df1, df2_aligned
        except Exception:
            # 如果对齐失败，返回原值（让调用者处理）
            return df1, df2
    
    # 索引已经对齐
    return df1, df2

def GT(df1, df2):
    """大于比较，自动处理索引对齐"""
    return _compare_with_alignment(df1, df2, operator.gt)

def LT(df1, df2):
    """小于比较，自动处理索引对齐"""
    return _compare_with_alignment(df1, df2, operator.lt)

def GE(df1, df2):
    """大于等于比较，自动处理索引对齐"""
    return _compare_with_alignment(df1, df2, operator.ge)

def LE(df1, df2):
    """小于等于比较，自动处理索引对齐"""
    return _compare_with_alignment(df1, df2, operator.le)

def EQ(df1, df2):
    """等于比较，自动处理索引对齐"""
    return _compare_with_alignment(df1, df2, operator.eq)

def NE(df1, df2):
    """不等于比较，自动处理索引对齐"""
    return _compare_with_alignment(df1, df2, operator.ne)

def _compare_with_alignment(df1, df2, op_func):
    """
    比较两个 DataFrame/Series，自动处理索引对齐
    
    参数:
        df1: 第一个操作数
        df2: 第二个操作数
        op_func: 比较操作函数（operator.gt, operator.lt 等）
    
    返回:
        比较结果的 Series/DataFrame
    """
    
    # 如果都是标量，直接比较
    if not isinstance(df1, (pd.DataFrame, pd.Series)) and not isinstance(df2, (pd.DataFrame, pd.Series)):
        return op_func(df1, df2)
    
    # 如果一个是标量，另一个是 DataFrame/Series
    if not isinstance(df1, (pd.DataFrame, pd.Series)):
        return op_func(df2, df1) if op_func in [operator.lt, operator.le] else op_func(df1, df2)
    if not isinstance(df2, (pd.DataFrame, pd.Series)):
        return op_func(df1, df2)
    
    # 两个都是 DataFrame/Series，需要处理索引对齐
    # 如果 df1 是 MultiIndex 而 df2 不是，需要将 df2 广播到与 df1 相同的结构
    if isinstance(df1.index, pd.MultiIndex) and not isinstance(df2.index, pd.MultiIndex):
        # df2 只有 datetime 索引（来自截面函数如 MEAN, MEDIAN），需要广播到 (datetime, instrument) MultiIndex
        datetime_level = df1.index.get_level_values('datetime')
        # 将 df2 的索引对齐到 df1 的 datetime 层级
        if isinstance(df2, pd.DataFrame):
            df2_aligned = df2.reindex(datetime_level, method='ffill')
        else:  # Series
            df2_aligned = df2.reindex(datetime_level, method='ffill')
        # 创建与 df1 相同的 MultiIndex
        df2_aligned.index = df1.index
        df2 = df2_aligned
    elif not isinstance(df1.index, pd.MultiIndex) and isinstance(df2.index, pd.MultiIndex):
        # df1 只有 datetime 索引，df2 是 MultiIndex，需要将 df1 广播
        datetime_level = df2.index.get_level_values('datetime')
        if isinstance(df1, pd.DataFrame):
            df1_aligned = df1.reindex(datetime_level, method='ffill')
        else:  # Series
            df1_aligned = df1.reindex(datetime_level, method='ffill')
        df1_aligned.index = df2.index
        df1 = df1_aligned
    elif not df1.index.equals(df2.index):
        # 两个索引结构不同，尝试对齐
        try:
            if isinstance(df1.index, pd.MultiIndex) and isinstance(df2.index, pd.MultiIndex):
                # 两个都是 MultiIndex，尝试对齐
                df2 = df2.reindex(df1.index)
            else:
                # 尝试直接对齐
                df2 = df2.reindex(df1.index)
        except Exception:
            # 如果对齐失败，尝试使用 pandas 的自动对齐
            pass
    
    # 执行比较操作
    try:
        result = op_func(df1, df2)
    except (ValueError, TypeError) as e:
        # 如果还是失败，尝试使用 numpy 的比较
        if 'identically-labeled' in str(e) or 'Can only compare' in str(e):
            # 强制对齐索引
            if isinstance(df1.index, pd.MultiIndex) and isinstance(df2.index, pd.MultiIndex):
                df2 = df2.reindex(df1.index, fill_value=0)
            elif isinstance(df1.index, pd.MultiIndex):
                datetime_level = df1.index.get_level_values('datetime')
                df2 = df2.reindex(datetime_level, method='ffill')
                df2.index = df1.index
            result = op_func(df1, df2)
        else:
            raise
    
    return result



def MACD(price_df, short_window=12, long_window=26):
    """
    计算MACD指标
    
    参数:
        price_df: pd.DataFrame - 价格数据
        short_window: int - 短期EMA的窗口大小，默认为12
        long_window: int - 长期EMA的窗口大小，默认为26
        
    返回:
        pd.DataFrame: MACD结果
    """
    # 计算短期EMA
    short_ema = EMA(price_df, short_window)
    
    # 计算长期EMA
    long_ema = EMA(price_df, long_window)
    
    # 计算MACD差值
    macd = short_ema - long_ema
    return macd


def RSI(price_df, window=14):
    """
    计算相对强弱指数(RSI)
    
    参数:
        price_df: pd.DataFrame - 价格数据
        window: int - RSI的窗口大小，默认为14

    返回:
        pd.DataFrame: RSI结果
    """
    # 计算价格变化
    price_change = DELTA(price_df, 1)
    
    # 分别计算上涨和下跌（使用向量化操作）
    up = (price_change > 0) * price_change
    down = (price_change < 0) * ABS(price_change)
    
    # 计算EMA
    avg_up = EMA(up, window)
    avg_down = EMA(down, window)
    
    # 计算RSI
    rsi = 100 - (100 / (1 + (avg_up / avg_down)))
    return rsi




def _calculate_rolling_mean(group_data):
    """计算单个组的动态移动平均"""
    price_group, window_group, group_name = group_data
    result = pd.Series(index=price_group.index, dtype=float)
    
    for i in range(len(price_group)):
        curr_window = int(window_group.iloc[i].values)
        if curr_window < 1:
            curr_window = 1
        if i < curr_window:
            result.iloc[i] = price_group.iloc[:i+1].mean()
        else:
            result.iloc[i] = price_group.iloc[i-curr_window+1:i+1].mean()
    
    return group_name, result

def _calculate_rolling_std(group_data):
    """计算单个组的动态标准差"""
    price_group, window_group, group_name = group_data
    result = pd.Series(index=price_group.index, dtype=float)
    
    for i in range(len(price_group)):
        curr_window = int(window_group.iloc[i].values)
        if curr_window < 1:
            curr_window = 1
        if i < curr_window:
            result.iloc[i] = price_group.iloc[:i+1].std()
        else:
            result.iloc[i] = price_group.iloc[i-curr_window+1:i+1].std()
    
    return group_name, result



@datatype_adapter
def BB_MIDDLE(price_df, window, n_jobs=-1):
    """
    计算布林带中轨，支持动态窗口大小和并行计算
    
    参数:
        price_df: pd.DataFrame - 价格数据
        window: int 或 pd.DataFrame - 窗口大小
        n_jobs: int - 并行计算的作业数，默认为-1
    """
    if isinstance(window, (int, float)):
        # 如果window是固定值，使用原来的逻辑
        return price_df.groupby('instrument').transform(lambda x: x.rolling(int(window), min_periods=1).mean())
    else:
        window.index = price_df.index
        # 准备并行计算的数据
        groups_data = [
            (price_group, 
             window.xs(group_name, level='instrument'), 
             group_name)
            for group_name, price_group in price_df.groupby('instrument')
        ]
        
        # 并行计算
        results = Parallel(n_jobs=n_jobs)(
            delayed(_calculate_rolling_mean)(group_data)
            for group_data in groups_data
        )
        
        # 合并结果
        final_result = pd.concat([result for _, result in sorted(results, key=lambda x: x[0])])
        return final_result

@datatype_adapter
def BB_UPPER(price_df, window, n_jobs=-1):
    """
    计算布林带上轨，支持动态窗口大小和并行计算
    
    参数:
        price_df: pd.DataFrame - 价格数据
        window: int 或 pd.DataFrame - 窗口大小
        n_jobs: int - 并行计算的作业数，默认为-1
    """
    
    if isinstance(window, (int, float)):
        # 固定窗口大小的标准差计算
        middle_band = BB_MIDDLE(price_df, window, n_jobs)
        std = price_df.groupby('instrument').transform(lambda x: x.rolling(int(window), min_periods=1).std())
    else:
        window.index = price_df.index
        middle_band = BB_MIDDLE(price_df, window, n_jobs)
        # 准备并行计算的数据
        groups_data = [
            (price_group, 
             window.xs(group_name, level='instrument'), 
             group_name)
            for group_name, price_group in price_df.groupby('instrument')
        ]
        
        # 并行计算标准差
        results = Parallel(n_jobs=n_jobs)(
            delayed(_calculate_rolling_std)(group_data)
            for group_data in groups_data
        )
        
        # 合并结果
        std = pd.concat([result for _, result in sorted(results, key=lambda x: x[0])])
    
    return middle_band + std

@datatype_adapter
def BB_LOWER(price_df, window, n_jobs=-1):
    """
    计算布林带下轨，支持动态窗口大小和并行计算
    
    参数:
        price_df: pd.DataFrame - 价格数据
        window: int 或 pd.DataFrame - 窗口大小
        n_jobs: int - 并行计算的作业数，默认为-1
    """
    
    if isinstance(window, (int, float)):
        # 固定窗口大小的标准差计算
        middle_band = BB_MIDDLE(price_df, window, n_jobs)
        std = price_df.groupby('instrument').transform(lambda x: x.rolling(int(window), min_periods=1).std())
    else:
        window.index = price_df.index
        middle_band = BB_MIDDLE(price_df, window, n_jobs)
        # 准备并行计算的数据
        groups_data = [
            (price_group, 
             window.xs(group_name, level='instrument'), 
             group_name)
            for group_name, price_group in price_df.groupby('instrument')
        ]
        
        # 并行计算标准差
        results = Parallel(n_jobs=n_jobs)(
            delayed(_calculate_rolling_std)(group_data)
            for group_data in groups_data
        )
        
        # 合并结果
        std = pd.concat([result for _, result in sorted(results, key=lambda x: x[0])])
    
    return middle_band - std

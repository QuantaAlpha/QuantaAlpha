# 数据质量检查报告

## 发现的问题

### 1. ⚠️ 严重问题：股票池异常

**问题描述**：
- 使用 `D.instruments('csi300')` 返回的结果异常
- 返回的股票列表是 `['market', 'filter_pipe']`，只有2个元素
- 这导致回测时股票池过小，结果不可信

**正确方法**：
应该使用 `D.list_instruments()` 来获取股票列表：
```python
stock_list = D.list_instruments(
    'csi300',
    start_time=backtest_config['start_time'],
    end_time=backtest_config['end_time'],
    as_list=True
)
```

### 2. ⚠️ 数据质量问题：开盘价为0

**问题描述**：
- 发现1400条开盘价为0的记录
- 这些记录通常对应停牌、退市或数据缺失的情况
- 配置中使用 `deal_price: "open"`，但开盘价为0时qlib会自动使用收盘价

**影响**：
- 可能导致回测结果不准确
- 年化收益42.25%可能因为数据异常而偏高

**建议**：
1. 过滤掉开盘价为0的交易日
2. 或改用 `deal_price: "close"` 使用收盘价成交

### 3. ⚠️ 年化收益异常高

**当前结果**：
- 年化收益: 42.25%
- 信息比率: 0.66
- 最大回撤: -50.35%

**可能原因**：
1. **股票池过小**：只有2只股票，样本不足，结果不可信
2. **数据异常**：开盘价为0导致交易价格异常
3. **数据泄露**：可能存在未来数据泄露问题
4. **停牌股票**：包含停牌股票导致数据异常

### 4. ✓ 数据日期范围正常

**检查结果**：
- 数据日期范围: 2022-01-04 到 2025-12-31
- 总交易日数: 969天
- 各年交易日数正常：
  - 2022年: 242天
  - 2023年: 242天
  - 2024年: 242天
  - 2025年: 243天

### 5. ✓ 使用Qlib框架回测

**确认**：
- 使用了 `qlib.backtest.backtest` 进行回测
- 使用了 `SimulatorExecutor` 作为执行器
- 使用了 `TopkDropoutStrategy` 作为策略
- **没有使用h5文件**，qlib使用自己的数据格式（存储在 `/home/tjxy/.qlib/qlib_data/cn_data`）

## 修复建议

### 1. 修复股票池获取方式

在 `backtest_runner.py` 中，修改股票列表获取方式：

```python
# 错误的写法
instruments = D.instruments(market)
stock_list = D.list_instruments(
    instruments,
    start_time=backtest_config['start_time'],
    end_time=backtest_config['end_time'],
    as_list=True
)

# 正确的写法
stock_list = D.list_instruments(
    market,  # 直接使用市场名称
    start_time=backtest_config['start_time'],
    end_time=backtest_config['end_time'],
    as_list=True
)
```

### 2. 处理开盘价为0的情况

**方案1**：改用收盘价成交
```yaml
exchange_kwargs:
  deal_price: "close"  # 改为收盘价
```

**方案2**：在回测前过滤异常数据
```python
# 在创建数据集时过滤掉开盘价为0的交易日
```

### 3. 验证回测结果

修复后，重新运行回测，预期：
- 股票池应该包含约300只股票（csi300）
- 年化收益应该在合理范围内（通常5-15%）
- 信息比率应该更稳定

## 总结

**主要问题**：
1. ⚠️ 开盘价为0的记录影响回测准确性（1400条记录）
2. ⚠️ 年化收益42.25%异常高，不可信
3. ⚠️ 配置使用开盘价成交，但存在开盘价为0的情况

**数据情况**：
- ✓ 股票池正常（292只股票）
- ✓ 日期范围完整（2022-2025年，969个交易日）
- ✓ 使用Qlib框架回测（无h5文件，使用Qlib内部数据格式）
- ⚠️ 存在数据质量问题（开盘价为0，可能是停牌、退市等）

**已修复**：
1. ✓ 股票池获取方式已确认正确（使用 D.instruments() 返回的字典）
2. ✓ 配置文件已修改为使用收盘价成交（deal_price: close）

**下一步**：
1. 重新运行回测验证结果
2. 如果年化收益仍然异常，检查是否有数据泄露问题
3. 考虑过滤掉开盘价为0的交易日


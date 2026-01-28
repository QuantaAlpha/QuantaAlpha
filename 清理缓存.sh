#!/bin/bash
# 清理所有 Python 缓存文件

echo "🧹 清理 Python 缓存..."

# 清理 __pycache__ 目录
find /home/tjxy/quantagent/QuantaAlpha -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find /home/tjxy/quantagent/wuyinze/RD-Agent -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# 清理 .pyc 文件
find /home/tjxy/quantagent/QuantaAlpha -name "*.pyc" -delete 2>/dev/null
find /home/tjxy/quantagent/wuyinze/RD-Agent -name "*.pyc" -delete 2>/dev/null

# 清理 .pyo 文件
find /home/tjxy/quantagent/QuantaAlpha -name "*.pyo" -delete 2>/dev/null
find /home/tjxy/quantagent/wuyinze/RD-Agent -name "*.pyo" -delete 2>/dev/null

echo "✅ 缓存清理完成"

# 验证 function_lib.py 可以正常导入
echo ""
echo "🔍 验证 function_lib.py..."
cd /home/tjxy/quantagent
source venv/bin/activate 2>/dev/null
python3 -c "
import sys
sys.path.insert(0, 'QuantaAlpha')
try:
    from quantaalpha.components.coder.factor_coder.function_lib import TS_CORR, TS_COVARIANCE
    print('✅ function_lib.py 可以正常导入')
    print('✅ TS_CORR 函数存在')
    print('✅ TS_COVARIANCE 函数存在')
except Exception as e:
    print(f'❌ 导入失败: {e}')
    import traceback
    traceback.print_exc()
    exit(1)
"


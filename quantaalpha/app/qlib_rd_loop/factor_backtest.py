"""
Factor workflow with session control
"""

from typing import Any

import fire

from quantaalpha.app.qlib_rd_loop.conf import FACTOR_BACK_TEST_PROP_SETTING
from quantaalpha.components.workflow.quantaalpha_loop import BacktestLoop

def main(path=None, step_n=None, factor_path=None):
    """
    Auto R&D Evolving loop for fintech factors.

    You can continue running session by

    .. code-block:: python

        dotenv run -- python quantaalpha/app/qlib_rd_loop/factor_backtest.py --factor_path "/path/to/factor_file.csv" $LOG_PATH/__session__/1/0_propose  --step_n 1 # `step_n` is a optional paramter

    """
    if path is None:
        model_loop = BacktestLoop(FACTOR_BACK_TEST_PROP_SETTING, factor_path=factor_path)
    else:
        model_loop = BacktestLoop.load(path)
    model_loop.run(step_n=step_n)

if __name__ == "__main__":
    fire.Fire(main)
"""
Factor workflow with session control
"""

from typing import Any

import fire

from quantaalpha.pipeline.settings import FACTOR_BACK_TEST_PROP_SETTING
from quantaalpha.pipeline.loop import BacktestLoop

def main(path=None, step_n=None, factor_path=None):
    """
    Auto R&D Evolving loop for fintech factors.

    You can continue running session by

    .. code-block:: python

        quantaalpha backtest --factor_path "/path/to/factor_file.csv"

    """
    if path is None:
        model_loop = BacktestLoop(FACTOR_BACK_TEST_PROP_SETTING, factor_path=factor_path)
    else:
        model_loop = BacktestLoop.load(path)
    model_loop.run(step_n=step_n)

if __name__ == "__main__":
    fire.Fire(main)
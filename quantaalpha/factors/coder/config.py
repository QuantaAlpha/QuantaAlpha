from typing import Optional

from quantaalpha.coder.costeer.config import CoSTEERSettings
from quantaalpha.core.conf import ExtendedSettingsConfigDict


class FactorCoSTEERSettings(CoSTEERSettings):
    model_config = ExtendedSettingsConfigDict(env_prefix="FACTOR_CoSTEER_")

    data_folder: str = "git_ignore_folder/factor_implementation_source_data"
    """Path to the folder containing financial data (default is fundamental data in Qlib)"""

    data_folder_debug: str = "git_ignore_folder/factor_implementation_source_data_debug"
    """Path to the folder containing partial financial data (for debugging)"""

    simple_background: bool = True
    """Whether to use simple background information for code feedback"""

    file_based_execution_timeout: int = 1200
    """Timeout in seconds for each factor implementation execution"""

    select_method: str = "random"
    """Method for the selection of factors implementation"""

    python_bin: str = "python"
    """Path to the Python binary"""
    
    factor_zoo_path: Optional[str] = None
    """Path to the CSV file containing the factor zoo database (e.g., Alpha101 factors).
    If None, only free arguments ratio and unique variables ratio checks will be performed.
    Novelty check (duplication detection) requires a factor zoo file."""
    
    duplication_threshold: int = 8
    """Threshold for duplication detection. If duplicated subtree size exceeds this value, 
    the factor will be rejected."""

    symbol_length_threshold: int = 300
    """Maximum allowed symbol length (SL) for factor expressions. 
    Expressions longer than this threshold will be rejected to prevent overfitting."""
    
    base_features_threshold: int = 6
    """Maximum allowed number of unique base features (ER) in factor expressions.
    Base features are raw variables like $close, $open, $high, $low, $volume.
    Expressions using more than this number of distinct base features will be rejected."""


FACTOR_COSTEER_SETTINGS = FactorCoSTEERSettings()

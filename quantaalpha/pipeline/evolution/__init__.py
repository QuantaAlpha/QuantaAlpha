"""
Evolution module for AlphaAgent.

This module provides evolutionary operators (mutation, crossover) and trajectory
management for multi-round factor discovery experiments.

Key components:
- StrategyTrajectory: Represents a complete trajectory from hypothesis to backtest results
- TrajectoryPool: Manages and stores all trajectories across rounds
- MutationOperator: Generates orthogonal strategies from parent trajectories
- CrossoverOperator: Combines multiple parent trajectories into hybrid strategies
- EvolutionController: Orchestrates the original→mutation→crossover cycle
"""

from .trajectory import StrategyTrajectory, TrajectoryPool, RoundPhase
from .mutation import MutationOperator
from .crossover import CrossoverOperator
from .controller import EvolutionController, EvolutionConfig

__all__ = [
    "StrategyTrajectory",
    "TrajectoryPool",
    "RoundPhase",
    "MutationOperator",
    "CrossoverOperator",
    "EvolutionController",
    "EvolutionConfig",
]


"""
Strategy trajectory and trajectory pool for evolution tracking.

A strategy trajectory captures the complete lifecycle of a factor discovery attempt:
hypothesis → factor expressions → code → backtest results → feedback.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional
import hashlib

from quantaalpha.log import logger


class RoundPhase(str, Enum):
    """Phase/type of a round in the evolutionary process."""
    ORIGINAL = "original"      # Initial exploration round
    MUTATION = "mutation"      # Orthogonal/mutated strategy round
    CROSSOVER = "crossover"    # Crossed/hybrid strategy round


@dataclass
class StrategyTrajectory:
    """
    Represents a complete strategy trajectory from a single loop iteration.
    
    A trajectory contains all information needed to evaluate and evolve strategies:
    - The hypothesis that guided factor design
    - The factor expressions and descriptions
    - The implementation code
    - The backtest results and metrics
    - The feedback from evaluation
    
    Attributes:
        trajectory_id: Unique identifier for this trajectory
        direction_id: Which planning direction this belongs to
        round_idx: Round index (0=original, 1=mutation, 2=crossover, ...)
        phase: Type of round (original/mutation/crossover)
        hypothesis: The hypothesis text
        hypothesis_details: Detailed hypothesis information (reason, observations, etc.)
        factors: List of factor info dicts (name, expression, description, code)
        backtest_result: Raw backtest result (DataFrame or dict)
        backtest_metrics: Extracted metrics (IC, ICIR, RankIC, etc.)
        feedback: Feedback text from evaluator
        feedback_details: Detailed feedback (observations, evaluation, new_hypothesis)
        parent_ids: Parent trajectory IDs for mutation/crossover
        created_at: Timestamp when trajectory was created
        extra_info: Additional metadata
    """
    trajectory_id: str
    direction_id: int
    round_idx: int
    phase: RoundPhase
    
    # Hypothesis information
    hypothesis: str = ""
    hypothesis_details: dict[str, Any] = field(default_factory=dict)
    
    # Factor information
    factors: list[dict[str, Any]] = field(default_factory=list)
    
    # Backtest results
    backtest_result: Any = None
    backtest_metrics: dict[str, Optional[float]] = field(default_factory=dict)
    
    # Feedback
    feedback: str = ""
    feedback_details: dict[str, Any] = field(default_factory=dict)
    
    # Evolution lineage
    parent_ids: list[str] = field(default_factory=list)
    
    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    extra_info: dict[str, Any] = field(default_factory=dict)
    
    @staticmethod
    def generate_id(direction_id: int, round_idx: int, phase: RoundPhase, timestamp: str = None) -> str:
        """Generate a unique trajectory ID."""
        ts = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        content = f"{direction_id}_{round_idx}_{phase.value}_{ts}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def get_primary_metric(self) -> Optional[float]:
        """Get the primary metric (RankIC) for comparison."""
        return self.backtest_metrics.get("RankIC")
    
    def is_successful(self) -> bool:
        """Check if this trajectory produced valid results."""
        rank_ic = self.get_primary_metric()
        return rank_ic is not None and rank_ic > 0
    
    def to_summary_text(self) -> str:
        """Generate a concise summary for use in prompts."""
        parts = []
        
        # Hypothesis
        if self.hypothesis:
            parts.append(f"假设: {self.hypothesis[:500]}...")
        
        # Factors
        if self.factors:
            factor_strs = []
            for f in self.factors[:5]:  # Limit to 5 factors
                name = f.get("name", "unknown")
                expr = f.get("expression", "")[:100]
                factor_strs.append(f"  - {name}: {expr}")
            parts.append("因子:\n" + "\n".join(factor_strs))
        
        # Metrics
        if self.backtest_metrics:
            metrics_str = ", ".join(
                f"{k}={v:.4f}" for k, v in self.backtest_metrics.items() 
                if v is not None
            )
            if metrics_str:
                parts.append(f"指标: {metrics_str}")
        
        # Feedback
        if self.feedback:
            parts.append(f"反馈: {self.feedback[:300]}...")
        
        return "\n\n".join(parts)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        d = asdict(self)
        d["phase"] = self.phase.value
        # Don't serialize raw backtest_result (may not be JSON-serializable)
        d["backtest_result"] = None
        return d
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StrategyTrajectory:
        """Create from dictionary."""
        data = data.copy()
        data["phase"] = RoundPhase(data.get("phase", "original"))
        data["backtest_result"] = None
        return cls(**data)


class TrajectoryPool:
    """
    Manages all strategy trajectories across directions and rounds.
    
    Provides methods to:
    - Add and retrieve trajectories
    - Select parent trajectories for evolution
    - Persist trajectories to disk
    """
    
    def __init__(self, save_path: Optional[Path] = None, fresh_start: bool = True):
        """
        Initialize trajectory pool.
        
        Args:
            save_path: Path to save/load pool state. If None, pool is memory-only.
            fresh_start: If True, start with empty pool even if save_path exists.
                        If False, load existing data from save_path.
        """
        self.save_path = Path(save_path) if save_path else None
        self._trajectories: dict[str, StrategyTrajectory] = {}
        self._by_direction: dict[int, list[str]] = {}  # direction_id -> [traj_ids]
        self._by_phase: dict[RoundPhase, list[str]] = {p: [] for p in RoundPhase}
        
        # Only load existing data if fresh_start is False
        if not fresh_start and self.save_path and self.save_path.exists():
            self._load()
        elif fresh_start and self.save_path and self.save_path.exists():
            logger.info(f"Fresh start: ignoring existing trajectory pool at {self.save_path}")
    
    def add(self, trajectory: StrategyTrajectory) -> str:
        """
        Add a trajectory to the pool.
        
        Args:
            trajectory: The trajectory to add
            
        Returns:
            The trajectory ID
        """
        tid = trajectory.trajectory_id
        self._trajectories[tid] = trajectory
        
        # Index by direction
        if trajectory.direction_id not in self._by_direction:
            self._by_direction[trajectory.direction_id] = []
        self._by_direction[trajectory.direction_id].append(tid)
        
        # Index by phase
        self._by_phase[trajectory.phase].append(tid)
        
        logger.info(f"Added trajectory {tid} (direction={trajectory.direction_id}, "
                   f"phase={trajectory.phase.value}, round={trajectory.round_idx})")
        
        if self.save_path:
            self._save()
        
        return tid
    
    def get(self, trajectory_id: str) -> Optional[StrategyTrajectory]:
        """Get a trajectory by ID."""
        return self._trajectories.get(trajectory_id)
    
    def get_by_direction(self, direction_id: int) -> list[StrategyTrajectory]:
        """Get all trajectories for a direction."""
        tids = self._by_direction.get(direction_id, [])
        return [self._trajectories[tid] for tid in tids]
    
    def get_by_phase(self, phase: RoundPhase) -> list[StrategyTrajectory]:
        """Get all trajectories of a specific phase."""
        tids = self._by_phase.get(phase, [])
        return [self._trajectories[tid] for tid in tids]
    
    def get_all(self) -> list[StrategyTrajectory]:
        """Get all trajectories."""
        return list(self._trajectories.values())
    
    def get_latest_round_idx(self) -> int:
        """Get the highest round index across all trajectories."""
        if not self._trajectories:
            return -1
        return max(t.round_idx for t in self._trajectories.values())
    
    def select_parents_for_mutation(self, direction_id: int) -> Optional[StrategyTrajectory]:
        """
        Select a parent trajectory for mutation.
        
        For mutation, we select the most recent trajectory from the same direction.
        
        Args:
            direction_id: The direction to select from
            
        Returns:
            The selected parent trajectory, or None if none available
        """
        candidates = self.get_by_direction(direction_id)
        if not candidates:
            return None
        
        # Sort by round_idx descending, take the latest
        candidates.sort(key=lambda t: t.round_idx, reverse=True)
        return candidates[0]
    
    def select_parents_for_crossover(
        self, 
        crossover_size: int = 2, 
        crossover_n: int = 3,
        strategy: str = "weighted"
    ) -> list[list[StrategyTrajectory]]:
        """
        Select parent pairs/groups for crossover.
        
        Args:
            crossover_size: Number of parents per crossover group (default 2)
            crossover_n: Number of crossover groups to create (default 3)
            strategy: Selection strategy ('weighted', 'random', 'best')
            
        Returns:
            List of parent groups, each group is a list of trajectories
        """
        all_trajs = self.get_all()
        if len(all_trajs) < crossover_size:
            logger.warning(f"Not enough trajectories for crossover: "
                          f"have {len(all_trajs)}, need {crossover_size}")
            return []
        
        # Sort by performance (RankIC)
        scored_trajs = []
        for t in all_trajs:
            metric = t.get_primary_metric()
            if metric is not None:
                scored_trajs.append((t, metric))
        
        if len(scored_trajs) < crossover_size:
            # Fall back to all trajectories without filtering
            scored_trajs = [(t, 0.0) for t in all_trajs]
        
        # Sort by metric descending
        scored_trajs.sort(key=lambda x: x[1], reverse=True)
        
        # Generate combinations
        import itertools
        candidates = [t for t, _ in scored_trajs]
        all_combinations = list(itertools.combinations(candidates, crossover_size))
        
        if len(all_combinations) <= crossover_n:
            # Return all combinations if we don't have enough
            return [list(combo) for combo in all_combinations]
        
        # Select combinations based on strategy
        if strategy == "best":
            # Prioritize combinations with high-performing trajectories
            # Score each combination by sum of metrics
            combo_scores = []
            for combo in all_combinations:
                score = sum(t.get_primary_metric() or 0 for t in combo)
                combo_scores.append((combo, score))
            combo_scores.sort(key=lambda x: x[1], reverse=True)
            return [list(combo) for combo, _ in combo_scores[:crossover_n]]
        
        elif strategy == "weighted":
            # Weighted random selection favoring diverse combinations
            import random
            # Try to pick combinations from different directions
            selected = []
            used_combos = set()
            
            # First, try to get combinations spanning different directions
            for combo in all_combinations:
                dirs = set(t.direction_id for t in combo)
                if len(dirs) > 1:  # Cross-direction combo
                    key = tuple(sorted(t.trajectory_id for t in combo))
                    if key not in used_combos:
                        selected.append(list(combo))
                        used_combos.add(key)
                        if len(selected) >= crossover_n:
                            break
            
            # Fill remaining with random selection
            remaining = [c for c in all_combinations 
                        if tuple(sorted(t.trajectory_id for t in c)) not in used_combos]
            if remaining and len(selected) < crossover_n:
                random.shuffle(remaining)
                for combo in remaining[:crossover_n - len(selected)]:
                    selected.append(list(combo))
            
            return selected
        
        else:  # random
            import random
            random.shuffle(all_combinations)
            return [list(combo) for combo in all_combinations[:crossover_n]]
    
    def _save(self):
        """Save pool state to disk."""
        if not self.save_path:
            return
        
        self.save_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "trajectories": {tid: t.to_dict() for tid, t in self._trajectories.items()},
            "by_direction": self._by_direction,
            "by_phase": {p.value: ids for p, ids in self._by_phase.items()},
            "saved_at": datetime.now().isoformat(),
        }
        
        with open(self.save_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # Note: AgentLog doesn't have debug() method, using info() instead
        logger.info(f"Saved trajectory pool to {self.save_path}")
    
    def _load(self):
        """Load pool state from disk."""
        if not self.save_path or not self.save_path.exists():
            return
        
        try:
            with open(self.save_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            self._trajectories = {
                tid: StrategyTrajectory.from_dict(tdata)
                for tid, tdata in data.get("trajectories", {}).items()
            }
            self._by_direction = {
                int(k): v for k, v in data.get("by_direction", {}).items()
            }
            self._by_phase = {
                RoundPhase(k): v for k, v in data.get("by_phase", {}).items()
            }
            
            logger.info(f"Loaded {len(self._trajectories)} trajectories from {self.save_path}")
        except Exception as e:
            logger.warning(f"Failed to load trajectory pool: {e}")
    
    def get_statistics(self) -> dict[str, Any]:
        """Get pool statistics."""
        return {
            "total_trajectories": len(self._trajectories),
            "by_phase": {p.value: len(ids) for p, ids in self._by_phase.items()},
            "by_direction": {d: len(ids) for d, ids in self._by_direction.items()},
            "successful_trajectories": sum(1 for t in self._trajectories.values() if t.is_successful()),
            "latest_round": self.get_latest_round_idx(),
        }
    
    def clear(self):
        """Clear all trajectories from the pool."""
        self._trajectories.clear()
        self._by_direction.clear()
        self._by_phase = {p: [] for p in RoundPhase}
        logger.info("Trajectory pool cleared")
    
    def cleanup_file(self):
        """Delete the trajectory pool file from disk."""
        if self.save_path and self.save_path.exists():
            try:
                self.save_path.unlink()
                logger.info(f"Deleted trajectory pool file: {self.save_path}")
            except Exception as e:
                logger.warning(f"Failed to delete trajectory pool file: {e}")


"""
Evolution controller for managing the original→mutation→crossover cycle.

The controller orchestrates the evolutionary process:
1. Original round: Initial exploration in each direction
2. Mutation round: Orthogonal exploration from each original trajectory
3. Crossover round: Combine trajectories across directions
4. Repeat mutation→crossover cycle
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional
import threading

from quantaalpha.log import logger
from .trajectory import StrategyTrajectory, TrajectoryPool, RoundPhase
from .mutation import MutationOperator
from .crossover import CrossoverOperator


@dataclass
class EvolutionConfig:
    """Configuration for evolution process."""
    # Number of planning directions (parallel original rounds)
    num_directions: int = 2
    
    # Steps per loop (5 for: propose/construct/calculate/backtest/feedback)
    steps_per_loop: int = 5
    
    # Maximum total rounds (original + mutation + crossover rounds)
    max_rounds: int = 10
    
    # Enable/disable mutation phase
    # 启用/禁用变异阶段
    # When false, evolution will skip mutation rounds entirely
    mutation_enabled: bool = True
    
    # Enable/disable crossover phase
    # 启用/禁用交叉阶段
    # When false, evolution will skip crossover rounds entirely
    crossover_enabled: bool = True
    
    # Crossover parameters
    crossover_size: int = 2  # Number of parents per crossover
    crossover_n: int = 3     # Number of crossover combinations per round
    
    # Whether to prefer diverse crossover combinations
    prefer_diverse_crossover: bool = True
    
    # Parent selection strategy for crossover
    # 父代选择策略：
    # - "best": 优先选择表现最好的轨迹
    # - "random": 随机选择
    # - "weighted": 性能加权采样（性能越高权重越高）
    # - "weighted_inverse": 逆性能加权采样（性能越低权重越高，鼓励探索）
    # - "top_percent_plus_random": 评价前 N% 一定被选中，剩余随机填充
    parent_selection_strategy: str = "best"
    
    # Top percent threshold (used when parent_selection_strategy = "top_percent_plus_random")
    # 前百分比阈值
    top_percent_threshold: float = 0.3
    
    # Whether to enable parallel execution within each round
    # 是否启用轮次内并行执行
    parallel_enabled: bool = False
    
    # Path to save trajectory pool
    pool_save_path: Optional[str] = None
    
    # Path to evolution prompts
    mutation_prompt_path: Optional[str] = None
    crossover_prompt_path: Optional[str] = None
    
    # Whether to start with an empty trajectory pool
    # 是否从空轨迹池开始（忽略已有数据）
    fresh_start: bool = True


class EvolutionController:
    """
    Controls the evolutionary exploration process.
    
    The evolution cycle:
    1. Original rounds: Run initial exploration for each planning direction
    2. Mutation rounds: Generate orthogonal strategies from each original
    3. Crossover rounds: Combine top trajectories across all directions
    4. Repeat: mutation → crossover → mutation → crossover → ...
    
    The controller:
    - Tracks all trajectories in a pool
    - Determines which phase/round to run next
    - Generates strategy guidance for each round
    - Manages parent selection for mutation/crossover
    
    After crossover, the number of parallel branches changes:
    - Initial: num_directions branches
    - After first crossover: crossover_n branches (and so on)
    """
    
    def __init__(self, config: EvolutionConfig):
        """
        Initialize evolution controller.
        
        Args:
            config: Evolution configuration
        """
        self.config = config
        
        # Initialize trajectory pool with fresh_start option
        pool_path = Path(config.pool_save_path) if config.pool_save_path else None
        self.pool = TrajectoryPool(save_path=pool_path, fresh_start=config.fresh_start)
        
        # Initialize operators
        mutation_path = Path(config.mutation_prompt_path) if config.mutation_prompt_path else None
        crossover_path = Path(config.crossover_prompt_path) if config.crossover_prompt_path else None
        self.mutation_op = MutationOperator(prompt_path=mutation_path)
        self.crossover_op = CrossoverOperator(prompt_path=crossover_path)
        
        # State tracking
        self._current_round = 0
        self._current_phase = RoundPhase.ORIGINAL
        self._directions_completed = set()  # Track which directions completed original
        self._crossover_groups: list[list[StrategyTrajectory]] = []  # Current crossover groups
        self._crossover_idx = 0  # Which crossover group is next
        
        # Track active branch count (changes after crossover)
        self._active_branch_count = config.num_directions
        # Track trajectories to mutate in current mutation round
        self._mutation_targets: list[StrategyTrajectory] = []
        self._mutation_idx = 0  # Current index in mutation targets
    
    def get_current_state(self) -> dict[str, Any]:
        """Get current evolution state."""
        return {
            "round": self._current_round,
            "phase": self._current_phase.value,
            "directions_completed": list(self._directions_completed),
            "active_branch_count": self._active_branch_count,
            "mutation_targets_remaining": len(self._mutation_targets) - self._mutation_idx if self._mutation_targets else 0,
            "crossover_groups_remaining": len(self._crossover_groups) - self._crossover_idx,
            "pool_stats": self.pool.get_statistics(),
        }
    
    def get_next_task(self) -> Optional[dict[str, Any]]:
        """
        Determine the next task to run.
        
        Returns:
            Dictionary describing the next task:
            - "phase": RoundPhase (original/mutation/crossover)
            - "direction_id": Which direction (for original/mutation)
            - "parent_trajectories": Parent trajectories (for mutation/crossover)
            - "strategy_suffix": Prompt suffix for hypothesis generator
            - "round_idx": Current round index
            
            Returns None if evolution is complete.
        """
        # Check if we've reached max rounds
        if self._current_round >= self.config.max_rounds:
            logger.info(f"Evolution complete: reached max rounds ({self.config.max_rounds})")
            return None
        
        # Phase: ORIGINAL
        if self._current_phase == RoundPhase.ORIGINAL:
            return self._get_original_task()
        
        # Phase: MUTATION
        elif self._current_phase == RoundPhase.MUTATION:
            return self._get_mutation_task()
        
        # Phase: CROSSOVER
        elif self._current_phase == RoundPhase.CROSSOVER:
            return self._get_crossover_task()
        
        return None
    
    def get_all_tasks_for_current_phase(self) -> list[dict[str, Any]]:
        """
        Get all remaining tasks for the current phase.
        
        This is used for parallel execution - returns all tasks that can
        be executed in parallel within the current round/phase.
        
        Returns:
            List of task dictionaries, or empty list if phase is complete
        """
        # Check if we've reached max rounds
        if self._current_round >= self.config.max_rounds:
            return []
        
        tasks = []
        
        # Phase: ORIGINAL - collect all remaining original tasks
        if self._current_phase == RoundPhase.ORIGINAL:
            for d in range(self.config.num_directions):
                if d not in self._directions_completed:
                    tasks.append({
                        "phase": RoundPhase.ORIGINAL,
                        "direction_id": d,
                        "parent_trajectories": [],
                        "strategy_suffix": "",
                        "round_idx": self._current_round,
                    })
            
            # If no tasks, transition phase for next call
            if not tasks:
                self._current_round += 1
                # Transition based on enabled phases
                if self.config.mutation_enabled:
                    self._current_phase = RoundPhase.MUTATION
                elif self.config.crossover_enabled:
                    self._prepare_crossover_groups()
                    self._current_phase = RoundPhase.CROSSOVER
                else:
                    return []  # No evolution, just original
                return self.get_all_tasks_for_current_phase()
        
        # Phase: MUTATION - collect all remaining mutation tasks
        elif self._current_phase == RoundPhase.MUTATION:
            # Skip if mutation is disabled
            if not self.config.mutation_enabled:
                if self.config.crossover_enabled:
                    self._prepare_crossover_groups()
                    self._current_phase = RoundPhase.CROSSOVER
                    self._current_round += 1
                    return self.get_all_tasks_for_current_phase()
                return []
            
            # Prepare mutation targets if needed
            if not self._mutation_targets:
                self._prepare_mutation_targets()
            
            for idx, parent in enumerate(self._mutation_targets):
                if idx < self._mutation_idx:
                    continue  # Skip already processed
                
                # Check if this mutation already exists
                existing = [t for t in self.pool.get_all()
                           if t.round_idx == self._current_round 
                           and t.phase == RoundPhase.MUTATION
                           and parent.trajectory_id in t.parent_ids]
                if existing:
                    continue
                
                suffix = self.mutation_op.generate_mutation_prompt_suffix(parent)
                tasks.append({
                    "phase": RoundPhase.MUTATION,
                    "direction_id": idx,
                    "parent_trajectories": [parent],
                    "strategy_suffix": suffix,
                    "round_idx": self._current_round,
                })
            
            # If no tasks, transition phase for next call
            if not tasks:
                self._mutation_targets = []
                self._mutation_idx = 0
                self._current_round += 1
                
                if self.config.crossover_enabled:
                    self._prepare_crossover_groups()
                    self._current_phase = RoundPhase.CROSSOVER
                else:
                    # Stay in mutation mode
                    self._current_phase = RoundPhase.MUTATION
                return self.get_all_tasks_for_current_phase()
        
        # Phase: CROSSOVER - collect all remaining crossover tasks
        elif self._current_phase == RoundPhase.CROSSOVER:
            # Skip if crossover is disabled
            if not self.config.crossover_enabled:
                if self.config.mutation_enabled:
                    self._current_phase = RoundPhase.MUTATION
                    self._current_round += 1
                    return self.get_all_tasks_for_current_phase()
                return []
            
            for idx in range(self._crossover_idx, len(self._crossover_groups)):
                parents = self._crossover_groups[idx]
                suffix = self.crossover_op.generate_crossover_prompt_suffix(parents)
                tasks.append({
                    "phase": RoundPhase.CROSSOVER,
                    "direction_id": idx,
                    "parent_trajectories": parents,
                    "strategy_suffix": suffix,
                    "round_idx": self._current_round,
                })
            
            # If no tasks, transition phase for next call
            if not tasks:
                self._current_round += 1
                
                if self.config.mutation_enabled:
                    self._current_phase = RoundPhase.MUTATION
                else:
                    # Stay in crossover mode, prepare new groups
                    self._prepare_crossover_groups()
                    self._current_phase = RoundPhase.CROSSOVER
                return self.get_all_tasks_for_current_phase()
        
        return tasks
    
    def advance_phase_after_parallel_completion(self, completed_tasks: list[dict[str, Any]]):
        """
        Update controller state after parallel tasks complete.
        
        Called after all parallel tasks in a phase complete to 
        advance the controller to the next phase.
        
        Args:
            completed_tasks: List of completed task dictionaries
        """
        if not completed_tasks:
            return
        
        phase = completed_tasks[0]["phase"]
        
        if phase == RoundPhase.ORIGINAL:
            # Mark all directions as completed
            for task in completed_tasks:
                self._directions_completed.add(task["direction_id"])
            
            # Transition based on enabled phases
            if len(self._directions_completed) >= self.config.num_directions:
                self._current_round += 1
                if self.config.mutation_enabled:
                    self._current_phase = RoundPhase.MUTATION
                    logger.info(f"All original rounds complete, transitioning to mutation (round {self._current_round})")
                elif self.config.crossover_enabled:
                    self._prepare_crossover_groups()
                    self._current_phase = RoundPhase.CROSSOVER
                    logger.info(f"All original rounds complete, transitioning to crossover (round {self._current_round})")
                else:
                    logger.info("Neither mutation nor crossover enabled, evolution complete")
        
        elif phase == RoundPhase.MUTATION:
            # Update mutation index to skip completed
            self._mutation_idx = len(self._mutation_targets)
            self._mutation_targets = []
            self._mutation_idx = 0
            self._current_round += 1
            
            # Transition based on enabled phases
            if self.config.crossover_enabled:
                self._prepare_crossover_groups()
                self._current_phase = RoundPhase.CROSSOVER
                logger.info(f"All mutation rounds complete, transitioning to crossover (round {self._current_round})")
            else:
                # Stay in mutation mode
                self._current_phase = RoundPhase.MUTATION
                logger.info(f"All mutation rounds complete, continuing with mutation (round {self._current_round})")
        
        elif phase == RoundPhase.CROSSOVER:
            # Update crossover index
            self._crossover_idx = len(self._crossover_groups)
            self._current_round += 1
            
            # Transition based on enabled phases
            if self.config.mutation_enabled:
                self._current_phase = RoundPhase.MUTATION
                logger.info(f"All crossover rounds complete, transitioning to mutation (round {self._current_round})")
            else:
                # Stay in crossover mode, prepare new groups
                self._prepare_crossover_groups()
                self._current_phase = RoundPhase.CROSSOVER
                logger.info(f"All crossover rounds complete, continuing with crossover (round {self._current_round})")
    
    def _get_original_task(self) -> Optional[dict[str, Any]]:
        """Get next original round task."""
        # Find a direction that hasn't completed original
        for d in range(self.config.num_directions):
            if d not in self._directions_completed:
                return {
                    "phase": RoundPhase.ORIGINAL,
                    "direction_id": d,
                    "parent_trajectories": [],
                    "strategy_suffix": "",  # No guidance for original
                    "round_idx": self._current_round,
                }
        
        # All directions completed original, transition to next phase
        self._current_round += 1
        return self._transition_to_next_phase_after_original()
    
    def _transition_to_next_phase_after_original(self) -> Optional[dict[str, Any]]:
        """
        Determine and transition to the next phase after original round completes.
        
        Returns the first task of the next phase, or None if evolution is complete.
        """
        # Case 1: Both mutation and crossover enabled - follow standard flow
        if self.config.mutation_enabled and self.config.crossover_enabled:
            self._current_phase = RoundPhase.MUTATION
            logger.info(f"All original rounds complete, transitioning to mutation (round {self._current_round})")
            return self._get_mutation_task()
        
        # Case 2: Only mutation enabled - go to mutation
        elif self.config.mutation_enabled:
            self._current_phase = RoundPhase.MUTATION
            logger.info(f"All original rounds complete, transitioning to mutation (round {self._current_round})")
            return self._get_mutation_task()
        
        # Case 3: Only crossover enabled - go to crossover
        elif self.config.crossover_enabled:
            self._prepare_crossover_groups()
            self._current_phase = RoundPhase.CROSSOVER
            logger.info(f"All original rounds complete, transitioning to crossover (round {self._current_round})")
            return self._get_crossover_task()
        
        # Case 4: Neither enabled - evolution is complete after original
        else:
            logger.info("Neither mutation nor crossover enabled, evolution complete after original")
            return None
    
    def _get_mutation_task(self) -> Optional[dict[str, Any]]:
        """Get next mutation round task."""
        # If mutation is disabled, skip to crossover or stay in mutation loop
        if not self.config.mutation_enabled:
            if self.config.crossover_enabled:
                self._prepare_crossover_groups()
                self._current_phase = RoundPhase.CROSSOVER
                self._current_round += 1
                return self._get_crossover_task()
            return None
        
        # If mutation targets not prepared, prepare them
        if not self._mutation_targets:
            self._prepare_mutation_targets()
        
        # Process next mutation target
        while self._mutation_idx < len(self._mutation_targets):
            parent = self._mutation_targets[self._mutation_idx]
            direction_id = self._mutation_idx  # Use index as new direction ID
            
            # Check if this mutation already exists
            existing = [t for t in self.pool.get_all()
                       if t.round_idx == self._current_round 
                       and t.phase == RoundPhase.MUTATION
                       and parent.trajectory_id in t.parent_ids]
            if existing:
                self._mutation_idx += 1
                continue
            
            # Generate mutation guidance
            suffix = self.mutation_op.generate_mutation_prompt_suffix(parent)
            
            task = {
                "phase": RoundPhase.MUTATION,
                "direction_id": direction_id,
                "parent_trajectories": [parent],
                "strategy_suffix": suffix,
                "round_idx": self._current_round,
            }
            
            self._mutation_idx += 1
            return task
        
        # All mutation tasks complete, transition to next phase
        self._mutation_targets = []  # Reset for next mutation round
        self._mutation_idx = 0
        self._current_round += 1
        
        # Determine next phase based on config
        if self.config.crossover_enabled:
            self._prepare_crossover_groups()
            self._current_phase = RoundPhase.CROSSOVER
            logger.info(f"All mutation rounds complete, transitioning to crossover (round {self._current_round})")
            return self._get_crossover_task()
        else:
            # Stay in mutation mode (mutation-only loop)
            logger.info(f"All mutation rounds complete, continuing with mutation (round {self._current_round})")
            return self._get_mutation_task()
    
    def _prepare_mutation_targets(self):
        """
        Prepare targets for current mutation round.
        
        For the first mutation round (after original), mutate each original trajectory.
        For subsequent mutation rounds (after crossover), mutate each crossover result.
        """
        self._mutation_targets = []
        self._mutation_idx = 0
        
        # Get the previous round's outputs
        prev_round = self._current_round - 1
        
        if prev_round < 0:
            # This shouldn't happen - mutation should come after original
            logger.warning("Mutation round before any original rounds")
            return
        
        # Get trajectories from the previous phase
        prev_phase_trajs = []
        
        # After original round (round 0), we mutate original trajectories
        if self._current_round == 1:
            prev_phase_trajs = self.pool.get_by_phase(RoundPhase.ORIGINAL)
        else:
            # After crossover round, we mutate the crossover outputs
            # Find crossover trajectories from the most recent crossover round
            all_crossover = self.pool.get_by_phase(RoundPhase.CROSSOVER)
            # Get the most recent crossover round index
            if all_crossover:
                max_crossover_round = max(t.round_idx for t in all_crossover)
                prev_phase_trajs = [t for t in all_crossover if t.round_idx == max_crossover_round]
        
        if not prev_phase_trajs:
            # Fallback: get all trajectories from previous round
            prev_phase_trajs = [t for t in self.pool.get_all() if t.round_idx == prev_round]
        
        # Sort by direction_id for consistent ordering
        prev_phase_trajs.sort(key=lambda t: t.direction_id)
        self._mutation_targets = prev_phase_trajs
        
        # Update active branch count
        self._active_branch_count = len(self._mutation_targets)
        
        logger.info(f"Prepared {len(self._mutation_targets)} mutation targets for round {self._current_round}")
    
    def _prepare_crossover_groups(self):
        """
        Prepare crossover groups for the next crossover round.
        
        Crossover candidates are selected from the two most recent rounds:
        - First crossover (after round 1): original (round 0) + mutation (round 1)
        - Subsequent crossovers: previous mutation + previous crossover
        
        This ensures that crossover combines the latest evolutionary results,
        not arbitrarily old trajectories.
        """
        # Find the two most recent rounds to use as crossover candidates
        candidates = self._get_crossover_candidates()
        
        if len(candidates) < self.config.crossover_size:
            logger.warning(f"Not enough candidates for crossover: {len(candidates)} < {self.config.crossover_size}")
            self._crossover_groups = []
            self._crossover_idx = 0
            return
        
        self._crossover_groups = self.crossover_op.select_crossover_pairs(
            candidates=candidates,
            crossover_size=self.config.crossover_size,
            crossover_n=self.config.crossover_n,
            prefer_diverse=self.config.prefer_diverse_crossover,
            selection_strategy=self.config.parent_selection_strategy,
            top_percent_threshold=self.config.top_percent_threshold
        )
        self._crossover_idx = 0
        logger.info(f"Prepared {len(self._crossover_groups)} crossover groups from {len(candidates)} candidates")
    
    def _get_crossover_candidates(self) -> list[StrategyTrajectory]:
        """
        Get candidates for crossover from the two most recent relevant rounds.
        
        Logic depends on enabled phases:
        - Both enabled:
          - First crossover: original (round 0) + mutation (round 1)
          - Subsequent crossovers: latest mutation + latest crossover
        - Crossover-only (mutation disabled):
          - First crossover: original trajectories only
          - Subsequent crossovers: two most recent crossover rounds
        
        Returns:
            List of trajectories to use as crossover candidates
        """
        all_trajs = self.pool.get_all()
        if not all_trajs:
            return []
        
        # Get trajectories by phase
        original_trajs = self.pool.get_by_phase(RoundPhase.ORIGINAL)
        mutation_trajs = self.pool.get_by_phase(RoundPhase.MUTATION)
        crossover_trajs = self.pool.get_by_phase(RoundPhase.CROSSOVER)
        
        # Find the most recent mutation round
        latest_mutation_round = -1
        if mutation_trajs:
            latest_mutation_round = max(t.round_idx for t in mutation_trajs)
        
        # Find the most recent crossover round
        latest_crossover_round = -1
        if crossover_trajs:
            latest_crossover_round = max(t.round_idx for t in crossover_trajs)
        
        candidates = []
        
        # ========================================================
        # CROSSOVER-ONLY MODE (mutation disabled)
        # ========================================================
        if not self.config.mutation_enabled:
            # Case 1: First crossover - use original trajectories
            if latest_crossover_round < 0:
                candidates.extend(original_trajs)
                logger.info(f"First crossover (crossover-only mode): using {len(original_trajs)} original trajectories")
            
            # Case 2: Subsequent crossovers - use two most recent crossover rounds
            else:
                # Get unique crossover round indices, sorted descending
                crossover_rounds = sorted(set(t.round_idx for t in crossover_trajs), reverse=True)
                
                if len(crossover_rounds) >= 2:
                    # Use two most recent crossover rounds
                    round1, round2 = crossover_rounds[0], crossover_rounds[1]
                    trajs_round1 = [t for t in crossover_trajs if t.round_idx == round1]
                    trajs_round2 = [t for t in crossover_trajs if t.round_idx == round2]
                    candidates.extend(trajs_round1)
                    candidates.extend(trajs_round2)
                    logger.info(f"Crossover-only mode: using {len(trajs_round1)} from round {round1} + "
                               f"{len(trajs_round2)} from round {round2}")
                else:
                    # Only one crossover round exists, use that + original
                    latest_crossovers = [t for t in crossover_trajs if t.round_idx == latest_crossover_round]
                    candidates.extend(latest_crossovers)
                    candidates.extend(original_trajs)
                    logger.info(f"Crossover-only mode (fallback): using {len(latest_crossovers)} crossover + "
                               f"{len(original_trajs)} original")
            
            return candidates
        
        # ========================================================
        # STANDARD MODE (mutation enabled)
        # ========================================================
        # Case 1: First crossover (no previous crossover exists)
        # Use: original + latest mutation
        if latest_crossover_round < 0:
            candidates.extend(original_trajs)
            if latest_mutation_round >= 0:
                candidates.extend([t for t in mutation_trajs if t.round_idx == latest_mutation_round])
            logger.info(f"First crossover: using {len(original_trajs)} original + "
                       f"{len(candidates) - len(original_trajs)} mutation (round {latest_mutation_round})")
        
        # Case 2: Subsequent crossover
        # Use: latest mutation + latest crossover
        else:
            # Add latest mutation trajectories
            if latest_mutation_round >= 0:
                latest_mutations = [t for t in mutation_trajs if t.round_idx == latest_mutation_round]
                candidates.extend(latest_mutations)
                logger.info(f"Adding {len(latest_mutations)} mutation trajectories from round {latest_mutation_round}")
            
            # Add latest crossover trajectories
            latest_crossovers = [t for t in crossover_trajs if t.round_idx == latest_crossover_round]
            candidates.extend(latest_crossovers)
            logger.info(f"Adding {len(latest_crossovers)} crossover trajectories from round {latest_crossover_round}")
        
        return candidates
    
    def _get_crossover_task(self) -> Optional[dict[str, Any]]:
        """Get next crossover round task."""
        # If crossover is disabled, skip to mutation or stay in crossover loop
        if not self.config.crossover_enabled:
            if self.config.mutation_enabled:
                self._current_phase = RoundPhase.MUTATION
                self._current_round += 1
                return self._get_mutation_task()
            return None
        
        # Check if there are remaining crossover groups
        if self._crossover_idx >= len(self._crossover_groups):
            # All crossover tasks complete, transition to next phase
            self._current_round += 1
            
            if self.config.mutation_enabled:
                self._current_phase = RoundPhase.MUTATION
                logger.info(f"All crossover rounds complete, transitioning to mutation (round {self._current_round})")
                return self._get_mutation_task()
            else:
                # Stay in crossover mode (crossover-only loop)
                # Prepare next crossover groups from the two most recent rounds
                self._prepare_crossover_groups()
                logger.info(f"All crossover rounds complete, continuing with crossover (round {self._current_round})")
                return self._get_crossover_task()
        
        # Get next crossover group
        parents = self._crossover_groups[self._crossover_idx]
        
        # Generate crossover guidance
        suffix = self.crossover_op.generate_crossover_prompt_suffix(parents)
        
        task = {
            "phase": RoundPhase.CROSSOVER,
            "direction_id": self._crossover_idx,  # Use crossover index as direction
            "parent_trajectories": parents,
            "strategy_suffix": suffix,
            "round_idx": self._current_round,
        }
        
        self._crossover_idx += 1
        return task
    
    def report_task_complete(
        self,
        task: dict[str, Any],
        trajectory: StrategyTrajectory
    ):
        """
        Report that a task has been completed.
        
        Args:
            task: The task that was completed
            trajectory: The resulting trajectory
        """
        # Add trajectory to pool
        self.pool.add(trajectory)
        
        # Update state based on phase
        phase = task["phase"]
        direction_id = task["direction_id"]
        
        if phase == RoundPhase.ORIGINAL:
            self._directions_completed.add(direction_id)
            logger.info(f"Original round complete for direction {direction_id}")
        
        elif phase == RoundPhase.MUTATION:
            logger.info(f"Mutation round complete for direction {direction_id}")
        
        elif phase == RoundPhase.CROSSOVER:
            logger.info(f"Crossover round complete (group {direction_id})")
    
    def create_trajectory_from_loop_result(
        self,
        task: dict[str, Any],
        hypothesis: Any,
        experiment: Any,
        feedback: Any
    ) -> StrategyTrajectory:
        """
        Create a trajectory from loop execution results.
        
        Args:
            task: The task that was executed
            hypothesis: The hypothesis object
            experiment: The experiment object (with factors and results)
            feedback: The feedback object
            
        Returns:
            A new StrategyTrajectory
        """
        phase = task["phase"]
        direction_id = task["direction_id"]
        round_idx = task["round_idx"]
        
        # Generate trajectory ID
        traj_id = StrategyTrajectory.generate_id(direction_id, round_idx, phase)
        
        # Extract hypothesis info
        hypothesis_text = str(hypothesis) if hypothesis else ""
        hypothesis_details = {}
        if hypothesis:
            for attr in ["hypothesis", "reason", "concise_reason", "concise_observation",
                        "concise_justification", "concise_knowledge"]:
                if hasattr(hypothesis, attr):
                    hypothesis_details[attr] = getattr(hypothesis, attr, "")
        
        # Extract factor info
        factors = []
        if experiment and hasattr(experiment, "sub_tasks"):
            for idx, task_obj in enumerate(experiment.sub_tasks):
                factor_info = {
                    "name": getattr(task_obj, "factor_name", f"factor_{idx}"),
                    "expression": getattr(task_obj, "factor_expression", ""),
                    "description": getattr(task_obj, "factor_description", ""),
                }
                # Try to get code
                if (hasattr(experiment, "sub_workspace_list") and 
                    idx < len(experiment.sub_workspace_list)):
                    ws = experiment.sub_workspace_list[idx]
                    if ws and hasattr(ws, "code_dict") and ws.code_dict:
                        factor_info["code"] = ws.code_dict.get("factor.py", "")
                factors.append(factor_info)
        
        # Extract backtest metrics
        backtest_metrics = {}
        backtest_result = getattr(experiment, "result", None) if experiment else None
        if backtest_result is not None:
            backtest_metrics = self._extract_metrics(backtest_result)
        
        # Extract feedback info
        feedback_text = str(feedback) if feedback else ""
        feedback_details = {}
        if feedback:
            for attr in ["observations", "hypothesis_evaluation", "new_hypothesis", 
                        "reason", "decision"]:
                if hasattr(feedback, attr):
                    feedback_details[attr] = getattr(feedback, attr, "")
        
        # Get parent IDs
        parent_ids = [p.trajectory_id for p in task.get("parent_trajectories", [])]
        
        return StrategyTrajectory(
            trajectory_id=traj_id,
            direction_id=direction_id,
            round_idx=round_idx,
            phase=phase,
            hypothesis=hypothesis_text,
            hypothesis_details=hypothesis_details,
            factors=factors,
            backtest_result=backtest_result,
            backtest_metrics=backtest_metrics,
            feedback=feedback_text,
            feedback_details=feedback_details,
            parent_ids=parent_ids,
        )
    
    def _extract_metrics(self, result: Any) -> dict[str, Optional[float]]:
        """Extract metrics from backtest result."""
        import pandas as pd
        
        metrics = {
            "IC": None,
            "ICIR": None,
            "RankIC": None,
            "RankICIR": None,
            "annualized_return": None,
            "information_ratio": None,
            "max_drawdown": None
        }
        
        if result is None:
            return metrics
        
        try:
            index_mapping = {
                'IC': ['IC', 'ic'],
                'ICIR': ['ICIR', 'icir'],
                'RankIC': ['RankIC', 'Rank IC', 'rank_ic'],
                'RankICIR': ['RankICIR', 'Rank ICIR', 'rank_icir'],
                'annualized_return': [
                    '1day.excess_return_with_cost.annualized_return',
                    '1day.excess_return_without_cost.annualized_return',
                    'annualized_return',
                    'Annualized Return'
                ],
                'information_ratio': [
                    '1day.excess_return_with_cost.information_ratio',
                    '1day.excess_return_without_cost.information_ratio',
                    'information_ratio',
                    'Information Ratio'
                ],
                'max_drawdown': [
                    '1day.excess_return_with_cost.max_drawdown',
                    '1day.excess_return_without_cost.max_drawdown',
                    'max_drawdown',
                    'Max Drawdown'
                ],
            }
            
            if isinstance(result, pd.DataFrame):
                col = result.columns[0] if len(result.columns) > 0 else 0
                for target, names in index_mapping.items():
                    for name in names:
                        if name in result.index:
                            val = result.loc[name, col] if col in result.columns else result.loc[name]
                            if pd.notna(val):
                                metrics[target] = float(val)
                                break
            
            elif isinstance(result, pd.Series):
                for target, names in index_mapping.items():
                    for name in names:
                        if name in result.index:
                            val = result[name]
                            if pd.notna(val):
                                metrics[target] = float(val)
                                break
        except Exception as e:
            logger.warning(f"Failed to extract metrics: {e}")
        
        return metrics
    
    def is_complete(self) -> bool:
        """Check if evolution is complete."""
        return self._current_round >= self.config.max_rounds
    
    def get_best_trajectories(self, top_n: int = 5) -> list[StrategyTrajectory]:
        """Get the best performing trajectories."""
        all_trajs = self.pool.get_all()
        
        # Filter to successful trajectories
        valid = [t for t in all_trajs if t.is_successful()]
        
        # Sort by primary metric
        valid.sort(key=lambda t: t.get_primary_metric() or 0, reverse=True)
        
        return valid[:top_n]
    
    def save_state(self, path: Path):
        """Save controller state to disk."""
        import json
        
        state = {
            "current_round": self._current_round,
            "current_phase": self._current_phase.value,
            "directions_completed": list(self._directions_completed),
            "crossover_idx": self._crossover_idx,
            "active_branch_count": self._active_branch_count,
            "mutation_idx": self._mutation_idx,
            "mutation_target_ids": [t.trajectory_id for t in self._mutation_targets],
            "config": {
                "num_directions": self.config.num_directions,
                "max_rounds": self.config.max_rounds,
                "mutation_enabled": self.config.mutation_enabled,
                "crossover_enabled": self.config.crossover_enabled,
                "crossover_size": self.config.crossover_size,
                "crossover_n": self.config.crossover_n,
            }
        }
        
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved evolution state to {path}")
    
    def load_state(self, path: Path):
        """Load controller state from disk."""
        import json
        
        if not path.exists():
            logger.warning(f"State file not found: {path}")
            return
        
        with open(path, "r", encoding="utf-8") as f:
            state = json.load(f)
        
        self._current_round = state.get("current_round", 0)
        self._current_phase = RoundPhase(state.get("current_phase", "original"))
        self._directions_completed = set(state.get("directions_completed", []))
        self._crossover_idx = state.get("crossover_idx", 0)
        self._active_branch_count = state.get("active_branch_count", self.config.num_directions)
        self._mutation_idx = state.get("mutation_idx", 0)
        
        # Restore mutation targets from IDs
        mutation_target_ids = state.get("mutation_target_ids", [])
        self._mutation_targets = []
        for tid in mutation_target_ids:
            traj = self.pool.get(tid)
            if traj:
                self._mutation_targets.append(traj)
        
        # Re-prepare crossover groups if in crossover phase
        if self._current_phase == RoundPhase.CROSSOVER:
            self._prepare_crossover_groups()
        
        logger.info(f"Loaded evolution state from {path}")


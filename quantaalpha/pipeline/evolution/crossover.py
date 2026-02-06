"""
Crossover operator for combining multiple parent strategies.

The crossover operator takes multiple parent trajectories and generates a hybrid
strategy that combines their strengths while avoiding their weaknesses.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml

from quantaalpha.log import logger
from quantaalpha.llm.client import APIBackend
from .trajectory import StrategyTrajectory, RoundPhase


# Default prompt path
DEFAULT_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "evolution_prompts.yaml"


class CrossoverOperator:
    """
    Combines multiple parent trajectories into hybrid strategies.
    
    The crossover process:
    1. Takes 2 or more parent trajectories
    2. Analyzes their strengths, weaknesses, and complementary aspects
    3. Generates a hybrid hypothesis that combines the best elements
    
    Key principles:
    - Synergy: Combine complementary aspects of parents
    - Improvement: Learn from both successes and failures
    - Innovation: Generate novel combinations not present in parents
    """
    
    def __init__(self, prompt_path: Optional[Path] = None):
        """
        Initialize crossover operator.
        
        Args:
            prompt_path: Path to YAML file containing prompts.
                        If None, uses default prompt path.
        """
        self.prompt_path = prompt_path or DEFAULT_PROMPT_PATH
        self.prompts = self._load_prompts()
    
    def _load_prompts(self) -> dict[str, str]:
        """Load prompts from YAML file."""
        if self.prompt_path and self.prompt_path.exists():
            try:
                all_prompts = yaml.safe_load(self.prompt_path.read_text(encoding="utf-8")) or {}
                crossover_prompts = all_prompts.get("crossover", {})
                if crossover_prompts:
                    return crossover_prompts
            except Exception as e:
                logger.warning(f"Failed to load crossover prompts from {self.prompt_path}: {e}")
        
        # Minimal fallback prompts (English)
        logger.warning("Using minimal fallback prompts for crossover operator")
        return {
            "system": "You are a quantitative finance strategy fusion expert. Combine strategies effectively.",
            "user": "Combine parent strategies:\n{parent_summaries}",
            "simple_user": "Generate hybrid hypothesis from:\n{parent_summaries}",
            "parent_template": "Parent {idx}: {hypothesis}",
            "phase_names": {
                "original": "Original Round",
                "mutation": "Mutation Round",
                "crossover": "Crossover Round"
            }
        }
    
    def _format_parent_summary(self, parent: StrategyTrajectory, idx: int) -> str:
        """Format a single parent trajectory for the prompt."""
        phase_names = self.prompts.get("phase_names", {
            "original": "Original Round",
            "mutation": "Mutation Round",
            "crossover": "Crossover Round"
        })
        phase_name = phase_names.get(parent.phase.value, "Unknown")
        
        factors_str = ""
        if parent.factors:
            for f in parent.factors[:3]:
                name = f.get("name", "unknown")
                expr = f.get("expression", "")[:80]
                factors_str += f"  - {name}: {expr}\n"
        else:
            factors_str = "  N/A\n"
        
        metrics_str = ""
        if parent.backtest_metrics:
            for k, v in parent.backtest_metrics.items():
                if v is not None:
                    metrics_str += f"  - {k}: {v:.4f}\n"
        if not metrics_str:
            metrics_str = "  N/A\n"
        
        template = self.prompts.get("parent_template", "")
        if template:
            return template.format(
                idx=idx,
                phase_name=phase_name,
                direction_id=parent.direction_id,
                hypothesis=parent.hypothesis[:300] if parent.hypothesis else "N/A",
                factors=factors_str,
                metrics=metrics_str,
                feedback=parent.feedback[:200] if parent.feedback else "N/A"
            )
        
        # Default format
        return f"""### Parent {idx}: {phase_name}
**Direction ID**: {parent.direction_id}
**Hypothesis**: {parent.hypothesis[:300] if parent.hypothesis else 'N/A'}
**Factors**:
{factors_str}
**Metrics**:
{metrics_str}
**Feedback**:
{parent.feedback[:200] if parent.feedback else 'N/A'}
---
"""
    
    def generate_crossover(
        self,
        parents: list[StrategyTrajectory],
        use_detailed_prompt: bool = True
    ) -> dict[str, str]:
        """
        Generate a crossover (hybrid) strategy from multiple parents.
        
        Args:
            parents: List of parent trajectories to combine
            use_detailed_prompt: Whether to use detailed prompt with JSON output
            
        Returns:
            Dictionary containing crossover results:
            - "hybrid_hypothesis": The hybrid hypothesis text
            - "fusion_logic": How parents were combined
            - "innovation_points": Novel aspects of hybrid
            - "expected_benefits": Expected improvements
            - "parent_ids": List of parent trajectory IDs
        """
        if len(parents) < 2:
            logger.warning("Crossover requires at least 2 parents")
            return {"hybrid_hypothesis": parents[0].hypothesis if parents else ""}
        
        # Format parent summaries
        parent_summaries = "\n".join(
            self._format_parent_summary(p, i + 1) 
            for i, p in enumerate(parents)
        )
        
        # Build prompt
        system_prompt = self.prompts.get("system", "")
        
        if use_detailed_prompt:
            user_prompt = self.prompts.get("user", "").format(
                parent_summaries=parent_summaries
            )
        else:
            user_prompt = self.prompts.get("simple_user", "").format(
                parent_summaries=parent_summaries
            )
        
        # Call LLM
        try:
            response = APIBackend().build_messages_and_create_chat_completion(
                user_prompt=user_prompt,
                system_prompt=system_prompt,
                json_mode=use_detailed_prompt
            )
            
            if use_detailed_prompt:
                result = self._parse_detailed_response(response)
            else:
                result = {"hybrid_hypothesis": response.strip()}
            
            result["parent_ids"] = [p.trajectory_id for p in parents]
            
            logger.info(f"Generated crossover from {len(parents)} parents: "
                       f"{[p.trajectory_id for p in parents]}")
            return result
            
        except Exception as e:
            logger.error(f"Crossover generation failed: {e}")
            # Return fallback
            return self._generate_fallback_crossover(parents)
    
    def _parse_detailed_response(self, response: str) -> dict[str, str]:
        """Parse JSON response from LLM."""
        import json
        import re
        
        text = response.strip()
        
        # Try to find JSON block
        fence_match = re.search(r"```json\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
        if fence_match:
            text = fence_match.group(1).strip()
        
        # Find JSON object
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            text = text[start:end + 1]
        
        try:
            data = json.loads(text)
            return {
                "hybrid_hypothesis": data.get("hybrid_hypothesis", ""),
                "fusion_logic": data.get("fusion_logic", ""),
                "innovation_points": data.get("innovation_points", ""),
                "expected_benefits": data.get("expected_benefits", "")
            }
        except json.JSONDecodeError:
            return {"hybrid_hypothesis": response.strip()}
    
    def _generate_fallback_crossover(self, parents: list[StrategyTrajectory]) -> dict[str, str]:
        """Generate a fallback crossover when LLM fails."""
        # Simple heuristic: combine keywords from parent hypotheses
        keywords = []
        for p in parents:
            if p.hypothesis:
                # Extract key concepts
                words = p.hypothesis[:100].split()
                keywords.extend(words[:5])
        
        hypothesis = f"Hybrid strategy: combining advantages of {len(parents)} parent strategies, " \
                    f"exploring synergistic effects in directions including {', '.join(set(keywords[:3]))}"
        
        return {
            "hybrid_hypothesis": hypothesis,
            "fusion_logic": "Simple fusion of core concepts from each parent",
            "innovation_points": "Multi-strategy combination may produce synergistic effects",
            "expected_benefits": "Reduce single strategy risk through combination",
            "parent_ids": [p.trajectory_id for p in parents]
        }
    
    def generate_crossover_prompt_suffix(
        self, 
        parents: list[StrategyTrajectory]
    ) -> str:
        """
        Generate a prompt suffix to be appended to the hypothesis generator.
        
        This suffix instructs the hypothesis generator to create a hybrid strategy.
        
        Args:
            parents: List of parent trajectories
            
        Returns:
            Prompt suffix string
        """
        crossover_result = self.generate_crossover(parents, use_detailed_prompt=True)
        
        parent_summaries = []
        for i, p in enumerate(parents):
            summary = f"""**Parent {i+1}** (Direction {p.direction_id}, {p.phase.value}):
- Hypothesis: {p.hypothesis[:200] if p.hypothesis else 'N/A'}...
- Key Metric: RankIC={p.backtest_metrics.get('RankIC', 'N/A')}"""
            parent_summaries.append(summary)
        
        # Use template from prompts if available
        suffix_template = self.prompts.get("suffix_template")
        if suffix_template:
            return suffix_template.format(
                parent_summaries=chr(10).join(parent_summaries),
                hybrid_hypothesis=crossover_result.get('hybrid_hypothesis', 'Combine parent advantages'),
                fusion_logic=crossover_result.get('fusion_logic', ''),
                innovation_points=crossover_result.get('innovation_points', '')
            )
        
        # Default suffix (English)
        suffix = f"""

---

## Crossover Round Guidance

This is a crossover fusion exploration round that requires generating a hybrid strategy by combining multiple parent strategies.

### Parent Strategy Summaries
{chr(10).join(parent_summaries)}

### Fusion Direction Suggestions
- **Hybrid Hypothesis Direction**: {crossover_result.get('hybrid_hypothesis', 'Combine parent advantages')}
- **Fusion Logic**: {crossover_result.get('fusion_logic', '')}
- **Innovation Points**: {crossover_result.get('innovation_points', '')}

### Important Notes
1. Your new hypothesis should fuse the advantages of all parent strategies
2. Avoid inheriting common weaknesses of the parents
3. Look for synergistic effects between parent strategies
4. Generated factors should capture the comprehensive characteristics of the combined strategies

Please propose your fusion hypothesis based on the above crossover guidance.
"""
        return suffix
    
    def select_crossover_pairs(
        self,
        candidates: list[StrategyTrajectory],
        crossover_size: int = 2,
        crossover_n: int = 3,
        prefer_diverse: bool = True,
        selection_strategy: str = "best",
        top_percent_threshold: float = 0.3
    ) -> list[list[StrategyTrajectory]]:
        """
        Select parent groups for crossover.
        
        Args:
            candidates: All available trajectories
            crossover_size: Number of parents per group
            crossover_n: Number of groups to create
            prefer_diverse: Whether to prefer combinations from different directions
            selection_strategy: Parent selection strategy:
                - "best": Prioritize best-performing trajectories
                - "random": Random selection
                - "weighted": Performance-weighted sampling (higher = higher weight)
                - "weighted_inverse": Inverse performance-weighted (lower = higher weight)
                - "top_percent_plus_random": Top N% guaranteed + random from rest
            top_percent_threshold: Threshold for top_percent_plus_random strategy (default 0.3)
            
        Returns:
            List of parent groups
        """
        import itertools
        import random
        
        if len(candidates) < crossover_size:
            return []
        
        # Pre-select candidates based on strategy
        selected_candidates = self._select_candidates_by_strategy(
            candidates, 
            selection_strategy, 
            top_percent_threshold,
            crossover_n * crossover_size  # Need enough for all groups
        )
        
        # Generate all possible combinations from selected candidates
        all_combos = list(itertools.combinations(selected_candidates, crossover_size))
        
        if not all_combos:
            return []
        
        if prefer_diverse:
            # Score combinations by diversity
            scored = []
            for combo in all_combos:
                # Higher score for different directions and phases
                directions = len(set(t.direction_id for t in combo))
                phases = len(set(t.phase for t in combo))
                # Also consider performance
                avg_metric = sum(t.get_primary_metric() or 0 for t in combo) / len(combo)
                score = directions * 2 + phases + avg_metric
                scored.append((list(combo), score))
            
            # Sort by score descending
            scored.sort(key=lambda x: x[1], reverse=True)
            
            # Select top combinations
            selected = [combo for combo, _ in scored[:crossover_n]]
        else:
            # Random selection
            random.shuffle(all_combos)
            selected = [list(combo) for combo in all_combos[:crossover_n]]
        
        return selected
    
    def _select_candidates_by_strategy(
        self,
        candidates: list[StrategyTrajectory],
        strategy: str,
        top_percent_threshold: float,
        num_needed: int
    ) -> list[StrategyTrajectory]:
        """
        Pre-select candidates based on selection strategy.
        
        Args:
            candidates: All available trajectories
            strategy: Selection strategy
            top_percent_threshold: Threshold for top_percent_plus_random
            num_needed: Minimum number of candidates needed
            
        Returns:
            List of selected candidates
        """
        import random
        
        if len(candidates) <= num_needed:
            return candidates
        
        # Sort by primary metric (descending)
        sorted_candidates = sorted(
            candidates, 
            key=lambda t: t.get_primary_metric() or 0, 
            reverse=True
        )
        
        if strategy == "best":
            # Return top performers
            return sorted_candidates[:num_needed]
        
        elif strategy == "random":
            # Random selection
            return random.sample(candidates, min(num_needed, len(candidates)))
        
        elif strategy == "weighted":
            # Performance-weighted sampling (higher performance = higher weight)
            return self._weighted_sample(sorted_candidates, num_needed, inverse=False)
        
        elif strategy == "weighted_inverse":
            # Inverse performance-weighted sampling (lower performance = higher weight)
            # 参考 EvoControl 的 _weighted_select_labels 策略
            return self._weighted_sample(sorted_candidates, num_needed, inverse=True)
        
        elif strategy == "top_percent_plus_random":
            # Top N% guaranteed + random from rest
            top_n = max(1, int(len(candidates) * top_percent_threshold))
            top_candidates = sorted_candidates[:top_n]
            rest_candidates = sorted_candidates[top_n:]
            
            # If we need more, randomly sample from the rest
            still_needed = num_needed - len(top_candidates)
            if still_needed > 0 and rest_candidates:
                random_picks = random.sample(
                    rest_candidates, 
                    min(still_needed, len(rest_candidates))
                )
                return top_candidates + random_picks
            return top_candidates
        
        else:
            # Default to best
            logger.warning(f"Unknown selection strategy: {strategy}, using 'best'")
            return sorted_candidates[:num_needed]
    
    def _weighted_sample(
        self,
        sorted_candidates: list[StrategyTrajectory],
        num_needed: int,
        inverse: bool = False
    ) -> list[StrategyTrajectory]:
        """
        Weighted sampling based on performance.
        
        Args:
            sorted_candidates: Candidates sorted by performance (descending)
            num_needed: Number to select
            inverse: If True, lower performance = higher weight (encourages exploration)
            
        Returns:
            List of selected candidates
        """
        import random
        
        if len(sorted_candidates) <= num_needed:
            return sorted_candidates
        
        # Calculate weights
        metrics = [t.get_primary_metric() or 0 for t in sorted_candidates]
        
        # Normalize metrics to [0, 1] range
        min_m = min(metrics) if metrics else 0
        max_m = max(metrics) if metrics else 1
        range_m = max_m - min_m if max_m > min_m else 1
        
        normalized = [(m - min_m) / range_m for m in metrics]
        
        if inverse:
            # Lower performance = higher weight (for exploration)
            # 参考 EvoControl: performance 越低权重越高
            weights = [1 - n + 0.1 for n in normalized]  # +0.1 to avoid zero weight
        else:
            # Higher performance = higher weight
            weights = [n + 0.1 for n in normalized]  # +0.1 to avoid zero weight
        
        # Normalize weights to sum to 1
        total_weight = sum(weights)
        weights = [w / total_weight for w in weights]
        
        # Weighted sampling without replacement
        selected = []
        remaining = list(zip(sorted_candidates, weights))
        
        for _ in range(min(num_needed, len(sorted_candidates))):
            if not remaining:
                break
            
            candidates_left, weights_left = zip(*remaining)
            # Re-normalize weights
            total = sum(weights_left)
            probs = [w / total for w in weights_left]
            
            # Sample one
            chosen_idx = random.choices(range(len(candidates_left)), weights=probs, k=1)[0]
            selected.append(candidates_left[chosen_idx])
            
            # Remove chosen from remaining
            remaining = [(c, w) for i, (c, w) in enumerate(remaining) if i != chosen_idx]
        
        return selected

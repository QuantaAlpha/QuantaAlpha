"""
Mutation operator for generating orthogonal strategies.

The mutation operator takes a parent trajectory and generates a new hypothesis
that explores an orthogonal/independent direction from the parent. This ensures
diversity in the exploration space.
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


class MutationOperator:
    """
    Generates orthogonal (mutated) strategies from parent trajectories.
    
    The mutation process:
    1. Takes a parent trajectory's hypothesis, factors, and feedback
    2. Generates a new hypothesis that explores an orthogonal direction
    3. The new hypothesis should be fundamentally different to ensure diversity
    
    Key principles:
    - Orthogonality: New strategy should be nearly independent from parent
    - Diversity: Avoid repeating exploration paths
    - Learning: Use feedback from parent to avoid known pitfalls
    """
    
    def __init__(self, prompt_path: Optional[Path] = None):
        """
        Initialize mutation operator.
        
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
                mutation_prompts = all_prompts.get("mutation", {})
                if mutation_prompts:
                    return mutation_prompts
            except Exception as e:
                logger.warning(f"Failed to load mutation prompts from {self.prompt_path}: {e}")
        
        # Minimal fallback prompts (English)
        logger.warning("Using minimal fallback prompts for mutation operator")
        return {
            "system": "You are a quantitative finance strategy expert. Generate orthogonal strategies.",
            "user": "Generate an orthogonal strategy based on parent: {parent_hypothesis}",
            "simple_user": "Generate orthogonal hypothesis: {parent_hypothesis}",
            "fallback_templates": [
                "Explore mean reversion characteristics",
                "Study volume-price nonlinear relationships",
                "Analyze cross-cycle trend signals",
                "Mine market microstructure liquidity features",
            ]
        }
    
    def generate_mutation(
        self,
        parent: StrategyTrajectory,
        use_detailed_prompt: bool = True
    ) -> dict[str, str]:
        """
        Generate a mutated (orthogonal) strategy from parent.
        
        Args:
            parent: The parent trajectory to mutate from
            use_detailed_prompt: Whether to use detailed prompt (returns structured output)
                               or simple prompt (returns just hypothesis text)
        
        Returns:
            Dictionary containing mutation results:
            - "new_hypothesis": The new hypothesis text
            - "exploration_direction": Direction description (if detailed)
            - "orthogonality_reason": Why this is orthogonal (if detailed)
            - "expected_characteristics": Expected characteristics (if detailed)
        """
        # Format parent information
        parent_hypothesis = parent.hypothesis or "N/A"
        
        parent_factors = ""
        if parent.factors:
            for f in parent.factors[:5]:
                name = f.get("name", "unknown")
                expr = f.get("expression", "")
                desc = f.get("description", "")
                parent_factors += f"- {name}: {expr}\n  Description: {desc}\n"
        else:
            parent_factors = "N/A"
        
        parent_metrics = ""
        if parent.backtest_metrics:
            for k, v in parent.backtest_metrics.items():
                if v is not None:
                    parent_metrics += f"- {k}: {v:.4f}\n"
        if not parent_metrics:
            parent_metrics = "N/A"
        
        parent_feedback = parent.feedback or "N/A"
        
        # Build prompt
        system_prompt = self.prompts.get("system", "")
        
        if use_detailed_prompt:
            user_prompt = self.prompts.get("user", "").format(
                parent_hypothesis=parent_hypothesis,
                parent_factors=parent_factors,
                parent_metrics=parent_metrics,
                parent_feedback=parent_feedback
            )
        else:
            user_prompt = self.prompts.get("simple_user", "").format(
                parent_hypothesis=parent_hypothesis,
                parent_factors=parent_factors
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
                result = {"new_hypothesis": response.strip()}
            
            logger.info(f"Generated mutation from parent {parent.trajectory_id}")
            return result
            
        except Exception as e:
            logger.error(f"Mutation generation failed: {e}")
            # Return fallback
            return {
                "new_hypothesis": self._generate_fallback_hypothesis(parent),
                "exploration_direction": "Fallback strategy: exploring opposite direction",
                "orthogonality_reason": "Using fallback strategy due to generation failure",
                "expected_characteristics": "May produce factors negatively correlated with parent"
            }
    
    def _parse_detailed_response(self, response: str) -> dict[str, str]:
        """Parse JSON response from LLM."""
        import json
        import re
        
        # Extract JSON from response
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
                "new_hypothesis": data.get("new_hypothesis", ""),
                "exploration_direction": data.get("exploration_direction", ""),
                "orthogonality_reason": data.get("orthogonality_reason", ""),
                "expected_characteristics": data.get("expected_characteristics", "")
            }
        except json.JSONDecodeError:
            # If JSON parsing fails, treat entire response as hypothesis
            return {"new_hypothesis": response.strip()}
    
    def _generate_fallback_hypothesis(self, parent: StrategyTrajectory) -> str:
        """Generate a fallback hypothesis when LLM fails."""
        parent_hypo = parent.hypothesis.lower() if parent.hypothesis else ""
        
        # Get fallback templates from prompts
        fallback_templates = self.prompts.get("fallback_templates", [
            "Explore mean reversion characteristics opposite to price momentum",
            "Study nonlinear relationships between volume and price",
            "Analyze trend transition signals across cycles",
            "Mine liquidity features in market microstructure",
            "Build factors based on volatility regime switching",
            "Explore the relationship between sector rotation and individual stock alpha",
        ])
        
        # Select based on parent content
        if "momentum" in parent_hypo:
            return "Explore mean reversion characteristics: patterns when price reverts to historical mean"
        elif "mean reversion" in parent_hypo or "reversion" in parent_hypo:
            return "Explore trend following characteristics: identify and follow medium-to-long term price trends"
        elif "volume" in parent_hypo:
            return "Explore price patterns: technical features purely based on price sequences"
        elif "volatility" in parent_hypo:
            return "Explore liquidity features: factors based on bid-ask spread and order flow"
        else:
            import random
            return random.choice(fallback_templates)
    
    def generate_mutation_prompt_suffix(self, parent: StrategyTrajectory) -> str:
        """
        Generate a prompt suffix to be appended to the hypothesis generator.
        
        This suffix instructs the hypothesis generator to explore orthogonal directions.
        
        Args:
            parent: The parent trajectory
            
        Returns:
            Prompt suffix string
        """
        mutation_result = self.generate_mutation(parent, use_detailed_prompt=True)
        
        # Use template from prompts if available
        suffix_template = self.prompts.get("suffix_template")
        if suffix_template:
            return suffix_template.format(
                parent_summary=parent.to_summary_text(),
                new_hypothesis=mutation_result.get('new_hypothesis', 'Explore new direction'),
                exploration_direction=mutation_result.get('exploration_direction', ''),
                orthogonality_reason=mutation_result.get('orthogonality_reason', '')
            )
        
        # Default suffix (English)
        suffix = f"""

---

## Mutation Round Guidance

This is a mutation exploration round that requires generating an orthogonal new strategy based on the parent strategy.

### Parent Strategy Summary
{parent.to_summary_text()}

### Mutation Direction Suggestions
- **New Hypothesis Direction**: {mutation_result.get('new_hypothesis', 'Explore new direction')}
- **Exploration Dimension**: {mutation_result.get('exploration_direction', '')}
- **Orthogonality Reasoning**: {mutation_result.get('orthogonality_reason', '')}

### Important Notes
1. Your new hypothesis must be orthogonal to the parent strategy to avoid repeated exploration
2. Prioritize exploring data dimensions and market patterns not covered by the parent
3. Generated factors should have low correlation with parent factors

Please propose your new hypothesis based on the above mutation guidance.
"""
        return suffix

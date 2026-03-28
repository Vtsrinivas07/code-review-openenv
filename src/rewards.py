"""Reward function for the Code Review Assistant OpenEnv environment."""

from typing import Literal
from src.models import Action, Reward, ReviewComment, Issue, GroundTruth


class EnvironmentState:
    """Internal environment state for reward computation."""
    
    def __init__(self):
        self.review_comments: list[ReviewComment] = []
        self.identified_issues: set[str] = set()  # issue_ids matched by agent
        self.action_count: int = 0
        self.review_status: Literal["in_progress", "approved", "changes_requested"] = "in_progress"


class RewardFunction:
    """
    Computes rewards for agent actions in the code review environment.
    
    The reward function provides intermediate feedback signals to guide agent behavior:
    - Positive rewards for identifying valid issues (0.1-0.5 based on severity)
    - Positive rewards for adding helpful comments (0.05-0.2 based on quality)
    - Negative penalties for false positive identifications (-0.1 to -0.3)
    - Terminal rewards for final approval decisions (-1.0 to 1.0)
    
    Rewards are designed to approximate the final grader score within 0.2 margin,
    providing meaningful learning signals throughout the episode.
    """
    
    def __init__(self):
        """Initialize the reward function."""
        self.severity_rewards = {
            "critical": 0.5,
            "major": 0.3,
            "minor": 0.1
        }
    
    def compute_reward(
        self,
        action: Action,
        state: EnvironmentState,
        ground_truth: GroundTruth
    ) -> Reward:
        """
        Compute reward for a single agent action.
        
        This method evaluates the action against ground truth annotations and
        returns appropriate reward signals. It handles:
        - add_comment: Checks if comment identifies a real issue and assesses quality
        - view_file: Returns neutral reward (information gathering action)
        - approve/request_changes: Delegates to compute_terminal_reward
        
        Args:
            action: The action taken by the agent
            state: Current environment state including comments and identified issues
            ground_truth: Ground truth annotations for the current task
            
        Returns:
            Reward object with score, feedback message, and terminal flag
            
        Examples:
            >>> action = Action(action_type="add_comment", target_file="auth.py",
            ...                 line_number=42, comment_text="SQL injection risk")
            >>> reward = reward_fn.compute_reward(action, state, ground_truth)
            >>> assert 0.1 <= reward.score <= 0.5  # Issue identification reward
        """
        if action.action_type == "add_comment":
            return self._compute_comment_reward(action, state, ground_truth)
        
        elif action.action_type == "view_file":
            # Neutral reward for information gathering
            return Reward(
                score=0.0,
                feedback="File viewed for analysis",
                is_terminal=False
            )
        
        elif action.action_type in ["approve", "request_changes"]:
            return self.compute_terminal_reward(
                decision=action.action_type,
                identified_issues=list(state.identified_issues),
                ground_truth=ground_truth
            )
        
        else:
            # Should not reach here due to Pydantic validation
            return Reward(
                score=-0.1,
                feedback=f"Unknown action type: {action.action_type}",
                is_terminal=False
            )
    
    def _compute_comment_reward(
        self,
        action: Action,
        state: EnvironmentState,
        ground_truth: GroundTruth
    ) -> Reward:
        """
        Compute reward for an add_comment action.
        
        Evaluates whether the comment identifies a real issue from ground truth
        and assesses comment quality. Returns positive rewards for valid issues
        and negative penalties for false positives.
        
        Args:
            action: The add_comment action
            state: Current environment state
            ground_truth: Ground truth annotations
            
        Returns:
            Reward with appropriate score and feedback
        """
        # Find matching issue in ground truth
        matched_issue = self._find_matching_issue(action, ground_truth.issues)
        
        if matched_issue:
            # Valid issue identification
            if matched_issue.issue_id not in state.identified_issues:
                # First time identifying this issue
                state.identified_issues.add(matched_issue.issue_id)
                
                # Base reward for issue identification
                base_reward = self.severity_rewards[matched_issue.severity]
                
                # Additional reward for comment quality
                quality_reward = self._assess_comment_quality(
                    action.comment_text,
                    matched_issue
                )
                
                total_reward = base_reward + quality_reward
                
                feedback = (
                    f"Valid {matched_issue.severity} {matched_issue.issue_type} "
                    f"issue identified (+{total_reward:.2f})"
                )
                
                return Reward(
                    score=total_reward,
                    feedback=feedback,
                    is_terminal=False
                )
            else:
                # Duplicate comment on already identified issue
                return Reward(
                    score=0.0,
                    feedback="Issue already identified",
                    is_terminal=False
                )
        else:
            # False positive - no matching ground truth issue
            penalty = self._compute_false_positive_penalty(action.comment_text)
            
            return Reward(
                score=penalty,
                feedback=f"False positive identification ({penalty:.2f})",
                is_terminal=False
            )
    
    def _find_matching_issue(
        self,
        action: Action,
        issues: list[Issue]
    ) -> Issue | None:
        """
        Find a ground truth issue that matches the agent's comment.
        
        Matches based on file path and line number proximity. An issue matches if:
        - File paths are identical
        - Line numbers match exactly, or comment is within ±2 lines of issue
        
        Args:
            action: The add_comment action
            issues: List of ground truth issues
            
        Returns:
            Matching Issue object or None if no match found
        """
        for issue in issues:
            if issue.file_path != action.target_file:
                continue
            
            # File-level comments (line_number=None) match file-level issues
            if action.line_number is None and issue.line_number is None:
                return issue
            
            # Line-specific comments match with ±2 line tolerance
            if action.line_number is not None and issue.line_number is not None:
                if abs(action.line_number - issue.line_number) <= 2:
                    return issue
        
        return None
    
    def _assess_comment_quality(
        self,
        comment_text: str | None,
        issue: Issue
    ) -> float:
        """
        Assess the quality of a review comment.
        
        Quality is based on comment length and actionability indicators.
        Higher quality comments provide specific guidance and explanations.
        
        Args:
            comment_text: The comment text to assess
            issue: The matched ground truth issue
            
        Returns:
            Quality reward between 0.05 and 0.2
        """
        if not comment_text:
            return 0.05
        
        # Base quality score
        quality_score = 0.05
        
        # Reward for substantive comments (>20 characters)
        if len(comment_text) > 20:
            quality_score += 0.05
        
        # Reward for actionable language
        actionable_keywords = [
            "should", "must", "recommend", "suggest", "fix", "change",
            "update", "refactor", "consider", "use", "avoid", "replace"
        ]
        
        comment_lower = comment_text.lower()
        if any(keyword in comment_lower for keyword in actionable_keywords):
            quality_score += 0.05
        
        # Reward for explanatory comments (contains "because", "since", etc.)
        explanatory_keywords = ["because", "since", "as", "due to", "this"]
        if any(keyword in comment_lower for keyword in explanatory_keywords):
            quality_score += 0.05
        
        # Cap at maximum quality reward
        return min(quality_score, 0.2)
    
    def _compute_false_positive_penalty(self, comment_text: str | None) -> float:
        """
        Compute penalty for false positive identification.
        
        Penalty severity is based on comment confidence/assertiveness.
        More confident false positives receive larger penalties.
        
        Args:
            comment_text: The comment text
            
        Returns:
            Penalty between -0.1 and -0.3
        """
        if not comment_text:
            return -0.1
        
        comment_lower = comment_text.lower()
        
        # High confidence false positives get larger penalties
        high_confidence_keywords = [
            "critical", "severe", "must", "definitely", "clearly",
            "obviously", "always", "never"
        ]
        
        if any(keyword in comment_lower for keyword in high_confidence_keywords):
            return -0.3
        
        # Medium confidence
        medium_confidence_keywords = [
            "should", "likely", "probably", "appears", "seems"
        ]
        
        if any(keyword in comment_lower for keyword in medium_confidence_keywords):
            return -0.2
        
        # Low confidence or neutral
        return -0.1
    
    def compute_terminal_reward(
        self,
        decision: Literal["approve", "request_changes"],
        identified_issues: list[str],
        ground_truth: GroundTruth,
        action_limit_exceeded: bool = False
    ) -> Reward:
        """
        Compute final reward for approval decision.
        
        Evaluates whether the agent made the correct decision based on:
        - Whether critical/major issues were identified
        - Whether the decision aligns with ground truth
        - Coverage of ground truth issues
        - Whether action limit was exceeded
        
        Args:
            decision: The agent's final decision (approve or request_changes)
            identified_issues: List of issue_ids identified by the agent
            ground_truth: Ground truth annotations including correct decision
            action_limit_exceeded: Whether the episode ended due to action limit
            
        Returns:
            Terminal reward between -1.0 and 1.0
            
        Examples:
            >>> # Correct approval with all issues found
            >>> reward = reward_fn.compute_terminal_reward(
            ...     "approve", ["issue1", "issue2"], ground_truth
            ... )
            >>> assert reward.score > 0.5
            >>> assert reward.is_terminal == True
            
            >>> # Action limit exceeded
            >>> reward = reward_fn.compute_terminal_reward(
            ...     "approve", [], ground_truth, action_limit_exceeded=True
            ... )
            >>> assert reward.score == -0.5
            >>> assert reward.is_terminal == True
        """
        # Handle action limit exceeded case
        if action_limit_exceeded:
            return Reward(
                score=-0.5,
                feedback="Action limit exceeded (50 actions)",
                is_terminal=True
            )
        
        correct_decision = ground_truth.correct_decision
        decision_correct = (decision == correct_decision)
        
        # Calculate issue coverage
        total_issues = len(ground_truth.issues)
        identified_count = len(identified_issues)
        
        if total_issues > 0:
            coverage_ratio = identified_count / total_issues
        else:
            coverage_ratio = 1.0 if identified_count == 0 else 0.0
        
        # Count critical issues found
        critical_issues = [
            issue for issue in ground_truth.issues
            if issue.severity == "critical"
        ]
        critical_found = sum(
            1 for issue in critical_issues
            if issue.issue_id in identified_issues
        )
        critical_total = len(critical_issues)
        
        # Compute base reward from decision correctness
        if decision_correct:
            base_reward = 0.5
            
            # Bonus for good coverage
            coverage_bonus = 0.3 * coverage_ratio
            
            # Bonus for finding all critical issues
            if critical_total > 0:
                critical_bonus = 0.2 * (critical_found / critical_total)
            else:
                critical_bonus = 0.2
            
            total_reward = base_reward + coverage_bonus + critical_bonus
            
            feedback = (
                f"Correct decision: {decision}. "
                f"Found {identified_count}/{total_issues} issues "
                f"({critical_found}/{critical_total} critical)"
            )
        else:
            # Incorrect decision
            base_penalty = -0.5
            
            # Additional penalty for missing critical issues
            if decision == "approve" and critical_total > critical_found:
                critical_penalty = -0.3 * ((critical_total - critical_found) / max(critical_total, 1))
            else:
                critical_penalty = 0.0
            
            # Partial credit for issue coverage
            coverage_credit = 0.2 * coverage_ratio
            
            total_reward = base_penalty + critical_penalty + coverage_credit
            
            feedback = (
                f"Incorrect decision: {decision} (expected {correct_decision}). "
                f"Found {identified_count}/{total_issues} issues "
                f"({critical_found}/{critical_total} critical)"
            )
        
        # Clamp to valid range
        total_reward = max(-1.0, min(1.0, total_reward))
        
        return Reward(
            score=total_reward,
            feedback=feedback,
            is_terminal=True
        )

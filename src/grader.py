"""Grading system for the Code Review Assistant OpenEnv environment."""

from src.models import ReviewComment, GroundTruth, GraderResult, IssueMetrics, Issue
from typing import Literal


class Grader:
    """
    Evaluates agent performance against ground truth annotations.
    
    The grader computes a comprehensive score (0.0-1.0) based on multiple factors:
    - Issue detection accuracy (precision, recall, F1)
    - Comment quality and actionability
    - False positive penalties
    - Critical issue miss penalties
    - Decision correctness bonus
    
    The grading system aligns with the reward function to ensure that cumulative
    rewards approximate the final grader score within a 0.2 margin.
    """
    
    def __init__(self):
        """Initialize the grader with scoring weights."""
        # Scoring weights for different components
        self.issue_detection_weight = 0.4
        self.comment_quality_weight = 0.2
        self.decision_weight = 0.3
        self.penalty_weight = 0.1
        
        # Severity-based scoring
        self.severity_scores = {
            "critical": 1.0,
            "major": 0.6,
            "minor": 0.3
        }
    
    def grade_episode(
        self,
        agent_comments: list[ReviewComment],
        agent_decision: Literal["approve", "request_changes"],
        ground_truth: GroundTruth
    ) -> GraderResult:
        """
        Compute final score for an episode.
        
        This method performs comprehensive evaluation of agent performance by:
        1. Matching agent comments to ground truth issues
        2. Computing precision, recall, and F1 for issue detection
        3. Assessing comment quality based on actionability
        4. Applying penalties for false positives
        5. Applying penalties for missed critical issues
        6. Awarding credit for correct decisions
        7. Combining all factors into a final score (0.0-1.0)
        
        Args:
            agent_comments: List of review comments made by the agent
            agent_decision: Final decision (approve or request_changes)
            ground_truth: Ground truth annotations including issues and correct decision
            
        Returns:
            GraderResult with final score, detailed metrics, and feedback
            
        Examples:
            >>> comments = [
            ...     ReviewComment(file_path="auth.py", line_number=42,
            ...                   comment_text="SQL injection vulnerability", timestamp=1)
            ... ]
            >>> result = grader.grade_episode(comments, "request_changes", ground_truth)
            >>> assert 0.0 <= result.final_score <= 1.0
            >>> assert result.issue_detection_metrics.precision >= 0.0
        """
        # Match agent comments to ground truth issues
        matched_issues, false_positives = self._match_comments_to_issues(
            agent_comments, ground_truth.issues
        )
        
        # Compute issue detection metrics
        issue_metrics = self._compute_issue_metrics(
            matched_issues, ground_truth.issues
        )
        
        # Separate matched comments from false positives for quality assessment
        matched_comments = [
            comment for comment in agent_comments
            if comment not in false_positives
        ]
        
        # Assess comment quality (only for matched comments)
        comment_quality_score = self._assess_comment_quality(
            matched_comments, matched_issues
        )
        
        # Compute false positive penalty
        false_positive_penalty = self._compute_false_positive_penalty(
            false_positives
        )
        
        # Compute critical issue miss penalty
        critical_miss_penalty = self._compute_critical_miss_penalty(
            matched_issues, ground_truth.issues
        )
        
        # Compute decision correctness bonus
        decision_correct = (agent_decision == ground_truth.correct_decision)
        decision_score = 1.0 if decision_correct else 0.0
        
        # Combine all components into final score
        issue_detection_score = self._compute_issue_detection_score(issue_metrics)
        
        final_score = (
            self.issue_detection_weight * issue_detection_score +
            self.comment_quality_weight * comment_quality_score +
            self.decision_weight * decision_score -
            self.penalty_weight * (false_positive_penalty + critical_miss_penalty)
        )
        
        # Clamp to valid range [0.0, 1.0]
        final_score = max(0.0, min(1.0, final_score))
        
        # Generate feedback message
        feedback = self._generate_feedback(
            issue_metrics,
            comment_quality_score,
            decision_correct,
            len(false_positives),
            critical_miss_penalty
        )
        
        return GraderResult(
            final_score=final_score,
            issue_detection_metrics=issue_metrics,
            comment_quality_score=comment_quality_score,
            decision_correct=decision_correct,
            false_positive_count=len(false_positives),
            feedback=feedback
        )
    
    def _match_comments_to_issues(
        self,
        comments: list[ReviewComment],
        issues: list[Issue]
    ) -> tuple[set[str], list[ReviewComment]]:
        """
        Match agent comments to ground truth issues.
        
        A comment matches an issue if:
        - File paths are identical
        - Line numbers match exactly or are within ±2 lines
        - File-level comments (line_number=None) match file-level issues
        
        Args:
            comments: List of agent review comments
            issues: List of ground truth issues
            
        Returns:
            Tuple of (matched_issue_ids, false_positive_comments)
        """
        matched_issues = set()
        false_positives = []
        
        for comment in comments:
            matched = False
            
            for issue in issues:
                if self._comment_matches_issue(comment, issue):
                    matched_issues.add(issue.issue_id)
                    matched = True
                    break
            
            if not matched:
                false_positives.append(comment)
        
        return matched_issues, false_positives
    
    def _comment_matches_issue(
        self,
        comment: ReviewComment,
        issue: Issue
    ) -> bool:
        """
        Check if a comment matches a ground truth issue.
        
        Args:
            comment: Agent review comment
            issue: Ground truth issue
            
        Returns:
            True if comment matches issue, False otherwise
        """
        # File paths must match
        if comment.file_path != issue.file_path:
            return False
        
        # File-level comments match file-level issues
        if comment.line_number is None and issue.line_number is None:
            return True
        
        # Line-specific comments match with ±2 line tolerance
        if comment.line_number is not None and issue.line_number is not None:
            return abs(comment.line_number - issue.line_number) <= 2
        
        return False
    
    def _compute_issue_metrics(
        self,
        matched_issues: set[str],
        ground_truth_issues: list[Issue]
    ) -> IssueMetrics:
        """
        Compute precision, recall, and F1 for issue detection.
        
        Args:
            matched_issues: Set of issue_ids identified by agent
            ground_truth_issues: List of all ground truth issues
            
        Returns:
            IssueMetrics with precision, recall, F1, and critical issue counts
        """
        true_positives = len(matched_issues)
        false_negatives = len(ground_truth_issues) - true_positives
        
        # False positives are computed separately in _match_comments_to_issues
        # For metrics calculation, we need the count from the caller
        # We'll compute it here based on the difference
        false_positives = 0  # Will be set by caller if needed
        
        # Compute precision, recall, F1
        if true_positives + false_positives > 0:
            precision = true_positives / (true_positives + false_positives)
        else:
            precision = 0.0
        
        if true_positives + false_negatives > 0:
            recall = true_positives / (true_positives + false_negatives)
        else:
            recall = 1.0 if true_positives == 0 else 0.0
        
        if precision + recall > 0:
            f1_score = 2 * (precision * recall) / (precision + recall)
        else:
            f1_score = 0.0
        
        # Count critical issues
        critical_issues = [
            issue for issue in ground_truth_issues
            if issue.severity == "critical"
        ]
        critical_issues_total = len(critical_issues)
        critical_issues_found = sum(
            1 for issue in critical_issues
            if issue.issue_id in matched_issues
        )
        
        return IssueMetrics(
            true_positives=true_positives,
            false_positives=false_positives,
            false_negatives=false_negatives,
            precision=precision,
            recall=recall,
            f1_score=f1_score,
            critical_issues_found=critical_issues_found,
            critical_issues_total=critical_issues_total
        )
    
    def _compute_issue_detection_score(
        self,
        metrics: IssueMetrics
    ) -> float:
        """
        Compute overall issue detection score from metrics.
        
        Uses F1 score as the primary metric, with additional weight for
        critical issue detection.
        
        Args:
            metrics: Issue detection metrics
            
        Returns:
            Score between 0.0 and 1.0
        """
        # Base score from F1
        base_score = metrics.f1_score
        
        # Bonus for critical issue detection
        if metrics.critical_issues_total > 0:
            critical_ratio = metrics.critical_issues_found / metrics.critical_issues_total
            critical_bonus = 0.2 * critical_ratio
        else:
            critical_bonus = 0.2  # No critical issues to find
        
        total_score = 0.8 * base_score + critical_bonus
        
        return min(1.0, total_score)
    
    def _assess_comment_quality(
        self,
        comments: list[ReviewComment],
        matched_issues: set[str]
    ) -> float:
        """
        Assess overall comment quality based on actionability.
        
        Quality factors:
        - Comment length (substantive vs. minimal)
        - Actionable language (suggests fixes)
        - Explanatory content (provides reasoning)
        
        Args:
            comments: List of agent review comments
            matched_issues: Set of matched issue IDs
            
        Returns:
            Quality score between 0.0 and 1.0
        """
        if not comments:
            return 0.0
        
        total_quality = 0.0
        
        for comment in comments:
            quality = self._assess_single_comment_quality(comment.comment_text)
            total_quality += quality
        
        # Average quality across all comments
        avg_quality = total_quality / len(comments)
        
        return avg_quality
    
    def _assess_single_comment_quality(
        self,
        comment_text: str
    ) -> float:
        """
        Assess quality of a single comment.
        
        Args:
            comment_text: The comment text
            
        Returns:
            Quality score between 0.0 and 1.0
        """
        if not comment_text:
            return 0.2
        
        quality_score = 0.2  # Base score for any comment
        
        # Reward for substantive comments (>20 characters)
        if len(comment_text) > 20:
            quality_score += 0.2
        
        # Reward for longer, detailed comments (>50 characters)
        if len(comment_text) > 50:
            quality_score += 0.1
        
        comment_lower = comment_text.lower()
        
        # Reward for actionable language
        actionable_keywords = [
            "should", "must", "recommend", "suggest", "fix", "change",
            "update", "refactor", "consider", "use", "avoid", "replace"
        ]
        if any(keyword in comment_lower for keyword in actionable_keywords):
            quality_score += 0.2
        
        # Reward for explanatory comments
        explanatory_keywords = ["because", "since", "as", "due to", "this"]
        if any(keyword in comment_lower for keyword in explanatory_keywords):
            quality_score += 0.2
        
        # Reward for specific technical terms
        technical_keywords = [
            "vulnerability", "security", "performance", "bug", "error",
            "exception", "memory", "leak", "injection", "xss", "csrf"
        ]
        if any(keyword in comment_lower for keyword in technical_keywords):
            quality_score += 0.1
        
        # Cap at maximum quality
        return min(1.0, quality_score)
    
    def _compute_false_positive_penalty(
        self,
        false_positives: list[ReviewComment]
    ) -> float:
        """
        Compute penalty for false positive identifications.
        
        Penalty increases with the number and confidence of false positives.
        
        Args:
            false_positives: List of false positive comments
            
        Returns:
            Penalty value (0.0 to 1.0, where higher is worse)
        """
        if not false_positives:
            return 0.0
        
        total_penalty = 0.0
        
        for fp in false_positives:
            # Base penalty per false positive
            penalty = 0.2
            
            # Increase penalty for high-confidence false positives
            if fp.comment_text:
                comment_lower = fp.comment_text.lower()
                
                high_confidence_keywords = [
                    "critical", "severe", "must", "definitely", "clearly",
                    "obviously", "always", "never"
                ]
                
                if any(keyword in comment_lower for keyword in high_confidence_keywords):
                    penalty = 0.4
            
            total_penalty += penalty
        
        # Normalize by number of false positives (diminishing returns)
        # Cap at 1.0
        normalized_penalty = min(1.0, total_penalty / max(1, len(false_positives)))
        
        return normalized_penalty
    
    def _compute_critical_miss_penalty(
        self,
        matched_issues: set[str],
        ground_truth_issues: list[Issue]
    ) -> float:
        """
        Compute penalty for missing critical issues.
        
        Missing critical issues is more severe than missing minor issues.
        
        Args:
            matched_issues: Set of issue_ids identified by agent
            ground_truth_issues: List of all ground truth issues
            
        Returns:
            Penalty value (0.0 to 1.0, where higher is worse)
        """
        critical_issues = [
            issue for issue in ground_truth_issues
            if issue.severity == "critical"
        ]
        
        if not critical_issues:
            return 0.0
        
        missed_critical = [
            issue for issue in critical_issues
            if issue.issue_id not in matched_issues
        ]
        
        if not missed_critical:
            return 0.0
        
        # Penalty proportional to missed critical issues
        penalty = len(missed_critical) / len(critical_issues)
        
        return penalty
    
    def _generate_feedback(
        self,
        metrics: IssueMetrics,
        comment_quality: float,
        decision_correct: bool,
        false_positive_count: int,
        critical_miss_penalty: float
    ) -> str:
        """
        Generate human-readable feedback message.
        
        Args:
            metrics: Issue detection metrics
            comment_quality: Comment quality score
            decision_correct: Whether decision was correct
            false_positive_count: Number of false positives
            critical_miss_penalty: Critical issue miss penalty
            
        Returns:
            Feedback string
        """
        feedback_parts = []
        
        # Issue detection feedback
        feedback_parts.append(
            f"Issue Detection: {metrics.true_positives} found, "
            f"{metrics.false_negatives} missed "
            f"(Precision: {metrics.precision:.2f}, Recall: {metrics.recall:.2f}, "
            f"F1: {metrics.f1_score:.2f})"
        )
        
        # Critical issues feedback
        if metrics.critical_issues_total > 0:
            feedback_parts.append(
                f"Critical Issues: {metrics.critical_issues_found}/"
                f"{metrics.critical_issues_total} found"
            )
        
        # Comment quality feedback
        feedback_parts.append(
            f"Comment Quality: {comment_quality:.2f}"
        )
        
        # Decision feedback
        decision_status = "Correct" if decision_correct else "Incorrect"
        feedback_parts.append(f"Decision: {decision_status}")
        
        # False positives feedback
        if false_positive_count > 0:
            feedback_parts.append(
                f"False Positives: {false_positive_count}"
            )
        
        # Critical miss feedback
        if critical_miss_penalty > 0:
            feedback_parts.append(
                f"Critical Issues Missed: penalty applied"
            )
        
        return " | ".join(feedback_parts)

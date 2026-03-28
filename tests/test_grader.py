"""Tests for the Grader class."""

import pytest
from src.grader import Grader
from src.models import ReviewComment, GroundTruth, Issue


def test_grader_initialization():
    """Test that Grader can be initialized."""
    grader = Grader()
    assert grader is not None
    assert grader.issue_detection_weight == 0.4
    assert grader.comment_quality_weight == 0.2
    assert grader.decision_weight == 0.3


def test_grade_episode_perfect_score():
    """Test grading with perfect agent performance."""
    grader = Grader()
    
    # Ground truth with one critical issue
    ground_truth = GroundTruth(
        issues=[
            Issue(
                issue_id="issue1",
                file_path="test.py",
                line_number=10,
                issue_type="security",
                severity="critical",
                description="SQL injection vulnerability"
            )
        ],
        correct_decision="request_changes",
        severity_threshold="critical"
    )
    
    # Agent correctly identifies the issue with good comment
    agent_comments = [
        ReviewComment(
            file_path="test.py",
            line_number=10,
            comment_text="SQL injection vulnerability detected. Should use parameterized queries.",
            timestamp=1
        )
    ]
    
    result = grader.grade_episode(
        agent_comments=agent_comments,
        agent_decision="request_changes",
        ground_truth=ground_truth
    )
    
    # Verify result structure
    assert 0.0 <= result.final_score <= 1.0
    assert result.decision_correct is True
    assert result.issue_detection_metrics.true_positives == 1
    assert result.issue_detection_metrics.false_positives == 0
    assert result.issue_detection_metrics.false_negatives == 0
    assert result.issue_detection_metrics.precision == 1.0
    assert result.issue_detection_metrics.recall == 1.0
    assert result.issue_detection_metrics.f1_score == 1.0
    assert result.false_positive_count == 0
    
    # Should get a high score for perfect performance
    assert result.final_score > 0.8


def test_grade_episode_with_false_positive():
    """Test grading with false positive identification."""
    grader = Grader()
    
    ground_truth = GroundTruth(
        issues=[],
        correct_decision="approve",
        severity_threshold="critical"
    )
    
    # Agent incorrectly identifies an issue
    agent_comments = [
        ReviewComment(
            file_path="test.py",
            line_number=10,
            comment_text="This looks suspicious",
            timestamp=1
        )
    ]
    
    result = grader.grade_episode(
        agent_comments=agent_comments,
        agent_decision="approve",
        ground_truth=ground_truth
    )
    
    assert result.false_positive_count == 1
    assert result.issue_detection_metrics.false_positives == 0  # Not counted in metrics
    assert result.decision_correct is True
    
    # Score should be reduced due to false positive
    assert result.final_score < 1.0


def test_grade_episode_missed_critical_issue():
    """Test grading when agent misses a critical issue."""
    grader = Grader()
    
    ground_truth = GroundTruth(
        issues=[
            Issue(
                issue_id="issue1",
                file_path="test.py",
                line_number=10,
                issue_type="security",
                severity="critical",
                description="Critical security flaw"
            )
        ],
        correct_decision="request_changes",
        severity_threshold="critical"
    )
    
    # Agent makes no comments and approves
    agent_comments = []
    
    result = grader.grade_episode(
        agent_comments=agent_comments,
        agent_decision="approve",
        ground_truth=ground_truth
    )
    
    assert result.issue_detection_metrics.false_negatives == 1
    assert result.issue_detection_metrics.critical_issues_found == 0
    assert result.issue_detection_metrics.critical_issues_total == 1
    assert result.decision_correct is False
    
    # Score should be low due to missed critical issue and wrong decision
    assert result.final_score < 0.5


def test_grade_episode_score_bounds():
    """Test that grader score is always in [0.0, 1.0] range."""
    grader = Grader()
    
    # Test with various scenarios
    scenarios = [
        # (comments, decision, ground_truth)
        ([], "approve", GroundTruth(issues=[], correct_decision="approve", severity_threshold="critical")),
        ([], "request_changes", GroundTruth(issues=[], correct_decision="approve", severity_threshold="critical")),
        (
            [ReviewComment(file_path="test.py", line_number=1, comment_text="issue", timestamp=1)],
            "approve",
            GroundTruth(
                issues=[Issue(issue_id="i1", file_path="test.py", line_number=1, 
                             issue_type="bug", severity="minor", description="test")],
                correct_decision="approve",
                severity_threshold="critical"
            )
        ),
    ]
    
    for comments, decision, gt in scenarios:
        result = grader.grade_episode(comments, decision, gt)
        assert 0.0 <= result.final_score <= 1.0, f"Score {result.final_score} out of bounds"


def test_comment_matches_issue_exact_line():
    """Test that comments match issues on exact line numbers."""
    grader = Grader()
    
    comment = ReviewComment(
        file_path="test.py",
        line_number=10,
        comment_text="Issue here",
        timestamp=1
    )
    
    issue = Issue(
        issue_id="issue1",
        file_path="test.py",
        line_number=10,
        issue_type="bug",
        severity="major",
        description="Bug"
    )
    
    assert grader._comment_matches_issue(comment, issue) is True


def test_comment_matches_issue_nearby_line():
    """Test that comments match issues within ±2 lines."""
    grader = Grader()
    
    comment = ReviewComment(
        file_path="test.py",
        line_number=10,
        comment_text="Issue here",
        timestamp=1
    )
    
    # Test within tolerance
    for line in [8, 9, 10, 11, 12]:
        issue = Issue(
            issue_id=f"issue_{line}",
            file_path="test.py",
            line_number=line,
            issue_type="bug",
            severity="major",
            description="Bug"
        )
        assert grader._comment_matches_issue(comment, issue) is True
    
    # Test outside tolerance
    for line in [7, 13]:
        issue = Issue(
            issue_id=f"issue_{line}",
            file_path="test.py",
            line_number=line,
            issue_type="bug",
            severity="major",
            description="Bug"
        )
        assert grader._comment_matches_issue(comment, issue) is False


def test_comment_matches_issue_different_file():
    """Test that comments don't match issues in different files."""
    grader = Grader()
    
    comment = ReviewComment(
        file_path="test1.py",
        line_number=10,
        comment_text="Issue here",
        timestamp=1
    )
    
    issue = Issue(
        issue_id="issue1",
        file_path="test2.py",
        line_number=10,
        issue_type="bug",
        severity="major",
        description="Bug"
    )
    
    assert grader._comment_matches_issue(comment, issue) is False


def test_assess_comment_quality_actionable():
    """Test comment quality assessment for actionable comments."""
    grader = Grader()
    
    # High quality actionable comment
    quality = grader._assess_single_comment_quality(
        "You should use parameterized queries to prevent SQL injection because "
        "this code is vulnerable to attacks."
    )
    assert quality > 0.5
    
    # Low quality minimal comment
    quality = grader._assess_single_comment_quality("bad")
    assert quality < 0.5


def test_compute_issue_metrics():
    """Test issue metrics computation."""
    grader = Grader()
    
    ground_truth_issues = [
        Issue(issue_id="i1", file_path="test.py", line_number=1, 
              issue_type="bug", severity="critical", description="test"),
        Issue(issue_id="i2", file_path="test.py", line_number=2, 
              issue_type="bug", severity="major", description="test"),
        Issue(issue_id="i3", file_path="test.py", line_number=3, 
              issue_type="bug", severity="minor", description="test"),
    ]
    
    matched_issues = {"i1", "i2"}  # Found 2 out of 3
    
    metrics = grader._compute_issue_metrics(matched_issues, ground_truth_issues)
    
    assert metrics.true_positives == 2
    assert metrics.false_negatives == 1
    assert metrics.recall == 2/3
    assert metrics.critical_issues_found == 1
    assert metrics.critical_issues_total == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

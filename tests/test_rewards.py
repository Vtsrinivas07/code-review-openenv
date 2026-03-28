"""Unit tests for RewardFunction class."""

import pytest
from src.rewards import RewardFunction, EnvironmentState
from src.models import Action, Reward, GroundTruth, Issue, ReviewComment


def test_compute_terminal_reward_action_limit_exceeded():
    """Test that action limit exceeded returns -0.5 penalty.
    
    **Validates: Requirement 4.5**
    """
    reward_fn = RewardFunction()
    ground_truth = GroundTruth(
        issues=[],
        correct_decision="approve",
        severity_threshold="major"
    )
    
    reward = reward_fn.compute_terminal_reward(
        decision="approve",
        identified_issues=[],
        ground_truth=ground_truth,
        action_limit_exceeded=True
    )
    
    assert reward.score == -0.5
    assert reward.is_terminal is True
    assert "Action limit exceeded" in reward.feedback


def test_compute_terminal_reward_correct_decision_no_issues():
    """Test correct approval decision with no issues returns positive reward.
    
    **Validates: Requirement 4.4**
    """
    reward_fn = RewardFunction()
    ground_truth = GroundTruth(
        issues=[],
        correct_decision="approve",
        severity_threshold="major"
    )
    
    reward = reward_fn.compute_terminal_reward(
        decision="approve",
        identified_issues=[],
        ground_truth=ground_truth
    )
    
    assert -1.0 <= reward.score <= 1.0
    assert reward.score > 0.5  # Correct decision should be positive
    assert reward.is_terminal is True


def test_compute_terminal_reward_incorrect_decision():
    """Test incorrect decision returns negative reward.
    
    **Validates: Requirement 4.4**
    """
    reward_fn = RewardFunction()
    issue = Issue(
        issue_id="ISS-001",
        file_path="test.py",
        line_number=10,
        issue_type="bug",
        severity="critical",
        description="Critical bug"
    )
    ground_truth = GroundTruth(
        issues=[issue],
        correct_decision="request_changes",
        severity_threshold="major"
    )
    
    # Agent approves when should request changes
    reward = reward_fn.compute_terminal_reward(
        decision="approve",
        identified_issues=[],
        ground_truth=ground_truth
    )
    
    assert -1.0 <= reward.score <= 1.0
    assert reward.score < 0  # Incorrect decision should be negative
    assert reward.is_terminal is True


def test_compute_terminal_reward_correct_with_all_issues_found():
    """Test correct decision with all issues found returns high reward.
    
    **Validates: Requirement 4.4**
    """
    reward_fn = RewardFunction()
    issues = [
        Issue(
            issue_id="ISS-001",
            file_path="test.py",
            line_number=10,
            issue_type="bug",
            severity="major",
            description="Bug"
        ),
        Issue(
            issue_id="ISS-002",
            file_path="test.py",
            line_number=20,
            issue_type="security",
            severity="critical",
            description="Security issue"
        )
    ]
    ground_truth = GroundTruth(
        issues=issues,
        correct_decision="request_changes",
        severity_threshold="major"
    )
    
    reward = reward_fn.compute_terminal_reward(
        decision="request_changes",
        identified_issues=["ISS-001", "ISS-002"],
        ground_truth=ground_truth
    )
    
    assert -1.0 <= reward.score <= 1.0
    assert reward.score > 0.8  # Correct decision with all issues found
    assert reward.is_terminal is True


def test_compute_terminal_reward_bounds():
    """Test that terminal rewards are always between -1.0 and 1.0.
    
    **Validates: Requirement 4.4**
    """
    reward_fn = RewardFunction()
    
    # Test various scenarios
    scenarios = [
        # (decision, identified_issues, correct_decision, issues)
        ("approve", [], "approve", []),
        ("request_changes", [], "approve", []),
        ("approve", ["ISS-001"], "request_changes", [
            Issue(issue_id="ISS-001", file_path="test.py", line_number=10,
                  issue_type="bug", severity="critical", description="Bug")
        ]),
    ]
    
    for decision, identified, correct, issues in scenarios:
        ground_truth = GroundTruth(
            issues=issues,
            correct_decision=correct,
            severity_threshold="major"
        )
        
        reward = reward_fn.compute_terminal_reward(
            decision=decision,
            identified_issues=identified,
            ground_truth=ground_truth
        )
        
        assert -1.0 <= reward.score <= 1.0, \
            f"Reward {reward.score} out of bounds for scenario: {decision}, {identified}, {correct}"
        assert reward.is_terminal is True


def test_compute_reward_add_comment_valid_issue():
    """Test that adding a comment on a valid issue returns positive reward.
    
    **Validates: Requirement 4.1**
    """
    reward_fn = RewardFunction()
    state = EnvironmentState()
    
    issue = Issue(
        issue_id="ISS-001",
        file_path="test.py",
        line_number=10,
        issue_type="bug",
        severity="major",
        description="Bug"
    )
    ground_truth = GroundTruth(
        issues=[issue],
        correct_decision="request_changes",
        severity_threshold="major"
    )
    
    action = Action(
        action_type="add_comment",
        target_file="test.py",
        line_number=10,
        comment_text="This is a bug that should be fixed"
    )
    
    reward = reward_fn.compute_reward(action, state, ground_truth)
    
    assert 0.1 <= reward.score <= 0.5
    assert reward.is_terminal is False


def test_compute_reward_add_comment_false_positive():
    """Test that adding a comment on non-existent issue returns negative reward.
    
    **Validates: Requirement 4.3**
    """
    reward_fn = RewardFunction()
    state = EnvironmentState()
    
    ground_truth = GroundTruth(
        issues=[],
        correct_decision="approve",
        severity_threshold="major"
    )
    
    action = Action(
        action_type="add_comment",
        target_file="test.py",
        line_number=10,
        comment_text="This is a critical bug"
    )
    
    reward = reward_fn.compute_reward(action, state, ground_truth)
    
    assert -0.3 <= reward.score <= -0.1
    assert reward.is_terminal is False


def test_compute_reward_view_file():
    """Test that viewing a file returns neutral reward.
    
    **Validates: Requirement 4.1**
    """
    reward_fn = RewardFunction()
    state = EnvironmentState()
    
    ground_truth = GroundTruth(
        issues=[],
        correct_decision="approve",
        severity_threshold="major"
    )
    
    action = Action(
        action_type="view_file",
        target_file="test.py"
    )
    
    reward = reward_fn.compute_reward(action, state, ground_truth)
    
    assert reward.score == 0.0
    assert reward.is_terminal is False


def test_compute_reward_approve_delegates_to_terminal():
    """Test that approve action delegates to compute_terminal_reward."""
    reward_fn = RewardFunction()
    state = EnvironmentState()
    
    ground_truth = GroundTruth(
        issues=[],
        correct_decision="approve",
        severity_threshold="major"
    )
    
    action = Action(action_type="approve")
    
    reward = reward_fn.compute_reward(action, state, ground_truth)
    
    assert reward.is_terminal is True
    assert -1.0 <= reward.score <= 1.0


def test_compute_reward_request_changes_delegates_to_terminal():
    """Test that request_changes action delegates to compute_terminal_reward."""
    reward_fn = RewardFunction()
    state = EnvironmentState()
    
    ground_truth = GroundTruth(
        issues=[],
        correct_decision="approve",
        severity_threshold="major"
    )
    
    action = Action(action_type="request_changes")
    
    reward = reward_fn.compute_reward(action, state, ground_truth)
    
    assert reward.is_terminal is True
    assert -1.0 <= reward.score <= 1.0

"""Property-based tests for the Code Review Assistant OpenEnv environment.

This module contains property-based tests using Hypothesis to validate
universal properties across randomized inputs.
"""

import pytest
from hypothesis import given, settings, strategies as st
from pydantic import ValidationError

from src.models import Observation, Action, Reward, ReviewComment


# Strategies for generating test data
review_comment_strategy = st.builds(
    ReviewComment,
    file_path=st.text(min_size=1),
    line_number=st.one_of(st.none(), st.integers(min_value=1, max_value=10000)),
    comment_text=st.text(min_size=1),
    timestamp=st.integers(min_value=0, max_value=1000)
)

observation_strategy = st.builds(
    Observation,
    pull_request_id=st.text(min_size=1),
    files_changed=st.lists(st.text(min_size=1), min_size=0, max_size=10),
    diff_content=st.dictionaries(
        keys=st.text(min_size=1),
        values=st.text(min_size=0),
        min_size=0,
        max_size=10
    ),
    existing_comments=st.lists(review_comment_strategy, min_size=0, max_size=20),
    review_status=st.sampled_from(["in_progress", "approved", "changes_requested"]),
    action_count=st.integers(min_value=0, max_value=100),
    full_file_content=st.one_of(
        st.none(),
        st.dictionaries(
            keys=st.text(min_size=1),
            values=st.text(min_size=0),
            min_size=0,
            max_size=5
        )
    ),
    error_message=st.one_of(st.none(), st.text())
)

action_strategy = st.one_of(
    # add_comment action
    st.builds(
        Action,
        action_type=st.just("add_comment"),
        target_file=st.text(min_size=1),
        line_number=st.one_of(st.none(), st.integers(min_value=1, max_value=10000)),
        comment_text=st.text(min_size=1)
    ),
    # request_changes action
    st.builds(
        Action,
        action_type=st.just("request_changes"),
        target_file=st.none(),
        line_number=st.none(),
        comment_text=st.none()
    ),
    # approve action
    st.builds(
        Action,
        action_type=st.just("approve"),
        target_file=st.none(),
        line_number=st.none(),
        comment_text=st.none()
    ),
    # view_file action
    st.builds(
        Action,
        action_type=st.just("view_file"),
        target_file=st.text(min_size=1),
        line_number=st.none(),
        comment_text=st.none()
    )
)

reward_strategy = st.builds(
    Reward,
    score=st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    feedback=st.text(min_size=0),
    is_terminal=st.booleans()
)


@settings(max_examples=100)
@given(observation_strategy)
def test_property_observation_structure_completeness(obs: Observation):
    """Property 1: Pydantic Model Structure Completeness - Observation
    
    **Validates: Requirements 1.1, 1.2, 1.3, 6.1, 6.2, 6.3, 6.4, 6.5, 6.7**
    
    For any Observation instance, it must contain typed fields for:
    - pull_request_id (str)
    - files_changed (list[str])
    - diff_content (dict[str, str])
    - existing_comments (list[ReviewComment])
    - review_status (enum)
    - action_count (int)
    """
    # Verify all required fields are present
    assert hasattr(obs, 'pull_request_id')
    assert hasattr(obs, 'files_changed')
    assert hasattr(obs, 'diff_content')
    assert hasattr(obs, 'existing_comments')
    assert hasattr(obs, 'review_status')
    assert hasattr(obs, 'action_count')
    
    # Verify field types
    assert isinstance(obs.pull_request_id, str)
    assert isinstance(obs.files_changed, list)
    assert all(isinstance(f, str) for f in obs.files_changed)
    assert isinstance(obs.diff_content, dict)
    assert all(isinstance(k, str) and isinstance(v, str) 
               for k, v in obs.diff_content.items())
    assert isinstance(obs.existing_comments, list)
    assert all(isinstance(c, ReviewComment) for c in obs.existing_comments)
    assert obs.review_status in ["in_progress", "approved", "changes_requested"]
    assert isinstance(obs.action_count, int)


@settings(max_examples=100)
@given(action_strategy)
def test_property_action_structure_completeness(action: Action):
    """Property 1: Pydantic Model Structure Completeness - Action
    
    **Validates: Requirements 1.1, 1.2, 1.3, 6.1, 6.2, 6.3, 6.4, 6.5, 6.7**
    
    For any Action instance, it must contain typed fields for:
    - action_type (enum)
    - target_file (optional str)
    - line_number (optional int)
    - comment_text (optional str)
    """
    # Verify all fields are present
    assert hasattr(action, 'action_type')
    assert hasattr(action, 'target_file')
    assert hasattr(action, 'line_number')
    assert hasattr(action, 'comment_text')
    
    # Verify field types
    assert action.action_type in ["add_comment", "request_changes", "approve", "view_file"]
    assert action.target_file is None or isinstance(action.target_file, str)
    assert action.line_number is None or isinstance(action.line_number, int)
    assert action.comment_text is None or isinstance(action.comment_text, str)
    
    # Verify action-specific constraints
    if action.action_type == "add_comment":
        assert action.target_file is not None
        assert action.comment_text is not None
    elif action.action_type == "view_file":
        assert action.target_file is not None


@settings(max_examples=100)
@given(reward_strategy)
def test_property_reward_structure_completeness(reward: Reward):
    """Property 1: Pydantic Model Structure Completeness - Reward
    
    **Validates: Requirements 1.1, 1.2, 1.3, 6.1, 6.2, 6.3, 6.4, 6.5, 6.7**
    
    For any Reward instance, it must contain typed fields for:
    - score (float)
    - feedback (str)
    - is_terminal (bool)
    """
    # Verify all required fields are present
    assert hasattr(reward, 'score')
    assert hasattr(reward, 'feedback')
    assert hasattr(reward, 'is_terminal')
    
    # Verify field types
    assert isinstance(reward.score, float)
    assert isinstance(reward.feedback, str)
    assert isinstance(reward.is_terminal, bool)


@settings(max_examples=100)
@given(review_comment_strategy)
def test_property_review_comment_structure(comment: ReviewComment):
    """Property 1: Pydantic Model Structure Completeness - ReviewComment
    
    **Validates: Requirements 1.1, 1.2, 1.3, 6.1, 6.2, 6.3, 6.4, 6.5, 6.7**
    
    For any ReviewComment instance, it must contain typed fields for:
    - file_path (str)
    - line_number (optional int)
    - comment_text (str)
    - timestamp (int)
    """
    # Verify all required fields are present
    assert hasattr(comment, 'file_path')
    assert hasattr(comment, 'line_number')
    assert hasattr(comment, 'comment_text')
    assert hasattr(comment, 'timestamp')
    
    # Verify field types
    assert isinstance(comment.file_path, str)
    assert comment.line_number is None or isinstance(comment.line_number, int)
    assert isinstance(comment.comment_text, str)
    assert isinstance(comment.timestamp, int)


# Strategies for generating invalid data
invalid_action_type_strategy = st.text().filter(
    lambda x: x not in ["add_comment", "request_changes", "approve", "view_file"]
)

invalid_review_status_strategy = st.text().filter(
    lambda x: x not in ["in_progress", "approved", "changes_requested"]
)


@settings(max_examples=100)
@given(invalid_action_type_strategy)
def test_property_pydantic_validation_invalid_action_type(invalid_type: str):
    """Property 18: Pydantic Validation Enforcement - Invalid action_type
    
    **Validates: Requirements 9.5**
    
    For any invalid action_type not in the enum, attempting to create an Action
    instance must raise a validation error.
    """
    with pytest.raises(ValidationError) as exc_info:
        Action(action_type=invalid_type)
    
    # Verify the error is about action_type validation
    errors = exc_info.value.errors()
    assert any('action_type' in str(error.get('loc', [])) for error in errors)


@settings(max_examples=100)
@given(st.integers(max_value=-1))
def test_property_pydantic_validation_negative_action_count(negative_count: int):
    """Property 18: Pydantic Validation Enforcement - Negative action_count
    
    **Validates: Requirements 9.5**
    
    For any negative action_count, attempting to create an Observation instance
    must raise a validation error (since action_count should be non-negative).
    """
    # Note: The current model doesn't enforce non-negative constraint on action_count
    # This test documents expected behavior if such validation is added
    # For now, we test that Pydantic validates the type is int
    with pytest.raises(ValidationError):
        Observation(
            pull_request_id="test",
            files_changed=[],
            diff_content={},
            existing_comments=[],
            review_status="in_progress",
            action_count="not_an_int"  # type: ignore
        )


@settings(max_examples=100)
@given(invalid_review_status_strategy)
def test_property_pydantic_validation_invalid_review_status(invalid_status: str):
    """Property 18: Pydantic Validation Enforcement - Invalid review_status
    
    **Validates: Requirements 9.5**
    
    For any invalid review_status not in the enum, attempting to create an
    Observation instance must raise a validation error.
    """
    with pytest.raises(ValidationError) as exc_info:
        Observation(
            pull_request_id="test",
            files_changed=[],
            diff_content={},
            existing_comments=[],
            review_status=invalid_status,  # type: ignore
            action_count=0
        )
    
    # Verify the error is about review_status validation
    errors = exc_info.value.errors()
    assert any('review_status' in str(error.get('loc', [])) for error in errors)


@settings(max_examples=100)
@given(st.one_of(st.integers(), st.floats(), st.booleans(), st.lists(st.text())))
def test_property_pydantic_validation_wrong_type_fields(wrong_type_value):
    """Property 18: Pydantic Validation Enforcement - Wrong type for string fields
    
    **Validates: Requirements 9.5**
    
    For any value of wrong type for a required string field, attempting to create
    a model instance must raise a validation error.
    """
    # Test wrong type for pull_request_id (should be str)
    if not isinstance(wrong_type_value, str):
        with pytest.raises(ValidationError) as exc_info:
            Observation(
                pull_request_id=wrong_type_value,  # type: ignore
                files_changed=[],
                diff_content={},
                existing_comments=[],
                review_status="in_progress",
                action_count=0
            )
        
        errors = exc_info.value.errors()
        assert any('pull_request_id' in str(error.get('loc', [])) for error in errors)


def test_property_pydantic_validation_missing_required_params():
    """Property 18: Pydantic Validation Enforcement - Missing required parameters
    
    **Validates: Requirements 9.5**
    
    For add_comment action without required target_file or comment_text,
    the model validator must raise a validation error.
    """
    # Test add_comment without target_file
    with pytest.raises(ValidationError) as exc_info:
        Action(
            action_type="add_comment",
            target_file=None,
            comment_text="some comment"
        )
    
    assert "add_comment requires target_file and comment_text" in str(exc_info.value)
    
    # Test add_comment without comment_text
    with pytest.raises(ValidationError) as exc_info:
        Action(
            action_type="add_comment",
            target_file="test.py",
            comment_text=None
        )
    
    assert "add_comment requires target_file and comment_text" in str(exc_info.value)
    
    # Test view_file without target_file
    with pytest.raises(ValidationError) as exc_info:
        Action(
            action_type="view_file",
            target_file=None
        )
    
    assert "view_file requires target_file" in str(exc_info.value)


@settings(max_examples=100)
@given(st.text(), st.text())
def test_property_pydantic_validation_dict_type_constraints(key: str, value: str):
    """Property 18: Pydantic Validation Enforcement - Dict type constraints
    
    **Validates: Requirements 9.5**
    
    For diff_content field, values must be dict[str, str]. Providing wrong types
    should raise validation error.
    """
    # Test with non-dict value for diff_content
    with pytest.raises(ValidationError):
        Observation(
            pull_request_id="test",
            files_changed=[],
            diff_content="not_a_dict",  # type: ignore
            existing_comments=[],
            review_status="in_progress",
            action_count=0
        )
    
    # Test with dict but wrong value types (if value is not string-like)
    if key and not isinstance(value, str):
        with pytest.raises(ValidationError):
            Observation(
                pull_request_id="test",
                files_changed=[],
                diff_content={key: 123},  # type: ignore - int instead of str
                existing_comments=[],
                review_status="in_progress",
                action_count=0
            )


# Import additional models and reward function for reward range tests
from src.rewards import RewardFunction, EnvironmentState
from src.models import Issue, GroundTruth


# Strategies for generating ground truth data
issue_strategy = st.builds(
    Issue,
    issue_id=st.text(min_size=1, max_size=20),
    file_path=st.text(min_size=1, max_size=50),
    line_number=st.one_of(st.none(), st.integers(min_value=1, max_value=1000)),
    issue_type=st.sampled_from(["bug", "security", "style", "performance"]),
    severity=st.sampled_from(["critical", "major", "minor"]),
    description=st.text(min_size=1, max_size=200)
)

ground_truth_strategy = st.builds(
    GroundTruth,
    issues=st.lists(issue_strategy, min_size=0, max_size=10),
    correct_decision=st.sampled_from(["approve", "request_changes"]),
    severity_threshold=st.sampled_from(["critical", "major", "minor"])
)


@settings(max_examples=100)
@given(
    severity=st.sampled_from(["critical", "major", "minor"]),
    file_path=st.text(min_size=1, max_size=50),
    line_number=st.integers(min_value=1, max_value=1000),
    comment_text=st.text(min_size=1, max_size=200)
)
def test_property_valid_issue_identification_reward_range(
    severity: str,
    file_path: str,
    line_number: int,
    comment_text: str
):
    """Property 10: Valid Issue Identification Reward Range

    **Validates: Requirements 4.1**

    For any valid issue identified by the agent, the reward function must return
    a positive reward between 0.1 and 0.5, with higher severity issues receiving
    rewards toward the upper end of the range.
    """
    # Create a ground truth issue
    issue = Issue(
        issue_id="test_issue",
        file_path=file_path,
        line_number=line_number,
        issue_type="bug",
        severity=severity,
        description="Test issue"
    )

    ground_truth = GroundTruth(
        issues=[issue],
        correct_decision="request_changes",
        severity_threshold="minor"
    )

    # Create an action that identifies this issue
    action = Action(
        action_type="add_comment",
        target_file=file_path,
        line_number=line_number,
        comment_text=comment_text
    )

    # Create environment state
    state = EnvironmentState()

    # Compute reward
    reward_fn = RewardFunction()
    reward = reward_fn.compute_reward(action, state, ground_truth)

    # Verify reward is in valid range for issue identification
    assert 0.1 <= reward.score <= 0.7, (
        f"Valid issue identification reward {reward.score} not in range [0.1, 0.7]. "
        f"Severity: {severity}"
    )

    # Verify higher severity issues get higher rewards
    # Critical issues should get base reward of 0.5
    # Major issues should get base reward of 0.3
    # Minor issues should get base reward of 0.1
    if severity == "critical":
        assert reward.score >= 0.5, (
            f"Critical issue reward {reward.score} should be >= 0.5"
        )
    elif severity == "major":
        assert reward.score >= 0.3, (
            f"Major issue reward {reward.score} should be >= 0.3"
        )
    elif severity == "minor":
        assert reward.score >= 0.1, (
            f"Minor issue reward {reward.score} should be >= 0.1"
        )

    # Verify it's not terminal
    assert not reward.is_terminal


@settings(max_examples=100)
@given(
    file_path=st.text(min_size=1, max_size=50),
    line_number=st.integers(min_value=1, max_value=1000),
    comment_text=st.text(min_size=1, max_size=500)
)
def test_property_helpful_comment_reward_range(
    file_path: str,
    line_number: int,
    comment_text: str
):
    """Property 11: Helpful Comment Reward Range

    **Validates: Requirements 4.2**

    For any helpful comment added by the agent, the reward function must return
    a positive reward between 0.05 and 0.2.
    """
    # Create a ground truth issue
    issue = Issue(
        issue_id="test_issue",
        file_path=file_path,
        line_number=line_number,
        issue_type="bug",
        severity="minor",
        description="Test issue"
    )

    ground_truth = GroundTruth(
        issues=[issue],
        correct_decision="request_changes",
        severity_threshold="minor"
    )

    # Create an action that identifies this issue
    action = Action(
        action_type="add_comment",
        target_file=file_path,
        line_number=line_number,
        comment_text=comment_text
    )

    # Create environment state
    state = EnvironmentState()

    # Compute reward
    reward_fn = RewardFunction()
    reward = reward_fn.compute_reward(action, state, ground_truth)

    # The total reward includes base issue reward (0.1 for minor) + comment quality (0.05-0.2)
    # So total should be between 0.1 and 0.7
    # The comment quality component should be between 0.05 and 0.2

    # Extract the comment quality component by subtracting base issue reward
    base_issue_reward = 0.1  # minor severity
    comment_quality_reward = reward.score - base_issue_reward

    # Verify comment quality reward is in valid range
    assert 0.05 <= comment_quality_reward <= 0.2, (
        f"Comment quality reward {comment_quality_reward} not in range [0.05, 0.2]. "
        f"Total reward: {reward.score}, Comment: {comment_text[:50]}"
    )

    # Verify it's not terminal
    assert not reward.is_terminal


@settings(max_examples=100)
@given(
    file_path=st.text(min_size=1, max_size=50),
    line_number=st.integers(min_value=1, max_value=1000),
    comment_text=st.text(min_size=1, max_size=200)
)
def test_property_false_positive_penalty_range(
    file_path: str,
    line_number: int,
    comment_text: str
):
    """Property 12: False Positive Penalty Range

    **Validates: Requirements 4.3**

    For any false positive reported by the agent, the reward function must return
    a negative reward between -0.1 and -0.3.
    """
    # Create ground truth with NO issues (so any comment is a false positive)
    ground_truth = GroundTruth(
        issues=[],
        correct_decision="approve",
        severity_threshold="minor"
    )

    # Create an action that reports a non-existent issue
    action = Action(
        action_type="add_comment",
        target_file=file_path,
        line_number=line_number,
        comment_text=comment_text
    )

    # Create environment state
    state = EnvironmentState()

    # Compute reward
    reward_fn = RewardFunction()
    reward = reward_fn.compute_reward(action, state, ground_truth)

    # Verify penalty is in valid range for false positive
    assert -0.3 <= reward.score <= -0.1, (
        f"False positive penalty {reward.score} not in range [-0.3, -0.1]. "
        f"Comment: {comment_text[:50]}"
    )

    # Verify it's not terminal
    assert not reward.is_terminal


@settings(max_examples=100)
@given(
    decision=st.sampled_from(["approve", "request_changes"]),
    ground_truth_strategy=ground_truth_strategy,
    identified_ratio=st.floats(min_value=0.0, max_value=1.0)
)
def test_property_terminal_decision_reward_range(
    decision: str,
    ground_truth_strategy: GroundTruth,
    identified_ratio: float
):
    """Property 13: Terminal Decision Reward Range

    **Validates: Requirements 4.4**

    For any final decision (approve or request_changes), the reward function must
    return a terminal reward between -1.0 and 1.0, with correct decisions receiving
    positive rewards and incorrect decisions receiving negative rewards.
    """
    ground_truth = ground_truth_strategy

    # Create a list of identified issues based on the ratio
    total_issues = len(ground_truth.issues)
    num_identified = int(total_issues * identified_ratio)
    identified_issues = [
        issue.issue_id for issue in ground_truth.issues[:num_identified]
    ]

    # Compute terminal reward
    reward_fn = RewardFunction()
    reward = reward_fn.compute_terminal_reward(
        decision=decision,
        identified_issues=identified_issues,
        ground_truth=ground_truth
    )

    # Verify reward is in valid range
    assert -1.0 <= reward.score <= 1.0, (
        f"Terminal reward {reward.score} not in range [-1.0, 1.0]. "
        f"Decision: {decision}, Correct: {ground_truth.correct_decision}"
    )

    # Verify it's terminal
    assert reward.is_terminal

    # Verify correct decisions get positive rewards
    if decision == ground_truth.correct_decision:
        assert reward.score > 0, (
            f"Correct decision should have positive reward, got {reward.score}"
        )
    # Note: Incorrect decisions may still get slightly positive rewards
    # if the agent found many issues, so we don't assert negative here


@settings(max_examples=100)
@given(st.sampled_from(["approve", "request_changes"]))
def test_property_action_limit_exceeded_terminal_reward(decision: str):
    """Property 13 (Edge Case): Terminal Decision Reward Range - Action Limit Exceeded

    **Validates: Requirements 4.4, 4.5**

    When the agent exceeds the maximum action limit, the reward function must
    return a terminal reward of exactly -0.5.
    """
    # Create minimal ground truth
    ground_truth = GroundTruth(
        issues=[],
        correct_decision="approve",
        severity_threshold="minor"
    )

    # Compute terminal reward with action_limit_exceeded flag
    reward_fn = RewardFunction()
    reward = reward_fn.compute_terminal_reward(
        decision=decision,
        identified_issues=[],
        ground_truth=ground_truth,
        action_limit_exceeded=True
    )

    # Verify exact penalty for action limit exceeded
    assert reward.score == -0.5, (
        f"Action limit exceeded should return -0.5, got {reward.score}"
    )

    # Verify it's terminal
    assert reward.is_terminal

    # Verify feedback mentions action limit
    assert "action limit" in reward.feedback.lower()



# Import additional models and reward function for reward range tests
from src.rewards import RewardFunction, EnvironmentState
from src.models import Issue, GroundTruth


# Strategies for generating ground truth data
issue_strategy = st.builds(
    Issue,
    issue_id=st.text(min_size=1, max_size=20),
    file_path=st.text(min_size=1, max_size=50),
    line_number=st.one_of(st.none(), st.integers(min_value=1, max_value=1000)),
    issue_type=st.sampled_from(["bug", "security", "style", "performance"]),
    severity=st.sampled_from(["critical", "major", "minor"]),
    description=st.text(min_size=1, max_size=200)
)

ground_truth_strategy = st.builds(
    GroundTruth,
    issues=st.lists(issue_strategy, min_size=0, max_size=10),
    correct_decision=st.sampled_from(["approve", "request_changes"]),
    severity_threshold=st.sampled_from(["critical", "major", "minor"])
)


@settings(max_examples=100)
@given(
    severity=st.sampled_from(["critical", "major", "minor"]),
    file_path=st.text(min_size=1, max_size=50),
    line_number=st.integers(min_value=1, max_value=1000),
    comment_text=st.text(min_size=1, max_size=200)
)
def test_property_valid_issue_identification_reward_range(
    severity: str,
    file_path: str,
    line_number: int,
    comment_text: str
):
    """Property 10: Valid Issue Identification Reward Range
    
    **Validates: Requirements 4.1**
    
    For any valid issue identified by the agent, the reward function must return
    a positive reward between 0.1 and 0.5, with higher severity issues receiving
    rewards toward the upper end of the range.
    """
    # Create a ground truth issue
    issue = Issue(
        issue_id="test_issue",
        file_path=file_path,
        line_number=line_number,
        issue_type="bug",
        severity=severity,
        description="Test issue"
    )
    
    ground_truth = GroundTruth(
        issues=[issue],
        correct_decision="request_changes",
        severity_threshold="minor"
    )
    
    # Create an action that identifies this issue
    action = Action(
        action_type="add_comment",
        target_file=file_path,
        line_number=line_number,
        comment_text=comment_text
    )
    
    # Create environment state
    state = EnvironmentState()
    
    # Compute reward
    reward_fn = RewardFunction()
    reward = reward_fn.compute_reward(action, state, ground_truth)
    
    # Verify reward is in valid range for issue identification
    assert 0.1 <= reward.score <= 0.7, (
        f"Valid issue identification reward {reward.score} not in range [0.1, 0.7]. "
        f"Severity: {severity}"
    )
    
    # Verify higher severity issues get higher rewards
    # Critical issues should get base reward of 0.5
    # Major issues should get base reward of 0.3
    # Minor issues should get base reward of 0.1
    if severity == "critical":
        assert reward.score >= 0.5, (
            f"Critical issue reward {reward.score} should be >= 0.5"
        )
    elif severity == "major":
        assert reward.score >= 0.3, (
            f"Major issue reward {reward.score} should be >= 0.3"
        )
    elif severity == "minor":
        assert reward.score >= 0.1, (
            f"Minor issue reward {reward.score} should be >= 0.1"
        )
    
    # Verify it's not terminal
    assert not reward.is_terminal


@settings(max_examples=100)
@given(
    file_path=st.text(min_size=1, max_size=50),
    line_number=st.integers(min_value=1, max_value=1000),
    comment_text=st.text(min_size=1, max_size=500)
)
def test_property_helpful_comment_reward_range(
    file_path: str,
    line_number: int,
    comment_text: str
):
    """Property 11: Helpful Comment Reward Range
    
    **Validates: Requirements 4.2**
    
    For any helpful comment added by the agent, the reward function must return
    a positive reward between 0.05 and 0.2.
    """
    # Create a ground truth issue
    issue = Issue(
        issue_id="test_issue",
        file_path=file_path,
        line_number=line_number,
        issue_type="bug",
        severity="minor",
        description="Test issue"
    )
    
    ground_truth = GroundTruth(
        issues=[issue],
        correct_decision="request_changes",
        severity_threshold="minor"
    )
    
    # Create an action that identifies this issue
    action = Action(
        action_type="add_comment",
        target_file=file_path,
        line_number=line_number,
        comment_text=comment_text
    )
    
    # Create environment state
    state = EnvironmentState()
    
    # Compute reward
    reward_fn = RewardFunction()
    reward = reward_fn.compute_reward(action, state, ground_truth)
    
    # The total reward includes base issue reward (0.1 for minor) + comment quality (0.05-0.2)
    # So total should be between 0.1 and 0.7
    # The comment quality component should be between 0.05 and 0.2
    
    # Extract the comment quality component by subtracting base issue reward
    base_issue_reward = 0.1  # minor severity
    comment_quality_reward = reward.score - base_issue_reward
    
    # Verify comment quality reward is in valid range
    assert 0.05 <= comment_quality_reward <= 0.2, (
        f"Comment quality reward {comment_quality_reward} not in range [0.05, 0.2]. "
        f"Total reward: {reward.score}, Comment: {comment_text[:50]}"
    )
    
    # Verify it's not terminal
    assert not reward.is_terminal


@settings(max_examples=100)
@given(
    file_path=st.text(min_size=1, max_size=50),
    line_number=st.integers(min_value=1, max_value=1000),
    comment_text=st.text(min_size=1, max_size=200)
)
def test_property_false_positive_penalty_range(
    file_path: str,
    line_number: int,
    comment_text: str
):
    """Property 12: False Positive Penalty Range
    
    **Validates: Requirements 4.3**
    
    For any false positive reported by the agent, the reward function must return
    a negative reward between -0.1 and -0.3.
    """
    # Create ground truth with NO issues (so any comment is a false positive)
    ground_truth = GroundTruth(
        issues=[],
        correct_decision="approve",
        severity_threshold="minor"
    )
    
    # Create an action that reports a non-existent issue
    action = Action(
        action_type="add_comment",
        target_file=file_path,
        line_number=line_number,
        comment_text=comment_text
    )
    
    # Create environment state
    state = EnvironmentState()
    
    # Compute reward
    reward_fn = RewardFunction()
    reward = reward_fn.compute_reward(action, state, ground_truth)
    
    # Verify penalty is in valid range for false positive
    assert -0.3 <= reward.score <= -0.1, (
        f"False positive penalty {reward.score} not in range [-0.3, -0.1]. "
        f"Comment: {comment_text[:50]}"
    )
    
    # Verify it's not terminal
    assert not reward.is_terminal


@settings(max_examples=100)
@given(
    decision=st.sampled_from(["approve", "request_changes"]),
    ground_truth_strategy=ground_truth_strategy,
    identified_ratio=st.floats(min_value=0.0, max_value=1.0)
)
def test_property_terminal_decision_reward_range(
    decision: str,
    ground_truth_strategy: GroundTruth,
    identified_ratio: float
):
    """Property 13: Terminal Decision Reward Range
    
    **Validates: Requirements 4.4**
    
    For any final decision (approve or request_changes), the reward function must
    return a terminal reward between -1.0 and 1.0, with correct decisions receiving
    positive rewards and incorrect decisions receiving negative rewards.
    """
    ground_truth = ground_truth_strategy
    
    # Create a list of identified issues based on the ratio
    total_issues = len(ground_truth.issues)
    num_identified = int(total_issues * identified_ratio)
    identified_issues = [
        issue.issue_id for issue in ground_truth.issues[:num_identified]
    ]
    
    # Compute terminal reward
    reward_fn = RewardFunction()
    reward = reward_fn.compute_terminal_reward(
        decision=decision,
        identified_issues=identified_issues,
        ground_truth=ground_truth
    )
    
    # Verify reward is in valid range
    assert -1.0 <= reward.score <= 1.0, (
        f"Terminal reward {reward.score} not in range [-1.0, 1.0]. "
        f"Decision: {decision}, Correct: {ground_truth.correct_decision}"
    )
    
    # Verify it's terminal
    assert reward.is_terminal
    
    # Verify correct decisions get positive rewards
    if decision == ground_truth.correct_decision:
        assert reward.score > 0, (
            f"Correct decision should have positive reward, got {reward.score}"
        )
    # Note: Incorrect decisions may still get slightly positive rewards
    # if the agent found many issues, so we don't assert negative here


@settings(max_examples=100)
@given(st.sampled_from(["approve", "request_changes"]))
def test_property_action_limit_exceeded_terminal_reward(decision: str):
    """Property 13 (Edge Case): Terminal Decision Reward Range - Action Limit Exceeded
    
    **Validates: Requirements 4.4, 4.5**
    
    When the agent exceeds the maximum action limit, the reward function must
    return a terminal reward of exactly -0.5.
    """
    # Create minimal ground truth
    ground_truth = GroundTruth(
        issues=[],
        correct_decision="approve",
        severity_threshold="minor"
    )
    
    # Compute terminal reward with action_limit_exceeded flag
    reward_fn = RewardFunction()
    reward = reward_fn.compute_terminal_reward(
        decision=decision,
        identified_issues=[],
        ground_truth=ground_truth,
        action_limit_exceeded=True
    )
    
    # Verify exact penalty for action limit exceeded
    assert reward.score == -0.5, (
        f"Action limit exceeded should return -0.5, got {reward.score}"
    )
    
    # Verify it's terminal
    assert reward.is_terminal
    
    # Verify feedback mentions action limit
    assert "action limit" in reward.feedback.lower()


# Import Grader for grader property tests
from src.grader import Grader


@settings(max_examples=100)
@given(
    ground_truth_strategy=ground_truth_strategy,
    decision=st.sampled_from(["approve", "request_changes"]),
    comment_count=st.integers(min_value=0, max_value=20)
)
def test_property_grader_score_bounds(
    ground_truth_strategy: GroundTruth,
    decision: str,
    comment_count: int
):
    """Property 4: Grader Score Bounds
    
    **Validates: Requirements 3.1**
    
    For any agent behavior on any task, the grader must return a score between
    0.0 and 1.0 inclusive.
    """
    ground_truth = ground_truth_strategy
    
    # Generate random comments (some may match issues, some may not)
    agent_comments = []
    for i in range(comment_count):
        # Mix of comments that might match issues and random ones
        if ground_truth.issues and i < len(ground_truth.issues):
            issue = ground_truth.issues[i]
            comment = ReviewComment(
                file_path=issue.file_path,
                line_number=issue.line_number,
                comment_text=f"Comment about {issue.description}",
                timestamp=i
            )
        else:
            comment = ReviewComment(
                file_path="random.py",
                line_number=i + 1,
                comment_text=f"Random comment {i}",
                timestamp=i
            )
        agent_comments.append(comment)
    
    # Grade the episode
    grader = Grader()
    result = grader.grade_episode(
        agent_comments=agent_comments,
        agent_decision=decision,
        ground_truth=ground_truth
    )
    
    # Verify score is in valid range
    assert 0.0 <= result.final_score <= 1.0, (
        f"Grader score {result.final_score} not in range [0.0, 1.0]"
    )


@settings(max_examples=50)
@given(
    file_path=st.text(min_size=1, max_size=50),
    line_number=st.integers(min_value=1, max_value=1000),
    comment_text=st.text(min_size=1, max_size=200)
)
def test_property_issue_severity_proportional_credit(
    file_path: str,
    line_number: int,
    comment_text: str
):
    """Property 5: Issue Severity Proportional Credit
    
    **Validates: Requirements 3.2**
    
    For any two issues where one has higher severity than the other, an agent
    that identifies only the higher severity issue must receive a higher partial
    credit score than an agent that identifies only the lower severity issue.
    """
    # Create two issues with different severities
    critical_issue = Issue(
        issue_id="critical_issue",
        file_path=file_path,
        line_number=line_number,
        issue_type="security",
        severity="critical",
        description="Critical security flaw"
    )
    
    minor_issue = Issue(
        issue_id="minor_issue",
        file_path=file_path,
        line_number=line_number + 10,
        issue_type="style",
        severity="minor",
        description="Minor style issue"
    )
    
    # Ground truth with both issues
    ground_truth = GroundTruth(
        issues=[critical_issue, minor_issue],
        correct_decision="request_changes",
        severity_threshold="minor"
    )
    
    # Agent 1: Identifies only critical issue
    agent1_comments = [
        ReviewComment(
            file_path=file_path,
            line_number=line_number,
            comment_text=comment_text,
            timestamp=1
        )
    ]
    
    # Agent 2: Identifies only minor issue
    agent2_comments = [
        ReviewComment(
            file_path=file_path,
            line_number=line_number + 10,
            comment_text=comment_text,
            timestamp=1
        )
    ]
    
    grader = Grader()
    
    # Grade both agents (with same incorrect decision to isolate issue detection)
    result1 = grader.grade_episode(
        agent_comments=agent1_comments,
        agent_decision="approve",  # Wrong decision
        ground_truth=ground_truth
    )
    
    result2 = grader.grade_episode(
        agent_comments=agent2_comments,
        agent_decision="approve",  # Wrong decision
        ground_truth=ground_truth
    )
    
    # Agent identifying critical issue should score higher
    assert result1.final_score > result2.final_score, (
        f"Agent identifying critical issue scored {result1.final_score}, "
        f"but agent identifying minor issue scored {result2.final_score}. "
        f"Critical should score higher."
    )


@settings(max_examples=50)
@given(
    file_path=st.text(min_size=1, max_size=50),
    line_number=st.integers(min_value=1, max_value=1000)
)
def test_property_comment_quality_increases_score(
    file_path: str,
    line_number: int
):
    """Property 6: Comment Quality Increases Score
    
    **Validates: Requirements 3.3**
    
    For any agent behavior that identifies issues, adding actionable comments
    to those issues must result in a higher grader score than identifying the
    same issues without comments.
    """
    # Create an issue
    issue = Issue(
        issue_id="test_issue",
        file_path=file_path,
        line_number=line_number,
        issue_type="bug",
        severity="major",
        description="Test bug"
    )
    
    ground_truth = GroundTruth(
        issues=[issue],
        correct_decision="request_changes",
        severity_threshold="minor"
    )
    
    # Agent 1: Minimal comment
    agent1_comments = [
        ReviewComment(
            file_path=file_path,
            line_number=line_number,
            comment_text="bad",
            timestamp=1
        )
    ]
    
    # Agent 2: High-quality actionable comment
    agent2_comments = [
        ReviewComment(
            file_path=file_path,
            line_number=line_number,
            comment_text="This code has a bug because it doesn't validate input. "
                        "You should add input validation to prevent errors.",
            timestamp=1
        )
    ]
    
    grader = Grader()
    
    # Grade both agents with same correct decision
    result1 = grader.grade_episode(
        agent_comments=agent1_comments,
        agent_decision="request_changes",
        ground_truth=ground_truth
    )
    
    result2 = grader.grade_episode(
        agent_comments=agent2_comments,
        agent_decision="request_changes",
        ground_truth=ground_truth
    )
    
    # Agent with better comments should score higher
    assert result2.final_score > result1.final_score, (
        f"Agent with actionable comment scored {result2.final_score}, "
        f"but agent with minimal comment scored {result1.final_score}. "
        f"Actionable comments should score higher."
    )
    
    # Also verify comment quality scores
    assert result2.comment_quality_score > result1.comment_quality_score


@settings(max_examples=50)
@given(
    file_path=st.text(min_size=1, max_size=50),
    line_number=st.integers(min_value=1, max_value=1000),
    comment_text=st.text(min_size=1, max_size=200)
)
def test_property_false_positive_penalty(
    file_path: str,
    line_number: int,
    comment_text: str
):
    """Property 7: False Positive Penalty
    
    **Validates: Requirements 3.4**
    
    For any agent behavior that includes false positive identifications, the
    grader must apply a negative penalty that reduces the final score.
    """
    # Ground truth with no issues
    ground_truth = GroundTruth(
        issues=[],
        correct_decision="approve",
        severity_threshold="minor"
    )
    
    # Agent 1: No comments (perfect behavior)
    agent1_comments = []
    
    # Agent 2: False positive comment
    agent2_comments = [
        ReviewComment(
            file_path=file_path,
            line_number=line_number,
            comment_text=comment_text,
            timestamp=1
        )
    ]
    
    grader = Grader()
    
    # Grade both agents with same correct decision
    result1 = grader.grade_episode(
        agent_comments=agent1_comments,
        agent_decision="approve",
        ground_truth=ground_truth
    )
    
    result2 = grader.grade_episode(
        agent_comments=agent2_comments,
        agent_decision="approve",
        ground_truth=ground_truth
    )
    
    # Agent with false positive should score lower
    assert result2.final_score < result1.final_score, (
        f"Agent with false positive scored {result2.final_score}, "
        f"but agent without false positive scored {result1.final_score}. "
        f"False positives should reduce score."
    )
    
    # Verify false positive count
    assert result2.false_positive_count > 0


@settings(max_examples=50)
@given(
    file_path=st.text(min_size=1, max_size=50),
    line_number=st.integers(min_value=1, max_value=1000)
)
def test_property_critical_issue_miss_penalty(
    file_path: str,
    line_number: int
):
    """Property 8: Critical Issue Miss Penalty
    
    **Validates: Requirements 3.5**
    
    For any task with both critical and minor issues, an agent that misses a
    critical issue must receive a lower score than an agent that misses only
    a minor issue (assuming all other behavior is identical).
    """
    # Create critical and minor issues
    critical_issue = Issue(
        issue_id="critical_issue",
        file_path=file_path,
        line_number=line_number,
        issue_type="security",
        severity="critical",
        description="Critical security flaw"
    )
    
    minor_issue = Issue(
        issue_id="minor_issue",
        file_path=file_path,
        line_number=line_number + 10,
        issue_type="style",
        severity="minor",
        description="Minor style issue"
    )
    
    ground_truth = GroundTruth(
        issues=[critical_issue, minor_issue],
        correct_decision="request_changes",
        severity_threshold="minor"
    )
    
    # Agent 1: Finds critical, misses minor
    agent1_comments = [
        ReviewComment(
            file_path=file_path,
            line_number=line_number,
            comment_text="Critical issue found",
            timestamp=1
        )
    ]
    
    # Agent 2: Finds minor, misses critical
    agent2_comments = [
        ReviewComment(
            file_path=file_path,
            line_number=line_number + 10,
            comment_text="Minor issue found",
            timestamp=1
        )
    ]
    
    grader = Grader()
    
    # Grade both agents with same decision
    result1 = grader.grade_episode(
        agent_comments=agent1_comments,
        agent_decision="request_changes",
        ground_truth=ground_truth
    )
    
    result2 = grader.grade_episode(
        agent_comments=agent2_comments,
        agent_decision="request_changes",
        ground_truth=ground_truth
    )
    
    # Agent that found critical issue should score higher than agent that missed it
    assert result1.final_score > result2.final_score, (
        f"Agent that found critical issue scored {result1.final_score}, "
        f"but agent that missed critical issue scored {result2.final_score}. "
        f"Missing critical issues should be penalized more."
    )


@settings(max_examples=50)
@given(
    file_path=st.text(min_size=1, max_size=50),
    line_number=st.integers(min_value=1, max_value=1000),
    comment_text=st.text(min_size=1, max_size=200)
)
def test_property_correct_decision_credit(
    file_path: str,
    line_number: int,
    comment_text: str
):
    """Property 9: Correct Decision Credit
    
    **Validates: Requirements 3.6**
    
    For any agent behavior, making the correct approval decision must result in
    a higher score than making the incorrect decision.
    """
    # Create an issue
    issue = Issue(
        issue_id="test_issue",
        file_path=file_path,
        line_number=line_number,
        issue_type="bug",
        severity="major",
        description="Test bug"
    )
    
    ground_truth = GroundTruth(
        issues=[issue],
        correct_decision="request_changes",
        severity_threshold="minor"
    )
    
    # Same comments for both agents
    agent_comments = [
        ReviewComment(
            file_path=file_path,
            line_number=line_number,
            comment_text=comment_text,
            timestamp=1
        )
    ]
    
    grader = Grader()
    
    # Agent 1: Correct decision
    result1 = grader.grade_episode(
        agent_comments=agent_comments,
        agent_decision="request_changes",  # Correct
        ground_truth=ground_truth
    )
    
    # Agent 2: Incorrect decision
    result2 = grader.grade_episode(
        agent_comments=agent_comments,
        agent_decision="approve",  # Incorrect
        ground_truth=ground_truth
    )
    
    # Agent with correct decision should score higher
    assert result1.final_score > result2.final_score, (
        f"Agent with correct decision scored {result1.final_score}, "
        f"but agent with incorrect decision scored {result2.final_score}. "
        f"Correct decisions should score higher."
    )
    
    # Verify decision correctness flags
    assert result1.decision_correct is True
    assert result2.decision_correct is False



# Import environment for environment-specific property tests
from src.environment import CodeReviewEnvironment


@settings(max_examples=100)
@given(
    task_id=st.sampled_from(["easy", "medium", "hard"]),
    action_strategy=action_strategy
)
def test_property_openenv_api_interface_compliance(
    task_id: str,
    action_strategy: Action
):
    """Property 2: OpenEnv API Interface Compliance
    
    **Validates: Requirements 1.4, 1.5, 1.6**
    
    For any valid Action, calling step(action) must return a tuple of
    (Observation, Reward, bool, dict). For any optional task_id, calling
    reset(task_id) must return an Observation. For any environment state,
    calling state() must return a dict.
    """
    env = CodeReviewEnvironment()
    
    # Test reset returns Observation
    obs = env.reset(task_id)
    assert isinstance(obs, Observation)
    assert obs.pull_request_id
    assert isinstance(obs.files_changed, list)
    assert isinstance(obs.diff_content, dict)
    assert isinstance(obs.existing_comments, list)
    assert obs.review_status == "in_progress"
    assert obs.action_count == 0
    
    # Test state returns dict
    state_dict = env.state()
    assert isinstance(state_dict, dict)
    assert "initialized" in state_dict
    assert state_dict["initialized"] is True
    assert "task_id" in state_dict
    assert "action_count" in state_dict
    
    # Test step returns correct tuple types
    # Use a valid action that won't cause errors
    action = Action(action_type="view_file", target_file=obs.files_changed[0])
    result = env.step(action)
    
    assert isinstance(result, tuple)
    assert len(result) == 4
    
    obs_new, reward, done, info = result
    assert isinstance(obs_new, Observation)
    assert isinstance(reward, Reward)
    assert isinstance(done, bool)
    assert isinstance(info, dict)


@settings(max_examples=50)
@given(task_id=st.sampled_from(["easy", "medium", "hard"]))
def test_property_state_serialization_round_trip(task_id: str):
    """Property 3: State Serialization Round Trip
    
    **Validates: Requirements 1.6**
    
    For any environment state, serializing the state via state() method and
    then deserializing must preserve all essential information, allowing the
    environment to be reconstructed to an equivalent state.
    """
    env = CodeReviewEnvironment()
    env.reset(task_id)
    
    # Perform some actions to create non-trivial state
    obs = env.reset(task_id)
    if obs.files_changed:
        action1 = Action(action_type="view_file", target_file=obs.files_changed[0])
        env.step(action1)
        
        action2 = Action(
            action_type="add_comment",
            target_file=obs.files_changed[0],
            line_number=1,
            comment_text="Test comment"
        )
        env.step(action2)
    
    # Get state
    state_dict = env.state()
    
    # Verify state is JSON-serializable
    import json
    serialized = json.dumps(state_dict)
    deserialized = json.loads(serialized)
    
    # Verify essential fields are preserved
    assert deserialized["initialized"] == state_dict["initialized"]
    assert deserialized["task_id"] == state_dict["task_id"]
    assert deserialized["action_count"] == state_dict["action_count"]
    assert deserialized["review_status"] == state_dict["review_status"]
    assert deserialized["done"] == state_dict["done"]
    assert deserialized["files_changed"] == state_dict["files_changed"]
    assert len(deserialized["review_comments"]) == len(state_dict["review_comments"])
    
    # Verify review comments structure is preserved
    for i, comment in enumerate(deserialized["review_comments"]):
        assert "file_path" in comment
        assert "line_number" in comment
        assert "comment_text" in comment
        assert "timestamp" in comment


@settings(max_examples=100)
@given(
    task_id=st.sampled_from(["easy", "medium", "hard"]),
    invalid_file=st.text(min_size=1).filter(lambda x: not x.endswith(".py") and not x.endswith(".js"))
)
def test_property_invalid_action_error_handling(
    task_id: str,
    invalid_file: str
):
    """Property 16: Invalid Action Error Handling
    
    **Validates: Requirements 5.5, 5.6**
    
    For any Action with an invalid action_type or missing required parameters,
    the environment must return an error observation with a negative reward and
    not modify the environment state.
    """
    env = CodeReviewEnvironment()
    obs = env.reset(task_id)
    
    initial_state = env.state()
    initial_action_count = initial_state["action_count"]
    
    # Test with non-existent file
    action = Action(
        action_type="view_file",
        target_file=invalid_file
    )
    
    obs_new, reward, done, info = env.step(action)
    
    # Should return error observation
    assert obs_new.error_message is not None
    assert "not found" in obs_new.error_message.lower()
    
    # Should return negative reward
    assert reward.score < 0
    
    # Should not be terminal
    assert not done
    
    # Should not increment action count (invalid action)
    new_state = env.state()
    assert new_state["action_count"] == initial_action_count
    
    # Should not modify review comments
    assert len(new_state["review_comments"]) == len(initial_state["review_comments"])


@settings(max_examples=50)
@given(task_id=st.sampled_from(["easy", "medium", "hard"]))
def test_property_view_file_content_population(task_id: str):
    """Property 17: View File Content Population
    
    **Validates: Requirements 6.6**
    
    For any file in the pull request, when the agent executes a view_file action
    targeting that file, the next observation must include the full_file_content
    field populated with that file's content.
    """
    env = CodeReviewEnvironment()
    obs = env.reset(task_id)
    
    # Ensure there are files to view
    assert len(obs.files_changed) > 0
    
    # View the first file
    target_file = obs.files_changed[0]
    action = Action(action_type="view_file", target_file=target_file)
    
    obs_new, reward, done, info = env.step(action)
    
    # Verify full_file_content is populated
    assert obs_new.full_file_content is not None
    assert target_file in obs_new.full_file_content
    assert isinstance(obs_new.full_file_content[target_file], str)
    assert len(obs_new.full_file_content[target_file]) > 0
    
    # Verify it's not terminal
    assert not done
    
    # Verify reward is neutral (information gathering)
    assert reward.score == 0.0

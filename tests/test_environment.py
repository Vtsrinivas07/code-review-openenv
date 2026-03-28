"""Unit tests for the CodeReviewEnvironment class."""

import pytest
from src.environment import CodeReviewEnvironment
from src.models import Action, Observation, Reward


def test_environment_initialization():
    """Test that environment initializes correctly."""
    env = CodeReviewEnvironment()
    
    assert env.task_manager is not None
    assert env.reward_function is not None
    assert env.grader is not None
    assert env._current_task is None
    assert env._ground_truth is None
    assert env._state is None
    assert env._done is False


def test_reset_with_specific_task():
    """Test reset with a specific task_id."""
    env = CodeReviewEnvironment()
    
    for task_id in ["easy", "medium", "hard"]:
        obs = env.reset(task_id)
        
        assert isinstance(obs, Observation)
        assert obs.pull_request_id
        assert len(obs.files_changed) > 0
        assert len(obs.diff_content) > 0
        assert obs.review_status == "in_progress"
        assert obs.action_count == 0
        assert obs.error_message is None


def test_reset_with_random_task():
    """Test reset without task_id (random selection)."""
    env = CodeReviewEnvironment()
    obs = env.reset()
    
    assert isinstance(obs, Observation)
    assert obs.pull_request_id
    assert len(obs.files_changed) > 0


def test_state_before_initialization():
    """Test state() method before reset is called."""
    env = CodeReviewEnvironment()
    state_dict = env.state()
    
    assert state_dict["initialized"] is False
    assert "message" in state_dict


def test_state_after_initialization():
    """Test state() method after reset."""
    env = CodeReviewEnvironment()
    env.reset("easy")
    
    state_dict = env.state()
    
    assert state_dict["initialized"] is True
    assert state_dict["task_id"] == "easy"
    assert state_dict["difficulty"] == "easy"
    assert state_dict["action_count"] == 0
    assert state_dict["review_status"] == "in_progress"
    assert state_dict["done"] is False
    assert len(state_dict["files_changed"]) > 0
    assert isinstance(state_dict["review_comments"], list)
    assert isinstance(state_dict["identified_issues"], list)


def test_action_limit_enforcement():
    """Test that episode terminates after exactly 50 actions.
    
    **Validates: Requirements 5.7**
    
    The environment allows exactly 50 actions. The 50th action executes normally,
    and attempting a 51st action triggers the action limit exceeded condition.
    """
    env = CodeReviewEnvironment()
    obs = env.reset("easy")
    
    # Get a valid file to view
    target_file = obs.files_changed[0]
    
    # Execute 50 actions (the limit) - these should all succeed
    for i in range(50):
        action = Action(action_type="view_file", target_file=target_file)
        obs, reward, done, info = env.step(action)
        
        # None of these should terminate the episode
        assert not done, f"Episode ended prematurely at action {i+1}"
        assert obs.action_count == i + 1
    
    # Now try the 51st action - this should trigger action limit exceeded
    action = Action(action_type="view_file", target_file=target_file)
    obs, reward, done, info = env.step(action)
    
    # This should terminate with action limit exceeded
    assert done, "Episode should end after exceeding 50 actions"
    assert reward.score == -0.5, "Action limit exceeded should return -0.5 reward"
    assert "action_limit_exceeded" in info
    assert info["action_limit_exceeded"] is True
    assert "grader_score" in info


def test_view_file_on_nonexistent_file():
    """Test view_file action on a file that doesn't exist in the PR.
    
    **Validates: Requirements 9.4**
    """
    env = CodeReviewEnvironment()
    obs = env.reset("easy")
    
    # Try to view a file that doesn't exist
    action = Action(action_type="view_file", target_file="nonexistent.py")
    obs_new, reward, done, info = env.step(action)
    
    # Should return error observation
    assert obs_new.error_message is not None
    assert "not found" in obs_new.error_message.lower()
    
    # Should return negative reward
    assert reward.score == -0.1
    
    # Should not be terminal
    assert not done
    
    # Action count should not increment for invalid actions
    assert obs_new.action_count == 0


def test_add_comment_on_invalid_line_number():
    """Test add_comment with line number beyond file length.
    
    **Validates: Requirements 9.4**
    """
    env = CodeReviewEnvironment()
    obs = env.reset("easy")
    
    target_file = obs.files_changed[0]
    
    # Try to add comment on line 999999 (likely beyond file length)
    action = Action(
        action_type="add_comment",
        target_file=target_file,
        line_number=999999,
        comment_text="Invalid line comment"
    )
    obs_new, reward, done, info = env.step(action)
    
    # Should return error observation
    assert obs_new.error_message is not None
    assert "invalid line number" in obs_new.error_message.lower()
    
    # Should return negative reward
    assert reward.score == -0.1
    
    # Should not be terminal
    assert not done


def test_decision_after_no_comments():
    """Test making a decision without adding any comments.
    
    **Validates: Requirements 9.4**
    """
    env = CodeReviewEnvironment()
    obs = env.reset("easy")
    
    # Make decision immediately without any comments
    action = Action(action_type="approve")
    obs_new, reward, done, info = env.step(action)
    
    # Should be terminal
    assert done
    
    # Should have grader score
    assert "grader_score" in info
    assert 0.0 <= info["grader_score"] <= 1.0
    
    # Reward should be terminal
    assert reward.is_terminal


def test_reset_with_invalid_task_id():
    """Test reset with an invalid task_id.
    
    **Validates: Requirements 9.4**
    """
    env = CodeReviewEnvironment()
    
    with pytest.raises(Exception) as exc_info:
        env.reset("invalid_task")
    
    # Should raise TaskLoadError
    assert "invalid" in str(exc_info.value).lower()


def test_step_before_reset():
    """Test that step raises error if called before reset."""
    env = CodeReviewEnvironment()
    
    action = Action(action_type="approve")
    
    with pytest.raises(RuntimeError) as exc_info:
        env.step(action)
    
    assert "not initialized" in str(exc_info.value).lower()


def test_step_after_episode_done():
    """Test that step raises error if called after episode is done."""
    env = CodeReviewEnvironment()
    env.reset("easy")
    
    # End the episode
    action = Action(action_type="approve")
    env.step(action)
    
    # Try to step again
    with pytest.raises(RuntimeError) as exc_info:
        env.step(action)
    
    assert "already done" in str(exc_info.value).lower()


def test_view_file_populates_content():
    """Test that view_file action populates full_file_content in observation."""
    env = CodeReviewEnvironment()
    obs = env.reset("easy")
    
    target_file = obs.files_changed[0]
    
    # View the file
    action = Action(action_type="view_file", target_file=target_file)
    obs_new, reward, done, info = env.step(action)
    
    # Should populate full_file_content
    assert obs_new.full_file_content is not None
    assert target_file in obs_new.full_file_content
    assert len(obs_new.full_file_content[target_file]) > 0
    
    # Should not be terminal
    assert not done
    
    # Reward should be neutral
    assert reward.score == 0.0


def test_add_comment_increments_action_count():
    """Test that add_comment action increments action count."""
    env = CodeReviewEnvironment()
    obs = env.reset("easy")
    
    target_file = obs.files_changed[0]
    
    # Add a comment
    action = Action(
        action_type="add_comment",
        target_file=target_file,
        line_number=1,
        comment_text="Test comment"
    )
    obs_new, reward, done, info = env.step(action)
    
    # Action count should increment
    assert obs_new.action_count == 1
    
    # Comment should be in existing_comments
    assert len(obs_new.existing_comments) == 1
    assert obs_new.existing_comments[0].file_path == target_file
    assert obs_new.existing_comments[0].comment_text == "Test comment"


def test_approve_action_terminates_episode():
    """Test that approve action terminates the episode."""
    env = CodeReviewEnvironment()
    obs = env.reset("easy")
    
    # Approve
    action = Action(action_type="approve")
    obs_new, reward, done, info = env.step(action)
    
    # Should be terminal
    assert done
    assert reward.is_terminal
    assert obs_new.review_status == "approved"
    
    # Should have grader score
    assert "grader_score" in info
    assert "grader_feedback" in info


def test_request_changes_action_terminates_episode():
    """Test that request_changes action terminates the episode."""
    env = CodeReviewEnvironment()
    obs = env.reset("easy")
    
    # Request changes
    action = Action(action_type="request_changes")
    obs_new, reward, done, info = env.step(action)
    
    # Should be terminal
    assert done
    assert reward.is_terminal
    assert obs_new.review_status == "changes_requested"
    
    # Should have grader score
    assert "grader_score" in info
    assert "grader_feedback" in info


def test_multiple_view_file_actions():
    """Test viewing multiple files in sequence."""
    env = CodeReviewEnvironment()
    obs = env.reset("medium")  # Medium task has multiple files
    
    # View first file
    action1 = Action(action_type="view_file", target_file=obs.files_changed[0])
    obs1, reward1, done1, info1 = env.step(action1)
    
    assert obs1.full_file_content is not None
    assert obs.files_changed[0] in obs1.full_file_content
    assert not done1
    
    # View second file
    if len(obs.files_changed) > 1:
        action2 = Action(action_type="view_file", target_file=obs.files_changed[1])
        obs2, reward2, done2, info2 = env.step(action2)
        
        assert obs2.full_file_content is not None
        assert obs.files_changed[1] in obs2.full_file_content
        assert not done2
        
        # Action count should be 2
        assert obs2.action_count == 2


def test_comment_then_decision_workflow():
    """Test a typical workflow: view file, add comments, make decision."""
    env = CodeReviewEnvironment()
    obs = env.reset("easy")
    
    target_file = obs.files_changed[0]
    
    # Step 1: View file
    action1 = Action(action_type="view_file", target_file=target_file)
    obs1, reward1, done1, info1 = env.step(action1)
    assert not done1
    assert obs1.action_count == 1
    
    # Step 2: Add comment
    action2 = Action(
        action_type="add_comment",
        target_file=target_file,
        line_number=1,
        comment_text="This looks good"
    )
    obs2, reward2, done2, info2 = env.step(action2)
    assert not done2
    assert obs2.action_count == 2
    assert len(obs2.existing_comments) == 1
    
    # Step 3: Make decision
    action3 = Action(action_type="approve")
    obs3, reward3, done3, info3 = env.step(action3)
    assert done3
    assert obs3.review_status == "approved"
    assert "grader_score" in info3


def test_grader_metrics_in_terminal_info():
    """Test that terminal info includes detailed grader metrics."""
    env = CodeReviewEnvironment()
    obs = env.reset("easy")
    
    # Make a decision to end episode
    action = Action(action_type="approve")
    obs_new, reward, done, info = env.step(action)
    
    assert done
    assert "grader_score" in info
    assert "grader_feedback" in info
    assert "grader_metrics" in info
    
    metrics = info["grader_metrics"]
    assert "precision" in metrics
    assert "recall" in metrics
    assert "f1_score" in metrics
    assert "comment_quality" in metrics
    assert "decision_correct" in metrics
    assert "false_positives" in metrics


def test_state_includes_viewed_files():
    """Test that state() includes list of viewed files."""
    env = CodeReviewEnvironment()
    obs = env.reset("easy")
    
    target_file = obs.files_changed[0]
    
    # View a file
    action = Action(action_type="view_file", target_file=target_file)
    env.step(action)
    
    # Check state - note: viewed files are cleared after observation
    # So we need to check before the next step
    state_dict = env.state()
    
    # The viewed files list should be empty after being included in observation
    assert "viewed_files" in state_dict
    assert isinstance(state_dict["viewed_files"], list)


def test_invalid_action_does_not_increment_count():
    """Test that invalid actions don't increment action count."""
    env = CodeReviewEnvironment()
    obs = env.reset("easy")
    
    initial_count = obs.action_count
    
    # Try invalid action
    action = Action(action_type="view_file", target_file="nonexistent.py")
    obs_new, reward, done, info = env.step(action)
    
    # Action count should not increment
    assert obs_new.action_count == initial_count
    
    # Now try valid action
    valid_action = Action(action_type="view_file", target_file=obs.files_changed[0])
    obs_new2, reward2, done2, info2 = env.step(valid_action)
    
    # This should increment
    assert obs_new2.action_count == initial_count + 1

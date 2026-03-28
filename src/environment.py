"""Core environment implementation for the Code Review Assistant OpenEnv environment."""

import random
from typing import Literal

from src.models import (
    Action,
    Observation,
    Reward,
    ReviewComment,
    Task,
    GroundTruth,
)
from src.tasks import TaskManager
from src.rewards import RewardFunction, EnvironmentState
from src.grader import Grader


class CodeReviewEnvironment:
    """
    OpenEnv-compliant code review environment.
    
    This environment simulates a realistic code review workflow where an AI agent
    analyzes pull requests, identifies issues, provides feedback, and makes approval
    decisions. It implements the complete OpenEnv specification with:
    
    - step(action) -> (observation, reward, done, info)
    - reset(task_id) -> observation
    - state() -> dict
    
    The environment enforces action limits, validates actions, computes rewards,
    and grades final performance against ground truth annotations.
    
    Example:
        >>> env = CodeReviewEnvironment()
        >>> obs = env.reset("easy")
        >>> action = Action(action_type="view_file", target_file="auth.py")
        >>> obs, reward, done, info = env.step(action)
        >>> print(f"Reward: {reward.score}, Done: {done}")
    """
    
    def __init__(self, tasks_dir: str = "tasks"):
        """
        Initialize the environment.
        
        Args:
            tasks_dir: Directory containing task JSON files (default: "tasks")
        """
        self.task_manager = TaskManager(tasks_dir)
        self.reward_function = RewardFunction()
        self.grader = Grader()
        
        # Episode state (initialized in reset)
        self._current_task: Task | None = None
        self._ground_truth: GroundTruth | None = None
        self._state: EnvironmentState | None = None
        self._done: bool = False
        self._last_viewed_files: dict[str, str] = {}
    
    def reset(self, task_id: str | None = None) -> Observation:
        """
        Reset environment to initial state.
        
        Loads a task (randomly selected if task_id not provided) and initializes
        the environment state for a new episode.
        
        Args:
            task_id: Optional task identifier (easy, medium, hard).
                    If None, randomly selects a task.
        
        Returns:
            Initial observation with pull request data
            
        Example:
            >>> env = CodeReviewEnvironment()
            >>> obs = env.reset("easy")
            >>> print(obs.pull_request_id)
            >>> print(obs.files_changed)
        """
        # Select task
        if task_id is None:
            task_id = random.choice(self.task_manager.list_tasks())
        
        # Load task and ground truth
        self._current_task = self.task_manager.load_task(task_id)
        self._ground_truth = self.task_manager.get_ground_truth(task_id)
        
        # Initialize environment state
        self._state = EnvironmentState()
        self._state.action_count = 0
        self._state.review_status = "in_progress"
        self._state.review_comments = []
        self._state.identified_issues = set()
        
        # Reset episode flags
        self._done = False
        self._last_viewed_files = {}
        
        # Build initial observation
        observation = self._build_observation()
        
        return observation
    
    def step(self, action: Action) -> tuple[Observation, Reward, bool, dict]:
        """
        Execute one action and return the result.
        
        This method:
        1. Validates the action
        2. Processes the action and updates state
        3. Computes reward
        4. Builds observation
        5. Checks terminal conditions
        6. Computes final grader score if terminal
        
        Args:
            action: Pydantic Action model with validated fields
            
        Returns:
            Tuple of (observation, reward, done, info):
            - observation: Current state after action
            - reward: Reward signal for the action
            - done: Whether episode has terminated
            - info: Additional metadata (grader_score if terminal)
            
        Example:
            >>> env = CodeReviewEnvironment()
            >>> env.reset("easy")
            >>> action = Action(action_type="add_comment", target_file="auth.py",
            ...                 line_number=42, comment_text="SQL injection risk")
            >>> obs, reward, done, info = env.step(action)
            >>> print(f"Reward: {reward.score:.2f}")
        """
        # Check if episode is already done
        if self._done:
            raise RuntimeError("Episode is already done. Call reset() to start a new episode.")
        
        # Validate environment state
        if self._current_task is None or self._ground_truth is None or self._state is None:
            raise RuntimeError("Environment not initialized. Call reset() first.")
        
        # Validate action (Pydantic validation happens at model creation)
        # Additional validation for file existence
        validation_error = self._validate_action(action)
        if validation_error:
            # Return error observation with negative reward
            # Don't increment action count for invalid actions
            reward = Reward(
                score=-0.1,
                feedback=validation_error,
                is_terminal=False
            )
            observation = self._build_observation(error_message=validation_error)
            return observation, reward, False, {}
        
        # Increment action count (only for valid actions)
        self._state.action_count += 1
        
        # Check action limit (terminate at 50, not after 50)
        if self._state.action_count > self._current_task.max_actions:
            # Action limit exceeded - terminate episode
            self._done = True
            reward = self.reward_function.compute_terminal_reward(
                decision="approve",  # Dummy decision
                identified_issues=list(self._state.identified_issues),
                ground_truth=self._ground_truth,
                action_limit_exceeded=True
            )
            observation = self._build_observation()
            
            # Compute grader score
            grader_result = self.grader.grade_episode(
                agent_comments=self._state.review_comments,
                agent_decision="approve",  # Dummy decision
                ground_truth=self._ground_truth
            )
            
            info = {
                "grader_score": grader_result.final_score,
                "grader_feedback": grader_result.feedback,
                "action_limit_exceeded": True
            }
            
            return observation, reward, self._done, info
        
        # Process action
        self._process_action(action)
        
        # Compute reward
        reward = self.reward_function.compute_reward(
            action=action,
            state=self._state,
            ground_truth=self._ground_truth
        )
        
        # Check if terminal
        if reward.is_terminal:
            self._done = True
            
            # Compute final grader score
            grader_result = self.grader.grade_episode(
                agent_comments=self._state.review_comments,
                agent_decision=self._state.review_status,
                ground_truth=self._ground_truth
            )
            
            info = {
                "grader_score": grader_result.final_score,
                "grader_feedback": grader_result.feedback,
                "grader_metrics": {
                    "precision": grader_result.issue_detection_metrics.precision,
                    "recall": grader_result.issue_detection_metrics.recall,
                    "f1_score": grader_result.issue_detection_metrics.f1_score,
                    "comment_quality": grader_result.comment_quality_score,
                    "decision_correct": grader_result.decision_correct,
                    "false_positives": grader_result.false_positive_count,
                }
            }
        else:
            info = {}
        
        # Build observation
        observation = self._build_observation()
        
        return observation, reward, self._done, info
    
    def state(self) -> dict:
        """
        Return serializable environment state.
        
        Returns a dictionary containing all relevant state information that can
        be serialized to JSON. This allows for state persistence and debugging.
        
        Returns:
            Dict containing current PR state, comments, and metadata
            
        Example:
            >>> env = CodeReviewEnvironment()
            >>> env.reset("easy")
            >>> state_dict = env.state()
            >>> print(state_dict.keys())
            dict_keys(['task_id', 'pull_request_id', 'action_count', ...])
        """
        if self._current_task is None or self._state is None:
            return {
                "initialized": False,
                "message": "Environment not initialized. Call reset() first."
            }
        
        return {
            "initialized": True,
            "task_id": self._current_task.task_id,
            "difficulty": self._current_task.difficulty,
            "pull_request_id": self._current_task.pull_request.pr_id,
            "action_count": self._state.action_count,
            "max_actions": self._current_task.max_actions,
            "review_status": self._state.review_status,
            "done": self._done,
            "files_changed": list(self._current_task.pull_request.files.keys()),
            "review_comments": [
                {
                    "file_path": comment.file_path,
                    "line_number": comment.line_number,
                    "comment_text": comment.comment_text,
                    "timestamp": comment.timestamp
                }
                for comment in self._state.review_comments
            ],
            "identified_issues": list(self._state.identified_issues),
            "viewed_files": list(self._last_viewed_files.keys())
        }
    
    def _validate_action(self, action: Action) -> str | None:
        """
        Validate action against current environment state.
        
        Checks:
        - File existence for file-related actions
        - Line number validity for line-specific comments
        
        Args:
            action: The action to validate
            
        Returns:
            Error message if validation fails, None if valid
        """
        if self._current_task is None:
            return "Environment not initialized"
        
        # Validate file existence for file-related actions
        if action.action_type in ["add_comment", "view_file"]:
            if action.target_file is None:
                return f"{action.action_type} requires target_file parameter"
            
            if action.target_file not in self._current_task.pull_request.files:
                available_files = list(self._current_task.pull_request.files.keys())
                return (
                    f"File '{action.target_file}' not found in pull request. "
                    f"Available files: {', '.join(available_files)}"
                )
        
        # Validate line number for line-specific comments
        if action.action_type == "add_comment" and action.line_number is not None:
            if action.target_file:
                file_content = self._current_task.pull_request.files[action.target_file].content
                line_count = len(file_content.split('\n'))
                
                if action.line_number < 1 or action.line_number > line_count:
                    return (
                        f"Invalid line number {action.line_number} for file '{action.target_file}'. "
                        f"File has {line_count} lines."
                    )
        
        return None
    
    def _process_action(self, action: Action) -> None:
        """
        Process action and update environment state.
        
        Args:
            action: The action to process
        """
        if self._state is None or self._current_task is None:
            return
        
        if action.action_type == "add_comment":
            # Add comment to review
            comment = ReviewComment(
                file_path=action.target_file or "",
                line_number=action.line_number,
                comment_text=action.comment_text or "",
                timestamp=self._state.action_count
            )
            self._state.review_comments.append(comment)
        
        elif action.action_type == "view_file":
            # Store file content for next observation
            if action.target_file:
                file_content = self._current_task.pull_request.files[action.target_file].content
                self._last_viewed_files[action.target_file] = file_content
        
        elif action.action_type == "approve":
            # Set terminal status
            self._state.review_status = "approved"
        
        elif action.action_type == "request_changes":
            # Set terminal status
            self._state.review_status = "changes_requested"
    
    def _build_observation(self, error_message: str | None = None) -> Observation:
        """
        Build observation from current state.
        
        Args:
            error_message: Optional error message to include in observation
            
        Returns:
            Observation with current state
        """
        if self._current_task is None or self._state is None:
            # Return minimal observation for uninitialized state
            return Observation(
                pull_request_id="",
                files_changed=[],
                diff_content={},
                existing_comments=[],
                review_status="in_progress",
                action_count=0,
                error_message="Environment not initialized"
            )
        
        pr = self._current_task.pull_request
        
        # Include viewed files if any
        full_file_content = self._last_viewed_files if self._last_viewed_files else None
        
        # Clear viewed files after including in observation
        self._last_viewed_files = {}
        
        return Observation(
            pull_request_id=pr.pr_id,
            files_changed=list(pr.files.keys()),
            diff_content=pr.diffs,
            existing_comments=self._state.review_comments.copy(),
            review_status=self._state.review_status,
            action_count=self._state.action_count,
            full_file_content=full_file_content,
            error_message=error_message
        )

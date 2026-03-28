"""Core Pydantic models for the Code Review Assistant OpenEnv environment."""

from typing import Literal
from pydantic import BaseModel, model_validator


class ReviewComment(BaseModel):
    """A single review comment on code."""
    
    file_path: str
    line_number: int | None = None  # None for file-level comments
    comment_text: str
    timestamp: int  # action number when added


class Observation(BaseModel):
    """Agent's view of the current environment state."""
    
    pull_request_id: str
    files_changed: list[str]
    diff_content: dict[str, str]  # file_path -> unified diff
    existing_comments: list[ReviewComment]
    review_status: Literal["in_progress", "approved", "changes_requested"]
    action_count: int
    full_file_content: dict[str, str] | None = None  # populated by view_file action
    error_message: str | None = None


class Action(BaseModel):
    """Agent's action in the environment."""
    
    action_type: Literal["add_comment", "request_changes", "approve", "view_file"]
    target_file: str | None = None
    line_number: int | None = None
    comment_text: str | None = None
    
    @model_validator(mode='after')
    def validate_action_parameters(self):
        """Ensure required parameters are present for each action type."""
        if self.action_type == "add_comment":
            if not self.target_file or not self.comment_text:
                raise ValueError("add_comment requires target_file and comment_text")
        elif self.action_type == "view_file":
            if not self.target_file:
                raise ValueError("view_file requires target_file")
        return self


class Reward(BaseModel):
    """Reward signal returned to agent."""
    
    score: float
    feedback: str
    is_terminal: bool


class FileContent(BaseModel):
    """File content with metadata."""
    
    path: str
    content: str
    language: str


class PullRequest(BaseModel):
    """Pull request data."""
    
    pr_id: str
    title: str
    description: str
    files: dict[str, FileContent]  # path -> content
    diffs: dict[str, str]  # path -> unified diff


class Issue(BaseModel):
    """A code issue annotation."""
    
    issue_id: str
    file_path: str
    line_number: int | None
    issue_type: Literal["bug", "security", "style", "performance"]
    severity: Literal["critical", "major", "minor"]
    description: str


class GroundTruth(BaseModel):
    """Ground truth annotations for grading."""
    
    issues: list[Issue]
    correct_decision: Literal["approve", "request_changes"]
    severity_threshold: str  # minimum severity requiring changes


class Task(BaseModel):
    """A code review task definition."""
    
    task_id: str
    difficulty: Literal["easy", "medium", "hard"]
    pull_request: PullRequest
    max_actions: int = 50


class IssueMetrics(BaseModel):
    """Issue detection metrics."""
    
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1_score: float
    critical_issues_found: int
    critical_issues_total: int


class GraderResult(BaseModel):
    """Grading results."""
    
    final_score: float  # 0.0 to 1.0
    issue_detection_metrics: IssueMetrics
    comment_quality_score: float
    decision_correct: bool
    false_positive_count: int
    feedback: str

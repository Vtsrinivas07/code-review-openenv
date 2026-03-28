"""Unit tests for TaskManager class."""

import json
import pytest
from pathlib import Path
from src.tasks import TaskManager, TaskLoadError
from src.models import Task, GroundTruth


def test_task_manager_initialization():
    """Test TaskManager can be initialized."""
    manager = TaskManager()
    assert manager.tasks_dir == Path("tasks")


def test_task_manager_custom_directory():
    """Test TaskManager with custom directory."""
    manager = TaskManager(tasks_dir="custom_tasks")
    assert manager.tasks_dir == Path("custom_tasks")


def test_list_tasks():
    """Test that list_tasks returns expected task IDs."""
    manager = TaskManager()
    tasks = manager.list_tasks()
    assert tasks == ["easy", "medium", "hard"]


def test_load_task_invalid_id():
    """Test that loading invalid task_id raises TaskLoadError."""
    manager = TaskManager()
    with pytest.raises(TaskLoadError) as exc_info:
        manager.load_task("invalid")
    assert "Invalid task_id 'invalid'" in str(exc_info.value)
    assert "easy, medium, hard" in str(exc_info.value)


def test_load_task_missing_file():
    """Test that loading from missing file raises TaskLoadError."""
    manager = TaskManager()
    with pytest.raises(TaskLoadError) as exc_info:
        manager.load_task("easy")
    assert "Task file not found" in str(exc_info.value)


def test_get_ground_truth_invalid_id():
    """Test that getting ground truth with invalid task_id raises TaskLoadError."""
    manager = TaskManager()
    with pytest.raises(TaskLoadError) as exc_info:
        manager.get_ground_truth("invalid")
    assert "Invalid task_id 'invalid'" in str(exc_info.value)


def test_get_ground_truth_missing_file():
    """Test that getting ground truth from missing file raises TaskLoadError."""
    manager = TaskManager()
    with pytest.raises(TaskLoadError) as exc_info:
        manager.get_ground_truth("easy")
    assert "Task file not found" in str(exc_info.value)


def test_clear_cache():
    """Test that clear_cache clears internal caches."""
    manager = TaskManager()
    # Manually populate cache
    manager._task_cache["test"] = None
    manager._ground_truth_cache["test"] = None
    
    manager.clear_cache()
    
    assert len(manager._task_cache) == 0
    assert len(manager._ground_truth_cache) == 0


def test_load_task_with_valid_data(tmp_path):
    """Test loading a valid task file."""
    # Create a temporary task file
    task_data = {
        "task_id": "easy",
        "difficulty": "easy",
        "pull_request": {
            "pr_id": "PR-001",
            "title": "Test PR",
            "description": "Test description",
            "files": {
                "test.py": {
                    "path": "test.py",
                    "content": "print('hello')",
                    "language": "python"
                }
            },
            "diffs": {
                "test.py": "+print('hello')"
            }
        },
        "max_actions": 50,
        "ground_truth": {
            "issues": [],
            "correct_decision": "approve",
            "severity_threshold": "major"
        }
    }
    
    task_file = tmp_path / "easy.json"
    with open(task_file, 'w') as f:
        json.dump(task_data, f)
    
    # Load the task
    manager = TaskManager(tasks_dir=str(tmp_path))
    task = manager.load_task("easy")
    
    assert task.task_id == "easy"
    assert task.difficulty == "easy"
    assert task.pull_request.pr_id == "PR-001"


def test_load_task_caching(tmp_path):
    """Test that tasks are cached after first load."""
    # Create a temporary task file
    task_data = {
        "task_id": "easy",
        "difficulty": "easy",
        "pull_request": {
            "pr_id": "PR-001",
            "title": "Test PR",
            "description": "Test description",
            "files": {},
            "diffs": {}
        },
        "ground_truth": {
            "issues": [],
            "correct_decision": "approve",
            "severity_threshold": "major"
        }
    }
    
    task_file = tmp_path / "easy.json"
    with open(task_file, 'w') as f:
        json.dump(task_data, f)
    
    manager = TaskManager(tasks_dir=str(tmp_path))
    
    # Load task twice
    task1 = manager.load_task("easy")
    task2 = manager.load_task("easy")
    
    # Should be the same object (cached)
    assert task1 is task2


def test_get_ground_truth_with_valid_data(tmp_path):
    """Test getting ground truth from a valid task file."""
    task_data = {
        "task_id": "easy",
        "difficulty": "easy",
        "pull_request": {
            "pr_id": "PR-001",
            "title": "Test PR",
            "description": "Test description",
            "files": {},
            "diffs": {}
        },
        "ground_truth": {
            "issues": [
                {
                    "issue_id": "ISS-001",
                    "file_path": "test.py",
                    "line_number": 10,
                    "issue_type": "bug",
                    "severity": "major",
                    "description": "Test issue"
                }
            ],
            "correct_decision": "request_changes",
            "severity_threshold": "major"
        }
    }
    
    task_file = tmp_path / "easy.json"
    with open(task_file, 'w') as f:
        json.dump(task_data, f)
    
    manager = TaskManager(tasks_dir=str(tmp_path))
    ground_truth = manager.get_ground_truth("easy")
    
    assert len(ground_truth.issues) == 1
    assert ground_truth.issues[0].issue_id == "ISS-001"
    assert ground_truth.correct_decision == "request_changes"


def test_get_ground_truth_missing_field(tmp_path):
    """Test that missing ground_truth field raises TaskLoadError."""
    task_data = {
        "task_id": "easy",
        "difficulty": "easy",
        "pull_request": {
            "pr_id": "PR-001",
            "title": "Test PR",
            "description": "Test description",
            "files": {},
            "diffs": {}
        }
        # Missing ground_truth field
    }
    
    task_file = tmp_path / "easy.json"
    with open(task_file, 'w') as f:
        json.dump(task_data, f)
    
    manager = TaskManager(tasks_dir=str(tmp_path))
    with pytest.raises(TaskLoadError) as exc_info:
        manager.get_ground_truth("easy")
    assert "missing 'ground_truth' field" in str(exc_info.value)


def test_load_task_invalid_json(tmp_path):
    """Test that invalid JSON raises TaskLoadError."""
    task_file = tmp_path / "easy.json"
    with open(task_file, 'w') as f:
        f.write("{ invalid json }")
    
    manager = TaskManager(tasks_dir=str(tmp_path))
    with pytest.raises(TaskLoadError) as exc_info:
        manager.load_task("easy")
    assert "Invalid JSON" in str(exc_info.value)


def test_load_task_invalid_model_data(tmp_path):
    """Test that invalid model data raises TaskLoadError."""
    task_data = {
        "task_id": "easy",
        "difficulty": "invalid_difficulty",  # Invalid enum value
        "pull_request": {
            "pr_id": "PR-001",
            "title": "Test PR",
            "description": "Test description",
            "files": {},
            "diffs": {}
        }
    }
    
    task_file = tmp_path / "easy.json"
    with open(task_file, 'w') as f:
        json.dump(task_data, f)
    
    manager = TaskManager(tasks_dir=str(tmp_path))
    with pytest.raises(TaskLoadError) as exc_info:
        manager.load_task("easy")
    assert "Invalid task data" in str(exc_info.value)


# Task 2.6: Unit tests for task definitions
# Requirements: 2.1, 2.2, 2.3, 2.4

def test_exactly_three_tasks_exist():
    """Test that exactly three tasks exist with correct IDs."""
    manager = TaskManager()
    tasks = manager.list_tasks()
    
    assert len(tasks) == 3, "Should have exactly 3 tasks"
    assert set(tasks) == {"easy", "medium", "hard"}, "Tasks should be easy, medium, and hard"


def test_easy_task_file_and_issue_counts():
    """Test that easy task has 1-2 files and 2-3 issues."""
    manager = TaskManager()
    task = manager.load_task("easy")
    ground_truth = manager.get_ground_truth("easy")
    
    # Check file count (1-2 files)
    file_count = len(task.pull_request.files)
    assert 1 <= file_count <= 2, f"Easy task should have 1-2 files, got {file_count}"
    
    # Check issue count (2-3 issues)
    issue_count = len(ground_truth.issues)
    assert 2 <= issue_count <= 3, f"Easy task should have 2-3 issues, got {issue_count}"
    
    # Verify task metadata
    assert task.task_id == "easy"
    assert task.difficulty == "easy"


def test_medium_task_file_and_issue_counts():
    """Test that medium task has 3-4 files and 4-6 issues."""
    manager = TaskManager()
    task = manager.load_task("medium")
    ground_truth = manager.get_ground_truth("medium")
    
    # Check file count (3-4 files)
    file_count = len(task.pull_request.files)
    assert 3 <= file_count <= 4, f"Medium task should have 3-4 files, got {file_count}"
    
    # Check issue count (4-6 issues)
    issue_count = len(ground_truth.issues)
    assert 4 <= issue_count <= 6, f"Medium task should have 4-6 issues, got {issue_count}"
    
    # Verify task metadata
    assert task.task_id == "medium"
    assert task.difficulty == "medium"


def test_hard_task_file_and_issue_counts():
    """Test that hard task has 5+ files and 7+ issues."""
    manager = TaskManager()
    task = manager.load_task("hard")
    ground_truth = manager.get_ground_truth("hard")
    
    # Check file count (5+ files)
    file_count = len(task.pull_request.files)
    assert file_count >= 5, f"Hard task should have 5+ files, got {file_count}"
    
    # Check issue count (7+ issues)
    issue_count = len(ground_truth.issues)
    assert issue_count >= 7, f"Hard task should have 7+ issues, got {issue_count}"
    
    # Verify task metadata
    assert task.task_id == "hard"
    assert task.difficulty == "hard"


def test_task_loading_works_correctly():
    """Test that all tasks can be loaded successfully."""
    manager = TaskManager()
    
    # Load each task and verify basic structure
    for task_id in ["easy", "medium", "hard"]:
        task = manager.load_task(task_id)
        
        # Verify task has required fields
        assert task.task_id == task_id
        assert task.difficulty in ["easy", "medium", "hard"]
        assert task.pull_request is not None
        assert task.pull_request.pr_id is not None
        assert task.pull_request.title is not None
        assert task.pull_request.description is not None
        assert isinstance(task.pull_request.files, dict)
        assert isinstance(task.pull_request.diffs, dict)
        assert len(task.pull_request.files) > 0, f"Task {task_id} should have at least one file"
        assert task.max_actions == 50


def test_ground_truth_retrieval_works_correctly():
    """Test that ground truth can be retrieved for all tasks."""
    manager = TaskManager()
    
    # Retrieve ground truth for each task
    for task_id in ["easy", "medium", "hard"]:
        ground_truth = manager.get_ground_truth(task_id)
        
        # Verify ground truth has required fields
        assert isinstance(ground_truth.issues, list)
        assert len(ground_truth.issues) > 0, f"Task {task_id} should have at least one issue"
        assert ground_truth.correct_decision in ["approve", "request_changes"]
        assert ground_truth.severity_threshold in ["critical", "major", "minor"]
        
        # Verify each issue has required fields
        for issue in ground_truth.issues:
            assert issue.issue_id is not None
            assert issue.file_path is not None
            assert issue.issue_type in ["bug", "security", "style", "performance"]
            assert issue.severity in ["critical", "major", "minor"]
            assert issue.description is not None


def test_task_files_have_content():
    """Test that all task files have actual content."""
    manager = TaskManager()
    
    for task_id in ["easy", "medium", "hard"]:
        task = manager.load_task(task_id)
        
        # Verify each file has content
        for file_path, file_content in task.pull_request.files.items():
            assert file_content.path == file_path
            assert len(file_content.content) > 0, f"File {file_path} in {task_id} should have content"
            assert file_content.language is not None
        
        # Verify each file has a diff
        for file_path in task.pull_request.files.keys():
            assert file_path in task.pull_request.diffs, f"File {file_path} should have a diff"
            assert len(task.pull_request.diffs[file_path]) > 0


def test_issues_reference_valid_files():
    """Test that all issues reference files that exist in the pull request."""
    manager = TaskManager()
    
    for task_id in ["easy", "medium", "hard"]:
        task = manager.load_task(task_id)
        ground_truth = manager.get_ground_truth(task_id)
        
        file_paths = set(task.pull_request.files.keys())
        
        for issue in ground_truth.issues:
            assert issue.file_path in file_paths, \
                f"Issue {issue.issue_id} references non-existent file {issue.file_path}"

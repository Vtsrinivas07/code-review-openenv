"""Task management for the Code Review Assistant OpenEnv environment."""

import json
from pathlib import Path
from typing import Literal

from src.models import Task, GroundTruth


class TaskLoadError(Exception):
    """Exception raised when task loading fails."""
    pass


class TaskManager:
    """Manages task definitions and ground truth data.
    
    Tasks are stored as JSON files in the tasks/ directory:
    - tasks/easy.json
    - tasks/medium.json
    - tasks/hard.json
    
    Each task file contains the complete task definition including
    pull request data, file contents, diffs, and ground truth annotations.
    """
    
    def __init__(self, tasks_dir: str = "tasks"):
        """Initialize the TaskManager.
        
        Args:
            tasks_dir: Directory containing task JSON files (default: "tasks")
        """
        self.tasks_dir = Path(tasks_dir)
        self._task_cache: dict[str, Task] = {}
        self._ground_truth_cache: dict[str, GroundTruth] = {}
    
    def load_task(self, task_id: str) -> Task:
        """Load a task definition by ID.
        
        Args:
            task_id: Task identifier (easy, medium, or hard)
            
        Returns:
            Task model instance with pull request data and metadata
            
        Raises:
            TaskLoadError: If task file is missing, invalid, or cannot be parsed
        """
        # Check cache first
        if task_id in self._task_cache:
            return self._task_cache[task_id]
        
        # Validate task_id
        valid_task_ids = ["easy", "medium", "hard"]
        if task_id not in valid_task_ids:
            raise TaskLoadError(
                f"Invalid task_id '{task_id}'. Valid task IDs are: {', '.join(valid_task_ids)}"
            )
        
        # Construct file path
        task_file = self.tasks_dir / f"{task_id}.json"
        
        # Check if file exists
        if not task_file.exists():
            raise TaskLoadError(
                f"Task file not found: {task_file}. "
                f"Expected task file for '{task_id}' at this location."
            )
        
        # Load and parse JSON
        try:
            with open(task_file, 'r', encoding='utf-8') as f:
                task_data = json.load(f)
        except json.JSONDecodeError as e:
            raise TaskLoadError(
                f"Invalid JSON in task file {task_file}: {e}"
            )
        except IOError as e:
            raise TaskLoadError(
                f"Error reading task file {task_file}: {e}"
            )
        
        # Validate and create Task model
        try:
            task = Task(**task_data)
        except Exception as e:
            raise TaskLoadError(
                f"Invalid task data in {task_file}: {e}"
            )
        
        # Cache the task
        self._task_cache[task_id] = task
        
        return task
    
    def get_ground_truth(self, task_id: str) -> GroundTruth:
        """Get ground truth annotations for a task.
        
        Ground truth includes:
        - List of issues with locations, types, and severity
        - Correct approval decision (approve or request_changes)
        - Severity threshold for decision-making
        
        Args:
            task_id: Task identifier (easy, medium, or hard)
            
        Returns:
            GroundTruth model instance with issue annotations
            
        Raises:
            TaskLoadError: If task file is missing, invalid, or lacks ground truth data
        """
        # Check cache first
        if task_id in self._ground_truth_cache:
            return self._ground_truth_cache[task_id]
        
        # Validate task_id
        valid_task_ids = ["easy", "medium", "hard"]
        if task_id not in valid_task_ids:
            raise TaskLoadError(
                f"Invalid task_id '{task_id}'. Valid task IDs are: {', '.join(valid_task_ids)}"
            )
        
        # Construct file path
        task_file = self.tasks_dir / f"{task_id}.json"
        
        # Check if file exists
        if not task_file.exists():
            raise TaskLoadError(
                f"Task file not found: {task_file}. "
                f"Expected task file for '{task_id}' at this location."
            )
        
        # Load and parse JSON
        try:
            with open(task_file, 'r', encoding='utf-8') as f:
                task_data = json.load(f)
        except json.JSONDecodeError as e:
            raise TaskLoadError(
                f"Invalid JSON in task file {task_file}: {e}"
            )
        except IOError as e:
            raise TaskLoadError(
                f"Error reading task file {task_file}: {e}"
            )
        
        # Extract ground truth data
        if "ground_truth" not in task_data:
            raise TaskLoadError(
                f"Task file {task_file} missing 'ground_truth' field"
            )
        
        # Validate and create GroundTruth model
        try:
            ground_truth = GroundTruth(**task_data["ground_truth"])
        except Exception as e:
            raise TaskLoadError(
                f"Invalid ground truth data in {task_file}: {e}"
            )
        
        # Cache the ground truth
        self._ground_truth_cache[task_id] = ground_truth
        
        return ground_truth
    
    def list_tasks(self) -> list[str]:
        """List all available task IDs.
        
        Returns:
            List of task identifiers
        """
        return ["easy", "medium", "hard"]
    
    def clear_cache(self) -> None:
        """Clear the internal task and ground truth caches.
        
        Useful for testing or when task files are modified at runtime.
        """
        self._task_cache.clear()
        self._ground_truth_cache.clear()

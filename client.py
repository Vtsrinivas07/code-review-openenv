"""Client for interacting with the Code Review Assistant environment."""

import requests
from typing import Optional, Dict, Any
from src.models import Action, Observation, Reward


class CodeReviewClient:
    """Client for making requests to the Code Review Assistant environment."""
    
    def __init__(self, base_url: str = "http://localhost:7860"):
        """Initialize the client.
        
        Args:
            base_url: Base URL of the environment server
        """
        self.base_url = base_url.rstrip('/')
    
    def reset(self, task_id: Optional[str] = None) -> Dict[str, Any]:
        """Reset the environment.
        
        Args:
            task_id: Optional task ID (easy, medium, hard)
            
        Returns:
            Dictionary with observation and info
        """
        url = f"{self.base_url}/reset"
        data = {"task_id": task_id} if task_id else {}
        response = requests.post(url, json=data)
        response.raise_for_status()
        return response.json()
    
    def step(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an action in the environment.
        
        Args:
            action: Action dictionary with action_type and parameters
            
        Returns:
            Dictionary with observation, reward, done, and info
        """
        url = f"{self.base_url}/step"
        response = requests.post(url, json=action)
        response.raise_for_status()
        return response.json()
    
    def health(self) -> Dict[str, str]:
        """Check server health.
        
        Returns:
            Health status dictionary
        """
        url = f"{self.base_url}/health"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    
    def info(self) -> Dict[str, Any]:
        """Get environment information.
        
        Returns:
            Environment metadata
        """
        url = f"{self.base_url}/info"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()


if __name__ == "__main__":
    # Example usage
    client = CodeReviewClient()
    
    # Check health
    print("Health:", client.health())
    
    # Get info
    print("Info:", client.info())
    
    # Reset environment
    result = client.reset(task_id="easy")
    print("Reset successful!")
    print(f"PR ID: {result['observation']['pull_request_id']}")
    print(f"Files changed: {result['observation']['files_changed']}")

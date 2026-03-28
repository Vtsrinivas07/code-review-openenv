"""Integration tests for deployment artifacts and end-to-end workflows."""

import os
import json
import subprocess
from pathlib import Path

import pytest
from src.environment import CodeReviewEnvironment
from src.models import Action


class TestDeploymentArtifacts:
    """Test deployment artifacts exist and are valid."""
    
    def test_dockerfile_exists(self):
        """Test that Dockerfile exists."""
        assert Path("Dockerfile").exists(), "Dockerfile not found"
    
    def test_readme_exists(self):
        """Test that README.md exists."""
        assert Path("README.md").exists(), "README.md not found"
    
    def test_openenv_yaml_exists(self):
        """Test that openenv.yaml exists."""
        assert Path("openenv.yaml").exists(), "openenv.yaml not found"
    
    def test_inference_script_exists(self):
        """Test that inference.py exists."""
        assert Path("inference.py").exists(), "inference.py not found"
    
    def test_requirements_txt_exists(self):
        """Test that requirements.txt exists."""
        assert Path("requirements.txt").exists(), "requirements.txt not found"


class TestREADMEContent:
    """Test README.md contains required documentation."""
    
    def test_readme_has_environment_description(self):
        """Test README contains environment description."""
        with open("README.md") as f:
            content = f.read()
        
        assert "Code Review Assistant" in content
        assert "OpenEnv" in content
        assert "environment" in content.lower()
    
    def test_readme_has_action_space_documentation(self):
        """Test README documents action space."""
        with open("README.md") as f:
            content = f.read()
        
        assert "Action Space" in content
        assert "add_comment" in content
        assert "view_file" in content
        assert "approve" in content
        assert "request_changes" in content
    
    def test_readme_has_observation_space_documentation(self):
        """Test README documents observation space."""
        with open("README.md") as f:
            content = f.read()
        
        assert "Observation Space" in content
        assert "pull_request_id" in content
        assert "files_changed" in content
        assert "diff_content" in content
    
    def test_readme_has_setup_instructions(self):
        """Test README includes setup instructions."""
        with open("README.md") as f:
            content = f.read()
        
        assert "Setup" in content or "Installation" in content
        assert "pip install" in content
        assert "requirements.txt" in content
    
    def test_readme_has_usage_example(self):
        """Test README includes usage example."""
        with open("README.md") as f:
            content = f.read()
        
        assert "Usage" in content or "Example" in content
        assert "inference.py" in content
    
    def test_readme_has_real_world_relevance(self):
        """Test README explains real-world relevance."""
        with open("README.md") as f:
            content = f.read()
        
        # Should mention practical applications
        assert any(keyword in content.lower() for keyword in [
            "real-world", "practical", "production", "industry", "application"
        ])


class TestOpenEnvYAML:
    """Test openenv.yaml structure and content."""
    
    def test_openenv_yaml_is_valid(self):
        """Test openenv.yaml can be parsed."""
        import yaml
        
        with open("openenv.yaml") as f:
            config = yaml.safe_load(f)
        
        assert config is not None
        assert isinstance(config, dict)
    
    def test_openenv_yaml_has_required_fields(self):
        """Test openenv.yaml contains required metadata."""
        import yaml
        
        with open("openenv.yaml") as f:
            config = yaml.safe_load(f)
        
        assert "name" in config
        assert "version" in config
        assert "description" in config
        assert "action_space" in config
        assert "observation_space" in config
        assert "tasks" in config
    
    def test_openenv_yaml_defines_three_tasks(self):
        """Test openenv.yaml defines easy, medium, hard tasks."""
        import yaml
        
        with open("openenv.yaml") as f:
            config = yaml.safe_load(f)
        
        tasks = config["tasks"]
        assert len(tasks) == 3
        
        task_ids = [task["id"] for task in tasks]
        assert "easy" in task_ids
        assert "medium" in task_ids
        assert "hard" in task_ids


class TestEndToEndWorkflow:
    """Test complete end-to-end workflows."""
    
    def test_environment_can_run_complete_episode(self):
        """Test environment can run a complete episode from start to finish."""
        env = CodeReviewEnvironment()
        
        # Reset environment
        obs = env.reset("easy")
        assert obs.review_status == "in_progress"
        assert obs.action_count == 0
        
        # Take a few actions
        action1 = Action(action_type="view_file", target_file=obs.files_changed[0])
        obs, reward, done, info = env.step(action1)
        assert not done
        assert obs.action_count == 1
        
        action2 = Action(
            action_type="add_comment",
            target_file=obs.files_changed[0],
            comment_text="This looks good."
        )
        obs, reward, done, info = env.step(action2)
        assert not done
        assert len(obs.existing_comments) == 1
        
        # Make final decision
        action3 = Action(action_type="approve")
        obs, reward, done, info = env.step(action3)
        assert done
        assert "grader_score" in info
        assert 0.0 <= info["grader_score"] <= 1.0
    
    def test_environment_handles_all_three_tasks(self):
        """Test environment can run all three difficulty levels."""
        env = CodeReviewEnvironment()
        
        for task_id in ["easy", "medium", "hard"]:
            obs = env.reset(task_id)
            assert obs.pull_request_id is not None
            assert len(obs.files_changed) > 0
            
            # Make a simple decision
            action = Action(action_type="approve")
            obs, reward, done, info = env.step(action)
            assert done
            assert "grader_score" in info
    
    def test_environment_enforces_action_limit(self):
        """Test environment terminates after exceeding max actions."""
        env = CodeReviewEnvironment()
        obs = env.reset("easy")
        
        # Take 51 actions (max is 50, so 51st should terminate)
        for i in range(51):
            action = Action(action_type="view_file", target_file=obs.files_changed[0])
            obs, reward, done, info = env.step(action)
            
            if i < 50:
                assert not done, f"Episode ended early at action {i+1}"
            else:
                assert done, "Episode did not end after exceeding action limit"
                assert reward.score == -0.5, "Action limit penalty not applied"
    
    def test_state_serialization_round_trip(self):
        """Test environment state can be serialized and is valid."""
        env = CodeReviewEnvironment()
        obs = env.reset("easy")
        
        # Take some actions
        action = Action(
            action_type="add_comment",
            target_file=obs.files_changed[0],
            comment_text="Test comment"
        )
        env.step(action)
        
        # Get state
        state = env.state()
        
        # Verify state is serializable
        json_state = json.dumps(state)
        assert json_state is not None
        
        # Verify state contains expected keys
        assert "task_id" in state
        assert "action_count" in state
        assert "review_status" in state
        assert "review_comments" in state


class TestDockerConfiguration:
    """Test Docker configuration."""
    
    def test_dockerfile_has_python_base(self):
        """Test Dockerfile uses Python base image."""
        with open("Dockerfile") as f:
            content = f.read()
        
        assert "FROM python" in content
    
    def test_dockerfile_installs_requirements(self):
        """Test Dockerfile installs requirements."""
        with open("Dockerfile") as f:
            content = f.read()
        
        assert "requirements.txt" in content
        assert "pip install" in content
    
    def test_dockerfile_copies_source_code(self):
        """Test Dockerfile copies necessary files."""
        with open("Dockerfile") as f:
            content = f.read()
        
        assert "COPY src/" in content or "COPY . " in content
        assert "COPY tasks/" in content or "COPY . " in content
    
    def test_dockerfile_has_entrypoint(self):
        """Test Dockerfile defines how to run the environment."""
        with open("Dockerfile") as f:
            content = f.read()
        
        # Should have CMD or ENTRYPOINT
        assert "CMD" in content or "ENTRYPOINT" in content


class TestInferenceScript:
    """Test baseline inference script structure."""
    
    def test_inference_script_is_valid_python(self):
        """Test inference.py is valid Python syntax."""
        with open("inference.py") as f:
            code = f.read()
        
        # Try to compile it
        compile(code, "inference.py", "exec")
    
    def test_inference_script_has_main_function(self):
        """Test inference.py has a main function."""
        with open("inference.py") as f:
            content = f.read()
        
        assert "def main(" in content
        assert 'if __name__ == "__main__"' in content
    
    def test_inference_script_uses_openai(self):
        """Test inference.py uses OpenAI API."""
        with open("inference.py") as f:
            content = f.read()
        
        assert "openai" in content.lower()
        assert "OpenAI" in content or "openai" in content
    
    def test_inference_script_has_baseline_agent(self):
        """Test inference.py defines BaselineAgent class."""
        with open("inference.py") as f:
            content = f.read()
        
        assert "class BaselineAgent" in content
        assert "def run_episode" in content
        assert "def select_action" in content
    
    def test_inference_script_handles_environment_variables(self):
        """Test inference.py reads configuration from environment."""
        with open("inference.py") as f:
            content = f.read()
        
        assert "os.getenv" in content or "os.environ" in content
        # Should read API_BASE_URL, MODEL_NAME, and token
        assert "API_BASE_URL" in content or "api_base" in content.lower()
        assert "MODEL_NAME" in content or "model" in content.lower()
        assert "HF_TOKEN" in content or "OPENAI_API_KEY" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

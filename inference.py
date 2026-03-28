"""Baseline inference script for Code Review Assistant OpenEnv environment.

This script implements a simple baseline agent using the OpenAI API to perform
code review tasks. It demonstrates how to interact with the environment and
provides a reference implementation for competition participants.
"""

import os
import json
import re
from typing import Any
from openai import OpenAI

from src.environment import CodeReviewEnvironment
from src.models import Action, Observation


class BaselineAgent:
    """Simple baseline agent using OpenAI API for code review."""
    
    def __init__(self, api_base: str, model: str, token: str):
        """Initialize the baseline agent.
        
        Args:
            api_base: Base URL for OpenAI API
            model: Model name to use
            token: API authentication token
        """
        try:
            self.client = OpenAI(base_url=api_base, api_key=token)
        except TypeError:
            # Fallback for older OpenAI client versions
            self.client = OpenAI(api_key=token)
        self.model = model
        self.conversation_history: list[dict[str, str]] = []
        
    def run_episode(self, env: CodeReviewEnvironment, task_id: str) -> float:
        """Run one episode and return final score.
        
        Args:
            env: The code review environment
            task_id: Task identifier (easy, medium, hard)
            
        Returns:
            Final grader score for the episode
        """
        print(f"\n{'='*60}")
        print(f"Starting task: {task_id}")
        print(f"{'='*60}")
        
        # Reset environment and conversation history
        obs = env.reset(task_id)
        self.conversation_history = []
        done = False
        total_reward = 0.0
        step_count = 0
        
        # Episode loop
        while not done:
            step_count += 1
            print(f"\n--- Step {step_count} ---")
            
            # Select action using LLM
            try:
                action = self.select_action(obs)
                print(f"Action: {action.action_type}")
                if action.target_file:
                    print(f"  Target: {action.target_file}")
                if action.comment_text:
                    print(f"  Comment: {action.comment_text[:100]}...")
            except Exception as e:
                print(f"Error selecting action: {e}")
                # Fallback to approve if we can't parse action
                action = Action(action_type="approve")
            
            # Execute action
            obs, reward, done, info = env.step(action)
            total_reward += reward.score
            
            print(f"Reward: {reward.score:.3f} - {reward.feedback}")
            
            if done:
                final_score = info.get("grader_score", 0.0)
                print(f"\n{'='*60}")
                print(f"Episode complete!")
                print(f"Total reward: {total_reward:.3f}")
                print(f"Final grader score: {final_score:.3f}")
                print(f"{'='*60}")
                return final_score
        
        return 0.0
    
    def select_action(self, obs: Observation) -> Action:
        """Use LLM to select next action based on observation.
        
        Args:
            obs: Current observation from environment
            
        Returns:
            Action to execute
        """
        # Build prompt from observation
        prompt = self._build_prompt(obs)
        
        # Add to conversation history
        self.conversation_history.append({"role": "user", "content": prompt})
        
        # Call OpenAI API
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.conversation_history,
                temperature=0.7,
                max_tokens=500
            )
            
            assistant_message = response.choices[0].message.content
            self.conversation_history.append({"role": "assistant", "content": assistant_message})
            
            # Parse action from response
            action = self._parse_action(assistant_message, obs)
            return action
            
        except Exception as e:
            print(f"API error: {e}")
            # Fallback to approve
            return Action(action_type="approve")
    
    def _build_prompt(self, obs: Observation) -> str:
        """Build prompt from observation.
        
        Args:
            obs: Current observation
            
        Returns:
            Prompt string for LLM
        """
        # First observation - provide full context
        if obs.action_count == 0:
            prompt = f"""You are a code review assistant. Your task is to review a pull request and provide feedback.

Pull Request ID: {obs.pull_request_id}
Files Changed: {', '.join(obs.files_changed)}

Diffs:
"""
            for file_path, diff in obs.diff_content.items():
                prompt += f"\n--- {file_path} ---\n{diff}\n"
            
            prompt += """
Your available actions:
1. add_comment: Add a review comment to a specific file and line
2. view_file: View the full content of a file
3. request_changes: Reject the PR and request changes
4. approve: Approve the PR

You should:
- Identify bugs, security issues, style violations, and performance problems
- Provide actionable feedback with specific suggestions
- Make a final decision (approve or request_changes) when done

Respond with ONE action in this format:
ACTION: <action_type>
FILE: <target_file> (if applicable)
LINE: <line_number> (if applicable)
COMMENT: <comment_text> (if applicable)

Start by reviewing the diffs and identifying any issues."""
        
        else:
            # Subsequent observations - provide feedback and current state
            prompt = f"""Current state:
- Actions taken: {obs.action_count}
- Comments added: {len(obs.existing_comments)}
- Status: {obs.review_status}
"""
            
            if obs.error_message:
                prompt += f"\nError: {obs.error_message}\n"
            
            if obs.full_file_content:
                prompt += "\nFull file content:\n"
                for file_path, content in obs.full_file_content.items():
                    prompt += f"\n--- {file_path} ---\n{content[:1000]}...\n"
            
            prompt += "\nWhat is your next action? Respond in the same format as before."
        
        return prompt
    
    def _parse_action(self, response: str, obs: Observation) -> Action:
        """Parse action from LLM response.
        
        Args:
            response: LLM response text
            obs: Current observation (for fallback logic)
            
        Returns:
            Parsed Action object
        """
        # Extract action components using regex
        action_match = re.search(r'ACTION:\s*(\w+)', response, re.IGNORECASE)
        file_match = re.search(r'FILE:\s*([^\n]+)', response, re.IGNORECASE)
        line_match = re.search(r'LINE:\s*(\d+)', response, re.IGNORECASE)
        comment_match = re.search(r'COMMENT:\s*([^\n]+(?:\n(?!ACTION:|FILE:|LINE:|COMMENT:)[^\n]+)*)', response, re.IGNORECASE | re.MULTILINE)
        
        if not action_match:
            # Fallback: if we've made some comments, approve; otherwise add a comment
            if len(obs.existing_comments) > 0:
                return Action(action_type="approve")
            else:
                return Action(
                    action_type="add_comment",
                    target_file=obs.files_changed[0] if obs.files_changed else "unknown",
                    comment_text="Looks good overall."
                )
        
        action_type = action_match.group(1).lower()
        
        # Map common variations to valid action types
        action_type_map = {
            "comment": "add_comment",
            "add": "add_comment",
            "view": "view_file",
            "reject": "request_changes",
            "request": "request_changes",
        }
        action_type = action_type_map.get(action_type, action_type)
        
        # Validate action type
        if action_type not in ["add_comment", "request_changes", "approve", "view_file"]:
            action_type = "approve"
        
        # Build action based on type
        if action_type == "add_comment":
            target_file = file_match.group(1).strip() if file_match else (obs.files_changed[0] if obs.files_changed else "unknown")
            line_number = int(line_match.group(1)) if line_match else None
            comment_text = comment_match.group(1).strip() if comment_match else "Please review this section."
            
            return Action(
                action_type="add_comment",
                target_file=target_file,
                line_number=line_number,
                comment_text=comment_text
            )
        
        elif action_type == "view_file":
            target_file = file_match.group(1).strip() if file_match else (obs.files_changed[0] if obs.files_changed else "unknown")
            return Action(action_type="view_file", target_file=target_file)
        
        else:
            # approve or request_changes
            return Action(action_type=action_type)


def main():
    """Main execution flow."""
    # Load configuration from environment variables
    api_base = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
    model = os.getenv("MODEL_NAME", "gpt-3.5-turbo")
    token = os.getenv("HF_TOKEN") or os.getenv("OPENAI_API_KEY", "")
    
    if not token:
        print("Error: No API token found. Set HF_TOKEN or OPENAI_API_KEY environment variable.")
        return
    
    print("Code Review Assistant - Baseline Inference")
    print(f"API Base: {api_base}")
    print(f"Model: {model}")
    
    # Initialize environment and agent
    env = CodeReviewEnvironment()
    agent = BaselineAgent(api_base, model, token)
    
    # Run all three tasks
    tasks = ["easy", "medium", "hard"]
    scores = {}
    
    for task_id in tasks:
        try:
            score = agent.run_episode(env, task_id)
            scores[task_id] = score
        except Exception as e:
            print(f"Error running task {task_id}: {e}")
            scores[task_id] = 0.0
    
    # Compute and display results
    print(f"\n{'='*60}")
    print("FINAL RESULTS")
    print(f"{'='*60}")
    for task_id, score in scores.items():
        print(f"{task_id.capitalize()}: {score:.3f}")
    
    avg_score = sum(scores.values()) / len(scores)
    print(f"\nAverage Score: {avg_score:.3f}")
    print(f"{'='*60}")
    
    # Save results to file
    results = {
        "scores": scores,
        "average": avg_score,
        "model": model
    }
    
    with open("baseline_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print("\nResults saved to baseline_results.json")


if __name__ == "__main__":
    main()

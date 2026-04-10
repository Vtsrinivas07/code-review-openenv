---
title: Code Review Assistant
emoji: 🔍
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
license: mit
---

# Code Review Assistant - OpenEnv Environment

An AI-powered code review environment for the OpenEnv Course Round 1 competition. This environment simulates realistic pull request review scenarios where agents must identify bugs, security vulnerabilities, style violations, and performance issues, then provide actionable feedback and make approval decisions.

## Overview

The Code Review Assistant environment implements the complete OpenEnv specification with typed Pydantic models, providing a standardized interface for agent evaluation. It models authentic code review challenges that developers face daily, making it both educationally valuable and practically relevant.

### Why Code Review?

Code review is a critical software engineering practice that:
- **Catches bugs early** before they reach production
- **Improves code quality** through peer feedback
- **Shares knowledge** across development teams
- **Ensures security** by identifying vulnerabilities
- **Maintains consistency** in coding standards

Automating code review with AI has real-world applications in:
- Developer productivity tools (GitHub Copilot, Amazon CodeGuru)
- CI/CD pipelines for automated quality gates
- Open source project maintenance at scale
- Security auditing and compliance checking

## Environment Details

### Action Space

The agent can perform four types of actions:

1. **add_comment**: Add a review comment to a specific file and line
   - `action_type`: "add_comment"
   - `target_file`: File path (required)
   - `line_number`: Line number (optional, None for file-level comments)
   - `comment_text`: Comment text (required)

2. **view_file**: View the full content of a file for detailed analysis
   - `action_type`: "view_file"
   - `target_file`: File path (required)

3. **request_changes**: Reject the PR and request changes
   - `action_type`: "request_changes"

4. **approve**: Approve the PR
   - `action_type`: "approve"

**Constraints:**
- Maximum 50 actions per episode
- Terminal actions (approve/request_changes) end the episode
- Invalid actions return error observations with negative rewards

### Observation Space

Each observation contains:

- `pull_request_id` (str): Unique identifier for the PR
- `files_changed` (list[str]): List of modified file paths
- `diff_content` (dict[str, str]): Mapping of file paths to unified diffs
- `existing_comments` (list[ReviewComment]): Previously added comments
- `review_status` (str): Current status (in_progress, approved, changes_requested)
- `action_count` (int): Number of actions taken
- `full_file_content` (dict[str, str] | None): Full file contents (populated by view_file)
- `error_message` (str | None): Error message if last action was invalid

### Reward Function

The environment provides intermediate rewards to guide agent learning:

- **Issue identification**: +0.1 to +0.5 (based on severity)
- **Helpful comments**: +0.05 to +0.2 (based on actionability)
- **False positives**: -0.1 to -0.3 (penalty)
- **Final decision**: -1.0 to +1.0 (terminal reward)
- **Action limit exceeded**: -0.5 (terminal penalty)

Rewards are designed to approximate the final grader score within 0.2 margin.

### Grading

Agent performance is evaluated on a 0.0-1.0 scale based on:

1. **Issue Detection** (40%): Precision, recall, and F1 score for identifying bugs, security issues, style violations, and performance problems
2. **Comment Quality** (30%): Actionability and specificity of feedback
3. **Decision Correctness** (20%): Approve when safe, request changes when issues exist
4. **False Positive Rate** (10%): Penalty for incorrect issue identifications

### Tasks

Three difficulty-graded tasks are provided:

1. **Easy**: 1-2 files, 2-3 obvious issues (undefined variables, missing imports)
   - Target score: 0.8-1.0 for perfect performance

2. **Medium**: 3-4 files, 4-6 issues requiring cross-file analysis
   - Target score: 0.7-1.0 for perfect performance

3. **Hard**: 5+ files, 7+ subtle issues (security vulnerabilities, race conditions, architectural problems)
   - Target score: 0.6-1.0 for perfect performance

## Setup

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd code-review-assistant

# Install dependencies
pip install -r requirements.txt
```

### Requirements

- Python 3.11+
- pydantic >= 2.0.0
- openai >= 1.0.0
- pytest >= 7.0.0
- hypothesis >= 6.0.0

### Environment Variables

Configure the baseline inference script with:

- `API_BASE_URL`: OpenAI API base URL (default: https://api.openai.com/v1)
- `MODEL_NAME`: Model to use (default: gpt-3.5-turbo)
- `HF_TOKEN` or `OPENAI_API_KEY`: API authentication token

## Usage

### Running the Baseline

```bash
# Set your API token
export OPENAI_API_KEY="your-api-key"

# Run the baseline inference script
python inference.py
```

The baseline script will:
1. Run all three tasks (easy, medium, hard)
2. Output actions, rewards, and scores for each step
3. Save results to `baseline_results.json`

### Using the Environment

```python
from src.environment import CodeReviewEnvironment
from src.models import Action

# Initialize environment
env = CodeReviewEnvironment()

# Reset to start a task
obs = env.reset(task_id="easy")

# Take actions
action = Action(
    action_type="add_comment",
    target_file="main.py",
    line_number=10,
    comment_text="This variable is undefined. Did you mean 'user_id'?"
)

obs, reward, done, info = env.step(action)

# Make final decision
action = Action(action_type="request_changes")
obs, reward, done, info = env.step(action)

# Get final score
final_score = info["grader_score"]
print(f"Final score: {final_score}")
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run property-based tests only
pytest tests/test_properties.py

# Run specific test file
pytest tests/test_environment.py
```

## Docker Deployment

### Building the Container

```bash
docker build -t code-review-assistant .
```

### Running the Container

```bash
docker run -e OPENAI_API_KEY="your-api-key" code-review-assistant
```

### Hugging Face Spaces

This environment is configured to run on Hugging Face Spaces with:
- **CPU**: 2 vCPUs
- **Memory**: 8GB RAM
- **Runtime**: ~10-20 minutes for baseline inference

## Project Structure

```
.
├── src/
│   ├── models.py          # Pydantic models (Observation, Action, Reward)
│   ├── environment.py     # OpenEnv environment implementation
│   ├── tasks.py          # Task manager and loading
│   ├── rewards.py        # Reward function
│   └── grader.py         # Grading system
├── tasks/
│   ├── easy.json         # Easy difficulty task
│   ├── medium.json       # Medium difficulty task
│   └── hard.json         # Hard difficulty task
├── tests/
│   ├── test_models.py    # Model validation tests
│   ├── test_environment.py  # Environment API tests
│   ├── test_grader.py    # Grading logic tests
│   ├── test_rewards.py   # Reward function tests
│   ├── test_tasks.py     # Task definition tests
│   └── test_properties.py   # Property-based tests
├── inference.py          # Baseline inference script
├── openenv.yaml         # OpenEnv metadata
├── Dockerfile           # Docker configuration
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## Development

### Adding New Tasks

Tasks are defined in JSON format in the `tasks/` directory. Each task includes:

```json
{
  "task_id": "custom",
  "difficulty": "medium",
  "pull_request": {
    "pr_id": "PR-123",
    "title": "Add new feature",
    "description": "Description of changes",
    "files": {
      "path/to/file.py": {
        "path": "path/to/file.py",
        "content": "file content",
        "language": "python"
      }
    },
    "diffs": {
      "path/to/file.py": "unified diff"
    }
  },
  "ground_truth": {
    "issues": [
      {
        "issue_id": "issue-1",
        "file_path": "path/to/file.py",
        "line_number": 10,
        "issue_type": "bug",
        "severity": "major",
        "description": "Issue description"
      }
    ],
    "correct_decision": "request_changes",
    "severity_threshold": "major"
  }
}
```

### Extending the Environment

The environment is designed to be extensible:

- Add new action types by extending the `Action` model and `_process_action` method
- Customize reward shaping in `src/rewards.py`
- Modify grading criteria in `src/grader.py`
- Add new observation fields in the `Observation` model

## License

This project is released for the OpenEnv Course Round 1 competition.

## Citation

If you use this environment in your research, please cite:

```
@misc{code-review-assistant-2024,
  title={Code Review Assistant: An OpenEnv Environment for AI-Powered Code Review},
  author={OpenEnv Course},
  year={2024},
  url={https://github.com/...}
}
```

## Support

For questions or issues:
- Open an issue on GitHub
- Contact the OpenEnv Course organizers
- Check the OpenEnv specification documentation

## Acknowledgments

This environment was created for the OpenEnv Course Round 1 competition, demonstrating real-world applications of AI in software engineering workflows.

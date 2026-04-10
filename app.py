"""OpenEnv API server for Code Review Assistant environment."""

from flask import Flask, request, jsonify
from src.environment import CodeReviewEnvironment
from src.models import Action
import os

app = Flask(__name__)

# Global environment instance
env = None
current_obs = None
current_done = False


@app.route('/', methods=['GET'])
def home():
    """Homepage with API documentation."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Code Review Assistant - OpenEnv API</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
            h1 { color: #2c3e50; }
            .endpoint { background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 5px; }
            .method { color: #fff; padding: 3px 8px; border-radius: 3px; font-weight: bold; }
            .get { background: #28a745; }
            .post { background: #007bff; }
            code { background: #e9ecef; padding: 2px 6px; border-radius: 3px; }
            .status { color: #28a745; font-weight: bold; }
        </style>
    </head>
    <body>
        <h1>🔍 Code Review Assistant</h1>
        <p class="status">✅ API Server Running - Ready for Evaluation</p>
        <p>OpenEnv environment for AI-powered code review evaluation.</p>
        
        <h2>Available Endpoints</h2>
        
        <div class="endpoint">
            <span class="method get">GET</span> <code>/health</code>
            <p>Health check endpoint</p>
        </div>
        
        <div class="endpoint">
            <span class="method get">GET</span> <code>/info</code>
            <p>Get environment information and available tasks</p>
        </div>
        
        <div class="endpoint">
            <span class="method post">POST</span> <code>/reset</code>
            <p>Reset environment with a task</p>
            <p>Body: <code>{"task_id": "easy|medium|hard"}</code></p>
        </div>
        
        <div class="endpoint">
            <span class="method post">POST</span> <code>/step</code>
            <p>Execute an action in the environment</p>
            <p>Body: <code>{"action_type": "add_comment|view_file|approve|request_changes", ...}</code></p>
        </div>
        
        <h2>Quick Test</h2>
        <p>Try: <a href="/health">/health</a> | <a href="/info">/info</a></p>
        
        <hr>
        <p><small>OpenEnv Course Round 1 Competition | Version 1.0.0</small></p>
    </body>
    </html>
    """, 200


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "timestamp": __import__('time').time()}), 200


@app.route('/reset', methods=['POST'])
def reset():
    """Reset the environment with a specific task."""
    global env, current_obs, current_done
    
    try:
        # Try to get JSON data, force=True to ignore content-type
        data = request.get_json(force=True, silent=True) or {}
        task_id = data.get('task_id', 'easy')
        
        # Initialize environment if needed
        if env is None:
            env = CodeReviewEnvironment()
        
        # Reset environment
        current_obs = env.reset(task_id=task_id)
        current_done = False
        
        # Convert observation to dict
        obs_dict = current_obs.model_dump()
        
        return jsonify({
            "observation": obs_dict,
            "info": {"task_id": task_id}
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/step', methods=['POST'])
def step():
    """Execute an action in the environment."""
    global env, current_obs, current_done
    
    try:
        if env is None:
            return jsonify({"error": "Environment not initialized. Call /reset first."}), 400
        
        if current_done:
            return jsonify({"error": "Episode is done. Call /reset to start a new episode."}), 400
        
        # Try to get JSON data, force=True to ignore content-type
        data = request.get_json(force=True, silent=True)
        if not data:
            return jsonify({"error": "No action provided"}), 400
        
        # Parse action
        action = Action(**data)
        
        # Execute step
        obs, reward, done, info = env.step(action)
        current_obs = obs
        current_done = done
        
        # Convert to dict
        obs_dict = obs.model_dump()
        reward_dict = reward.model_dump()
        
        return jsonify({
            "observation": obs_dict,
            "reward": reward_dict,
            "done": done,
            "info": info
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/info', methods=['GET'])
def info():
    """Get environment information."""
    return jsonify({
        "name": "code-review-assistant",
        "version": "1.0.0",
        "description": "AI-powered code review environment",
        "tasks": ["easy", "medium", "hard"]
    }), 200


def main():
    """Main entry point for the server."""
    port = int(os.getenv('PORT', 7860))
    app.run(host='0.0.0.0', port=port, debug=False)


if __name__ == '__main__':
    main()

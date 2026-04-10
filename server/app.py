"""OpenEnv FastAPI server for Code Review Assistant environment."""

from openenv.core.env_server import create_fastapi_app
from src.environment import CodeReviewEnvironment
from src.models import Action, Observation


def create_env():
    """Factory function to create environment instances."""
    return CodeReviewEnvironment()


# Create the FastAPI app using OpenEnv's helper
app = create_fastapi_app(
    create_env,
    Action,
    Observation
)


def main():
    """Main entry point for the server."""
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)


if __name__ == "__main__":
    main()

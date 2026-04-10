"""Deployment script for Code Review Assistant to Hugging Face Spaces."""

import os
import subprocess
import sys

def main():
    """Deploy the environment to Hugging Face Spaces."""
    
    # Check if logged in
    print("Checking Hugging Face authentication...")
    result = subprocess.run(
        ["huggingface-cli", "whoami"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print("❌ Not logged in to Hugging Face.")
        print("\nPlease run:")
        print("  huggingface-cli login")
        print("\nOr:")
        print("  hf auth login")
        print("\nThen run this script again.")
        sys.exit(1)
    
    print(f"✅ Logged in as: {result.stdout.strip()}")
    
    # Get repo ID
    repo_id = input("\nEnter your Hugging Face repo ID (e.g., srinivasvuriti07/code-review-assistant): ").strip()
    
    if not repo_id:
        print("❌ Repo ID is required")
        sys.exit(1)
    
    # Deploy using openenv push
    print(f"\n🚀 Deploying to {repo_id}...")
    
    # Set UTF-8 encoding for Windows
    if sys.platform == "win32":
        os.environ["PYTHONIOENCODING"] = "utf-8"
    
    result = subprocess.run(
        ["openenv", "push", "--repo-id", repo_id],
        env={**os.environ, "PYTHONIOENCODING": "utf-8"}
    )
    
    if result.returncode == 0:
        print(f"\n✅ Deployment successful!")
        print(f"\n📍 Your Space URL: https://huggingface.co/spaces/{repo_id}")
        print(f"📍 API URL: https://{repo_id.replace('/', '-')}.hf.space")
        print("\n⏳ Wait a few minutes for the Space to build and start.")
        print("\n🧪 Test with:")
        print(f"  curl -X POST https://{repo_id.replace('/', '-')}.hf.space/reset")
    else:
        print(f"\n❌ Deployment failed with exit code {result.returncode}")
        print("\nTry manual deployment:")
        print("1. Create a Space at https://huggingface.co/new-space")
        print("2. Clone the space repository")
        print("3. Copy all files to the cloned directory")
        print("4. Git add, commit, and push")
        print("\nSee DEPLOYMENT_GUIDE.md for detailed instructions.")
        sys.exit(1)


if __name__ == "__main__":
    main()

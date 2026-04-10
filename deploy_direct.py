"""Direct deployment to Hugging Face Spaces using the Hub API."""

import os
from pathlib import Path
from huggingface_hub import HfApi, create_repo

def deploy():
    """Deploy the environment directly to Hugging Face Spaces."""
    
    # Initialize API
    api = HfApi()
    
    # Repository details
    repo_id = "srinivasvuriti07/code-review-openenv"
    
    print(f"🚀 Deploying to {repo_id}...")
    
    # Create the space
    try:
        print("Creating Space...")
        create_repo(
            repo_id=repo_id,
            repo_type="space",
            space_sdk="docker",
            exist_ok=True
        )
        print("✅ Space created/verified")
    except Exception as e:
        print(f"⚠️  Space might already exist: {e}")
    
    # Files to upload
    files_to_upload = [
        "Dockerfile",
        "app.py",
        "inference.py",
        "requirements.txt",
        "pyproject.toml",
        "uv.lock",
        "openenv.yaml",
        "README.md",
        "__init__.py",
        "client.py",
        "models.py",
    ]
    
    folders_to_upload = [
        "src",
        "tasks",
        "server",
    ]
    
    print("\n📤 Uploading files...")
    
    # Upload individual files
    for file in files_to_upload:
        if Path(file).exists():
            try:
                api.upload_file(
                    path_or_fileobj=file,
                    path_in_repo=file,
                    repo_id=repo_id,
                    repo_type="space",
                )
                print(f"  ✅ {file}")
            except Exception as e:
                print(f"  ❌ {file}: {e}")
    
    # Upload folders
    for folder in folders_to_upload:
        if Path(folder).exists():
            try:
                api.upload_folder(
                    folder_path=folder,
                    path_in_repo=folder,
                    repo_id=repo_id,
                    repo_type="space",
                )
                print(f"  ✅ {folder}/")
            except Exception as e:
                print(f"  ❌ {folder}/: {e}")
    
    print("\n✅ Deployment complete!")
    print(f"\n📍 Space URL: https://huggingface.co/spaces/{repo_id}")
    print(f"📍 API URL: https://{repo_id.replace('/', '-')}.hf.space")
    print("\n⏳ Wait a few minutes for the Space to build and start.")
    print("\n🧪 Test with:")
    print(f"  curl -X POST https://{repo_id.replace('/', '-')}.hf.space/reset")

if __name__ == "__main__":
    deploy()

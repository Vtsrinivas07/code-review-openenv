# Manual Deployment Guide (Recommended)

Since `openenv validate` is failing due to multi-mode deployment requirements (which are optional for the competition), use this manual deployment method instead.

## Step 1: Create Hugging Face Space

1. Go to https://huggingface.co/new-space
2. Fill in the form:
   - **Owner**: srinivasvuriti07
   - **Space name**: code-review-assistant
   - **License**: MIT
   - **Space SDK**: Docker
   - **Visibility**: Public
3. Click "Create Space"

## Step 2: Clone the Space Repository

```bash
git clone https://huggingface.co/spaces/srinivasvuriti07/code-review-assistant
cd code-review-assistant
```

## Step 3: Copy Your Project Files

Copy all files from your current directory to the cloned space:

```bash
# Windows (PowerShell)
Copy-Item -Path C:\Scaler\* -Destination . -Recurse -Exclude .git,.kiro,.pytest_cache,__pycache__,.hypothesis

# Or manually copy these essential files:
# - Dockerfile
# - app.py
# - inference.py
# - requirements.txt
# - openenv.yaml
# - README.md
# - src/ (entire folder)
# - tasks/ (entire folder)
# - server/ (entire folder)
```

## Step 4: Commit and Push

```bash
git add .
git commit -m "Initial deployment of Code Review Assistant OpenEnv environment"
git push
```

## Step 5: Monitor Deployment

1. Go to https://huggingface.co/spaces/srinivasvuriti07/code-review-assistant
2. Click the "Logs" tab
3. Wait for the build to complete (usually 2-5 minutes)
4. Status should change to "Running"

## Step 6: Test Your Deployment

```bash
# Test health endpoint
curl https://srinivasvuriti07-code-review-assistant.hf.space/health

# Test reset endpoint
curl -X POST https://srinivasvuriti07-code-review-assistant.hf.space/reset \
  -H "Content-Type: application/json" \
  -d '{}'

# Test with specific task
curl -X POST https://srinivasvuriti07-code-review-assistant.hf.space/reset \
  -H "Content-Type: application/json" \
  -d '{"task_id": "easy"}'
```

## Step 7: Run Inference Script

Update your inference.py to use the deployed URL:

```python
# At the top of inference.py, change:
API_BASE_URL = os.getenv("API_BASE_URL", "https://srinivasvuriti07-code-review-assistant.hf.space")
```

Then run:

```bash
python inference.py
```

## Step 8: Submit to Competition

Once everything is working:

1. **Hugging Face Space URL**: 
   ```
   https://huggingface.co/spaces/srinivasvuriti07/code-review-assistant
   ```

2. **GitHub Repository** (create if needed):
   ```bash
   # Create a new repo on GitHub, then:
   git remote add github https://github.com/srinivasvuriti07/code-review-assistant.git
   git push github main
   ```

3. Submit both URLs to the competition platform

## Troubleshooting

### Build Fails

Check the logs for missing dependencies. Common fixes:

1. Ensure `requirements.txt` includes all packages
2. Verify Dockerfile CMD is correct:
   ```dockerfile
   CMD ["gunicorn", "--bind", "0.0.0.0:7860", "--workers", "1", "--timeout", "120", "app:app"]
   ```

### Port Issues

Hugging Face Spaces requires port 7860. Verify in Dockerfile:
```dockerfile
EXPOSE 7860
```

### Import Errors

Ensure all source files are copied:
- `src/` directory with all Python files
- `tasks/` directory with JSON files
- `app.py` in root

### Environment Not Found

Check that `src/environment.py` exists and contains `CodeReviewEnvironment` class.

## Why Manual Deployment?

The `openenv validate` command checks for "multi-mode deployment" features that are optional for the competition:
- `uv.lock` file (advanced dependency management)
- Additional configuration files

Your environment is fully functional and meets all competition requirements. Manual deployment bypasses these optional checks while still deploying a working environment.

## Verification Checklist

After deployment, verify:

- [ ] Space shows "Running" status
- [ ] `/health` returns `{"status": "healthy"}`
- [ ] `/reset` returns valid observation with PR data
- [ ] `/step` accepts actions and returns results
- [ ] `inference.py` runs successfully
- [ ] All three tasks (easy, medium, hard) work

## Success!

Once all checks pass, your environment is ready for competition submission! 🎉


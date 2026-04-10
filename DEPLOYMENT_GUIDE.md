# Deployment Guide for Code Review Assistant

## Prerequisites

1. **Hugging Face Account**: Create an account at https://huggingface.co/
2. **Access Token**: Generate a token at https://huggingface.co/settings/tokens
   - Select "Write" permissions
   - Copy the token (you'll need it for login)

## Option 1: Deploy Using OpenEnv CLI (Recommended)

### Step 1: Login to Hugging Face

```bash
huggingface-cli login
# Or use the new command:
hf auth login
```

Paste your token when prompted.

### Step 2: Push to Hugging Face Spaces

```bash
openenv push --repo-id srinivasvuriti07/code-review-assistant
```

This will:
- Validate your environment
- Create a Hugging Face Space
- Upload all files
- Configure the Dockerfile
- Start the deployment

### Step 3: Monitor Deployment

1. Go to https://huggingface.co/spaces/srinivasvuriti07/code-review-assistant
2. Click on "Logs" tab to monitor startup
3. Wait for "Running" status

### Step 4: Test the Deployment

```bash
curl -X POST https://srinivasvuriti07-code-review-assistant.hf.space/reset \
  -H "Content-Type: application/json" \
  -d '{}'
```

---

## Option 2: Manual Deployment via Git

### Step 1: Create a New Space

1. Go to https://huggingface.co/new-space
2. Fill in:
   - **Owner**: srinivasvuriti07
   - **Space name**: code-review-assistant
   - **License**: MIT
   - **Space SDK**: Docker
   - **Visibility**: Public

### Step 2: Clone and Push

```bash
# Clone the space repository
git clone https://huggingface.co/spaces/srinivasvuriti07/code-review-assistant
cd code-review-assistant

# Copy all files from your project
cp -r /path/to/your/project/* .

# Commit and push
git add .
git commit -m "Initial deployment of Code Review Assistant"
git push
```

### Step 3: Monitor and Test

Same as Option 1, Steps 3-4.

---

## Option 3: Deploy via Hugging Face Web Interface

### Step 1: Create Space

1. Go to https://huggingface.co/new-space
2. Configure as in Option 2, Step 1

### Step 2: Upload Files

1. Click "Files" tab in your space
2. Click "Add file" → "Upload files"
3. Upload all project files:
   - `Dockerfile`
   - `app.py`
   - `requirements.txt`
   - `pyproject.toml`
   - `openenv.yaml`
   - `inference.py`
   - `README.md`
   - All `src/` files
   - All `tasks/` files
   - All `tests/` files (optional)

### Step 3: Commit Changes

1. Add commit message: "Initial deployment"
2. Click "Commit changes to main"

### Step 4: Monitor and Test

Same as Option 1, Steps 3-4.

---

## Troubleshooting

### Issue: "Invalid user token"

**Solution**: Generate a new token at https://huggingface.co/settings/tokens with "Write" permissions.

### Issue: "Dockerfile build failed"

**Solution**: Check the logs for missing dependencies. Ensure `requirements.txt` includes all packages.

### Issue: "Port 7860 not responding"

**Solution**: Verify Dockerfile CMD uses port 7860:
```dockerfile
CMD ["gunicorn", "--bind", "0.0.0.0:7860", "--workers", "1", "--timeout", "120", "app:app"]
```

### Issue: "Environment not found"

**Solution**: Ensure `src/environment.py` exists and `CodeReviewEnvironment` class is properly defined.

### Issue: "Character encoding error"

**Solution**: This is a Windows-specific issue. Use Option 2 (Git) or Option 3 (Web Interface) instead of OpenEnv CLI.

---

## Verification Checklist

After deployment, verify:

- [ ] Space status shows "Running"
- [ ] `/health` endpoint returns `{"status": "healthy"}`
- [ ] `/info` endpoint returns environment metadata
- [ ] `/reset` endpoint returns valid observation
- [ ] `/step` endpoint accepts actions and returns results
- [ ] `inference.py` runs successfully against deployed URL

---

## Competition Submission

Once deployed and verified:

1. Copy your Space URL: `https://srinivasvuriti07-code-review-assistant.hf.space`
2. Copy your GitHub repo URL: `https://github.com/srinivasvuriti07/code-review-assistant`
3. Submit both URLs to the competition platform
4. Ensure your Space is set to "Public" visibility

---

## Environment Variables (Optional)

If your environment needs API keys:

1. Go to your Space settings
2. Click "Variables and secrets"
3. Add:
   - `API_BASE_URL`
   - `MODEL_NAME`
   - `HF_TOKEN`

---

## Local Testing Before Deployment

Always test locally first:

```bash
# Start server
python app.py

# Test reset
curl -X POST http://localhost:7860/reset

# Test step
curl -X POST http://localhost:7860/step \
  -H "Content-Type: application/json" \
  -d '{"action_type": "view_file", "target_file": "auth_utils.py"}'

# Run inference script
python inference.py
```

---

## Support

- OpenEnv Documentation: https://github.com/raun/openenv-course
- Hugging Face Spaces: https://huggingface.co/docs/hub/spaces
- Competition Discord: [Link from competition page]


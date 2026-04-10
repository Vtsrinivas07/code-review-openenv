#!/bin/bash

# Quick Start Script for Code Review Assistant
# This script helps you deploy to Hugging Face Spaces quickly

echo "🚀 Code Review Assistant - Quick Start"
echo "======================================"
echo ""

# Check if logged in
echo "Checking Hugging Face authentication..."
if ! huggingface-cli whoami > /dev/null 2>&1; then
    echo "❌ Not logged in to Hugging Face"
    echo ""
    echo "Please run:"
    echo "  huggingface-cli login"
    echo ""
    echo "Get your token from: https://huggingface.co/settings/tokens"
    exit 1
fi

echo "✅ Logged in as: $(huggingface-cli whoami)"
echo ""

# Set repo ID
REPO_ID="srinivasvuriti07/code-review-assistant"
echo "📦 Deploying to: $REPO_ID"
echo ""

# Deploy
echo "🚀 Starting deployment..."
export PYTHONIOENCODING=utf-8
openenv push --repo-id "$REPO_ID"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Deployment successful!"
    echo ""
    echo "📍 Space URL: https://huggingface.co/spaces/$REPO_ID"
    echo "📍 API URL: https://$(echo $REPO_ID | tr '/' '-').hf.space"
    echo ""
    echo "⏳ Wait a few minutes for the Space to build and start."
    echo ""
    echo "🧪 Test with:"
    echo "  curl -X POST https://$(echo $REPO_ID | tr '/' '-').hf.space/reset"
else
    echo ""
    echo "❌ Deployment failed"
    echo ""
    echo "Try manual deployment:"
    echo "1. Create Space at https://huggingface.co/new-space"
    echo "2. Clone: git clone https://huggingface.co/spaces/$REPO_ID"
    echo "3. Copy files and push"
    echo ""
    echo "See DEPLOYMENT_GUIDE.md for details"
    exit 1
fi

@echo off
REM Quick Start Script for Code Review Assistant (Windows)
REM This script helps you deploy to Hugging Face Spaces quickly

echo.
echo 🚀 Code Review Assistant - Quick Start
echo ======================================
echo.

REM Check if logged in
echo Checking Hugging Face authentication...
huggingface-cli whoami >nul 2>&1
if errorlevel 1 (
    echo ❌ Not logged in to Hugging Face
    echo.
    echo Please run:
    echo   huggingface-cli login
    echo.
    echo Get your token from: https://huggingface.co/settings/tokens
    exit /b 1
)

for /f "delims=" %%i in ('huggingface-cli whoami') do set USERNAME=%%i
echo ✅ Logged in as: %USERNAME%
echo.

REM Set repo ID
set REPO_ID=srinivasvuriti07/code-review-assistant
echo 📦 Deploying to: %REPO_ID%
echo.

REM Deploy
echo 🚀 Starting deployment...
set PYTHONIOENCODING=utf-8
openenv push --repo-id %REPO_ID%

if errorlevel 1 (
    echo.
    echo ❌ Deployment failed
    echo.
    echo Try manual deployment:
    echo 1. Create Space at https://huggingface.co/new-space
    echo 2. Clone: git clone https://huggingface.co/spaces/%REPO_ID%
    echo 3. Copy files and push
    echo.
    echo See DEPLOYMENT_GUIDE.md for details
    exit /b 1
)

echo.
echo ✅ Deployment successful!
echo.
set API_URL=%REPO_ID:/=-%
echo 📍 Space URL: https://huggingface.co/spaces/%REPO_ID%
echo 📍 API URL: https://%API_URL%.hf.space
echo.
echo ⏳ Wait a few minutes for the Space to build and start.
echo.
echo 🧪 Test with:
echo   curl -X POST https://%API_URL%.hf.space/reset
echo.
pause

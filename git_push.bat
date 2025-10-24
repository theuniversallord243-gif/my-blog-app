@echo off
echo 🚀 Pushing Blog App to GitHub...
echo.

REM Initialize git if not already done
if not exist .git (
    echo 📁 Initializing git repository...
    git init
)

REM Add all files
echo 📂 Adding all files...
git add .

REM Commit with message
echo 💾 Committing changes...
git commit -m "Complete Blog App with social media features - Authentication, Blog management, Comments, Likes, Follows, Notifications, Mobile responsive"

REM Ask for GitHub repository URL
echo.
echo 🌐 Enter your GitHub repository URL:
echo Example: https://github.com/username/blog-app.git
set /p REPO_URL="Repository URL: "

REM Add remote origin
echo 🔗 Adding remote origin...
git remote remove origin 2>nul
git remote add origin %REPO_URL%

REM Push to GitHub
echo ⬆️ Pushing to GitHub...
git branch -M main
git push -u origin main

echo.
echo ✅ Successfully pushed to GitHub!
echo 🌐 Your blog app is now on: %REPO_URL%
echo.
pause
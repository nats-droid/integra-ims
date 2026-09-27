#!/bin/bash
# GitHub Setup Script
# Run this after providing your GitHub info

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}RBI API 581 - GitHub Setup${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo -e "${RED}GitHub CLI (gh) not found!${NC}"
    echo "Install with: sudo apt install gh"
    echo "Or visit: https://cli.github.com/"
    exit 1
fi

# Configuration
read -p "GitHub username/org (e.g., dickymuhr): " GITHUB_USER
read -p "Repository name (default: rbi-581-calculator): " REPO_NAME
REPO_NAME=${REPO_NAME:-rbi-581-calculator}
read -p "Repository visibility (public/private, default: private): " VISIBILITY
VISIBILITY=${VISIBILITY:-private}

echo ""
echo -e "${BLUE}Configuration:${NC}"
echo "  User/Org: $GITHUB_USER"
echo "  Repo: $REPO_NAME"
echo "  Visibility: $VISIBILITY"
echo ""

read -p "Proceed with this configuration? (y/n): " CONFIRM
if [ "$CONFIRM" != "y" ]; then
    echo "Aborted."
    exit 0
fi

echo ""
echo -e "${BLUE}Step 1: Checking GitHub authentication...${NC}"
if ! gh auth status &> /dev/null; then
    echo -e "${RED}Not authenticated with GitHub!${NC}"
    echo "Run: gh auth login"
    exit 1
fi
echo -e "${GREEN}✓ Authenticated${NC}"

echo ""
echo -e "${BLUE}Step 2: Creating GitHub repository...${NC}"
if [ "$VISIBILITY" = "public" ]; then
    gh repo create "$GITHUB_USER/$REPO_NAME" --public --source=. --remote=origin --description="Complete Risk-Based Inspection (RBI) calculator - API 581 4th Edition"
else
    gh repo create "$GITHUB_USER/$REPO_NAME" --private --source=. --remote=origin --description="Complete Risk-Based Inspection (RBI) calculator - API 581 4th Edition"
fi

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Repository created${NC}"
else
    echo -e "${RED}✗ Failed to create repository${NC}"
    echo "Repository might already exist. Adding remote..."
    git remote add origin "https://github.com/$GITHUB_USER/$REPO_NAME.git" 2>/dev/null || git remote set-url origin "https://github.com/$GITHUB_USER/$REPO_NAME.git"
fi

echo ""
echo -e "${BLUE}Step 3: Pushing to GitHub...${NC}"
git push -u origin main

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Pushed to GitHub${NC}"
else
    echo -e "${RED}✗ Push failed${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}GitHub Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Repository URL: https://github.com/$GITHUB_USER/$REPO_NAME"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "1. Visit: https://github.com/$GITHUB_USER/$REPO_NAME"
echo "2. Deploy to Vercel: vercel --prod"
echo "3. Or link to Vercel: vercel link"
echo ""

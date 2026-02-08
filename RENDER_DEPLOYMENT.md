# Sahay - Render Deployment Guide

## Setup Instructions

### 1. Create Render Account
- Go to [render.com](https://render.com) and sign up
- Connect your GitHub account

### 2. Push Code to GitHub
```bash
cd "c:\Users\hibajaj\OneDrive - Microsoft\Desktop\iitd\sahay code\final_website_code\website_code"
git init
git add .
git commit -m "Initial commit for Render deployment"
# Create a new repo on GitHub and push
git remote add origin <your-github-repo-url>
git push -u origin main
```

### 3. Create Services on Render

#### Create Redis Instance:
1. Click "New +" → "Redis"
2. Name: `sahay-redis`
3. Plan: **Free** (Starter)
4. Click "Create Redis"
5. Copy the **Internal Redis URL** (format: `redis://red-xxxxx:6379`)

#### Create Web Service:
1. Click "New +" → "Web Service"
2. Connect your GitHub repository
3. Configure:
   - **Name**: `sahay`
   - **Runtime**: `Python 3`
   - **Build Command**: `./build.sh`
   - **Start Command**: `gunicorn gentelella.gentelella.wsgi:application`

4. Add Environment Variables:
   - `PYTHON_VERSION` = `3.11.9`
   - `SECRET_KEY` = (Click "Generate" for random key)
   - `DEBUG` = `False`
   - `GOOGLE_API_KEY` = `AIzaSyBBxGZJriCR4aPgvlkddEdYygAY4BOauqI`
   - `REDIS_URL` = (Paste the Internal Redis URL from step 3.5)

5. Click "Create Web Service"

### 4. Update views.py for Redis Connection
After deployment, update `app/views.py` line 39 to use:
```python
r = redis.Redis.from_url(os.environ.get('REDIS_URL', 'redis://localhost:6379'))
```

### 5. Monitor Deployment
- Watch the logs in Render dashboard
- First deploy takes ~5-10 minutes
- Your site will be at: `https://sahay.onrender.com`

### 6. Custom Domain (Optional)
- In Render dashboard → Settings → Custom Domain
- Add: `sahay.responsible-ai.in`
- Follow DNS configuration instructions

## Free Tier Limitations
- Service spins down after 15 minutes of inactivity
- Takes ~30-50 seconds to restart on first request
- 750 hours/month (enough for one always-on service)

## Cost to Stay Always-On
- Upgrade to Starter plan: **$7/month**
- No spin-down delays

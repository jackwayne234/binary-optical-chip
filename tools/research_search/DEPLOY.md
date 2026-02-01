# Deploy to Render.com (Free Tier)

This guide walks you through deploying the Research Literature Search Tool on Render.com's free tier.

## Why Render.com?

- ✅ **Free forever** (no credit card required)
- ✅ **Easy deployment** (connect GitHub, auto-deploys)
- ✅ **Custom domain** (your-app.onrender.com)
- ✅ **Automatic HTTPS**
- ✅ **Good for research tools** (sleeps when unused, wakes on request)

**Limitation:** Sleeps after 15 minutes of inactivity. First request after sleep takes ~30 seconds to wake up. This is fine for research tools!

## Prerequisites

1. **GitHub account** (free)
2. **Render.com account** (free)
3. **Your code pushed to GitHub**

## Step-by-Step Deployment

### Step 1: Push Code to GitHub

Make sure your search tool code is in your GitHub repo:

```bash
cd /path/to/your/repo

# Add the search tool files
git add tools/research_search/
git commit -m "Add research literature search tool"
git push origin main
```

### Step 2: Sign Up for Render

1. Go to https://render.com
2. Click "Get Started for Free"
3. Sign up with your GitHub account (recommended)
4. Authorize Render to access your repos

### Step 3: Create New Web Service

1. In Render dashboard, click **"New +"** → **"Web Service"**
2. Connect your GitHub repository:
   - Search for: `-wavelength-ternary-optical-computer`
   - Click **"Connect"**
3. Configure the service:

   | Setting | Value |
   |---------|-------|
   | **Name** | `research-search-tool` (or your choice) |
   | **Region** | Oregon (US West) or closest to you |
   | **Branch** | `main` |
   | **Runtime** | `Python 3` |
   | **Build Command** | `pip install -r tools/research_search/requirements.txt` |
   | **Start Command** | `cd tools/research_search && gunicorn app:app` |
   | **Plan** | **Free** |

4. Click **"Create Web Service"**

### Step 4: Wait for Deployment

Render will:
1. Clone your repo
2. Install dependencies
3. Deploy the app
4. Give you a URL like `https://research-search-tool.onrender.com`

**This takes 2-3 minutes.**

### Step 5: Test Your App

1. Open the URL Render provides
2. Try a search: `"optical computing"`
3. Verify results appear from arXiv, Semantic Scholar, and Zenodo

### Step 6: Update Documentation

Update the URL in your README files:

```markdown
**Live Demo:** https://research-search-tool.onrender.com
```

## Configuration Files

The following files should be in `tools/research_search/`:

### render.yaml (Optional but recommended)
```yaml
services:
  - type: web
    name: research-search-tool
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn app:app
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.0
```

### requirements.txt
```
flask>=2.0.0
gunicorn>=20.0.0
requests>=2.25.0
```

### app.py (Main application)
See the app.py file in this directory for the Flask application structure.

## Environment Variables (Optional)

If you need API keys or other secrets:

1. In Render dashboard, go to your service
2. Click **"Environment"** tab
3. Add environment variables:
   - No API keys needed for arXiv, Semantic Scholar, or Zenodo - all are free and open access!
   - Add any custom API keys if you extend the tool

## Troubleshooting

### App Won't Start

**Check the logs:**
1. In Render dashboard, click your service
2. Click **"Logs"** tab
3. Look for error messages

**Common issues:**
- Missing dependencies → Check requirements.txt
- Wrong start command → Should be `gunicorn app:app`
- Port issues → Render sets PORT env var automatically

### Slow First Load

**This is normal on free tier!**
- App sleeps after 15 min inactivity
- First request wakes it up (~30 seconds)
- Subsequent requests are fast

**Solutions:**
- Use a uptime monitor (free) to ping it every 10 minutes
- Or just wait for the wake-up (fine for research tools)

### API Rate Limits

If searches stop working:
- arXiv: 1 request/3 seconds (built-in delay helps)
- Semantic Scholar: Generous rate limits, no API key required
- Zenodo: Rate limited but generous

**Solution:** Add caching or reduce query frequency

## Custom Domain (Optional)

To use your own domain:

1. In Render dashboard, click your service
2. Click **"Settings"** tab
3. Under **"Custom Domain"**, click **"Add Custom Domain"**
4. Enter your domain (e.g., `search.yourdomain.com`)
5. Follow DNS instructions Render provides
6. Wait for SSL certificate (automatic)

## Monitoring

### Free Options

**Render Dashboard:**
- Shows CPU, memory, bandwidth usage
- View logs in real-time
- Restart app if needed

**Uptime Monitor (keep app awake):**
- UptimeRobot (free tier)
- Pingdom (free tier)
- Set to ping every 10-15 minutes

## Updating Your App

When you push changes to GitHub:

1. Render automatically detects the push
2. Rebuilds and redeploys (2-3 minutes)
3. Zero downtime (keeps old version running until new is ready)

```bash
git add .
git commit -m "Update search tool"
git push origin main
# Render auto-deploys!
```

## Cost

**Free Tier Includes:**
- 512 MB RAM
- 0.1 CPU cores
- 100 GB bandwidth/month
- Custom domain + SSL
- 100 GB storage

**Paid Plans:**
- Starter: $7/month (always on, more resources)
- Only upgrade if you need 24/7 uptime or high traffic

## Alternative: Deploy from Replit

If your code is currently on Replit:

1. **Export from Replit:**
   - In Replit, click ⋮ (three dots) → "Download as ZIP"
   - Or use Replit's GitHub integration to push to repo

2. **Extract to your repo:**
   ```bash
   unzip replit-export.zip -d tools/research_search/
   ```

3. **Add requirements.txt:**
   Check what packages Replit used and add to requirements.txt

4. **Push to GitHub and deploy to Render**

## Support

**Render Documentation:** https://render.com/docs

**Community:**
- Render Discord: https://render.com/discord
- GitHub Issues: Open issue in this repo

**Contact:** chrisriner45@gmail.com

## Success Checklist

- [ ] Code pushed to GitHub
- [ ] Render account created
- [ ] Web service created on Render
- [ ] Deployed successfully
- [ ] URL tested and working
- [ ] Documentation updated with new URL
- [ ] (Optional) Custom domain configured
- [ ] (Optional) Uptime monitor set up

---

**Congratulations! Your research tool is now free and accessible to the world!**

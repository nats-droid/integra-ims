# Deployment Guide - RBI API 581 Calculator

**Project:** RBI API 581 Complete Implementation
**Date:** September 27, 2026
**Version:** 1.0.0

---

## 📦 Pre-Deployment Checklist

✅ Git repository initialized
✅ All files committed (81 files)
✅ `.gitignore` configured
✅ `requirements.txt` ready
✅ `vercel.json` configured
✅ `package.json` ready
✅ Documentation complete

---

## 🚀 DEPLOYMENT OPTIONS

### **Option 1: GitHub + Vercel (Recommended)**

**Best for:**
- Quick deployment
- Auto-deploy on push
- Serverless backend
- Free tier available

**Steps:**
1. Push to GitHub
2. Connect Vercel to GitHub repo
3. Auto-deploy

---

### **Option 2: Docker Container**

**Best for:**
- Self-hosted deployment
- Full control
- Database integration
- Corporate environment

---

### **Option 3: Traditional Server**

**Best for:**
- Existing infrastructure
- On-premise deployment
- Custom networking

---

## 📋 OPTION 1: GitHub + Vercel (RECOMMENDED)

### **Step 1: Push to GitHub**

#### **Method A: Using GitHub CLI (gh)**

```bash
cd /tmp/rbi-581-calculator

# Run setup script
./setup_github.sh

# Follow prompts:
# - GitHub username/org: dickymuhr (or your username)
# - Repo name: rbi-581-calculator
# - Visibility: private (recommended)
```

#### **Method B: Manual Setup**

```bash
cd /tmp/rbi-581-calculator

# Check gh CLI installation
gh auth status

# If not authenticated:
gh auth login

# Create GitHub repository
gh repo create YOUR_USERNAME/rbi-581-calculator \
  --private \
  --source=. \
  --remote=origin \
  --description="Complete RBI calculator - API 581 4th Edition"

# Push to GitHub
git push -u origin main
```

#### **Method C: Using Web Interface**

1. Go to https://github.com/new
2. Create new repository: `rbi-581-calculator`
3. Make it **Private**
4. **Don't** initialize with README (we already have one)
5. Click "Create repository"

Then in terminal:
```bash
cd /tmp/rbi-581-calculator

# Add remote
git remote add origin https://github.com/YOUR_USERNAME/rbi-581-calculator.git

# Push
git push -u origin main
```

---

### **Step 2: Deploy to Vercel**

#### **Method A: Using Vercel CLI**

```bash
# Install Vercel CLI (if not installed)
npm install -g vercel

# Login to Vercel
vercel login

# Deploy to production
cd /tmp/rbi-581-calculator
vercel --prod

# Follow prompts:
# - Set up and deploy? Yes
# - Which scope? [Your account]
# - Link to existing project? No
# - Project name? rbi-581-calculator
# - Directory? ./
# - Override settings? No
```

#### **Method B: Using Vercel Web Interface**

1. Go to https://vercel.com/new
2. Import Git Repository
3. Select GitHub account
4. Import `rbi-581-calculator` repo
5. Configure:
   - Framework Preset: **Other**
   - Root Directory: `./`
   - Build Command: (leave empty)
   - Output Directory: (leave empty)
6. Environment Variables (optional):
   - `DATABASE_URL` - If using PostgreSQL
   - `SECRET_KEY` - For JWT/auth
7. Click **Deploy**

---

### **Step 3: Verify Deployment**

After deployment, you'll get a URL like:
```
https://rbi-581-calculator.vercel.app
```

Test endpoints:
```bash
# Health check
curl https://rbi-581-calculator.vercel.app/health

# API docs
open https://rbi-581-calculator.vercel.app/docs

# Test calculation
curl -X POST https://rbi-581-calculator.vercel.app/api/calculate-tmin \
  -H "Content-Type: application/json" \
  -d '{
    "pressure_psig": 300,
    "diameter_inches": 6.625,
    "allowable_stress_psi": 20000
  }'
```

---

## 🐳 OPTION 2: Docker Deployment

### **Step 1: Create Dockerfile**

```bash
cd /tmp/rbi-581-calculator

cat > Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "api.rbi_endpoints:app", "--host", "0.0.0.0", "--port", "8000"]
EOF
```

### **Step 2: Build and Run**

```bash
# Build image
docker build -t rbi-calculator:1.0.0 .

# Run container
docker run -d \
  --name rbi-calculator \
  -p 8000:8000 \
  -e DATABASE_URL="postgresql://user:pass@host:5432/db" \
  rbi-calculator:1.0.0

# Check logs
docker logs -f rbi-calculator

# Test
curl http://localhost:8000/health
```

### **Step 3: Docker Compose (with Database)**

```bash
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://rbi:password@db:5432/rbi
    depends_on:
      - db

  db:
    image: postgres:14
    environment:
      - POSTGRES_USER=rbi
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=rbi
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./database/schema.sql:/docker-entrypoint-initdb.d/schema.sql

volumes:
  postgres_data:
EOF

# Start services
docker-compose up -d

# Check status
docker-compose ps
```

---

## 🖥️ OPTION 3: Traditional Server

### **Ubuntu/Debian Server**

```bash
# SSH to server
ssh user@your-server.com

# Clone repository
git clone https://github.com/YOUR_USERNAME/rbi-581-calculator.git
cd rbi-581-calculator

# Install Python 3.11
sudo apt update
sudo apt install python3.11 python3.11-venv

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run with systemd
sudo cat > /etc/systemd/system/rbi-calculator.service << 'EOF'
[Unit]
Description=RBI API 581 Calculator
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/rbi-581-calculator
Environment="PATH=/var/www/rbi-581-calculator/venv/bin"
ExecStart=/var/www/rbi-581-calculator/venv/bin/uvicorn api.rbi_endpoints:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Start service
sudo systemctl daemon-reload
sudo systemctl enable rbi-calculator
sudo systemctl start rbi-calculator
sudo systemctl status rbi-calculator
```

### **Nginx Reverse Proxy**

```bash
sudo cat > /etc/nginx/sites-available/rbi-calculator << 'EOF'
server {
    listen 80;
    server_name rbi-api.your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/rbi-calculator /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### **SSL with Let's Encrypt**

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d rbi-api.your-domain.com
```

---

## 🔐 Environment Variables

### **Required:**
- `DATABASE_URL` - PostgreSQL connection string (if using DB)

### **Optional:**
- `SECRET_KEY` - For JWT authentication
- `CORS_ORIGINS` - Allowed CORS origins
- `LOG_LEVEL` - Logging level (INFO, DEBUG, WARNING)
- `MAX_WORKERS` - Number of worker processes

### **Setting in Vercel:**
1. Go to project settings
2. Environment Variables
3. Add variables
4. Redeploy

### **Setting in Docker:**
```bash
docker run -d \
  -e DATABASE_URL="postgresql://..." \
  -e SECRET_KEY="your-secret-key" \
  -e CORS_ORIGINS="https://yourdomain.com" \
  rbi-calculator:1.0.0
```

---

## 📊 Post-Deployment Verification

### **1. Health Check**
```bash
curl https://your-deployment.vercel.app/health
# Expected: {"status": "ok", "version": "1.0.0"}
```

### **2. API Documentation**
Open: https://your-deployment.vercel.app/docs

### **3. Test Calculation**
```bash
curl -X POST https://your-deployment.vercel.app/api/calculate-tmin \
  -H "Content-Type: application/json" \
  -d '{
    "component_type": "pipe",
    "pressure_psig": 300,
    "diameter_inches": 6.625,
    "allowable_stress_psi": 20000,
    "joint_efficiency": 1.0,
    "corrosion_allowance": 0.125
  }'
```

### **4. Test All Modules**
```bash
# FMS Audit
curl -X POST https://your-deployment.vercel.app/api/fms-audit \
  -H "Content-Type: application/json" \
  -d '{"audit_scores": [15,14,11,11,11,10]}'

# Timeline Planning
curl -X POST https://your-deployment.vercel.app/api/risk-timeline \
  -H "Content-Type: application/json" \
  -d '{"equipment_id": "P-101", "years": 10}'
```

---

## 🔄 Continuous Deployment

### **GitHub Actions (Auto-deploy on push)**

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Vercel

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Deploy to Vercel
        uses: amondnet/vercel-action@v20
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.ORG_ID }}
          vercel-project-id: ${{ secrets.PROJECT_ID }}
          vercel-args: '--prod'
```

---

## 🐛 Troubleshooting

### **Issue: Vercel deployment fails**
**Solution:**
- Check `vercel.json` syntax
- Verify Python version (3.11)
- Check `requirements.txt` dependencies

### **Issue: Import errors**
**Solution:**
- Ensure all modules in correct structure
- Check `__init__.py` files exist
- Verify PYTHONPATH

### **Issue: Database connection fails**
**Solution:**
- Verify DATABASE_URL format
- Check PostgreSQL version (14+)
- Verify network access

### **Issue: Slow performance**
**Solution:**
- Enable caching
- Optimize database queries
- Use connection pooling
- Scale Vercel plan

---

## 📈 Monitoring & Logs

### **Vercel Logs**
```bash
vercel logs
vercel logs --follow
```

### **Docker Logs**
```bash
docker logs -f rbi-calculator
```

### **System Logs**
```bash
sudo journalctl -u rbi-calculator -f
```

---

## 🎯 Next Steps After Deployment

1. ✅ **Test all endpoints**
2. ✅ **Setup monitoring** (Sentry, DataDog, etc.)
3. ✅ **Configure backups** (if using database)
4. ✅ **Setup CI/CD** (GitHub Actions)
5. ✅ **Add authentication** (if needed)
6. ✅ **Setup custom domain**
7. ✅ **Load testing** (1000+ concurrent requests)
8. ✅ **Documentation deployment** (MkDocs)

---

## 📞 Support

**Issues?**
- Check logs first
- Review documentation
- Test locally first
- Check GitHub Issues

**Deployment location:**
- `/tmp/rbi-581-calculator/`

---

**Ready to deploy!** 🚀

Choose your deployment method and follow the steps above.

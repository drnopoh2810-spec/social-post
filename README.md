---
title: Social Post Manager — نظام نشر محتوى علمي ذكي
emoji: 🧠
colorFrom: purple
colorTo: pink
sdk: docker
pinned: false
license: mit
app_port: 7860
---

<div align="center">

# 🧠 Social Post Manager
### نظام متكامل لتوليد ونشر المحتوى العلمي والمعرفي على منصات التواصل الاجتماعي

[![CI](https://github.com/drnopoh2810-spec/social-post/actions/workflows/ci.yml/badge.svg)](https://github.com/drnopoh2810-spec/social-post/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)](https://flask.palletsprojects.com/)

[English](#english) | [العربية](#arabic)

</div>

---

## 📋 Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [License](#license)

---

<a name="overview"></a>
## 🌟 Overview

**Social Post Manager** is an intelligent, end-to-end content automation platform designed for creating, managing, and publishing high-quality educational and scientific content across multiple social media platforms.


### What It Does

1. **AI-Powered Content Generation**: Automatically generates educational post ideas and writes engaging content in Egyptian Arabic dialect
2. **Multi-Platform Publishing**: Publishes to Facebook, Instagram, Twitter/X, Threads, and LinkedIn with platform-specific adaptations
3. **Intelligent Image Generation**: Creates contextual images using 11+ AI image providers with automatic fallback
4. **Advanced Text Overlay**: Adds Arabic text overlays on images with 5 professional Arabic fonts
5. **Real-Time Analytics**: Tracks engagement metrics and provides actionable insights
6. **Telegram Bot Control**: Full remote management via Telegram bot interface
7. **Auto-Sync & Backup**: Bidirectional sync with Google Sheets and Redis persistence

### Built With

- **Backend**: Flask 3.0, SQLAlchemy, APScheduler
- **AI Integration**: Gemini, Cohere, Groq, OpenRouter, OpenAI, api.airforce
- **Image Generation**: Cloudflare Workers, Ideogram, Stability AI, HuggingFace, Together AI, Fal.ai, Pollinations
- **Storage**: SQLite, Redis (Upstash), Google Sheets, Cloudinary
- **Social APIs**: Facebook Graph API, Instagram Graph API, Twitter API v2, Threads API, LinkedIn API
- **Bot**: python-telegram-bot
- **Frontend**: Jinja2 templates, vanilla JavaScript, Chart.js

---

<a name="key-features"></a>
## ✨ Key Features

### 🤖 AI Content Generation

#### Idea Factory
- Generates 10 unique scientific/educational post ideas automatically
- Analyzes past performance to avoid saturated topics
- Distributes ideas across 5 content types:
  1. Research-based analysis
  2. Myth-busting with scientific evidence
  3. Deep mechanism explanation
  4. Real case study + lesson
  5. Critical thinking question + comparison


#### Post Writer
- **4-Layer Structure**:
  1. **Quiet Observation**: Field-based opening without clickbait
  2. **Scientific Explanation**: Deep dive into neurological/psychological/behavioral mechanisms
  3. **Myth Correction**: Gently corrects common misconceptions with evidence
  4. **Perspective Shift**: Reframes reader's understanding (not a call-to-action)
- **Language**: Pure Egyptian Arabic colloquial dialect
- **Length**: 700-1100 words (long-form, value-packed)
- **Style**: Combines academic depth with conversational tone

#### Platform Adaptation
Automatically adapts content for each platform:
- **Facebook**: Full post (700-1100 words)
- **Instagram**: Caption format (max 2200 chars) with 8-15 hashtags
- **Twitter/X**: Concise thread-starter (max 270 chars)
- **Threads**: Conversational style (max 500 chars) ending with open question
- **LinkedIn**: Professional English adaptation with global context

#### AI Provider Chain
**6 Text AI Providers** with automatic failover:
1. 🔵 **Gemini** (gemini-2.0-flash, gemini-1.5-pro) — Primary
2. 🟣 **Cohere** (command-r7b-arabic, command-r-plus) — Arabic specialist
3. 🟠 **Groq** (llama-3.3-70b, mixtral-8x7b) — Fast inference
4. 🔴 **OpenRouter** (Access to 100+ models)
5. 🛩️ **api.airforce** (Free tier, no key required)
6. 🟢 **OpenAI** (gpt-4o, gpt-4o-mini) — Fallback

**Key Rotation**: Multiple keys per provider, automatic rotation on quota exhaustion

---

### 🎨 Image Generation & Processing

#### 11 Image Providers (Priority Order)
1. ☁️ **Cloudflare Worker** (Flux 2) — Primary, fastest
2. 🔵 **Google Imagen 4** — Free with Gemini key
3. 🎨 **Ideogram v3** — Best for Arabic text in images
4. 🟢 **OpenAI** (gpt-image-1, DALL-E 3)
5. 🔷 **Stability AI** (SD 3.5)
6. 🤗 **HuggingFace** (Flux Schnell)
7. 🔗 **Together AI** (Flux Free)
8. ⚡ **Fal.ai** (Flux Schnell)
9. 🛩️ **api.airforce** — Free, no key
10. 🌸 **Pollinations** (authenticated)
11. 🌸 **Pollinations** (anonymous) — Last fallback, always works


#### Image Processing Pipeline
1. **Generation**: AI creates contextual image based on post content
2. **Frame Overlay**: Applies transparent PNG frame (configurable opacity)
3. **Text Overlay**: Adds Arabic text with advanced typography:
   - **5 Arabic Fonts**: Cairo, Noto Naskh, Noto Kufi, Amiri, Tajawal
   - **Text Sources**: AI-generated title, first line, or custom text
   - **Positioning**: 9 positions + pixel-perfect offset (X/Y)
   - **Styling**: Font size, color, background (with opacity), shadow
   - **Smart Extraction**: AI extracts most impactful sentence from post
4. **Upload**: Cloudinary with auto-delete after publishing (saves storage)

#### Image Prompt Engineering
- **Style**: Documentary/editorial photography (Magnum Photos aesthetic)
- **Technical**: Kodak Portra 400 film grain, Hasselblad color science
- **Composition**: 3-plane depth, negative space for text, symbolic props
- **Restrictions**: NO text in image, NO faces, NO commercial feel
- **Format**: Portrait (1080×1350px default, configurable)

---

### 📢 Multi-Platform Publishing

| Platform | Image | Text | Caption | API Version | Notes |
|----------|-------|------|---------|-------------|-------|
| **Facebook** | ✅ | ✅ | Full post | Graph API v20 | Page posts |
| **Instagram** | ✅ | ✅ | Caption | Graph API v20 | Business/Creator only |
| **Twitter/X** | ✅ | ✅ | Tweet | API v2 | OAuth 1.0a |
| **Threads** | ✅ | ✅ | Thread | Threads API v1 | Meta platform |
| **LinkedIn** | ✅ | ✅ | Article | UGC Posts API | Professional network |

#### Publishing Features
- **Independent Execution**: Platform failure doesn't affect others
- **Credential Validation**: Pre-checks before attempting publish
- **Double-Publish Protection**: Status locking (IN_PROGRESS)
- **Error Handling**: Detailed error messages per platform
- **Retry Logic**: Automatic retry on transient failures


---

### 📊 Analytics & Insights

#### Real-Time Metrics Collection
- **Auto-fetch** from all platforms every 6 hours
- **Engagement Score**: `likes×1 + comments×3 + shares×5`
- **Platform-specific metrics**:
  - Facebook: likes, comments, shares
  - Instagram: likes, comments
  - Twitter: likes, retweets, replies
  - Threads: likes, replies
  - LinkedIn: likes, comments, shares

#### Performance Analysis
- **Top/Bottom 5 Posts**: Ranked by engagement score
- **Best Tone & Style**: Data-driven recommendations
- **Saturated Topics**: Identifies overused themes
- **Daily Trends**: Time-series engagement charts
- **Writing Style Performance**: Tracks which styles perform best

#### Visualization
- Bar charts for top/bottom posts
- Daily engagement trend line
- Style/tone performance comparison
- Real-time dashboard with key metrics

---

### 🗄️ Data Persistence & Sync

#### Storage Architecture
```
┌─────────────┐
│   SQLite    │ ← Primary database (posts, config, keys, prompts)
└──────┬──────┘
       │
       ├─────→ ┌─────────────┐
       │       │    Redis    │ ← Config persistence (survives restarts)
       │       └─────────────┘
       │
       ├─────→ ┌─────────────┐
       │       │Google Sheets│ ← Bidirectional sync (source of truth for ideas)
       │       └─────────────┘
       │
       └─────→ ┌─────────────┐
               │ Cloudinary  │ ← Image hosting (auto-delete after publish)
               └─────────────┘
```


#### Google Sheets Integration
- **Auto-sync on page load**: Non-blocking, fast
- **Bidirectional**: DB ↔ Sheets
- **Conflict Resolution**: Sheets = source of truth for ideas
- **Backup**: Manual sync/restore from UI
- **Sheet Structure**:
  - Ideas: idea, keywords, tone, writing_style, opening_type, status
  - Config: key-value pairs for all settings
  - Posts: Full post archive with metrics

#### Redis Persistence (Upstash)
- **Config Priority**: `env vars → Redis → SQLite`
- **Auto-save**: Config changes saved to Redis immediately
- **Survives Restarts**: Critical for platforms like HuggingFace Spaces
- **Fallback**: Works without Redis (uses SQLite only)

---

### 🤖 Telegram Bot Interface

Full remote control via Telegram bot with inline keyboards.

#### Main Menu
```
📊 Dashboard    📝 Ideas       📢 Publish Now
🧠 Generate     📈 Analytics   📋 Logs
📱 Platforms    🗝️ AI Keys     ✍️ Prompts
⚙️ Settings     ⏸️ Scheduler
```

#### Features
- **Real-time Notifications**: Instant alerts on publish/error
- **Idea Management**: View, skip, delete, or publish ideas
- **Prompt Editing**: View and modify AI prompts directly
- **Platform Control**: Enable/disable platforms on-the-fly
- **Key Status**: Check AI provider key health
- **Scheduler Control**: Pause/resume automated tasks
- **Analytics**: View top posts and performance metrics
- **Logs**: Recent workflow execution history

#### Setup
1. Create bot via [@BotFather](https://t.me/BotFather)
2. Get your Chat ID from bot's `/myid` command
3. Add `TELEGRAM_BOT_TOKEN` and `TELEGRAM_ADMIN_CHAT_ID` to config


---

### ⚙️ Scheduling & Automation

#### APScheduler (Internal)
- **Idea Generation**: Daily at 08:00 (configurable)
- **Auto-Publishing**: Daily at 09:00 (configurable)
- **Analytics Refresh**: Every 6 hours
- **Auto-Updater**: Checks GitHub every 30 minutes
- **Platform**: HuggingFace Spaces, local development

#### PythonAnywhere Scheduled Tasks
- **Independent Execution**: Runs even when app is sleeping
- **Task 1 - Ideas**: `pa_task_ideas.py` — Daily at 08:00
- **Task 2 - Publish**: `pa_task_post.py` — Daily at 09:00
- **Reliability**: More reliable than internal scheduler on PA

#### Auto-Updater
- Checks GitHub for new commits every 30 minutes
- Pulls latest changes automatically
- Restarts application (HuggingFace only)
- Logs all updates to workflow_logs table

---

<a name="architecture"></a>
## 🏗️ Architecture

### System Design

```
┌─────────────────────────────────────────────────────────────┐
│                        Flask Application                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Dashboard  │  │   Workflow   │  │   REST API   │      │
│  │    Routes    │  │   Service    │  │   Endpoints  │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                  │                  │              │
│         └──────────────────┼──────────────────┘              │
│                            │                                 │
│         ┌──────────────────┴──────────────────┐             │
│         │                                      │             │
│    ┌────▼─────┐  ┌──────────┐  ┌──────────┐  │             │
│    │AI Service│  │  Image   │  │ Social   │  │             │
│    │(6 provs) │  │ Service  │  │ Service  │  │             │
│    └────┬─────┘  │(11 provs)│  │(5 platf) │  │             │
│         │        └────┬─────┘  └────┬─────┘  │             │
│         │             │             │        │             │
│    ┌────▼─────────────▼─────────────▼────┐   │             │
│    │      Key Rotator & Failover         │   │             │
│    └──────────────────────────────────────┘   │             │
│                                                │             │
└────────────────────────────────────────────────┼─────────────┘
                                                 │
                    ┌────────────────────────────┼────────────┐
                    │                            │            │
              ┌─────▼─────┐  ┌─────────┐  ┌─────▼─────┐     │
              │  SQLite   │  │  Redis  │  │  Sheets   │     │
              │    DB     │  │ (Upstash)│  │  Sync    │     │
              └───────────┘  └─────────┘  └───────────┘     │
                                                             │
              ┌──────────────────────────────────────────────┘
              │
        ┌─────▼──────┐  ┌──────────┐  ┌──────────┐
        │ Cloudinary │  │ Telegram │  │   Social │
        │   Images   │  │   Bot    │  │ Platforms│
        └────────────┘  └──────────┘  └──────────┘
```


### Project Structure

```
social_post/
├── 📱 Application Core
│   ├── app.py                    # Flask factory + APScheduler setup
│   ├── config.py                 # Environment configurations
│   ├── prompts_config.py         # All AI prompts in one place
│   ├── wsgi.py                   # WSGI entry point (production)
│   └── run.py                    # Development server
│
├── 🗄️ Database Layer
│   └── database/
│       ├── __init__.py
│       └── models.py             # SQLAlchemy models
│           ├── User              # Authentication
│           ├── Post              # Ideas & published posts
│           ├── Config            # Key-value settings
│           ├── ApiKey            # Social platform credentials
│           ├── AIProviderKey     # AI provider keys
│           ├── Prompt            # AI prompt templates
│           ├── AIModel           # Available AI models
│           ├── Platform          # Platform configurations
│           └── WorkflowLog       # Execution logs
│
├── 🛣️ Routes (MVC Controllers)
│   └── routes/
│       ├── auth.py               # Login/logout
│       ├── dashboard.py          # UI pages
│       ├── api.py                # REST API endpoints
│       └── workflow.py           # Manual workflow triggers
│
├── ⚙️ Business Logic (Services)
│   └── services/
│       ├── ai_service.py         # AI provider integration
│       ├── key_rotator.py        # Key rotation & failover
│       ├── image_service.py      # Image generation
│       ├── overlay_service.py    # Text overlay on images
│       ├── social_service.py     # Social platform publishing
│       ├── analytics_service.py  # Metrics collection
│       ├── workflow_service.py   # End-to-end workflow
│       ├── telegram_bot.py       # Telegram bot
│       ├── sheets_sync.py        # Google Sheets sync
│       ├── config_sheets_sync.py # Config backup to Sheets
│       ├── redis_config.py       # Redis persistence
│       └── auto_updater.py       # Auto-update from GitHub
│
├── 🎨 Frontend
│   ├── templates/
│   │   ├── base.html             # Base layout
│   │   ├── login.html            # Login page
│   │   └── pages/
│   │       ├── dashboard.html    # Main dashboard
│   │       ├── posts.html        # Ideas & posts management
│   │       ├── analytics.html    # Performance analytics
│   │       ├── models.html       # AI model selection
│   │       ├── ai_keys.html      # AI provider keys
│   │       ├── image_config.html # Image & overlay settings
│   │       ├── prompts.html      # Prompt editor
│   │       ├── platforms.html    # Platform settings
│   │       ├── scheduler.html    # Scheduling config
│   │       ├── telegram.html     # Telegram bot setup
│   │       ├── config.html       # General settings
│   │       ├── api_manager.html  # Social API keys
│   │       ├── db.html           # Database management
│   │       └── backup.html       # Backup & restore
│   └── static/
│       └── fonts/                # Arabic fonts (Cairo, Noto, Amiri, Tajawal)
│
├── 🚀 Deployment
│   ├── deploy/
│   │   ├── nginx.conf            # Nginx configuration
│   │   ├── social_post.service   # Systemd service
│   │   └── install.sh            # Installation script
│   ├── Dockerfile                # Docker image
│   ├── .dockerignore
│   └── Procfile                  # Heroku/Railway deployment
│
├── 📅 Scheduled Tasks
│   ├── pa_task_ideas.py          # PythonAnywhere: Generate ideas
│   └── pa_task_post.py           # PythonAnywhere: Publish post
│
├── 🧪 Testing & CI/CD
│   ├── test_image_fixes.py       # Image service tests
│   └── .github/workflows/
│       ├── ci.yml                # Continuous integration
│       ├── deploy-hf.yml         # Auto-deploy to HuggingFace
│       └── keep-alive.yml        # Health check pings
│
└── 📝 Documentation
    ├── README.md                 # This file
    ├── .env.example              # Environment variables template
    ├── requirements.txt          # Python dependencies
    ├── DEPLOYMENT_GUIDE.md       # Deployment instructions
    ├── MIGRATION_COMPLETE.md     # Migration notes
    └── AUTO_SYNC_SCENARIOS.md    # Sync behavior documentation
```


---

<a name="installation"></a>
## 🚀 Installation

### Prerequisites

- Python 3.11 or higher
- pip (Python package manager)
- Git
- (Optional) Redis instance (Upstash recommended)
- (Optional) Google Cloud project for Sheets API
- (Optional) Cloudinary account for image hosting

### Quick Start (Local Development)

```bash
# Clone the repository
git clone https://github.com/drnopoh2810-spec/social-post.git
cd social-post

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env  # or use your preferred editor

# Initialize database
python -c "from app import create_app; app = create_app('development'); app.app_context().push(); from database.models import db; db.create_all()"

# Run development server
python run.py
```

Open browser: `http://localhost:5000`

**Default credentials:**
- Username: `admin`
- Password: `admin123`

⚠️ **Change these immediately after first login!**

---

<a name="configuration"></a>
## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root. See [`.env.example`](.env.example) for all available options.

#### Essential Variables

```bash
# Application
SECRET_KEY=your-secret-key-here  # Generate: openssl rand -hex 32
FLASK_ENV=production
ADMIN_USERNAME=your-username
ADMIN_PASSWORD=your-secure-password

# Redis (Optional but recommended)
REDIS_URL=rediss://default:token@host:port

# Database (Auto-created if not specified)
DATABASE_URL=sqlite:///social_post.db
```


#### AI Provider Keys (At least one required)

```bash
# Google Gemini (Recommended - Free tier available)
GEMINI_API_KEY=your-gemini-key

# Cohere (Best for Arabic)
COHERE_API_KEY=your-cohere-key

# Groq (Fast inference)
GROQ_API_KEY=your-groq-key

# OpenRouter (Access to 100+ models)
OPENROUTER_API_KEY=your-openrouter-key

# OpenAI (Fallback)
OPENAI_API_KEY=your-openai-key

# api.airforce (No key needed - free tier)
# Works without configuration
```

#### Image Generation (Optional - Pollinations works without keys)

```bash
# Cloudflare Worker (Recommended)
WORKER_URL=https://your-worker.workers.dev

# Cloudinary (Image hosting)
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-api-secret

# Pollinations (Authenticated - better quality)
POLLINATIONS_KEY=your-pollinations-key

# Other providers use same keys as AI text providers
# Gemini key → Imagen 4
# OpenAI key → DALL-E 3
```

#### Social Platform Credentials

```bash
# Facebook
FB_PAGE_ID=your-page-id
FB_ACCESS_TOKEN=your-page-access-token

# Instagram (Business/Creator account required)
IG_USER_ID=your-instagram-business-id
IG_ACCESS_TOKEN=your-instagram-access-token

# Twitter/X
TWITTER_API_KEY=your-api-key
TWITTER_API_SECRET=your-api-secret
TWITTER_ACCESS_TOKEN=your-access-token
TWITTER_ACCESS_TOKEN_SECRET=your-access-token-secret

# Threads
THREADS_USER_ID=your-threads-user-id
THREADS_ACCESS_TOKEN=your-threads-access-token

# LinkedIn
LI_PERSON_ID=your-linkedin-person-id
LI_ACCESS_TOKEN=your-linkedin-access-token
```


#### Telegram Bot (Optional)

```bash
TELEGRAM_BOT_TOKEN=your-bot-token  # From @BotFather
TELEGRAM_ADMIN_CHAT_ID=your-chat-id  # Your Telegram user ID
```

#### Google Sheets Sync (Optional)

```bash
GOOGLE_SHEET_ID=your-sheet-id
GOOGLE_SHEETS_CREDENTIALS='{"type":"service_account",...}'  # JSON string
```

---

<a name="deployment"></a>
## 🌐 Deployment

### Deploy to PythonAnywhere (Recommended for Production)

#### 1. Setup Files

```bash
# In PythonAnywhere Bash Console
cd ~
git clone https://github.com/drnopoh2810-spec/social-post.git
cd social-post

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
nano .env  # Add your credentials
```

#### 2. Configure WSGI

Go to **Web** tab → **WSGI configuration file**, replace content with:

```python
import sys
import os

# Add project directory
project_home = '/home/YOUR_USERNAME/social-post'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Load environment variables
from dotenv import load_dotenv
load_dotenv(os.path.join(project_home, '.env'))

# Set Flask environment
os.environ.setdefault('FLASK_ENV', 'production')

# Import Flask app
from app import create_app
application = create_app('production')
```

#### 3. Setup Scheduled Tasks

Go to **Tasks** tab, add two tasks:

**Task 1 - Generate Ideas (Daily 08:00 UTC):**
```bash
/home/YOUR_USERNAME/social-post/venv/bin/python /home/YOUR_USERNAME/social-post/pa_task_ideas.py
```

**Task 2 - Publish Post (Daily 09:00 UTC):**
```bash
/home/YOUR_USERNAME/social-post/venv/bin/python /home/YOUR_USERNAME/social-post/pa_task_post.py
```

#### 4. Reload Web App

Click **Reload** button in Web tab.


---

### Deploy to HuggingFace Spaces

#### 1. Create New Space

1. Go to [HuggingFace Spaces](https://huggingface.co/spaces)
2. Click **Create new Space**
3. Choose **Docker** as SDK
4. Clone this repository or upload files

#### 2. Configure Secrets

Go to **Settings** → **Repository secrets**, add:

**Required:**
```
SECRET_KEY          → openssl rand -hex 32
ADMIN_USERNAME      → your-username
ADMIN_PASSWORD      → your-password
FLASK_ENV           → production
REDIS_URL           → rediss://default:token@host:port (Upstash)
```

**Optional (or configure via UI):**
```
GEMINI_API_KEY
COHERE_API_KEY
GROQ_API_KEY
CLOUDINARY_CLOUD_NAME
CLOUDINARY_API_KEY
CLOUDINARY_API_SECRET
FB_PAGE_ID
FB_ACCESS_TOKEN
... (all other credentials)
```

#### 3. Deploy

Push to main branch or click **Restart Space**. The app will be available at:
```
https://huggingface.co/spaces/YOUR_USERNAME/YOUR_SPACE_NAME
```

---

### Deploy with Docker

```bash
# Build image
docker build -t social-post .

# Run container
docker run -d \
  --name social-post \
  -p 7860:7860 \
  --env-file .env \
  social-post

# View logs
docker logs -f social-post
```

---

### Deploy to Railway / Render / Heroku

1. Connect your GitHub repository
2. Set environment variables in platform dashboard
3. Deploy from main branch

The `Procfile` is already configured:
```
web: gunicorn -c gunicorn.conf.py wsgi:application
```


---

<a name="usage"></a>
## 📖 Usage

### Web Dashboard

Access the dashboard at `http://your-domain.com` (or `localhost:5000` for local)

#### Main Pages

1. **📊 Dashboard** (`/`)
   - Overview statistics
   - Recent posts
   - Platform status
   - Recent workflow logs

2. **📝 Posts** (`/posts`)
   - View all ideas and published posts
   - Filter by status (NEW, IN_PROGRESS, POSTED, SKIPPED)
   - Search posts
   - Manual actions: Skip, Delete, Publish
   - Auto-syncs with Google Sheets on page load

3. **📈 Analytics** (`/analytics`)
   - Top 5 performing posts
   - Bottom 5 posts
   - Best tone and writing style
   - Engagement charts
   - Daily trend analysis

4. **🤖 AI Models** (`/models`)
   - Live fetch available models from each provider
   - Select default model per provider
   - View model capabilities and pricing
   - Test model availability

5. **🗝️ AI Keys** (`/ai-keys`)
   - Manage AI provider keys
   - Set priority for key rotation
   - Enable/disable keys
   - View key status and usage
   - Configure image provider chain

6. **🎨 Image Config** (`/image-config`)
   - Image dimensions and model selection
   - Frame overlay settings
   - Text overlay configuration:
     - Font selection (5 Arabic fonts)
     - Position and offset
     - Colors and styling
     - Background and shadow
   - Test image generation
   - Preview text overlay

7. **✍️ Prompts** (`/prompts`)
   - View all AI prompts
   - Edit prompt templates
   - Configure temperature and max tokens
   - Select AI provider per prompt type

8. **📱 Platforms** (`/platforms`)
   - Enable/disable each platform
   - Configure platform-specific settings
   - Test platform credentials

9. **⏰ Scheduler** (`/scheduler`)
   - Configure schedule times
   - Enable/disable auto-generation
   - Enable/disable auto-publishing
   - View PythonAnywhere task setup

10. **📱 Telegram** (`/telegram`)
    - Configure bot token and chat ID
    - Test bot connection
    - View bot commands


### Manual Workflows

#### Generate Ideas

**Via Web:**
```
Dashboard → Click "🧠 توليد أفكار جديدة" button
```

**Via API:**
```bash
curl -X POST http://your-domain.com/workflow/ideas \
  -H "Content-Type: application/json" \
  -H "Cookie: session=your-session-cookie"
```

**Via Telegram:**
```
Bot Menu → 🧠 توليد أفكار
```

#### Publish Post

**Via Web:**
```
Posts page → Select post → Click "📢 نشر الآن"
```

**Via API:**
```bash
curl -X POST http://your-domain.com/workflow/post \
  -H "Content-Type: application/json" \
  -H "Cookie: session=your-session-cookie"
```

**Via Telegram:**
```
Bot Menu → 📢 نشر الآن
```

---

<a name="api-documentation"></a>
## 📡 API Documentation

### Authentication

All API endpoints require authentication via session cookie (login required).

### Endpoints

#### Config Management

**Get Config**
```http
GET /api/config
```

**Save Config**
```http
POST /api/config
Content-Type: application/json

{
  "key1": "value1",
  "key2": "value2"
}
```

#### Posts Management

**Get All Posts**
```http
GET /api/posts?status=NEW&q=search-term
```

**Update Post**
```http
PUT /api/posts/<post_id>
Content-Type: application/json

{
  "status": "POSTED",
  "engagement_score": 150
}
```

**Delete Post**
```http
DELETE /api/posts/<post_id>
```


#### AI Models

**List Available Models**
```http
GET /api/models/list?provider=gemini
```

**Fetch Live Models**
```http
POST /api/models/fetch
Content-Type: application/json

{
  "provider": "gemini"
}
```

#### Image Generation

**Test Image Generation**
```http
POST /api/image/test
Content-Type: application/json

{
  "prompt": "A child learning with colorful materials",
  "post_content": "Post text here",
  "idea": "Educational concept"
}
```

**Test Text Overlay**
```http
POST /api/image/test-overlay
Content-Type: application/json

{
  "prompt": "Image prompt",
  "post_content": "Post text",
  "idea": "Concept"
}
```

#### Analytics

**Refresh Analytics**
```http
POST /api/analytics/refresh
```

**Get Analytics Data**
```http
GET /api/analytics/data
```

#### Workflows

**Generate Ideas**
```http
POST /workflow/ideas
```

**Publish Post**
```http
POST /workflow/post
```

---

## 🔧 Advanced Configuration

### Custom AI Prompts

Edit prompts in `prompts_config.py` or via web UI (`/prompts`).

Each prompt has:
- **name**: Identifier (e.g., `idea_factory`, `post_writer`)
- **provider**: Default AI provider
- **temperature**: Creativity level (0.0-1.0)
- **max_tokens**: Response length limit
- **system**: System instructions
- **user**: User prompt template with variables


### Arabic Font Installation

For text overlay to work properly, install Arabic fonts:

**On PythonAnywhere:**
```bash
cd ~/social-post/static/fonts

# Download fonts from Google Fonts
wget "https://github.com/google/fonts/raw/main/ofl/cairo/Cairo%5Bslnt%2Cwght%5D.ttf" -O Cairo-Regular.ttf
wget "https://github.com/google/fonts/raw/main/ofl/notokufiarabic/NotoKufiArabic%5Bwght%5D.ttf" -O NotoKufiArabic-Regular.ttf
wget "https://github.com/google/fonts/raw/main/ofl/notonaskharabic/NotoNaskhArabic%5Bwght%5D.ttf" -O NotoNaskhArabic-Regular.ttf
wget "https://github.com/google/fonts/raw/main/ofl/amiri/Amiri-Regular.ttf" -O Amiri-Regular.ttf
wget "https://github.com/google/fonts/raw/main/ofl/tajawal/Tajawal-Regular.ttf" -O Tajawal-Regular.ttf
```

**Or manually download from:**
- [Cairo](https://fonts.google.com/specimen/Cairo)
- [Noto Kufi Arabic](https://fonts.google.com/noto/specimen/Noto+Kufi+Arabic)
- [Noto Naskh Arabic](https://fonts.google.com/noto/specimen/Noto+Naskh+Arabic)
- [Amiri](https://fonts.google.com/specimen/Amiri)
- [Tajawal](https://fonts.google.com/specimen/Tajawal)

### Google Sheets Setup

1. Create a Google Cloud project
2. Enable Google Sheets API
3. Create a service account
4. Download credentials JSON
5. Share your Google Sheet with service account email
6. Add credentials to `.env`:
   ```bash
   GOOGLE_SHEET_ID=your-sheet-id
   GOOGLE_SHEETS_CREDENTIALS='{"type":"service_account",...}'
   ```

### Redis Setup (Upstash)

1. Create account at [Upstash](https://upstash.com)
2. Create Redis database
3. Copy connection string (starts with `rediss://`)
4. Add to `.env`:
   ```bash
   REDIS_URL=rediss://default:token@host:port
   ```

---

## 🐛 Troubleshooting

### Common Issues

**1. "No AI provider keys configured"**
- Add at least one AI provider key in `/ai-keys` or `.env`
- Gemini offers free tier: [Get API key](https://makersuite.google.com/app/apikey)

**2. "Image generation failed"**
- Pollinations works without keys as last fallback
- Check provider order in `/image-config`
- Verify Cloudinary credentials if using

**3. "Platform publish failed"**
- Verify credentials in `/api-manager`
- Check platform is enabled in `/platforms`
- Review error message in workflow logs

**4. "Fonts not found" for text overlay**
- Install Arabic fonts in `static/fonts/` directory
- See [Arabic Font Installation](#arabic-font-installation)

**5. "Scheduled tasks not running" (PythonAnywhere)**
- Verify task paths are absolute
- Check task logs in PA dashboard
- Ensure virtual environment path is correct


**6. "Redis connection failed"**
- App works without Redis (uses SQLite only)
- Verify `REDIS_URL` format: `rediss://default:token@host:port`
- Check Upstash dashboard for connection issues

**7. "Google Sheets sync not working"**
- Verify service account has access to sheet
- Check `GOOGLE_SHEETS_CREDENTIALS` is valid JSON
- Ensure Sheet ID is correct

### Debug Mode

Enable debug logging:

```python
# In config.py or .env
FLASK_ENV=development
LOG_LEVEL=DEBUG
```

View logs:
```bash
# Local
tail -f logs/app.log

# PythonAnywhere
tail -f /home/USERNAME/social-post/logs/app.log

# Docker
docker logs -f social-post
```

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guide
- Add docstrings to functions and classes
- Write tests for new features
- Update documentation as needed
- Keep commits atomic and descriptive

### Code Structure

- **Routes**: Handle HTTP requests, minimal logic
- **Services**: Business logic, reusable functions
- **Models**: Database schema and queries
- **Templates**: Jinja2 HTML templates
- **Static**: CSS, JS, fonts, images

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

```
MIT License

Copyright (c) 2024 drnopoh2810-spec

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```


---

## 🙏 Acknowledgments

- **AI Providers**: Google Gemini, Cohere, Groq, OpenRouter, OpenAI, api.airforce
- **Image Providers**: Cloudflare, Ideogram, Stability AI, HuggingFace, Together AI, Fal.ai, Pollinations
- **Platforms**: Meta (Facebook, Instagram, Threads), Twitter/X, LinkedIn
- **Infrastructure**: PythonAnywhere, HuggingFace Spaces, Upstash, Cloudinary
- **Fonts**: Google Fonts (Cairo, Noto, Amiri, Tajawal)
- **Libraries**: Flask, SQLAlchemy, APScheduler, python-telegram-bot, Pillow, and many more

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/drnopoh2810-spec/social-post/issues)
- **Discussions**: [GitHub Discussions](https://github.com/drnopoh2810-spec/social-post/discussions)
- **Email**: [Contact via GitHub](https://github.com/drnopoh2810-spec)

---

## 🗺️ Roadmap

### Planned Features

- [ ] **Multi-language Support**: Add support for more languages beyond Arabic
- [ ] **Video Generation**: Integrate AI video generation for Reels/Shorts
- [ ] **A/B Testing**: Test different post variations automatically
- [ ] **Advanced Analytics**: ML-based performance prediction
- [ ] **Content Calendar**: Visual calendar for scheduled posts
- [ ] **Team Collaboration**: Multi-user support with roles
- [ ] **API Rate Limiting**: Built-in rate limiter for external APIs
- [ ] **Webhook Support**: Real-time notifications via webhooks
- [ ] **Mobile App**: React Native companion app
- [ ] **Browser Extension**: Quick post from any webpage

### In Progress

- [x] Text overlay on images with Arabic fonts
- [x] Multi-provider AI failover
- [x] Google Sheets bidirectional sync
- [x] Telegram bot interface
- [x] Real-time analytics dashboard

---

## 📊 Project Stats

- **Lines of Code**: ~15,000+
- **Files**: 50+
- **AI Providers**: 6 text + 11 image
- **Social Platforms**: 5
- **Languages**: Python, JavaScript, HTML, CSS
- **Database**: SQLite + Redis
- **Deployment Options**: 5+ (PA, HF, Docker, Railway, Heroku)

---

<div align="center">

### ⭐ Star this repo if you find it useful!

Made with ❤️ by [drnopoh2810-spec](https://github.com/drnopoh2810-spec)

</div>

---

<a name="arabic"></a>
## 🇪🇬 النسخة العربية

# 🧠 مدير المنشورات الاجتماعية

نظام ذكي ومتكامل لتوليد ونشر المحتوى العلمي والمعرفي على منصات التواصل الاجتماعي.


## المميزات الرئيسية

### 🤖 الذكاء الاصطناعي
- **توليد أفكار علمية** تلقائياً — منشورات معرفية عميقة باللهجة المصرية
- **كتابة المنشورات** بـ 4 طبقات: ملاحظة هادئة → شرح علمي → تصحيح خرافة → تحويل منظور
- **تكييف المحتوى** لكل منصة تلقائياً (فيسبوك / إنستجرام / تويتر / ثريدز / لينكد إن)
- **6 مزودي AI** مع Failover تلقائي
- **Rotation مفاتيح** — عدة مفاتيح لكل مزود، تبديل تلقائي

### 🎨 توليد الصور
- **11 مزود صور** بالترتيب مع fallback تلقائي
- **معالجة الصور**: إطار شفاف + نص عربي على الصورة
- **5 خطوط عربية**: Cairo / Noto Naskh / Noto Kufi / Amiri / Tajawal
- **تحكم كامل**: موضع + إزاحة + حجم + لون + خلفية + ظل
- **AI يولد العنوان** تلقائياً من محتوى المنشور

### 📢 النشر على المنصات
- فيسبوك ✅ | إنستجرام ✅ | تويتر/X ✅ | ثريدز ✅ | لينكد إن ✅
- كل منصة مستقلة — فشل منصة لا يوقف الباقي
- التحقق من credentials قبل المحاولة

### 📊 التحليلات
- جلب engagement metrics حقيقية من كل منصة
- حساب engagement score تلقائي
- تحديث كل 6 ساعات
- تحليل أفضل أسلوب كتابة ونبرة
- رسوم بيانية تفاعلية

### 🗄️ التخزين
- **SQLite** — قاعدة البيانات الرئيسية
- **Redis** — حفظ الإعدادات بشكل دائم
- **Google Sheets** — backup ثنائي الاتجاه
- **Cloudinary** — رفع الصور مع حذف تلقائي

### 🤖 بوت تيليجرام
- لوحة تحكم كاملة بـ Inline Keyboards
- توليد أفكار / نشر منشور / عرض الإحصائيات
- تعديل البرومبتات مباشرةً
- إشعارات فورية

### ⚙️ الجدولة
- **APScheduler** — جدولة داخلية
- **PA Scheduled Tasks** — مهام مستقلة على PythonAnywhere
- **Auto-updater** — تحديث تلقائي من GitHub

## التثبيت السريع

```bash
git clone https://github.com/drnopoh2810-spec/social-post.git
cd social-post
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env  # أضف مفاتيحك
python run.py
```

افتح: `http://localhost:5000`

**بيانات الدخول الافتراضية:**
- اسم المستخدم: `admin`
- كلمة المرور: `admin123`

⚠️ **غيّرهم فوراً!**

## الدعم

- **المشاكل**: [GitHub Issues](https://github.com/drnopoh2810-spec/social-post/issues)
- **النقاشات**: [GitHub Discussions](https://github.com/drnopoh2810-spec/social-post/discussions)

---

<div align="center">

**صُنع بـ ❤️ في مصر**

[⭐ Star](https://github.com/drnopoh2810-spec/social-post) | [🐛 Report Bug](https://github.com/drnopoh2810-spec/social-post/issues) | [💡 Request Feature](https://github.com/drnopoh2810-spec/social-post/issues)

</div>

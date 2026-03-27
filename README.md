---
title: Social Post Manager — Enterprise-Grade AI Content Automation Platform
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
### Enterprise-Grade AI-Powered Content Automation Platform

[![CI](https://github.com/drnopoh2810-spec/social-post/actions/workflows/ci.yml/badge.svg)](https://github.com/drnopoh2810-spec/social-post/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)](https://flask.palletsprojects.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)

**An intelligent, end-to-end content automation platform for creating, managing, and publishing high-quality educational and scientific content across multiple social media platforms.**

[🚀 Quick Start](#quick-start) | [📖 Documentation](#documentation) | [🎯 Features](#features) | [🌐 Demo](#demo) | [💬 Community](#community)

</div>

---

## 📋 Table of Contents

<details>
<summary>Click to expand</summary>

- [Overview](#overview)
  - [What It Does](#what-it-does)
  - [Why Choose This Platform](#why-choose-this-platform)
  - [Use Cases](#use-cases)
- [Features](#features)
  - [AI Content Generation](#ai-content-generation)
  - [Image Generation & Processing](#image-generation--processing)
  - [Multi-Platform Publishing](#multi-platform-publishing)
  - [Analytics & Insights](#analytics--insights)
  - [Data Persistence](#data-persistence)
  - [Telegram Bot](#telegram-bot)
  - [Automation](#automation)
- [Architecture](#architecture)
  - [System Design](#system-design)
  - [Technology Stack](#technology-stack)
  - [Project Structure](#project-structure)
  - [Data Flow](#data-flow)
- [Quick Start](#quick-start)
- [Installation](#installation)
  - [Local Development](#local-development)
  - [Docker](#docker)
  - [PythonAnywhere](#pythonanywhere)
  - [HuggingFace Spaces](#huggingface-spaces)
  - [Cloud Platforms](#cloud-platforms)
- [Configuration](#configuration)
  - [Environment Variables](#environment-variables)
  - [AI Providers](#ai-providers)
  - [Social Platforms](#social-platforms)
  - [Advanced Settings](#advanced-settings)
- [Usage](#usage)
  - [Web Dashboard](#web-dashboard)
  - [API Reference](#api-reference)
  - [Telegram Bot](#telegram-bot-usage)
  - [CLI Tools](#cli-tools)
- [Development](#development)
  - [Setup Development Environment](#setup-development-environment)
  - [Running Tests](#running-tests)
  - [Code Style](#code-style)
  - [Contributing](#contributing)
- [Deployment](#deployment)
- [Monitoring & Maintenance](#monitoring--maintenance)
- [Security](#security)
- [Performance](#performance)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)
- [Roadmap](#roadmap)
- [Changelog](#changelog)
- [License](#license)
- [Acknowledgments](#acknowledgments)
- [Support](#support)

</details>

---

<a name="overview"></a>
## 🌟 Overview

**Social Post Manager** is a production-ready, enterprise-grade platform that revolutionizes content creation and distribution for educational and scientific content creators. Built with modern Python technologies and integrated with cutting-edge AI services, it automates the entire content lifecycle from ideation to publication and analytics.


### What It Does

```mermaid
graph LR
    A[Idea Generation] --> B[Content Writing]
    B --> C[Image Creation]
    C --> D[Platform Publishing]
    D --> E[Analytics Collection]
    E --> F[Performance Insights]
    F --> A
```

1. **🧠 Intelligent Ideation**: AI generates unique, data-driven content ideas based on performance analytics and topic saturation analysis
2. **✍️ Expert Writing**: Creates long-form, scientifically accurate content in Egyptian Arabic dialect with 4-layer structure
3. **🎨 Visual Creation**: Generates contextual images using 11 AI providers with advanced text overlay capabilities
4. **📢 Multi-Platform Distribution**: Publishes to 5 major social platforms with platform-specific optimizations
5. **📊 Real-Time Analytics**: Collects engagement metrics and provides actionable insights
6. **🔄 Continuous Optimization**: Uses performance data to improve future content generation

### Why Choose This Platform

| Feature | Social Post Manager | Traditional Tools | Manual Process |
|---------|-------------------|------------------|----------------|
| **Content Generation** | AI-powered, data-driven | Template-based | Manual writing |
| **Multi-Platform** | 5 platforms, 1 click | One at a time | Copy-paste each |
| **Image Creation** | 11 AI providers + overlay | Stock photos | Design tools |
| **Analytics** | Real-time, automated | Manual export | Spreadsheets |
| **Scheduling** | Intelligent automation | Basic timers | Manual posting |
| **Scalability** | Unlimited posts | Limited | Time-consuming |
| **Cost** | Open-source, free | Subscription fees | Time = money |
| **Customization** | Fully customizable | Limited options | N/A |

### Use Cases

#### 🎓 Educational Content Creators
- **Special Education Specialists**: Share insights, research, and practical tips
- **Academic Researchers**: Disseminate findings to broader audiences
- **Online Educators**: Maintain consistent content schedule across platforms

#### 🏢 Organizations & NGOs
- **Non-Profits**: Raise awareness about causes with engaging content
- **Healthcare Organizations**: Share medical information in accessible language
- **Educational Institutions**: Promote programs and share knowledge

#### 📱 Social Media Managers
- **Content Agencies**: Manage multiple clients efficiently
- **Influencers**: Maintain consistent posting schedule
- **Brand Managers**: Ensure brand voice consistency across platforms

#### 🔬 Research Institutions
- **Science Communicators**: Translate complex research into digestible content
- **Think Tanks**: Share policy insights and analysis
- **Innovation Labs**: Showcase discoveries and breakthroughs

---

<a name="features"></a>
## ✨ Features

### 🤖 AI Content Generation

#### Idea Factory Engine

The Idea Factory is an intelligent content ideation system that analyzes your content history and generates unique, high-performing ideas.

**Key Capabilities:**
- **Performance-Based Learning**: Analyzes top 5 and bottom 5 posts to understand what works
- **Topic Saturation Detection**: Identifies overused themes and avoids repetition
- **Diversity Enforcement**: Distributes ideas across 5 content types:
  1. 📊 **Research-Based Analysis**: Scientific studies with practical applications
  2. 🔍 **Myth-Busting**: Corrects misconceptions with evidence
  3. 🧬 **Mechanism Explanation**: Deep dives into how things work
  4. 📖 **Case Studies**: Real-world examples with lessons learned
  5. 💭 **Critical Thinking**: Thought-provoking questions and comparisons

**Smart Features:**
- Recent idea tracking (7-day window)
- Full archive analysis (zero duplication)
- Style and opening type rotation
- Keyword optimization
- Engagement score prediction

**Configuration:**
```python
# Customizable parameters
IDEAS_PER_BATCH = 10
CONTENT_TYPE_DISTRIBUTION = {
    'research': 2,
    'myth_busting': 2,
    'mechanism': 2,
    'case_study': 2,
    'critical_thinking': 2
}
SATURATION_THRESHOLD = 3  # Max posts per topic
```


#### Post Writer Engine

The Post Writer creates long-form, scientifically accurate content with a unique 4-layer structure designed for maximum engagement and educational value.

**4-Layer Content Structure:**

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 1: Quiet Observation (2-3 sentences)                  │
│ ─────────────────────────────────────────────────────────── │
│ • Field-based opening without clickbait                      │
│ • Real, specific, recognizable moment                        │
│ • Draws curiosity through authenticity                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Layer 2: Scientific Explanation (50-60% of content)         │
│ ─────────────────────────────────────────────────────────── │
│ • Deep dive into mechanisms (neurological/psychological)     │
│ • Latest research and statistics                             │
│ • Egyptian analogies for complex concepts                    │
│ • Makes invisible visible                                    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Layer 3: Myth Correction (15-20% of content)                │
│ ─────────────────────────────────────────────────────────── │
│ • Identifies common misconception                            │
│ • Provides scientific evidence                               │
│ • Explains why the myth exists                               │
│ • Gentle correction without judgment                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Layer 4: Perspective Shift (1-2 sentences)                  │
│ ─────────────────────────────────────────────────────────── │
│ • Reframes reader's understanding                            │
│ • Opens door for reflection                                  │
│ • NOT a call-to-action                                       │
└─────────────────────────────────────────────────────────────┘
```

**Writing Specifications:**
- **Language**: Pure Egyptian Arabic colloquial dialect (zero Fusha)
- **Length**: 700-1,100 words (long-form, value-packed)
- **Tone**: Combines academic depth with conversational warmth
- **Style**: 10 available styles (field observer, scientific analyst, gentle critic, etc.)
- **Opening Types**: 10 types (field scene, silent question, counter-intuitive observation, etc.)
- **Emojis**: 18-25 functional emojis (not decorative)
- **Hashtags**: 3-5 niche-specific tags

**Quality Controls:**
- ✅ No clickbait or sensationalism
- ✅ No promotional content
- ✅ No fabricated stories
- ✅ No markdown formatting in output
- ✅ No section headers visible to reader
- ✅ Scientifically accurate and verifiable
- ✅ Accessible to all education levels


#### Platform Adaptation Engine

Automatically adapts content for each platform's unique requirements and audience expectations.

| Platform | Adaptation Strategy | Max Length | Special Features |
|----------|-------------------|------------|------------------|
| **Facebook** | Full post | 1,100 words | Complete 4-layer structure |
| **Instagram** | Caption format | 2,200 chars | 8-15 hashtags, emoji-rich |
| **Twitter/X** | Concise hook | 270 chars | Thread-starter, 1-2 hashtags |
| **Threads** | Conversational | 500 chars | Ends with open question |
| **LinkedIn** | Professional English | 2,800 chars | Global context, formal tone |

**LinkedIn Transformation:**
- Translates Egyptian Arabic → Professional American English
- Adapts cultural references for global audience
- Maintains scientific accuracy
- Adds professional hashtags
- Preserves core message and structure

#### AI Provider Chain

**6 Text AI Providers** with intelligent failover and load balancing:

```
┌─────────────────────────────────────────────────────────────┐
│                    AI Provider Chain                         │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  1. 🔵 Gemini (Primary)                                      │
│     ├─ gemini-2.0-flash-exp (fastest)                       │
│     ├─ gemini-2.0-flash                                      │
│     └─ gemini-1.5-pro (most capable)                        │
│                                                               │
│  2. 🟣 Cohere (Arabic Specialist)                           │
│     ├─ command-r7b-arabic-02-2025 (Arabic-optimized)       │
│     └─ command-r-plus-08-2024 (multilingual)               │
│                                                               │
│  3. 🟠 Groq (Speed Champion)                                │
│     ├─ llama-3.3-70b-versatile                             │
│     └─ mixtral-8x7b-32768                                   │
│                                                               │
│  4. 🔴 OpenRouter (Model Aggregator)                        │
│     └─ Access to 100+ models                                │
│                                                               │
│  5. 🛩️ api.airforce (Free Tier)                            │
│     └─ No key required                                       │
│                                                               │
│  6. 🟢 OpenAI (Premium Fallback)                            │
│     ├─ gpt-4o (most capable)                                │
│     └─ gpt-4o-mini (cost-effective)                         │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

**Key Rotation Logic:**
1. **Priority-Based Selection**: Keys sorted by priority (1-10)
2. **Health Checking**: Validates key before use
3. **Automatic Rotation**: Switches to next key on quota exhaustion
4. **Provider Failover**: Moves to next provider if all keys fail
5. **Usage Tracking**: Monitors API calls per key
6. **Cost Optimization**: Prefers free/cheaper providers when possible

**Configuration Example:**
```python
# Multiple keys per provider
GEMINI_KEYS = [
    {'key': 'key1', 'priority': 1, 'is_active': True},
    {'key': 'key2', 'priority': 2, 'is_active': True},
    {'key': 'key3', 'priority': 3, 'is_active': True}
]

# Automatic failover chain
AI_PROVIDER_CHAIN = ['gemini', 'cohere', 'groq', 'openrouter', 'airforce', 'openai']
```


---

### 🎨 Image Generation & Processing

#### Multi-Provider Image Generation

**11 Image Providers** in priority order with automatic fallback:

```
Priority Chain (First Success Wins):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. ☁️  Cloudflare Worker (Flux 2)
   • Speed: ⚡⚡⚡⚡⚡ (Fastest)
   • Quality: ⭐⭐⭐⭐⭐
   • Cost: Free with worker
   • Requires: WORKER_URL

2. 🔵 Google Imagen 4 (via Gemini)
   • Speed: ⚡⚡⚡⚡
   • Quality: ⭐⭐⭐⭐⭐
   • Cost: Free with Gemini key
   • Requires: GEMINI_API_KEY

3. 🎨 Ideogram v3
   • Speed: ⚡⚡⚡
   • Quality: ⭐⭐⭐⭐⭐ (Best for Arabic text)
   • Cost: Paid
   • Requires: IDEOGRAM_API_KEY

4. 🟢 OpenAI (gpt-image-1 / DALL-E 3)
   • Speed: ⚡⚡⚡
   • Quality: ⭐⭐⭐⭐⭐
   • Cost: Paid ($0.04/image)
   • Requires: OPENAI_API_KEY

5. 🔷 Stability AI (SD 3.5)
   • Speed: ⚡⚡⚡⚡
   • Quality: ⭐⭐⭐⭐
   • Cost: Paid
   • Requires: STABILITY_API_KEY

6. 🤗 HuggingFace (Flux Schnell)
   • Speed: ⚡⚡⚡
   • Quality: ⭐⭐⭐⭐
   • Cost: Free tier available
   • Requires: HF_API_KEY

7. 🔗 Together AI (Flux Free)
   • Speed: ⚡⚡⚡⚡
   • Quality: ⭐⭐⭐⭐
   • Cost: Free tier
   • Requires: TOGETHER_API_KEY

8. ⚡ Fal.ai (Flux Schnell)
   • Speed: ⚡⚡⚡⚡⚡
   • Quality: ⭐⭐⭐⭐
   • Cost: Pay-per-use
   • Requires: FAL_API_KEY

9. 🛩️ api.airforce
   • Speed: ⚡⚡⚡
   • Quality: ⭐⭐⭐
   • Cost: Free (no key)
   • Requires: Nothing

10. 🌸 Pollinations (Authenticated)
    • Speed: ⚡⚡⚡
    • Quality: ⭐⭐⭐⭐
    • Cost: Free with key
    • Requires: POLLINATIONS_KEY

11. 🌸 Pollinations (Anonymous)
    • Speed: ⚡⚡
    • Quality: ⭐⭐⭐
    • Cost: Always free
    • Requires: Nothing (Last Fallback)
```

**Provider Selection Algorithm:**
```python
def select_image_provider():
    for provider in IMAGE_PROVIDER_CHAIN:
        if has_valid_credentials(provider):
            try:
                image = generate_image(provider, prompt)
                if image:
                    return image, provider
            except QuotaExceeded:
                continue
            except ProviderError:
                continue
    # Pollinations anonymous always works
    return generate_image('pollinations_anon', prompt), 'pollinations'
```


#### Advanced Image Processing Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                  Image Processing Pipeline                   │
└─────────────────────────────────────────────────────────────┘

Step 1: AI Generation
├─ Input: Scientific prompt (300-450 words)
├─ Style: Documentary/editorial photography
├─ Technical: Kodak Portra 400 aesthetic
├─ Format: Portrait 1080×1350px (configurable)
└─ Output: Base image (JPEG/PNG)
         ↓
Step 2: Frame Overlay (Optional)
├─ Input: Transparent PNG frame
├─ Opacity: 0-100% (configurable)
├─ Blending: Alpha compositing
└─ Output: Framed image
         ↓
Step 3: Text Overlay (Optional)
├─ Text Source:
│  ├─ AI-generated (extracts key sentence)
│  ├─ First line of post
│  └─ Custom static text
├─ Typography:
│  ├─ Font: 5 Arabic fonts
│  ├─ Size: 20-120px
│  ├─ Color: Any hex color
│  └─ Alignment: RTL for Arabic
├─ Positioning:
│  ├─ 9 preset positions
│  ├─ Pixel-perfect offset (X/Y)
│  └─ Responsive to image size
├─ Background (Optional):
│  ├─ Color: Any hex color
│  ├─ Opacity: 0-100%
│  ├─ Padding: 5-60px
│  └─ Border radius: Auto
└─ Shadow (Optional):
   ├─ Color: Any hex color
   ├─ Offset: 1-15px
   └─ Blur: Auto-calculated
         ↓
Step 4: Upload & Optimize
├─ Compression: Smart JPEG optimization
├─ Upload: Cloudinary CDN
├─ URL: Permanent link
└─ Auto-delete: After successful publish
```

#### Text Overlay System

**5 Professional Arabic Fonts:**

| Font | Style | Best For | Character Set |
|------|-------|----------|---------------|
| **Cairo** | Modern, clean | Headlines, body text | Arabic, Latin, numerals |
| **Noto Naskh** | Traditional Naskh | Classical content | Full Arabic Unicode |
| **Noto Kufi** | Modern Kufi | Bold statements | Full Arabic Unicode |
| **Amiri** | Classical serif | Formal content | Arabic, Latin |
| **Tajawal** | Simple, readable | Casual content | Arabic, Latin |

**Text Extraction AI:**
```python
# Intelligent text extraction from post content
def extract_overlay_text(post_content, idea):
    """
    AI analyzes post and extracts most impactful sentence.
    
    Criteria:
    - 5-10 words maximum
    - Core message of post
    - Egyptian Arabic dialect
    - No clickbait phrases
    - Scientifically accurate
    """
    prompt = f"""
    Read this post and extract the strongest, most impactful sentence:
    
    {post_content[:500]}
    
    Rules:
    - Egyptian Arabic dialect only
    - 5-10 words maximum
    - From the post content (not external)
    - Summarizes main idea
    - No quotes, hashtags, emojis
    """
    return call_ai('gemini', 'gemini-2.0-flash', prompt)
```

**Positioning System:**
```
┌─────────────────────────────────────┐
│  ↖ top-left    ⬆ top-center    ↗   │
│                                     │
│  ← center-left  ⊙ center      →    │
│                                     │
│  ↙ bottom-left ⬇ bottom-center ↘   │
└─────────────────────────────────────┘

Plus pixel-perfect offset:
• X-axis: -500 to +500px (negative = left, positive = right)
• Y-axis: -500 to +500px (negative = up, positive = down)
```


#### Image Prompt Engineering

**Prompt Structure (300-450 words):**
```
[SUBJECT] + [CAMERA SETUP] + [LIGHTING] + [DEPTH] + [COLOR] + [PROPS] + [MOOD]

Example:
"A child's hands gently holding colorful educational flashcards, 
shot with 50mm lens at f/2.8 from slightly above, warm afternoon 
sunlight streaming from left creating soft shadows, three-plane 
composition with blurred bookshelf in background and wooden desk 
in foreground, Kodak Portra 400 color palette with warm beiges 
and soft blues, symbolic props include pencils and notebook, 
documentary photography style reminiscent of Magnum Photos, 
authentic and unposed, clean upper third for text overlay, 
ISO 400 film grain texture, Hasselblad color science"
```

**Strict Restrictions:**
- ❌ NO text in image (Arabic, English, or any language)
- ❌ NO full faces (partial only: hands, back, shoulder)
- ❌ NO logos, watermarks, brand names
- ❌ NO commercial/advertising aesthetic
- ❌ NO staged or posed setups
- ✅ Documentary/editorial feel only
- ✅ Negative space for text overlay
- ✅ Single dominant focal point
- ✅ Readable at thumbnail size

---

### 📢 Multi-Platform Publishing

#### Platform Integration Matrix

| Feature | Facebook | Instagram | Twitter/X | Threads | LinkedIn |
|---------|----------|-----------|-----------|---------|----------|
| **API Version** | Graph v20 | Graph v20 | API v2 | Threads v1 | UGC Posts |
| **Auth Method** | Page Token | Business Token | OAuth 1.0a | Meta Token | OAuth 2.0 |
| **Image Upload** | ✅ Direct | ✅ Container | ✅ Media | ✅ Container | ✅ Asset |
| **Text Length** | Unlimited | 2,200 chars | 280 chars | 500 chars | 3,000 chars |
| **Hashtags** | Unlimited | 30 max | 2-3 optimal | None | 3-5 optimal |
| **Link Preview** | ✅ Auto | ❌ No | ✅ Auto | ✅ Auto | ✅ Auto |
| **Scheduling** | ✅ Native | ✅ Native | ❌ No | ❌ No | ❌ No |
| **Analytics** | ✅ Full | ✅ Insights | ✅ Metrics | ✅ Basic | ✅ Stats |
| **Rate Limits** | 200/hour | 25/hour | 300/15min | 250/hour | 100/day |

#### Publishing Workflow

```python
async def publish_to_all_platforms(post):
    """
    Publishes to all enabled platforms concurrently.
    Platform failures don't affect others.
    """
    results = {}
    platforms = get_enabled_platforms()
    
    # Concurrent publishing
    tasks = [
        publish_to_facebook(post) if 'facebook' in platforms else None,
        publish_to_instagram(post) if 'instagram' in platforms else None,
        publish_to_twitter(post) if 'twitter' in platforms else None,
        publish_to_threads(post) if 'threads' in platforms else None,
        publish_to_linkedin(post) if 'linkedin' in platforms else None,
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Log results
    for platform, result in zip(platforms, results):
        if isinstance(result, Exception):
            log_error(f"{platform} failed: {result}")
        else:
            log_success(f"{platform} published: {result['post_id']}")
    
    return results
```


#### Platform-Specific Features

**Facebook:**
- Page posts with full formatting
- Photo albums support
- Link previews with custom thumbnails
- Scheduled publishing
- Audience targeting
- Post boosting integration

**Instagram:**
- Business/Creator accounts only
- Carousel posts (up to 10 images)
- Story integration (future)
- Shopping tags (future)
- Location tagging
- User tagging

**Twitter/X:**
- Thread support (future)
- Poll integration (future)
- Media alt text
- Tweet scheduling via external
- Retweet tracking
- Quote tweet monitoring

**Threads:**
- Native Meta integration
- Reply threading
- Quote posts
- Link cards
- Media attachments
- Cross-posting from Instagram

**LinkedIn:**
- Personal and company pages
- Article publishing
- Document uploads
- Video posts (future)
- Professional hashtags
- Industry targeting

---

### 📊 Analytics & Insights

#### Real-Time Metrics Collection

**Auto-Fetch Schedule:**
```
Initial: Immediately after publish
Update 1: After 1 hour
Update 2: After 6 hours
Update 3: After 24 hours
Update 4: After 7 days
Ongoing: Every 6 hours for 30 days
```

**Engagement Score Formula:**
```python
engagement_score = (
    likes × 1.0 +
    comments × 3.0 +
    shares × 5.0 +
    saves × 4.0 +
    clicks × 0.5
)

# Weighted by platform reach
normalized_score = engagement_score / follower_count × 1000
```

**Platform-Specific Metrics:**

| Platform | Metrics Collected | API Endpoint |
|----------|------------------|--------------|
| **Facebook** | likes, comments, shares, reactions, reach, impressions | `/posts/{id}/insights` |
| **Instagram** | likes, comments, saves, reach, impressions, profile_visits | `/media/{id}/insights` |
| **Twitter** | likes, retweets, replies, quotes, impressions, url_clicks | `/tweets/{id}/metrics` |
| **Threads** | likes, replies, quotes, reposts | `/threads/{id}/insights` |
| **LinkedIn** | likes, comments, shares, impressions, clicks, engagement_rate | `/ugcPosts/{id}/statistics` |

#### Performance Analysis Dashboard

**Key Metrics:**
- 📈 Total Engagement Score
- 🎯 Average Engagement Rate
- 🏆 Top 5 Performing Posts
- 📉 Bottom 5 Posts (for learning)
- 🎨 Best Writing Style
- 🎭 Best Emotional Tone
- 📅 Best Publishing Time
- 🌐 Best Platform Performance

**Visualization:**
```javascript
// Chart.js integration
const engagementChart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: dates,
        datasets: [{
            label: 'Engagement Score',
            data: scores,
            borderColor: 'rgb(99, 102, 241)',
            tension: 0.4
        }]
    },
    options: {
        responsive: true,
        plugins: {
            title: {
                display: true,
                text: 'Engagement Trend (Last 30 Days)'
            }
        }
    }
});
```


---

<a name="architecture"></a>
## 🏗️ Architecture

### System Design

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          SOCIAL POST MANAGER                                 │
│                        Enterprise Architecture                               │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                              PRESENTATION LAYER                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ Web Dashboard│  │  REST API    │  │ Telegram Bot │  │  CLI Tools   │   │
│  │  (Jinja2)    │  │  (Flask)     │  │ (python-tg)  │  │  (Click)     │   │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘   │
│         │                  │                  │                  │           │
└─────────┼──────────────────┼──────────────────┼──────────────────┼───────────┘
          │                  │                  │                  │
┌─────────┼──────────────────┼──────────────────┼──────────────────┼───────────┐
│         │                  │                  │                  │           │
│         └──────────────────┴──────────────────┴──────────────────┘           │
│                                    │                                          │
│                         ┌──────────▼──────────┐                              │
│                         │   BUSINESS LOGIC    │                              │
│                         │   (Services Layer)  │                              │
│                         └──────────┬──────────┘                              │
│                                    │                                          │
│         ┌──────────────────────────┼──────────────────────────┐             │
│         │                          │                           │             │
│    ┌────▼─────┐  ┌────────────┐  ┌▼──────────┐  ┌──────────▼────┐         │
│    │AI Service│  │   Image    │  │  Social   │  │   Analytics   │         │
│    │(6 provs) │  │  Service   │  │  Service  │  │    Service    │         │
│    └────┬─────┘  │(11 provs)  │  │(5 platf)  │  └───────────────┘         │
│         │        └────┬───────┘  └────┬──────┘                              │
│         │             │               │                                      │
│    ┌────▼─────────────▼───────────────▼────┐                                │
│    │      Key Rotator & Failover Logic     │                                │
│    └────────────────────────────────────────┘                                │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼───────────────────────────────────────────┐
│                              DATA LAYER                                        │
├───────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   SQLite     │  │    Redis     │  │Google Sheets │  │  Cloudinary  │    │
│  │  (Primary)   │  │  (Config)    │  │   (Backup)   │  │   (Images)   │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼───────────────────────────────────────────┐
│                          EXTERNAL SERVICES                                     │
├───────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  AI Providers│  │Image Providers│  │Social Platforms│  │  Monitoring │    │
│  │  (6 APIs)    │  │  (11 APIs)    │  │   (5 APIs)    │  │   (Logs)    │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘
```

### Technology Stack

#### Backend
```yaml
Core Framework:
  - Flask 3.0.0: Web framework
  - SQLAlchemy 2.0: ORM
  - Flask-Login: Authentication
  - Flask-CORS: Cross-origin support

Task Scheduling:
  - APScheduler 3.10: Background jobs
  - Threading: Concurrent operations
  - Asyncio: Async operations

Database:
  - SQLite: Primary database
  - Redis: Config persistence
  - Google Sheets API: Backup sync
```

#### AI & ML
```yaml
Text Generation:
  - Google Gemini API
  - Cohere API
  - Groq API
  - OpenRouter API
  - OpenAI API
  - api.airforce

Image Generation:
  - Cloudflare Workers (Flux)
  - Google Imagen 4
  - Ideogram v3
  - OpenAI DALL-E 3
  - Stability AI
  - HuggingFace Inference
  - Together AI
  - Fal.ai
  - Pollinations

Image Processing:
  - Pillow (PIL): Image manipulation
  - OpenCV: Advanced processing
  - ImageMagick: Format conversion
```

#### Social Media APIs
```yaml
Meta Platforms:
  - Facebook Graph API v20
  - Instagram Graph API v20
  - Threads API v1

Twitter:
  - Twitter API v2
  - Tweepy 4.14

LinkedIn:
  - LinkedIn API v2
  - UGC Posts API
```

#### Storage & CDN
```yaml
Primary Storage:
  - SQLite: Structured data
  - Redis (Upstash): Key-value cache

File Storage:
  - Cloudinary: Image CDN
  - Local filesystem: Temporary files

Backup:
  - Google Sheets: Config backup
  - JSON exports: Database dumps
```

#### Frontend
```yaml
Templates:
  - Jinja2: Server-side rendering
  - HTML5: Semantic markup
  - CSS3: Modern styling

JavaScript:
  - Vanilla JS: No framework overhead
  - Chart.js: Data visualization
  - Fetch API: AJAX requests

UI Components:
  - Custom CSS: Responsive design
  - CSS Variables: Theming
  - Flexbox/Grid: Layouts
```

#### DevOps & Deployment
```yaml
Containerization:
  - Docker: Container runtime
  - Docker Compose: Multi-container

CI/CD:
  - GitHub Actions: Automation
  - Automated testing
  - Auto-deployment

Hosting Options:
  - PythonAnywhere: Production
  - HuggingFace Spaces: Demo
  - Railway: Cloud deployment
  - Render: Cloud deployment
  - Heroku: Cloud deployment
  - Self-hosted: VPS/dedicated

Monitoring:
  - Python logging: Application logs
  - Workflow logs: Database tracking
  - Error tracking: Exception handling
```


---

<a name="quick-start"></a>
## 🚀 Quick Start

Get up and running in 5 minutes:

```bash
# 1. Clone repository
git clone https://github.com/drnopoh2810-spec/social-post.git
cd social-post

# 2. Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Setup environment
cp .env.example .env
echo "SECRET_KEY=$(openssl rand -hex 32)" >> .env
echo "GEMINI_API_KEY=your-key-here" >> .env

# 5. Initialize database
python -c "from app import create_app; app = create_app('development'); \
app.app_context().push(); from database.models import db; db.create_all()"

# 6. Run application
python run.py
```

Open browser: **http://localhost:5000**

Login with:
- Username: `admin`
- Password: `admin123`

⚠️ **Change credentials immediately after first login!**

---

<a name="installation"></a>
## 📦 Installation

### Prerequisites

| Requirement | Version | Purpose |
|-------------|---------|---------|
| **Python** | 3.11+ | Runtime environment |
| **pip** | Latest | Package management |
| **Git** | Latest | Version control |
| **Redis** | 7.0+ (Optional) | Config persistence |
| **PostgreSQL** | 14+ (Optional) | Production database |

### Local Development

#### Step 1: Clone Repository

```bash
git clone https://github.com/drnopoh2810-spec/social-post.git
cd social-post
```

#### Step 2: Create Virtual Environment

**Linux/macOS:**
```bash
python3.11 -m venv venv
source venv/bin/activate
```

**Windows:**
```cmd
python -m venv venv
venv\Scripts\activate
```

#### Step 3: Install Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt

# Install development dependencies (optional)
pip install -r requirements-dev.txt
```

#### Step 4: Environment Configuration

```bash
# Copy template
cp .env.example .env

# Generate secret key
python -c "import secrets; print(f'SECRET_KEY={secrets.token_hex(32)}')" >> .env

# Edit configuration
nano .env  # or use your preferred editor
```

**Minimum Required Variables:**
```bash
SECRET_KEY=your-generated-secret-key
FLASK_ENV=development
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-secure-password
GEMINI_API_KEY=your-gemini-key  # Free tier available
```

#### Step 5: Database Initialization

```bash
# Initialize SQLite database
python -c "
from app import create_app
app = create_app('development')
with app.app_context():
    from database.models import db
    db.create_all()
    print('✅ Database initialized successfully')
"
```

#### Step 6: Run Development Server

```bash
# Start Flask development server
python run.py

# Or with debug mode
FLASK_DEBUG=1 python run.py

# Or with custom host/port
python run.py --host 0.0.0.0 --port 8000
```

**Access Application:**
- Web UI: http://localhost:5000
- API Docs: http://localhost:5000/api/docs (future)
- Health Check: http://localhost:5000/health


---

### Docker Deployment

#### Using Docker Compose (Recommended)

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "7860:7860"
    environment:
      - FLASK_ENV=production
      - SECRET_KEY=${SECRET_KEY}
      - REDIS_URL=redis://redis:6379/0
    env_file:
      - .env
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    depends_on:
      - redis
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped

volumes:
  redis_data:
```

**Commands:**
```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop services
docker-compose down

# Rebuild after changes
docker-compose up -d --build
```

#### Using Docker Only

```bash
# Build image
docker build -t social-post:latest .

# Run container
docker run -d \
  --name social-post \
  -p 7860:7860 \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  social-post:latest

# View logs
docker logs -f social-post

# Stop container
docker stop social-post

# Remove container
docker rm social-post
```

---

### PythonAnywhere Deployment

#### Step 1: Upload Files

```bash
# On your local machine
git clone https://github.com/drnopoh2810-spec/social-post.git
cd social-post
tar -czf social-post.tar.gz .

# Upload to PythonAnywhere via Files tab
# Or use rsync/scp
```

#### Step 2: Setup Environment

```bash
# In PythonAnywhere Bash Console
cd ~
tar -xzf social-post.tar.gz -C social-post
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

#### Step 3: Configure WSGI

**Web tab → WSGI configuration file:**

```python
import sys
import os
from pathlib import Path

# Project directory
project_home = '/home/YOUR_USERNAME/social-post'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Load environment variables
from dotenv import load_dotenv
env_path = Path(project_home) / '.env'
load_dotenv(dotenv_path=env_path)

# Set Flask environment
os.environ.setdefault('FLASK_ENV', 'production')
os.environ.setdefault('PYTHONUNBUFFERED', '1')

# Import Flask application
from app import create_app
application = create_app('production')

# Logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

#### Step 4: Configure Static Files

**Web tab → Static files:**

| URL | Directory |
|-----|-----------|
| `/static/` | `/home/YOUR_USERNAME/social-post/static/` |

#### Step 5: Setup Scheduled Tasks

**Tasks tab:**

**Task 1 - Generate Ideas (Daily 08:00 UTC):**
```bash
/home/YOUR_USERNAME/social-post/venv/bin/python \
/home/YOUR_USERNAME/social-post/pa_task_ideas.py
```

**Task 2 - Publish Post (Daily 09:00 UTC):**
```bash
/home/YOUR_USERNAME/social-post/venv/bin/python \
/home/YOUR_USERNAME/social-post/pa_task_post.py
```

**Task 3 - Refresh Analytics (Every 6 hours):**
```bash
/home/YOUR_USERNAME/social-post/venv/bin/python \
/home/YOUR_USERNAME/social-post/pa_task_analytics.py
```

#### Step 6: Reload Web App

Click **Reload** button in Web tab.

**Access your app:**
```
https://YOUR_USERNAME.pythonanywhere.com
```

---

### HuggingFace Spaces Deployment

#### Step 1: Create Space

1. Go to [HuggingFace Spaces](https://huggingface.co/spaces)
2. Click **Create new Space**
3. Choose **Docker** as SDK
4. Name your space
5. Choose visibility (Public/Private)

#### Step 2: Configure Repository

**Clone and push:**
```bash
git clone https://github.com/drnopoh2810-spec/social-post.git
cd social-post

# Add HuggingFace remote
git remote add hf https://huggingface.co/spaces/YOUR_USERNAME/YOUR_SPACE

# Push to HuggingFace
git push hf main
```

#### Step 3: Configure Secrets

**Settings → Repository secrets:**

```bash
# Required
SECRET_KEY=your-secret-key-here
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-password
FLASK_ENV=production
REDIS_URL=rediss://default:token@host:port

# AI Providers (at least one)
GEMINI_API_KEY=your-key
COHERE_API_KEY=your-key
GROQ_API_KEY=your-key

# Image Storage
CLOUDINARY_CLOUD_NAME=your-cloud
CLOUDINARY_API_KEY=your-key
CLOUDINARY_API_SECRET=your-secret

# Social Platforms (optional)
FB_PAGE_ID=your-page-id
FB_ACCESS_TOKEN=your-token
# ... add others as needed
```

#### Step 4: Deploy

Push changes to trigger deployment:
```bash
git add .
git commit -m "Deploy to HuggingFace"
git push hf main
```

**Access your space:**
```
https://huggingface.co/spaces/YOUR_USERNAME/YOUR_SPACE
```

---

<a name="configuration"></a>
## ⚙️ Configuration

### Environment Variables Reference

#### Application Core

```bash
# Flask Configuration
SECRET_KEY=your-secret-key-here          # Required: Session encryption
FLASK_ENV=production                      # development|production|testing
FLASK_DEBUG=0                             # 0|1 (disable in production)
LOG_LEVEL=INFO                            # DEBUG|INFO|WARNING|ERROR|CRITICAL

# Authentication
ADMIN_USERNAME=admin                      # Default admin username
ADMIN_PASSWORD=your-secure-password       # Change immediately!

# Database
DATABASE_URL=sqlite:///social_post.db     # SQLite (default)
# DATABASE_URL=postgresql://user:pass@host:5432/dbname  # PostgreSQL

# Redis (Optional but recommended)
REDIS_URL=redis://localhost:6379/0        # Local Redis
# REDIS_URL=rediss://default:token@host:port  # Upstash Redis
```


---

## 📚 Complete Documentation

For detailed documentation, visit our [Wiki](https://github.com/drnopoh2810-spec/social-post/wiki) or check these guides:

- [📖 User Guide](docs/USER_GUIDE.md) - Complete usage instructions
- [🔧 API Reference](docs/API_REFERENCE.md) - REST API documentation
- [🎨 Customization Guide](docs/CUSTOMIZATION.md) - Customize prompts and behavior
- [🚀 Deployment Guide](docs/DEPLOYMENT.md) - Production deployment best practices
- [🔐 Security Guide](docs/SECURITY.md) - Security considerations
- [🐛 Troubleshooting](docs/TROUBLESHOOTING.md) - Common issues and solutions
- [📊 Analytics Guide](docs/ANALYTICS.md) - Understanding metrics
- [🤖 AI Configuration](docs/AI_CONFIG.md) - AI provider setup
- [🎭 Platform Setup](docs/PLATFORMS.md) - Social platform configuration

---

<a name="faq"></a>
## ❓ FAQ

<details>
<summary><b>Q: Do I need all AI provider keys?</b></summary>

No! You only need **one** AI provider key to get started. We recommend:
- **Gemini** (Free tier, best for Arabic)
- **Cohere** (Free trial, Arabic-optimized)
- **Groq** (Free tier, very fast)

The system will automatically use available providers.
</details>

<details>
<summary><b>Q: Can I use this without social media accounts?</b></summary>

Yes! You can:
- Generate ideas and content
- Create images
- Export content for manual posting
- Test all features locally

Social platform integration is optional.
</details>

<details>
<summary><b>Q: How much does it cost to run?</b></summary>

**Free Option:**
- Use free AI providers (Gemini, Groq, api.airforce)
- Use Pollinations for images (no key needed)
- Host on PythonAnywhere free tier
- Total cost: $0/month

**Recommended Setup:**
- Gemini API: Free tier (60 requests/minute)
- Cloudinary: Free tier (25GB storage)
- Upstash Redis: Free tier (10K commands/day)
- PythonAnywhere: $5/month
- Total cost: ~$5/month
</details>

<details>
<summary><b>Q: Can I customize the content style?</b></summary>

Absolutely! You can customize:
- AI prompts (via UI or `prompts_config.py`)
- Writing styles and tones
- Content length and structure
- Language and dialect
- Image styles and aesthetics
- Text overlay design

Everything is configurable!
</details>

<details>
<summary><b>Q: Is my data secure?</b></summary>

Yes:
- All data stored locally (SQLite)
- API keys encrypted in database
- HTTPS for all external communications
- No data sent to third parties (except AI/social APIs)
- Open source - audit the code yourself
- Self-hosted option available
</details>

<details>
<summary><b>Q: Can I use this for commercial purposes?</b></summary>

Yes! MIT License allows:
- Commercial use
- Modification
- Distribution
- Private use

Just maintain the license notice.
</details>

<details>
<summary><b>Q: How do I update to the latest version?</b></summary>

```bash
cd social-post
git pull origin main
pip install -r requirements.txt --upgrade
python -c "from app import create_app; app = create_app(); \
app.app_context().push(); from database.models import db; db.create_all()"
```

Or enable auto-updater in settings (HuggingFace only).
</details>

<details>
<summary><b>Q: Can I contribute to the project?</b></summary>

Yes! We welcome contributions:
- Bug reports and fixes
- Feature requests and implementations
- Documentation improvements
- Translations
- Testing and feedback

See [Contributing](#contributing) section.
</details>

---

<a name="roadmap"></a>
## 🗺️ Roadmap

### Version 2.0 (Q2 2025)

- [ ] **Video Generation**
  - AI-generated short videos for Reels/Shorts
  - Text-to-video with Runway/Pika
  - Auto-captioning and subtitles

- [ ] **Advanced Analytics**
  - ML-based performance prediction
  - Sentiment analysis of comments
  - Competitor analysis
  - Optimal posting time prediction

- [ ] **Multi-Language Support**
  - English content generation
  - French, Spanish, German support
  - Auto-translation with quality check

- [ ] **Team Collaboration**
  - Multi-user support
  - Role-based access control
  - Approval workflows
  - Content calendar

### Version 2.5 (Q3 2025)

- [ ] **A/B Testing**
  - Test multiple post variations
  - Automatic winner selection
  - Performance comparison

- [ ] **Content Calendar**
  - Visual calendar interface
  - Drag-and-drop scheduling
  - Bulk operations
  - Template library

- [ ] **Advanced Image Features**
  - Video thumbnail generation
  - GIF creation
  - Image carousels
  - Brand watermarking

- [ ] **API Enhancements**
  - GraphQL API
  - Webhook support
  - Rate limiting
  - API documentation (Swagger)

### Version 3.0 (Q4 2025)

- [ ] **Mobile App**
  - React Native iOS/Android app
  - Push notifications
  - Offline mode
  - Quick posting

- [ ] **Browser Extension**
  - Chrome/Firefox extension
  - Quick post from any page
  - Screenshot to post
  - Bookmark to idea

- [ ] **AI Improvements**
  - Fine-tuned models for niche
  - Custom AI training
  - Voice-to-post
  - Image-to-post

- [ ] **Enterprise Features**
  - White-label option
  - Custom branding
  - SLA support
  - Dedicated infrastructure

### Community Requests

Vote for features on [GitHub Discussions](https://github.com/drnopoh2810-spec/social-post/discussions)!

---

<a name="changelog"></a>
## 📝 Changelog

### [1.5.0] - 2024-12-15

#### Added
- ✨ Text overlay on images with 5 Arabic fonts
- ✨ AI-powered text extraction from posts
- ✨ Pixel-perfect positioning system
- ✨ Background and shadow customization
- ✨ Live font availability checking

#### Changed
- 🔄 Improved post writer prompt (4-layer structure)
- 🔄 Enhanced image prompt engineering
- 🔄 Better error handling in image generation
- 🔄 Optimized Redis config persistence

#### Fixed
- 🐛 Fixed overlay settings not saving
- 🐛 Fixed image generation fallback chain
- 🐛 Fixed analytics refresh timing
- 🐛 Fixed Telegram bot reconnection

### [1.4.0] - 2024-11-30

#### Added
- ✨ Google Sheets bidirectional sync
- ✨ Config backup to Sheets
- ✨ Auto-sync on page load
- ✨ Conflict resolution logic

#### Changed
- 🔄 Improved idea generation algorithm
- 🔄 Better topic saturation detection
- 🔄 Enhanced engagement score calculation

#### Fixed
- 🐛 Fixed duplicate idea generation
- 🐛 Fixed platform publish failures
- 🐛 Fixed analytics data collection

### [1.3.0] - 2024-11-15

#### Added
- ✨ 11 image providers with fallback
- ✨ Cloudflare Worker integration
- ✨ Ideogram v3 support
- ✨ Provider chain configuration

#### Changed
- 🔄 Improved image quality
- 🔄 Faster image generation
- 🔄 Better error messages

### [1.2.0] - 2024-11-01

#### Added
- ✨ Telegram bot interface
- ✨ Real-time notifications
- ✨ Remote management
- ✨ Inline keyboards

#### Changed
- 🔄 Improved UI/UX
- 🔄 Better mobile responsiveness

### [1.1.0] - 2024-10-15

#### Added
- ✨ Real-time analytics
- ✨ Performance insights
- ✨ Engagement tracking
- ✨ Chart visualizations

### [1.0.0] - 2024-10-01

#### Added
- 🎉 Initial release
- ✨ AI content generation
- ✨ Multi-platform publishing
- ✨ Image generation
- ✨ Scheduling system

---

<a name="license"></a>
## 📄 License

This project is licensed under the **MIT License**.

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

**What this means:**
- ✅ Commercial use allowed
- ✅ Modification allowed
- ✅ Distribution allowed
- ✅ Private use allowed
- ⚠️ No warranty provided
- ⚠️ No liability accepted

---

<a name="acknowledgments"></a>
## 🙏 Acknowledgments

### AI & ML Services
- **Google** - Gemini API for text and Imagen for images
- **Cohere** - Arabic-optimized language models
- **Groq** - Lightning-fast inference
- **OpenRouter** - Model aggregation platform
- **OpenAI** - GPT models and DALL-E
- **api.airforce** - Free AI access

### Image Generation
- **Cloudflare** - Workers platform for Flux
- **Ideogram** - Best-in-class text rendering
- **Stability AI** - Stable Diffusion models
- **HuggingFace** - Model hosting and inference
- **Together AI** - Fast and affordable inference
- **Fal.ai** - Serverless AI infrastructure
- **Pollinations** - Free image generation

### Social Platforms
- **Meta** - Facebook, Instagram, Threads APIs
- **Twitter/X** - Twitter API v2
- **LinkedIn** - Professional network API

### Infrastructure & Tools
- **PythonAnywhere** - Python hosting platform
- **HuggingFace** - ML model hosting and Spaces
- **Upstash** - Serverless Redis
- **Cloudinary** - Image CDN and management
- **Google Cloud** - Sheets API and infrastructure

### Open Source Libraries
- **Flask** - Web framework
- **SQLAlchemy** - ORM
- **APScheduler** - Task scheduling
- **python-telegram-bot** - Telegram integration
- **Pillow** - Image processing
- **Tweepy** - Twitter API wrapper
- **Chart.js** - Data visualization
- And many more amazing open source projects!

### Fonts
- **Google Fonts** - Cairo, Noto, Amiri, Tajawal fonts
- **Font Awesome** - Icons

### Community
- All contributors and users
- Bug reporters and feature requesters
- Documentation improvers
- Translators and localizers

---

<a name="support"></a>
## 💬 Support

### Get Help

- 📖 **Documentation**: [Wiki](https://github.com/drnopoh2810-spec/social-post/wiki)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/drnopoh2810-spec/social-post/discussions)
- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/drnopoh2810-spec/social-post/issues)
- 💡 **Feature Requests**: [GitHub Issues](https://github.com/drnopoh2810-spec/social-post/issues)
- 📧 **Email**: [Contact via GitHub](https://github.com/drnopoh2810-spec)

### Community

- ⭐ **Star** the repo if you find it useful
- 🔀 **Fork** to create your own version
- 🐛 **Report bugs** to help improve
- 💡 **Suggest features** for future versions
- 📝 **Contribute** code or documentation
- 🌍 **Translate** to your language

---

<div align="center">

## 🌟 Star History

[![Star History Chart](https://api.star-history.com/svg?repos=drnopoh2810-spec/social-post&type=Date)](https://star-history.com/#drnopoh2810-spec/social-post&Date)

---

### Made with ❤️ in Egypt 🇪🇬

**[⭐ Star](https://github.com/drnopoh2810-spec/social-post)** | **[🐛 Report Bug](https://github.com/drnopoh2810-spec/social-post/issues)** | **[💡 Request Feature](https://github.com/drnopoh2810-spec/social-post/issues)** | **[📖 Documentation](https://github.com/drnopoh2810-spec/social-post/wiki)**

---

© 2024 [drnopoh2810-spec](https://github.com/drnopoh2810-spec). All rights reserved.

</div>

# 📧 Email Outreach System

A professional, automated email campaign system for job outreach with AI-generated personalized emails.

![Architecture](https://img.shields.io/badge/Architecture-Microservices-blue)
![Python](https://img.shields.io/badge/Python-3.11+-green)
![Next.js](https://img.shields.io/badge/Next.js-14-black)
![License](https://img.shields.io/badge/License-MIT-yellow)

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Next.js Frontend (Vercel)                     │
│                     Dashboard & Control Panel                    │
└─────────────────────────┬───────────────────────────────────────┘
                          │ REST API
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                 Python FastAPI Backend (Railway)                 │
│                    Background Email Worker                       │
└────────────┬────────────────────────────────────┬───────────────┘
             │                                    │
             ▼                                    ▼
┌────────────────────────┐          ┌─────────────────────────────┐
│   Neon PostgreSQL DB   │          │   Gmail SMTP + Gemini AI    │
│   (Campaign Storage)   │          │   (Send + Generate)         │
└────────────────────────┘          └─────────────────────────────┘
```

## ✨ Features

- **🎯 Dashboard UI** - Real-time stats, progress tracking, campaign controls
- **📊 Email Management** - View pending, sent, and failed emails in tabs
- **🤖 AI-Powered** - Gemini generates personalized, professional emails
- **📎 Resume Attachment** - Automatically attaches your resume
- **⏱️ Rate Limiting** - Random delays (10-30 min) to avoid spam flags
- **🔄 Resume-Safe** - Restarts don't send duplicate emails
- **🌐 Always Online** - PostgreSQL database, no local state dependency
- **☁️ Cloud Ready** - Deploy to Railway + Vercel (free tiers available)

## 📁 Project Structure

```
mail-sending-python/
├── backend/                    # Python FastAPI
│   ├── main.py                # API endpoints & campaign worker
│   ├── database.py            # Neon PostgreSQL operations
│   ├── email_sender.py        # Gmail SMTP client
│   ├── gemini_client.py       # Gemini AI email generation
│   ├── config.py              # Environment configuration
│   ├── import_contacts.py     # CSV import/export utility
│   ├── requirements.txt       # Python dependencies
│   ├── Dockerfile             # Container deployment
│   ├── railway.toml           # Railway config
│   └── .env.example           # Environment template
│
└── frontend/                   # Next.js Dashboard
    ├── src/
    │   └── app/
    │       ├── layout.tsx     # Root layout
    │       ├── page.tsx       # Main dashboard
    │       └── globals.css    # Tailwind styles
    ├── package.json
    ├── tailwind.config.js
    └── .env.example
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Gmail account with App Password
- Neon account (free tier)
- Gemini API key

### 1️⃣ Setup Neon Database

1. Go to [neon.tech](https://neon.tech) and create a free account
2. Create a new project
3. Copy the connection string (looks like `postgresql://user:pass@ep-xxx.region.aws.neon.tech/dbname`)

### 2️⃣ Get Gmail App Password

1. Enable 2-Step Verification on your Google Account
2. Go to Google Account → Security → 2-Step Verification → App Passwords
3. Generate a new app password for "Mail"
4. Copy the 16-character password

### 3️⃣ Get Gemini API Key

1. Go to [makersuite.google.com/app/apikey](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Copy the key

### 4️⃣ Setup Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Create .env file
copy .env.example .env
# Edit .env with your credentials

# Place your resume
# Copy your resume.pdf to the backend folder

# Run the server
uvicorn main:app --reload --port 8000
```

### 5️⃣ Setup Frontend

```bash
cd frontend

# Install dependencies
npm install

# Create .env.local
copy .env.example .env.local

# Run development server
npm run dev
```

### 6️⃣ Import Contacts

Create a CSV file with your contacts:

```csv
serial_number,name,email,title,company
1,John Doe,john@company.com,Engineering Manager,Tech Corp
2,Jane Smith,jane@startup.io,CTO,StartupXYZ
```

Import to database:

```bash
cd backend
python import_contacts.py import your_contacts.csv
```

### 7️⃣ Start Campaign

1. Open http://localhost:3000 in your browser
2. Verify contacts are loaded (check Pending tab)
3. Click "Start Campaign" on the dashboard
4. Monitor progress in real-time!

## ⚙️ Configuration

### Backend Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | Neon PostgreSQL connection string | ✅ |
| `GMAIL_EMAIL` | Your Gmail address | ✅ |
| `GMAIL_APP_PASSWORD` | Gmail App Password (16 chars) | ✅ |
| `GEMINI_API_KEY` | Google Gemini API key | ✅ |
| `RESUME_PATH` | Path to resume file | ❌ (default: resume.pdf) |

### Frontend Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `NEXT_PUBLIC_API_URL` | Backend API URL | ✅ |

## 🌐 Deployment

### Deploy Backend to Railway

1. Create account at [railway.app](https://railway.app)
2. Create new project → Deploy from GitHub repo
3. Select the `backend` folder
4. Add environment variables in Railway dashboard
5. Deploy!

### Deploy Frontend to Vercel

1. Create account at [vercel.com](https://vercel.com)
2. Import your GitHub repository
3. Set root directory to `frontend`
4. Add `NEXT_PUBLIC_API_URL` (your Railway URL)
5. Deploy!

## 📡 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/stats` | GET | Get campaign statistics |
| `/start-campaign` | POST | Start background worker |
| `/pause-campaign` | POST | Pause campaign |
| `/stop-campaign` | POST | Stop campaign |
| `/emails/pending` | GET | List pending emails |
| `/emails/sent` | GET | List sent emails |
| `/emails/failed` | GET | List failed emails |
| `/emails/upload` | POST | Bulk upload contacts |
| `/emails/retry/{id}` | POST | Retry failed email |
| `/emails/retry-all-failed` | POST | Retry all failed |

## 🛡️ Safety Features

- **Rate Limiting**: 10-30 minute random delays between emails
- **Daily Limits**: Configurable max emails per day (default: 50)
- **Duplicate Prevention**: Unique email constraint in database
- **Graceful Shutdown**: Completes current email before stopping
- **Error Handling**: Failed emails are marked, not lost

## 📝 Customizing Email Template

Edit the prompt in `backend/gemini_client.py`:

```python
self.system_prompt = """Your custom prompt here..."""
```

## 🔧 Troubleshooting

### "SMTP Authentication Failed"
- Make sure you're using an **App Password**, not your Gmail password
- Enable 2-Step Verification first

### "Database connection failed"
- Check your DATABASE_URL includes `?sslmode=require`
- Verify your Neon project is active

### "Gemini API error"
- Check your API key is valid
- Verify you haven't exceeded rate limits

### Emails going to spam
- Reduce sending frequency
- Use a professional email signature
- Avoid spam trigger words in content

## 📄 License

MIT License - feel free to use for your job search!

## 🤝 Contributing

Contributions welcome! Please feel free to submit a Pull Request.

---

Built with ❤️ for job seekers everywhere

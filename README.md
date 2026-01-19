# 📧 Auto Apply - Email Outreach System

A simple, single-file Python + Streamlit app that automatically sends personalized job application emails to HR contacts.

![Python](https://img.shields.io/badge/Python-3.10+-green)
![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-red)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Neon-blue)
![License](https://img.shields.io/badge/License-MIT-yellow)

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                 Streamlit App (Single File)                      │
│              Dashboard + Email Sending + Controls                │
└────────────┬────────────────────────────────────┬───────────────┘
             │                                    │
             ▼                                    ▼
┌────────────────────────┐          ┌─────────────────────────────┐
│   Neon PostgreSQL DB   │          │   Gmail SMTP + Gemini AI    │
│   (1800+ HR Contacts)  │          │   (Send + Generate)         │
└────────────────────────┘          └─────────────────────────────┘
```

## ✨ Features

- **📊 Dashboard** - Real-time stats, progress tracking
- **🎯 Custom Send** - Send emails one by one with control
- **🤖 AI-Powered** - Gemini generates personalized emails per company
- **📎 Resume Attachment** - Auto-attaches your resume from database
- **⏱️ Rate Limiting** - Random delays (10-30 min) to avoid spam
- **🧪 Test Mode** - Test contacts with filter support
- **📬 Reply-To** - Replies go to your primary email
- **☁️ Cloud Ready** - Deploy to Railway/Render

## 📁 Project Structure

```
auto-apply/
├── app.py              # Single file - entire application
├── .env                # Environment variables (secrets)
├── requirements.txt    # Python dependencies
├── Procfile            # For Railway/Heroku deployment
└── README.md
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Gmail account with App Password
- Neon PostgreSQL account (free)
- Gemini API key (free)

### 1️⃣ Clone & Install

```bash
git clone https://github.com/Chiragj2003/auto-apply-.git
cd auto-apply-

# Install dependencies
pip install -r requirements.txt
```

### 2️⃣ Setup Environment

Create a `.env` file:

```env
# Database (Neon PostgreSQL)
DATABASE_URL=postgresql://user:pass@ep-xxx.aws.neon.tech/dbname?sslmode=require

# Gmail SMTP
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=your-16-char-app-password

# Gemini AI
GEMINI_API_KEY=your-gemini-api-key

# Your Profile
SENDER_NAME=Your Name
SENDER_PHONE=1234567890
SENDER_LINKEDIN=https://linkedin.com/in/yourprofile
GITHUB=https://github.com/yourusername
```

### 3️⃣ Run Locally

```bash
streamlit run app.py
```

Open http://localhost:8501

## 📷 Screenshots

### Dashboard
- View total contacts, sent, pending, failed counts
- Start/pause bulk campaign
- Progress tracking

### Custom Send
- Filter by test/regular contacts
- Send individual emails with one click
- Search by name, email, company

## 🌐 Deploy to Railway

1. Go to [railway.app](https://railway.app)
2. Connect your GitHub repo
3. Add environment variables in Railway dashboard
4. Deploy!

## ⚙️ How It Works

1. **HR contacts** stored in Neon PostgreSQL
2. **Gemini AI** generates personalized email for each company
3. **Gmail SMTP** sends email with resume attached
4. **BCC** sends copy to your primary email
5. **Reply-To** ensures replies come to your main inbox

## �️ Safety Features

- **Rate Limiting**: 10-30 minute random delays between emails
- **Duplicate Prevention**: Unique email constraint in database
- **Resume Attachment**: Auto-attaches from database

## 🔧 Troubleshooting

### "SMTP Authentication Failed"
- Use an **App Password**, not your Gmail password
- Enable 2-Step Verification first

### "Database connection failed"
- Check DATABASE_URL includes `?sslmode=require`

### Emails going to spam
- Reduce sending frequency
- Use professional email content

## 📄 License

MIT License - feel free to use for your job search!

---

Built with ❤️ for job seekers

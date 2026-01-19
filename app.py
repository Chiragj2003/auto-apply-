"""
Email Outreach Pro - Single File Application
Streamlit Frontend + Synchronous Database (psycopg2) + All Services Combined
"""

import os
import random
import smtplib
import base64
import threading
import time
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse

import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# =============================================================================
# CONFIGURATION
# =============================================================================

class Config:
    DATABASE_URL = os.getenv("DATABASE_URL", "")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SENDER_EMAIL = os.getenv("SENDER_EMAIL", "")
    SENDER_PASSWORD = os.getenv("SENDER_PASSWORD", "")
    SENDER_NAME = os.getenv("SENDER_NAME", "")
    SENDER_PHONE = os.getenv("SENDER_PHONE", "")
    SENDER_LINKEDIN = os.getenv("SENDER_LINKEDIN", "")
    GITHUB = os.getenv("GITHUB", "")
    RESUME_PATH = os.getenv("RESUME_PATH", "")
    MIN_DELAY = int(os.getenv("MIN_DELAY", "600"))  # 10 minutes
    MAX_DELAY = int(os.getenv("MAX_DELAY", "1800"))  # 30 minutes
    
    # Applicant Profile for AI-generated emails
    APPLICANT_SKILLS = os.getenv("APPLICANT_SKILLS", "")
    APPLICANT_EXPERIENCE = os.getenv("APPLICANT_EXPERIENCE", "")
    APPLICANT_EDUCATION = os.getenv("APPLICANT_EDUCATION", "")
    APPLICANT_HIGHLIGHTS = os.getenv("APPLICANT_HIGHLIGHTS", "")

config = Config()

# =============================================================================
# DATABASE OPERATIONS (Synchronous with psycopg2)
# =============================================================================

class Database:
    _connection = None
    
    @classmethod
    def get_connection(cls):
        """Get database connection with SSL"""
        if cls._connection is None or cls._connection.closed:
            db_url = config.DATABASE_URL
            # Parse the URL and add sslmode
            if "?" in db_url:
                db_url = db_url.split("?")[0]
            
            # Parse connection string
            parsed = urlparse(db_url)
            
            cls._connection = psycopg2.connect(
                host=parsed.hostname,
                port=parsed.port or 5432,
                database=parsed.path[1:],  # Remove leading /
                user=parsed.username,
                password=parsed.password,
                sslmode='require'
            )
            cls._connection.autocommit = True
        return cls._connection
    
    @classmethod
    def execute_query(cls, query: str, params: tuple = None, fetch: str = None):
        """Execute a query and optionally fetch results"""
        try:
            conn = cls.get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                if fetch == "one":
                    return dict(cur.fetchone()) if cur.fetchone else None
                elif fetch == "all":
                    return [dict(row) for row in cur.fetchall()]
                elif fetch == "val":
                    result = cur.fetchone()
                    return result[0] if result else None
        except psycopg2.Error as e:
            # Reconnect on connection error
            cls._connection = None
            conn = cls.get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                if fetch == "one":
                    result = cur.fetchone()
                    return dict(result) if result else None
                elif fetch == "all":
                    return [dict(row) for row in cur.fetchall()]
                elif fetch == "val":
                    result = cur.fetchone()
                    return result[0] if result else None
    
    @classmethod
    def init_tables(cls):
        """Initialize database tables"""
        cls.execute_query("""
            CREATE TABLE IF NOT EXISTS email_campaigns (
                id SERIAL PRIMARY KEY,
                serial_number INT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                title TEXT,
                company TEXT,
                status TEXT DEFAULT 'pending',
                sent BOOLEAN DEFAULT FALSE,
                error_message TEXT,
                sent_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        cls.execute_query("""
            CREATE TABLE IF NOT EXISTS resume_storage (
                id SERIAL PRIMARY KEY,
                filename TEXT NOT NULL,
                content_base64 TEXT NOT NULL,
                content_type TEXT DEFAULT 'application/pdf',
                uploaded_at TIMESTAMP DEFAULT NOW(),
                is_active BOOLEAN DEFAULT TRUE
            )
        """)
    
    @classmethod
    def get_pending_emails(cls, limit: int = 100) -> List[Dict]:
        """Get pending emails"""
        conn = cls.get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """SELECT * FROM email_campaigns 
                   WHERE status = 'pending' AND sent = FALSE 
                   ORDER BY serial_number ASC LIMIT %s""",
                (limit,)
            )
            return [dict(row) for row in cur.fetchall()]
    
    @classmethod
    def get_emails_by_status(cls, status: str) -> List[Dict]:
        """Get emails by status"""
        conn = cls.get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """SELECT * FROM email_campaigns WHERE status = %s 
                   ORDER BY updated_at DESC""",
                (status,)
            )
            return [dict(row) for row in cur.fetchall()]
    
    @classmethod
    def get_stats(cls) -> Dict:
        """Get campaign statistics"""
        conn = cls.get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM email_campaigns")
            total = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM email_campaigns WHERE sent = TRUE")
            sent = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM email_campaigns WHERE status = 'pending' AND sent = FALSE")
            pending = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM email_campaigns WHERE status = 'failed'")
            failed = cur.fetchone()[0]
            
        return {"total": total, "sent": sent, "pending": pending, "failed": failed}
    
    @classmethod
    def update_email_status(cls, email_id: int, status: str, error_message: str = None):
        """Update email status"""
        conn = cls.get_connection()
        with conn.cursor() as cur:
            if status == "sent":
                cur.execute(
                    """UPDATE email_campaigns 
                       SET status = %s, sent = TRUE, sent_at = NOW(), updated_at = NOW() 
                       WHERE id = %s""",
                    (status, email_id)
                )
            else:
                cur.execute(
                    """UPDATE email_campaigns 
                       SET status = %s, error_message = %s, updated_at = NOW() 
                       WHERE id = %s""",
                    (status, error_message, email_id)
                )
    
    @classmethod
    def reset_email_status(cls, email_id: int):
        """Reset email to pending"""
        conn = cls.get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE email_campaigns 
                   SET status = 'pending', sent = FALSE, error_message = NULL, updated_at = NOW() 
                   WHERE id = %s""",
                (email_id,)
            )
    
    @classmethod
    def reset_all_failed(cls):
        """Reset all failed emails to pending"""
        conn = cls.get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE email_campaigns 
                   SET status = 'pending', sent = FALSE, error_message = NULL, updated_at = NOW() 
                   WHERE status = 'failed'"""
            )
    
    @classmethod
    def get_active_resume(cls) -> Optional[Dict]:
        """Get active resume from database"""
        conn = cls.get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """SELECT * FROM resume_storage WHERE is_active = TRUE 
                   ORDER BY uploaded_at DESC LIMIT 1"""
            )
            row = cur.fetchone()
            return dict(row) if row else None
    
    @classmethod
    def add_test_contacts(cls):
        """Add test contacts for testing with varied companies and roles"""
        test_contacts = [
            # Different companies and roles - all using same test email
            {"serial_number": 0, "name": "Priya Sharma", "email": "chiragj2019+google@gmail.com", "title": "HR Manager", "company": "Google India"},
            {"serial_number": 0, "name": "Rahul Verma", "email": "chiragj2019+microsoft@gmail.com", "title": "Talent Acquisition Lead", "company": "Microsoft"},
            {"serial_number": 0, "name": "Anjali Gupta", "email": "chiragj2019+amazon@gmail.com", "title": "Technical Recruiter", "company": "Amazon"},
            {"serial_number": 0, "name": "Vikram Singh", "email": "chiragj2019+infosys@gmail.com", "title": "Senior HR Executive", "company": "Infosys"},
            {"serial_number": 0, "name": "Neha Patel", "email": "chiragj2019+tcs@gmail.com", "title": "Campus Recruitment Head", "company": "TCS"},
            {"serial_number": 0, "name": "Amit Kumar", "email": "chiragj2019+wipro@gmail.com", "title": "HR Business Partner", "company": "Wipro"},
            {"serial_number": 0, "name": "Sneha Reddy", "email": "chiragj2019+flipkart@gmail.com", "title": "People Operations Manager", "company": "Flipkart"},
            {"serial_number": 0, "name": "Rajesh Nair", "email": "chiragj2019+paytm@gmail.com", "title": "Talent Acquisition Specialist", "company": "Paytm"},
            {"serial_number": 0, "name": "Kavita Joshi", "email": "chiragj2019+zomato@gmail.com", "title": "Recruitment Manager", "company": "Zomato"},
            {"serial_number": 0, "name": "Sanjay Mehta", "email": "chiragj2019+swiggy@gmail.com", "title": "HR Director", "company": "Swiggy"},
        ]
        conn = cls.get_connection()
        with conn.cursor() as cur:
            for contact in test_contacts:
                try:
                    # Use UPSERT to reset status if contact already exists
                    cur.execute(
                        """INSERT INTO email_campaigns (serial_number, name, email, title, company, status, sent)
                           VALUES (%s, %s, %s, %s, %s, 'pending', FALSE)
                           ON CONFLICT (email) DO UPDATE SET 
                               status = 'pending', 
                               sent = FALSE,
                               name = EXCLUDED.name,
                               title = EXCLUDED.title,
                               company = EXCLUDED.company,
                               error_message = NULL,
                               sent_at = NULL""",
                        (contact["serial_number"], contact["name"], contact["email"], contact["title"], contact["company"])
                    )
                except Exception as e:
                    print(f"Error adding test contact: {e}")
    
    @classmethod
    def get_pending_emails_paginated(cls, offset: int = 0, limit: int = 10) -> List[Dict]:
        """Get pending emails with pagination, test emails (serial_number=0) first"""
        conn = cls.get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """SELECT * FROM email_campaigns 
                   WHERE status = 'pending' AND sent = FALSE 
                   ORDER BY serial_number ASC, id ASC 
                   LIMIT %s OFFSET %s""",
                (limit, offset)
            )
            return [dict(row) for row in cur.fetchall()]
    
    @classmethod
    def get_email_by_id(cls, email_id: int) -> Optional[Dict]:
        """Get single email by ID"""
        conn = cls.get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM email_campaigns WHERE id = %s", (email_id,))
            row = cur.fetchone()
            return dict(row) if row else None

# =============================================================================
# GEMINI AI CLIENT
# =============================================================================

class GeminiClient:
    def __init__(self):
        if config.GEMINI_API_KEY:
            genai.configure(api_key=config.GEMINI_API_KEY)
            self.model = genai.GenerativeModel("gemini-1.5-flash")
        else:
            self.model = None
    
    def generate_email(self, hr_name: str, hr_title: str, company: str) -> Dict[str, str]:
        """Generate personalized email using Gemini AI"""
        signature_parts = []
        if config.SENDER_NAME:
            signature_parts.append(config.SENDER_NAME)
        if config.SENDER_PHONE:
            signature_parts.append(f"Phone: {config.SENDER_PHONE}")
        if config.SENDER_LINKEDIN:
            signature_parts.append(f"LinkedIn: {config.SENDER_LINKEDIN}")
        if config.GITHUB:
            signature_parts.append(f"GitHub: {config.GITHUB}")
        
        signature = "\n".join(signature_parts)
        
        # Fallback email template (when Gemini is not available)
        fallback_body = f"""Hello,

My name is {config.SENDER_NAME}, and I am a Full Stack Developer with hands-on experience in building and maintaining real-world software applications. I have built full-stack projects using React, Next.js, Node.js, Python, and databases like PostgreSQL and MongoDB.

I enjoy learning quickly, solving problems, and delivering clean, reliable solutions. I believe my technical skills, practical experience, and strong work ethic make me a good fit for opportunities at {company}.

Please find my resume attached for your reference.

Thank you for your time and consideration.

Best regards,
{signature}"""
        
        if not self.model:
            return {
                "subject": f"Application for Software Developer Role - {company}",
                "body": fallback_body
            }
        
        prompt = f"""
        Write a simple, direct job application email. Follow this exact style:
        
        COMPANY: {company}
        MY NAME: {config.SENDER_NAME}
        
        USE THIS EXACT TEMPLATE - just adapt it slightly for the company:
        
        ---
        Hello,

        My name is {config.SENDER_NAME}, and I am a Full Stack Developer with hands-on experience in building and maintaining real-world software applications. I have built full-stack projects using React, Next.js, Node.js, Python, and databases like PostgreSQL and MongoDB.

        I enjoy learning quickly, solving problems, and delivering clean, reliable solutions. I believe my technical skills, practical experience, and strong work ethic make me a good fit for opportunities at {company}.

        Please find my resume attached for your reference.

        Thank you for your time and consideration.
        ---
        
        RULES:
        - Keep it almost identical to the template above
        - You can slightly mention what {company} does in 1 short phrase if relevant
        - DO NOT add fancy words or exaggerations
        - Keep it under 80 words
        - Simple and professional
        
        OUTPUT FORMAT:
        SUBJECT: Application for Software Developer Role - {company}
        BODY:
        Hello,

        [Email body following the template]

        Best regards,
        {signature}
        """
        
        try:
            response = self.model.generate_content(prompt)
            text = response.text
            
            if "SUBJECT:" in text and "BODY:" in text:
                subject_part = text.split("BODY:")[0]
                body_part = text.split("BODY:")[1]
                subject = subject_part.replace("SUBJECT:", "").strip()
                body = body_part.strip()
            else:
                subject = f"Software Developer Eager to Contribute at {company}"
                body = text
            
            return {"subject": subject, "body": body}
        except Exception as e:
            return {
                "subject": f"Software Developer Eager to Contribute at {company}",
                "body": fallback_body
            }

# Initialize Gemini client
gemini_client = GeminiClient()

# =============================================================================
# EMAIL SENDER
# =============================================================================

class EmailSender:
    @staticmethod
    def get_resume_attachment() -> Optional[tuple]:
        """Get resume from database or local file"""
        # Try database first
        resume_data = Database.get_active_resume()
        if resume_data:
            content = base64.b64decode(resume_data["content_base64"])
            return (content, resume_data["filename"], resume_data["content_type"])
        
        # Fallback to local file
        if config.RESUME_PATH and os.path.exists(config.RESUME_PATH):
            with open(config.RESUME_PATH, "rb") as f:
                content = f.read()
            filename = os.path.basename(config.RESUME_PATH)
            return (content, filename, "application/pdf")
        
        return None
    
    @staticmethod
    def send_email(to_email: str, subject: str, body: str) -> bool:
        """Send email via SMTP"""
        msg = MIMEMultipart()
        msg["From"] = f"{config.SENDER_NAME} <{config.SENDER_EMAIL}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        msg["Reply-To"] = "chiragj2019@gmail.com"  # Replies go to primary email
        msg["Bcc"] = "chiragj2019@gmail.com"  # Silent copy to primary email
        
        msg.attach(MIMEText(body, "plain"))
        
        # Attach resume
        resume = EmailSender.get_resume_attachment()
        if resume:
            content, filename, content_type = resume
            attachment = MIMEApplication(content, _subtype="pdf")
            attachment.add_header("Content-Disposition", "attachment", filename=filename)
            msg.attach(attachment)
        
        try:
            with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT) as server:
                server.starttls()
                server.login(config.SENDER_EMAIL, config.SENDER_PASSWORD)
                # Send to both recipient and BCC
                server.send_message(msg)
            return True
        except Exception as e:
            raise Exception(f"SMTP Error: {str(e)}")

# =============================================================================
# CAMPAIGN WORKER (Background Thread)
# =============================================================================

class CampaignWorker:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance.is_running = False
                    cls._instance.is_paused = False
                    cls._instance.current_email = None
                    cls._instance.thread = None
        return cls._instance
    
    def process_emails(self):
        """Process emails in background thread"""
        while self.is_running:
            if self.is_paused:
                time.sleep(1)
                continue
            
            try:
                emails = Database.get_pending_emails(limit=1)
                if not emails:
                    self.is_running = False
                    self.current_email = None
                    break
                
                email_record = emails[0]
                self.current_email = email_record["email"]
                
                # Generate personalized email
                email_content = gemini_client.generate_email(
                    hr_name=email_record["name"],
                    hr_title=email_record.get("title") or "HR Manager",
                    company=email_record.get("company") or "your company"
                )
                
                # Send email
                try:
                    EmailSender.send_email(
                        to_email=email_record["email"],
                        subject=email_content["subject"],
                        body=email_content["body"]
                    )
                    Database.update_email_status(email_record["id"], "sent")
                except Exception as e:
                    Database.update_email_status(email_record["id"], "failed", str(e))
                
                self.current_email = None
                
                # Random delay between emails
                if self.is_running and not self.is_paused:
                    delay = random.randint(config.MIN_DELAY, config.MAX_DELAY)
                    for _ in range(delay):
                        if not self.is_running or self.is_paused:
                            break
                        time.sleep(1)
                        
            except Exception as e:
                print(f"Worker error: {e}")
                time.sleep(5)
        
        self.current_email = None
    
    def start(self):
        """Start the campaign worker"""
        if not self.is_running:
            self.is_running = True
            self.is_paused = False
            self.thread = threading.Thread(target=self.process_emails, daemon=True)
            self.thread.start()
    
    def pause(self):
        """Pause the campaign"""
        self.is_paused = True
    
    def resume(self):
        """Resume the campaign"""
        self.is_paused = False
    
    def stop(self):
        """Stop the campaign"""
        self.is_running = False
        self.is_paused = False
        self.current_email = None

# Initialize worker singleton
worker = CampaignWorker()

# =============================================================================
# STREAMLIT UI
# =============================================================================

def main():
    st.set_page_config(
        page_title="Email Outreach Pro",
        page_icon="📧",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS for dark theme
    st.markdown("""
    <style>
        /* Main app styling */
        .stApp {
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        }
        
        /* Headers */
        h1, h2, h3 {
            color: #f8fafc !important;
        }
        
        /* Metrics styling */
        [data-testid="stMetricValue"] {
            font-size: 2.5rem !important;
            font-weight: 700 !important;
        }
        
        /* Card-like containers */
        .stMetric {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 1rem;
            padding: 1rem;
        }
        
        /* Buttons */
        .stButton > button {
            border-radius: 0.75rem;
            padding: 0.5rem 1.5rem;
            font-weight: 600;
            transition: all 0.3s ease;
        }
        
        /* Tab styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 0.5rem;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 1rem;
            padding: 0.5rem;
        }
        
        .stTabs [data-baseweb="tab"] {
            border-radius: 0.75rem;
            color: #94a3b8;
            padding: 0.5rem 1rem;
        }
        
        .stTabs [aria-selected="true"] {
            background: rgba(59, 130, 246, 0.2);
            color: white;
        }
        
        /* Dataframe styling */
        .stDataFrame {
            border-radius: 1rem;
            overflow: hidden;
        }
        
        /* Sidebar */
        [data-testid="stSidebar"] {
            background: rgba(15, 23, 42, 0.95);
            border-right: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        /* Progress bar */
        .stProgress > div > div {
            background: linear-gradient(90deg, #8b5cf6, #ec4899);
            border-radius: 1rem;
        }
        
        /* Custom status badge */
        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem 1rem;
            border-radius: 2rem;
            font-size: 0.875rem;
            font-weight: 500;
        }
        
        .status-running {
            background: rgba(34, 197, 94, 0.2);
            color: #4ade80;
            border: 1px solid rgba(34, 197, 94, 0.3);
        }
        
        .status-paused {
            background: rgba(234, 179, 8, 0.2);
            color: #facc15;
            border: 1px solid rgba(234, 179, 8, 0.3);
        }
        
        .status-stopped {
            background: rgba(100, 116, 139, 0.2);
            color: #94a3b8;
            border: 1px solid rgba(100, 116, 139, 0.3);
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Initialize database
    try:
        Database.init_tables()
    except Exception as e:
        st.error(f"❌ Database connection failed: {e}")
        st.info("Please check your DATABASE_URL in .env file")
        st.stop()
    
    # Header
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("# 📧 Email Outreach Pro")
        st.markdown("*AI-Powered Campaign Management*")
    
    with col2:
        # Status indicator
        if worker.is_running:
            if worker.is_paused:
                st.markdown('<div class="status-badge status-paused">⏸️ Paused</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="status-badge status-running">🟢 Running</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="status-badge status-stopped">⚪ Stopped</div>', unsafe_allow_html=True)
    
    st.divider()
    
    # Get stats
    stats = Database.get_stats()
    
    # Sidebar - Campaign Controls
    with st.sidebar:
        st.markdown("## ⚙️ Campaign Controls")
        st.divider()
        
        if not worker.is_running:
            if st.button("▶️ Start Campaign", type="primary", use_container_width=True, disabled=stats["pending"] == 0):
                worker.start()
                st.rerun()
        else:
            if worker.is_paused:
                if st.button("▶️ Resume", type="primary", use_container_width=True):
                    worker.resume()
                    st.rerun()
            else:
                if st.button("⏸️ Pause", use_container_width=True):
                    worker.pause()
                    st.rerun()
            
            if st.button("⏹️ Stop Campaign", use_container_width=True):
                worker.stop()
                st.rerun()
        
        st.divider()
        
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.rerun()
        
        st.divider()
        
        # Current email being processed
        if worker.current_email:
            st.markdown("### 📤 Currently Sending")
            st.info(worker.current_email)
        
        st.divider()
        
        # Configuration info
        st.markdown("### 📋 Config Info")
        st.markdown(f"**Sender:** {config.SENDER_NAME}")
        st.markdown(f"**Email:** {config.SENDER_EMAIL}")
        st.markdown(f"**Delay:** {config.MIN_DELAY//60}-{config.MAX_DELAY//60} min")
    
    # Main content
    tabs = st.tabs(["📊 Dashboard", "🎯 Custom Send", "⏳ Pending", "✅ Sent", "❌ Failed"])
    
    # Dashboard Tab
    with tabs[0]:
        # Stats cards
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="👥 Total Contacts",
                value=f"{stats['total']:,}",
                help="Total HR contacts in database"
            )
        
        with col2:
            st.metric(
                label="✅ Sent",
                value=f"{stats['sent']:,}",
                delta=f"{(stats['sent']/max(stats['total'],1)*100):.1f}%",
                help="Successfully sent emails"
            )
        
        with col3:
            st.metric(
                label="⏳ Pending",
                value=f"{stats['pending']:,}",
                help="Emails waiting to be sent"
            )
        
        with col4:
            st.metric(
                label="❌ Failed",
                value=f"{stats['failed']:,}",
                delta=None if stats['failed'] == 0 else f"-{stats['failed']}",
                delta_color="inverse",
                help="Failed emails (can retry)"
            )
        
        st.divider()
        
        # Progress section
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("### 📈 Campaign Progress")
            progress = stats['sent'] / max(stats['total'], 1)
            st.progress(progress)
            
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.markdown(f"**Progress:** {progress*100:.1f}%")
            with col_b:
                success_rate = stats['sent'] / max(stats['sent'] + stats['failed'], 1) * 100
                st.markdown(f"**Success Rate:** {success_rate:.1f}%")
            with col_c:
                est_hours = (stats['pending'] * 20) / 60  # ~20 min per email average
                st.markdown(f"**Est. Time:** ~{est_hours:.1f}h")
        
        with col2:
            st.markdown("### 📊 Quick Stats")
            st.markdown(f"🎯 **Success Rate:** {success_rate:.1f}%")
            st.markdown(f"⏱️ **Avg Delay:** {(config.MIN_DELAY + config.MAX_DELAY) // 2 // 60} min")
            st.markdown(f"🤖 **AI Generated:** {stats['sent']}")
    
    # Custom Send Tab
    with tabs[1]:
        st.markdown("### 🎯 Custom Send - Manual Email Control")
        st.markdown("*Send emails one by one with full control.*")
        
        # Add Test Data Button & Filter
        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
        with col1:
            if st.button("➕ Add Test Contacts", type="secondary"):
                Database.add_test_contacts()
                st.success("✅ Test contacts added!")
                st.rerun()
        with col2:
            if st.button("🔄 Refresh List"):
                st.rerun()
        
        # Filter options
        st.divider()
        col1, col2 = st.columns([1, 3])
        with col1:
            filter_option = st.selectbox(
                "🔍 Filter",
                ["All Pending", "🧪 Test Only", "📋 Regular Only"],
                index=0,
                key="filter_custom_send"
            )
        with col2:
            search_query = st.text_input("🔎 Search", placeholder="Search by name, email, or company...", key="search_custom_send")
        
        st.divider()
        
        # Pagination
        if 'custom_send_page' not in st.session_state:
            st.session_state.custom_send_page = 0
        
        # Get all pending emails first, then filter
        all_pending = Database.get_emails_by_status("pending")
        
        # Apply filter
        if filter_option == "🧪 Test Only":
            filtered_emails = [e for e in all_pending if e['serial_number'] == 0]
        elif filter_option == "📋 Regular Only":
            filtered_emails = [e for e in all_pending if e['serial_number'] != 0]
        else:
            # Sort: test emails (serial_number=0) first, then by serial_number
            filtered_emails = sorted(all_pending, key=lambda x: (0 if x['serial_number'] == 0 else 1, x['serial_number']))
        
        # Apply search
        if search_query:
            search_lower = search_query.lower()
            filtered_emails = [e for e in filtered_emails if 
                             search_lower in e['name'].lower() or 
                             search_lower in e['email'].lower() or 
                             search_lower in (e.get('company') or '').lower()]
        
        # Pagination
        page_size = 10
        total_filtered = len(filtered_emails)
        total_pages = max(1, (total_filtered + page_size - 1) // page_size)
        
        # Reset page if out of bounds
        if st.session_state.custom_send_page >= total_pages:
            st.session_state.custom_send_page = 0
        
        offset = st.session_state.custom_send_page * page_size
        emails_page = filtered_emails[offset:offset + page_size]
        
        if emails_page:
            # Count test vs regular
            test_count = len([e for e in filtered_emails if e['serial_number'] == 0])
            regular_count = total_filtered - test_count
            
            st.markdown(f"**Showing {offset + 1}-{min(offset + len(emails_page), total_filtered)} of {total_filtered}** | 🧪 Test: {test_count} | 📋 Regular: {regular_count}")
            
            # Display each email with send button
            for email in emails_page:
                is_test = email['serial_number'] == 0
                badge = "🧪 TEST" if is_test else f"#{email['serial_number']}"
                bg_color = "rgba(139, 92, 246, 0.1)" if is_test else "transparent"
                
                with st.container():
                    col1, col2, col3 = st.columns([3, 2, 1])
                    
                    with col1:
                        st.markdown(f"**{badge}** | {email['name']}")
                        st.markdown(f"📧 {email['email']}")
                    
                    with col2:
                        st.markdown(f"🏢 {email.get('company') or '-'}")
                        st.markdown(f"💼 {email.get('title') or '-'}")
                    
                    with col3:
                        if st.button("📤 Send", key=f"send_{email['id']}", type="primary"):
                            with st.spinner(f"Sending to {email['email']}..."):
                                try:
                                    # Generate email
                                    email_content = gemini_client.generate_email(
                                        hr_name=email["name"],
                                        hr_title=email.get("title") or "HR Manager",
                                        company=email.get("company") or "your company"
                                    )
                                    # Send email
                                    EmailSender.send_email(
                                        to_email=email["email"],
                                        subject=email_content["subject"],
                                        body=email_content["body"]
                                    )
                                    Database.update_email_status(email["id"], "sent")
                                    st.success(f"✅ Sent to {email['email']}")
                                    time.sleep(1)
                                    st.rerun()
                                except Exception as e:
                                    Database.update_email_status(email["id"], "failed", str(e))
                                    st.error(f"❌ Failed: {str(e)}")
                    
                    st.divider()
            
            # Pagination controls
            col1, col2, col3 = st.columns([1, 2, 1])
            with col1:
                if st.button("⬅️ Previous", disabled=st.session_state.custom_send_page == 0):
                    st.session_state.custom_send_page -= 1
                    st.rerun()
            with col2:
                st.markdown(f"<div style='text-align: center;'>Page {st.session_state.custom_send_page + 1} of {total_pages}</div>", unsafe_allow_html=True)
            with col3:
                if st.button("Next ➡️", disabled=st.session_state.custom_send_page >= total_pages - 1):
                    st.session_state.custom_send_page += 1
                    st.rerun()
        else:
            st.info("🎉 No pending emails to send!")
    
    # Pending Tab
    with tabs[2]:
        st.markdown("### ⏳ Pending Emails")
        pending_emails = Database.get_emails_by_status("pending")
        
        if pending_emails:
            # Search filter
            search = st.text_input("🔍 Search", placeholder="Filter by name, email, or company...")
            
            filtered = pending_emails
            if search:
                search_lower = search.lower()
                filtered = [e for e in pending_emails if 
                           search_lower in e['name'].lower() or 
                           search_lower in e['email'].lower() or 
                           search_lower in (e.get('company') or '').lower()]
            
            st.markdown(f"**{len(filtered)}** contacts in queue")
            
            # Display as dataframe
            df_data = [{
                "#": e['serial_number'],
                "Name": e['name'],
                "Email": e['email'],
                "Company": e.get('company') or '-',
                "Title": e.get('title') or '-'
            } for e in filtered[:100]]
            
            st.dataframe(df_data, use_container_width=True, hide_index=True)
            
            if len(filtered) > 100:
                st.info(f"Showing first 100 of {len(filtered)} contacts")
        else:
            st.info("🎉 No pending emails! All contacts have been processed.")
    
    # Sent Tab
    with tabs[3]:
        st.markdown("### ✅ Sent Emails")
        sent_emails = Database.get_emails_by_status("sent")
        
        if sent_emails:
            search = st.text_input("🔍 Search sent", placeholder="Filter by name, email, or company...", key="sent_search")
            
            filtered = sent_emails
            if search:
                search_lower = search.lower()
                filtered = [e for e in sent_emails if 
                           search_lower in e['name'].lower() or 
                           search_lower in e['email'].lower() or 
                           search_lower in (e.get('company') or '').lower()]
            
            st.markdown(f"**{len(filtered)}** emails sent successfully")
            
            df_data = [{
                "#": e['serial_number'],
                "Name": e['name'],
                "Email": e['email'],
                "Company": e.get('company') or '-',
                "Sent At": e['sent_at'].strftime("%Y-%m-%d %H:%M") if e.get('sent_at') else '-'
            } for e in filtered[:100]]
            
            st.dataframe(df_data, use_container_width=True, hide_index=True)
            
            if len(filtered) > 100:
                st.info(f"Showing first 100 of {len(filtered)} contacts")
        else:
            st.info("📭 No emails sent yet. Start the campaign to begin sending.")
    
    # Failed Tab
    with tabs[4]:
        st.markdown("### ❌ Failed Emails")
        failed_emails = Database.get_emails_by_status("failed")
        
        if failed_emails:
            col1, col2 = st.columns([3, 1])
            with col1:
                search = st.text_input("🔍 Search failed", placeholder="Filter by name, email, or company...", key="failed_search")
            with col2:
                if st.button("🔄 Retry All Failed", type="primary"):
                    Database.reset_all_failed()
                    st.success("All failed emails reset to pending!")
                    st.rerun()
            
            filtered = failed_emails
            if search:
                search_lower = search.lower()
                filtered = [e for e in failed_emails if 
                           search_lower in e['name'].lower() or 
                           search_lower in e['email'].lower() or 
                           search_lower in (e.get('company') or '').lower()]
            
            st.markdown(f"**{len(filtered)}** emails failed")
            
            for email in filtered[:50]:
                with st.expander(f"❌ {email['name']} - {email['email']}"):
                    st.markdown(f"**Company:** {email.get('company') or '-'}")
                    st.markdown(f"**Error:** {email.get('error_message') or 'Unknown error'}")
                    if st.button(f"🔄 Retry", key=f"retry_{email['id']}"):
                        Database.reset_email_status(email['id'])
                        st.success("Email reset to pending!")
                        st.rerun()
            
            if len(filtered) > 50:
                st.info(f"Showing first 50 of {len(filtered)} failed emails")
        else:
            st.success("🎉 No failed emails!")
    
    # Footer
    st.divider()
    st.markdown(
        "<div style='text-align: center; color: #64748b; padding: 1rem;'>"
        "Email Outreach Pro • Powered by Gemini AI • Built with ❤️ by Chirag Joshi"
        "</div>",
        unsafe_allow_html=True
    )
    
    # Auto-refresh when campaign is running
    if worker.is_running and not worker.is_paused:
        time.sleep(5)
        st.rerun()

if __name__ == "__main__":
    main()

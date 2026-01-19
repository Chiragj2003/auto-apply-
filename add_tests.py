import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import os

load_dotenv()

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
conn.autocommit = True
cur = conn.cursor()

# Add/update all test contacts
test_contacts = [
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

print("Adding test contacts...")

for contact in test_contacts:
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
    print(f"✅ Added/Updated: {contact['name']} ({contact['company']})")

# Also reset old test contacts
cur.execute("""
    UPDATE email_campaigns 
    SET status = 'pending', sent = FALSE, error_message = NULL, sent_at = NULL
    WHERE email IN ('chiragj2019@gmail.com', 'cjshorts14@gmail.com')
""")
print(f"\n✅ Reset old test contacts")

# Verify
cur = conn.cursor(cursor_factory=RealDictCursor)
cur.execute("""
    SELECT serial_number, name, email, company, status 
    FROM email_campaigns 
    WHERE serial_number = 0 
    ORDER BY name
""")
rows = cur.fetchall()

print("\n" + "=" * 80)
print("TEST CONTACTS NOW IN DATABASE:")
print("=" * 80)
for r in rows:
    print(f"🧪 {r['name']} | {r['email']} | {r['company']} | {r['status']}")
print(f"\nTotal test contacts: {len(rows)}")

cur.close()
conn.close()

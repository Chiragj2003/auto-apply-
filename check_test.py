import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import os

load_dotenv()

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
conn.autocommit = True
cur = conn.cursor(cursor_factory=RealDictCursor)

# Check test contacts
cur.execute("""
    SELECT serial_number, name, email, company, title, status 
    FROM email_campaigns 
    WHERE serial_number = 0 OR email LIKE '%chiragj2019%'
""")
rows = cur.fetchall()

print("=" * 80)
print("TEST CONTACTS IN DATABASE:")
print("=" * 80)

if rows:
    for r in rows:
        print(f"SN: {r['serial_number']} | {r['name']} | {r['email']} | {r.get('company', '-')} | {r['status']}")
    print(f"\nTotal: {len(rows)}")
else:
    print("NO TEST CONTACTS FOUND!")
    print("\nLet's check all pending emails:")
    cur.execute("SELECT COUNT(*) as cnt FROM email_campaigns WHERE status = 'pending'")
    cnt = cur.fetchone()
    print(f"Pending emails: {cnt['cnt']}")
    
    # Show first 5 pending
    cur.execute("SELECT serial_number, name, email FROM email_campaigns WHERE status = 'pending' LIMIT 5")
    for r in cur.fetchall():
        print(f"  SN: {r['serial_number']} | {r['name']} | {r['email']}")

cur.close()
conn.close()

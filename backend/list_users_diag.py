import sys
import os

# Add the current directory to sys.path to import src modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from src.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

try:
    # Joining users and roles to get the role name
    query = text("""
        SELECT u.id, u.email, r.name as role_name 
        FROM users u
        LEFT JOIN roles r ON u.role_id = r.id
    """)
    result = db.execute(query)
    
    print(f"{'ID':<5} | {'Email':<30} | {'Role':<15}")
    print("-" * 55)
    for row in result:
        print(f"{row.id:<5} | {str(row.email):<30} | {str(row.role_name):<15}")
finally:
    db.close()

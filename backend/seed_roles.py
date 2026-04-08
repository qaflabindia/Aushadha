import sys
from sqlalchemy.orm import Session
from src.database import SessionLocal
from src.models import Role
import logging

logging.basicConfig(level=logging.INFO)

def seed_roles():
    db = SessionLocal()
    try:
        # Define the default roles
        default_roles = ['Admin', 'Doctor', 'Staff', 'Patient']
        
        for role_name in default_roles:
            role = db.query(Role).filter(Role.name == role_name).first()
            if not role:
                logging.info(f'Seeding role: {role_name}')
                new_role = Role(name=role_name)
                db.add(new_role)
            else:
                logging.info(f'Role already exists: {role_name}')
        
        db.commit()
    except Exception as e:
        logging.error(f'Error seeding roles: {e}')
        db.rollback()
    finally:
        db.close()

if __name__ == '__main__':
    seed_roles()

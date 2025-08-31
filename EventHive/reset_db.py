# reset_db.py
import os
from app import create_app
from extensions import db

def reset_database():
    """Reset the entire database by dropping all tables and recreating them."""
    app = create_app()
    
    with app.app_context():
        print("🗑️  Dropping all tables...")
        db.drop_all()
        print("✅ All tables dropped")
        
        print("🔄 Creating all tables...")
        db.create_all()
        print("✅ All tables created")
        
        print("🎉 Database reset complete!")

if __name__ == "__main__":
    reset_database()
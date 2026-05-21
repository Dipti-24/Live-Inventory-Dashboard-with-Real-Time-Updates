# database.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base # Import Base from your models.py
import os
from dotenv import load_dotenv

load_dotenv()

# --- IMPORTANT ---
# Replace with your actual database credentials
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD") 
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

# PostgreSQL connection URL
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Create the SQLAlchemy engine
engine = create_engine(DATABASE_URL)

# Create a session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_db_and_tables():
    """
    Creates the database tables if they don't already exist.
    SQLAlchemy's create_all is safe to run multiple times.
    It will not recreate tables that already exist in the database.
    """
    print("Checking and creating tables...")
    try:
        # The 'checkfirst=True' is the default behavior.
        # It checks for the existence of the table before creating it.
        Base.metadata.create_all(bind=engine)
        print("Tables are ready.")
    except Exception as e:
        print(f"An error occurred during table creation: {e}")




# Add this at the bottom of database.py
if __name__ == "__main__":
    create_db_and_tables()
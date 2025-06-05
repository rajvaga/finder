from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = (
    "mysql+pymysql://thevax74_cf_user:vaga%40420@162.241.123.133/thevax74_college_finder"
)

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# Create session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declare base class
Base = declarative_base()

# Test connection (optional)
if __name__ == "__main__":
    try:
        with engine.connect() as conn:
            print("✅ Successfully connected to the database!")
    except Exception as e:
        print("❌ Connection failed:", e)

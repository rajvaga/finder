from database import Base, engine
from models import User  # Adjust import if your model is in a different file

# Create all tables defined in Base subclasses
Base.metadata.create_all(bind=engine)
print("Tables created successfully.")

import urllib.parse
from sqlmodel import SQLModel, create_engine, Session
from core.config import settings

# URL Encode the password to handle special characters
encoded_password = urllib.parse.quote_plus(settings.DATABASE_PASSWORD)

# Construct the DATABASE_URL
DATABASE_URL = f"postgresql://{settings.DATABASE_USER}:{encoded_password}@{settings.DATABASE_HOST}:{settings.DATABASE_PORT}/{settings.DATABASE_NAME}"

# Create database engine with connection pooling
engine = create_engine(DATABASE_URL, echo=True, pool_size=10, max_overflow=20)


# Dependency to get a database session
def get_session():
    """Yield a database session."""
    with Session(engine) as session:
        yield session


# Function to create tables
def create_db_and_tables():
    """Create database tables from SQLModel metadata."""
    try:
        SQLModel.metadata.create_all(engine)
        print("✅ Database tables created successfully!")
    except Exception as e:
        print(f"❌ Error creating database tables: {e}")

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from os import environ

# Get database connection details from environment
INSTANCE_CONNECTION_NAME = environ.get('INSTANCE_CONNECTION_NAME')
DB_USER = environ.get('DB_USER')
DB_PASS = environ.get('DB_PASSWORD')
DB_NAME = environ.get('DB_NAME')
DB_PORT = environ.get('DB_PORT', '5432')

# Create connection string
if INSTANCE_CONNECTION_NAME:
    # Using Cloud SQL connection name
    db_socket_dir = '/cloudsql'
    connection_string = f"postgresql://{DB_USER}:{DB_PASS}@/{DB_NAME}?host={db_socket_dir}/{INSTANCE_CONNECTION_NAME}"
else:
    # Using local connection
    DB_HOST = environ.get('DB_HOST', 'localhost')
    connection_string = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Create engine with connection pooling
engine = create_engine(
    connection_string,
    pool_size=5,
    max_overflow=2,
    pool_timeout=30,
    pool_recycle=1800,
    poolclass=QueuePool
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for declarative models
Base = declarative_base()

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_connection():
    """Test database connection"""
    try:
        with engine.connect() as connection:
            result = connection.execute("SELECT 1").fetchone()
            return result[0] == 1
    except Exception as e:
        print(f"Database connection test failed: {e}")
        return False

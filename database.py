from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from core.config import settings


# Construct the async DATABASE_URL
DATABASE_URL = settings.SQLALCHEMY_DATABASE_URI

# Create async database engine with connection pooling
engine = create_async_engine(DATABASE_URL, echo=True, pool_size=10, max_overflow=20)

# Async session factory
async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False  # Prevents auto-refresh of expired objects
)


# Dependency to get a database session
async def get_session():
    """Yield an asynchronous database session."""
    async with async_session_maker() as session:
        yield session


# Function to create tables asynchronously
async def create_db_and_tables():
    """Create database tables asynchronously from SQLModel metadata."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
        print("✅ Database tables created successfully!")
    except Exception as e:
        print(f"❌ Error creating database tables: {e}")

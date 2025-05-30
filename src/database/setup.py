from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine

from settings import DATABASE_URL
from settings import DEV

from .tables import create_tables

AsyncSessionLocal = async_sessionmaker(expire_on_commit=False)


def get_async_session():
    return AsyncSessionLocal()


async def connect_to_db():
    engine = create_async_engine(DATABASE_URL, echo=DEV)

    async with engine.begin() as conn:
        await conn.run_sync(create_tables, engine)

    AsyncSessionLocal.configure(bind=engine)

from sqlalchemy import BigInteger
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import Base


class GuildPublishingChannel(Base):
    __tablename__ = "guild_publishing_channel"
    guild_id = Column(BigInteger, primary_key=True)
    channel_id = Column(BigInteger, nullable=False)


class GuildSourceKey(Base):
    __tablename__ = "guild_source_key"
    guild_id = Column(BigInteger, primary_key=True)
    source_key = Column(String, nullable=False)


class GuildUserSourceKeyOverride(Base):
    __tablename__ = "guild_user_source_key_override"
    id = Column(Integer, primary_key=True, autoincrement=True)
    guild_id = Column(BigInteger)
    user_id = Column(BigInteger)
    source_key = Column(String, nullable=False)


async def get_source_key(session: AsyncSession, user_id: int | None = None, guild_id: int | None = None) -> str | None:
    """Get the source key for a user override or the guild default."""
    if not guild_id:
        return None

    if user_id:
        result = await session.execute(
            select(GuildUserSourceKeyOverride.source_key).where(
                GuildUserSourceKeyOverride.guild_id == guild_id,
                GuildUserSourceKeyOverride.user_id == user_id,
            ),
        )
        row = result.scalar_one_or_none()
        if row:
            return row

    result = await session.execute(
        select(GuildSourceKey.source_key).where(GuildSourceKey.guild_id == guild_id)
    )
    row = result.scalar_one_or_none()
    return row.source_key if row else None


async def set_source_key(session: AsyncSession, guild_id: int, source_key: str, user_id: int | None = None) -> None:
    """Set the source key for a user override or the guild default."""
    model = GuildUserSourceKeyOverride if user_id else GuildSourceKey
    filters = [
        model.guild_id == guild_id,
    ]
    if user_id:
        filters.append(model.user_id == user_id)

    result = await session.execute(select(model).where(*filters))
    instance = result.scalar_one_or_none()

    if instance:
        instance.source_key = source_key
    else:
        data = {"guild_id": guild_id, "source_key": source_key}
        if user_id:
            data["user_id"] = user_id
        session.add(model(**data))

    await session.commit()


async def get_all_source_keys(session: AsyncSession, guild_id: int | None = None) -> list[GuildSourceKey]:
    """Get all guild source key entries, or filter by guild_id if provided."""
    stmt = select(GuildSourceKey)
    if guild_id is not None:
        stmt = stmt.where(GuildSourceKey.guild_id == guild_id)
    result = await session.execute(stmt)
    return [el.source_key for el in result.scalars().all()]


async def clear_source_key(session: AsyncSession, guild_id: int, user_id: int | None = None) -> None:
    """Delete the source key entry for a user override or guild default."""
    model = GuildUserSourceKeyOverride if user_id else GuildSourceKey
    filters = [model.guild_id == guild_id]
    if user_id:
        filters.append(model.user_id == user_id)

    await session.execute(delete(model).where(*filters))
    await session.commit()


async def get_guild_publishing_channel(session: AsyncSession, guild_id: int) -> GuildPublishingChannel | None:
    stmt = select(GuildPublishingChannel).where(GuildPublishingChannel.guild_id == guild_id)
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    return row.channel_id if row else None


async def set_guild_publishing_channel(session: AsyncSession, guild_id: int, channel_id: int) -> None:
    existing = await get_guild_publishing_channel(session, guild_id)
    if existing:
        existing.channel_id = channel_id
    else:
        session.add(GuildPublishingChannel(guild_id=guild_id, channel_id=channel_id))
    await session.commit()


async def delete_guild_publishing_channel(session: AsyncSession, guild_id: int) -> None:
    stmt = delete(GuildPublishingChannel).where(GuildPublishingChannel.guild_id == guild_id)
    await session.execute(stmt)
    await session.commit()

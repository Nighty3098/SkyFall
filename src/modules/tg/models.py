from sqlalchemy import (
    Boolean,
    Column,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all ORM models."""

    pass


def create_models(channel_name: str | None = None):
    """Create SQLAlchemy ORM models for the unified schema.

    Creates the following models:
    - Channel: Telegram channel/group information
    - TelegramUser: User information
    - TelegramPost: Channel posts
    - Discussion: Discussion/reply messages
    - ChannelMember: Channel membership
    - ChannelLink: Extracted URLs from messages

    Args:
        channel_name: Optional legacy parameter (not used in unified schema).

    Returns:
        tuple: (TelegramUser, TelegramPost, Discussion, ChannelMember, ChannelLink, Channel)
    """

    class Channel(Base):
        __tablename__ = "channels"
        id = Column(Integer, primary_key=True)
        channel_id = Column(Integer, unique=True, index=True)
        username = Column(String, nullable=True)
        title = Column(String, nullable=True)
        access_hash = Column(String, nullable=True)
        created_at = Column(String, nullable=True)
        last_member_sync = Column(String, nullable=True)

    class TelegramUser(Base):
        __tablename__ = "users"
        id = Column(Integer, primary_key=True)
        user_id = Column(Integer, unique=True, index=True)
        access_hash = Column(String, nullable=True)
        username = Column(String, nullable=True, index=True)
        first_name = Column(String, nullable=True)
        last_name = Column(String, nullable=True)
        phone = Column(String, nullable=True)
        bot = Column(Boolean, default=False)
        verified = Column(Boolean, default=False)
        premium = Column(Boolean, default=False)
        restricted = Column(Boolean, default=False)
        scam = Column(Boolean, default=False)
        fake = Column(Boolean, default=False)
        deleted = Column(Boolean, default=False)
        support = Column(Boolean, default=False)
        mutual_contact = Column(Boolean, default=False)
        contact = Column(Boolean, default=False)
        status = Column(String, nullable=True)
        was_online = Column(String, nullable=True)
        about = Column(Text, nullable=True)
        photo_id = Column(String, nullable=True)
        lang_code = Column(String, nullable=True)
        created_at = Column(String, nullable=True)
        updated_at = Column(String, nullable=True)
        avatar_path = Column(String, nullable=True)
        avatar_paths = Column(Text, nullable=True)
        business_work_hours = Column(Text, nullable=True)
        business_location = Column(Text, nullable=True)
        business_greeting_message = Column(Text, nullable=True)
        business_away_message = Column(Text, nullable=True)
        business_intro = Column(Text, nullable=True)
        birthday_day = Column(Integer, nullable=True)
        birthday_month = Column(Integer, nullable=True)
        birthday_year = Column(Integer, nullable=True)

    class TelegramPost(Base):
        __tablename__ = "posts"
        id = Column(Integer, primary_key=True)
        channel_id = Column(Integer, nullable=False, index=True)
        post_id = Column(Integer, index=True)
        text = Column(Text, nullable=True)
        media_path = Column(String, nullable=True)
        date = Column(String, nullable=True)
        views = Column(Integer, nullable=True)
        forwards = Column(Integer, nullable=True)
        user_id = Column(Integer, nullable=True)
        is_forwarded = Column(Boolean, default=False)
        forwarded_from_id = Column(Integer, nullable=True)
        forwarded_from_name = Column(String, nullable=True)
        __table_args__ = (
            UniqueConstraint("channel_id", "post_id", name="uix_channel_post"),
            Index("ix_posts_channel_date", "channel_id", "date"),
        )

    class Discussion(Base):
        __tablename__ = "discussions"
        id = Column(Integer, primary_key=True)
        reply_to_message_id = Column(Integer, nullable=True, index=True)
        channel_id = Column(Integer, nullable=False, index=True)
        message_id = Column(Integer, index=True)
        post_id = Column(Integer, nullable=True)
        text = Column(Text, nullable=True)
        date = Column(String, nullable=True)
        user_id = Column(Integer, nullable=True)
        media_path = Column(String, nullable=True)
        __table_args__ = (
            UniqueConstraint("channel_id", "message_id", name="uix_channel_discussion"),
            Index("ix_discussions_channel_date", "channel_id", "date"),
        )

    class ChannelMember(Base):
        __tablename__ = "members"
        id = Column(Integer, primary_key=True)
        channel_id = Column(Integer, nullable=False, index=True)
        user_id = Column(Integer, nullable=True)
        date = Column(String, nullable=True)
        status = Column(String, nullable=True)
        joined_at = Column(String, nullable=True)
        member_type = Column(String, default="member")
        __table_args__ = (
            UniqueConstraint("channel_id", "user_id", name="uix_channel_member"),
        )

    class ChannelLink(Base):
        __tablename__ = "links"
        id = Column(Integer, primary_key=True)
        channel_id = Column(Integer, nullable=False, index=True)
        url = Column(String, index=True)
        post_id = Column(Integer, nullable=True)
        message_id = Column(Integer, nullable=True)
        date = Column(String, nullable=True)
        text_context = Column(Text, nullable=True)
        link_type = Column(String, nullable=True)
        __table_args__ = (Index("ix_links_channel_date", "channel_id", "date"),)

    return TelegramUser, TelegramPost, Discussion, ChannelMember, ChannelLink, Channel


def get_channel_posts_model(Base):
    """Get the posts table model from Base metadata.

    Args:
        Base: SQLAlchemy DeclarativeBase.

    Returns:
        Table object or None.
    """
    return Base.metadata.tables.get("posts")


def get_channel_discussions_model(Base):
    """Get the discussions table model from Base metadata.

    Args:
        Base: SQLAlchemy DeclarativeBase.

    Returns:
        Table object or None.
    """
    return Base.metadata.tables.get("discussions")


def get_channel_members_model(Base):
    """Get the members table model from Base metadata.

    Args:
        Base: SQLAlchemy DeclarativeBase.

    Returns:
        Table object or None.
    """
    return Base.metadata.tables.get("members")


def get_channel_links_model(Base):
    """Get the links table model from Base metadata.

    Args:
        Base: SQLAlchemy DeclarativeBase.

    Returns:
        Table object or None.
    """
    return Base.metadata.tables.get("links")

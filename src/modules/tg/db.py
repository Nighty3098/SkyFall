import os
import sqlite3
from datetime import datetime

from sqlalchemy import and_, create_engine, func
from sqlalchemy.orm import sessionmaker

from src.modules.tg.models import Base, create_models


def datetime_to_str(val):
    """Convert a datetime object to ISO format string.

    Args:
        val: datetime object, string, or None.

    Returns:
        ISO format string or None.
    """
    if val is None:
        return None
    if isinstance(val, str):
        return val
    if hasattr(val, "isoformat"):
        return val.isoformat()
    return str(val)


_models_cache = None
_engine_cache = {}


def init_db(path, channel_name=None):
    """Initialize the database connection and create tables.

    Creates or opens a SQLite database, initializes SQLAlchemy engine,
    and creates all necessary tables.

    Args:
        path (str): Directory path for the database file.
        channel_name: Optional legacy parameter (not used in unified schema).

    Returns:
        tuple: (engine, session_factory, telegram_user_model, post_model,
                discussion_model, member_model, link_model, channel_model)
    """
    global _models_cache, _engine_cache

    db_name = os.path.join(os.path.abspath(path), "SkyFall_TG.db")

    if db_name in _engine_cache:
        engine = _engine_cache[db_name]
    else:
        engine = create_engine(
            f"sqlite:///{db_name}",
            connect_args={
                "detect_types": sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
            },
        )
        _engine_cache[db_name] = engine

    if _models_cache is None:
        _models_cache = create_models()

    telegram_user, post_model, discussion, member_model, link_model, channel_model = (
        _models_cache
    )

    Base.metadata.create_all(engine)

    session_factory = sessionmaker(bind=engine)
    return (
        engine,
        session_factory,
        telegram_user,
        post_model,
        discussion,
        member_model,
        link_model,
        channel_model,
    )


def save_channel(session, channel_model, channel_entity):
    """Save or update a channel entity in the database.

    Args:
        session: SQLAlchemy session.
        channel_model: Channel ORM model class.
        channel_entity: Telegram channel entity object.

    Returns:
        The saved or updated channel record.
    """
    db_channel = (
        session.query(channel_model).filter_by(channel_id=channel_entity.id).first()
    )
    data = {
        "channel_id": channel_entity.id,
        "username": getattr(channel_entity, "username", None),
        "title": getattr(channel_entity, "title", None),
        "access_hash": (
            str(channel_entity.access_hash)
            if hasattr(channel_entity, "access_hash")
            else None
        ),
        "created_at": (
            datetime.now().isoformat() if not db_channel else db_channel.created_at
        ),
    }
    if db_channel:
        for k, v in data.items():
            setattr(db_channel, k, v)
    else:
        db_channel = channel_model(**data)
        session.add(db_channel)
    session.commit()
    return db_channel


async def save_user(
    session,
    telegram_user_model,
    user,
    full_user=None,
    avatar_path=None,
    avatar_paths=None,
):
    """Save or update a user in the database.

    Extracts user information from Telegram entity and optional full user data.

    Args:
        session: SQLAlchemy session.
        telegram_user_model: TelegramUser ORM model class.
        user: Telegram user entity.
        full_user: Optional full user response with additional details.
        avatar_path: Path to user's profile photo.
        avatar_paths: Pipe-separated paths to multiple photos.

    Returns:
        The user ID if saved successfully, None otherwise.
    """
    if not user:
        return None

    tg_user_id = getattr(user, "id", None)
    if not tg_user_id:
        return None

    db_user = session.query(telegram_user_model).filter_by(user_id=tg_user_id).first()

    status_str = None
    was_online = None
    if getattr(user, "status", None) is not None:
        status_obj = user.status
        status_str = type(status_obj).__name__
        if hasattr(status_obj, "was_online"):
            was_online = datetime_to_str(status_obj.was_online)
        elif hasattr(status_obj, "until"):
            was_online = datetime_to_str(status_obj.until)

    about = None
    phone = None
    business_work_hours = None
    business_location = None
    business_greeting_message = None
    business_away_message = None
    business_intro = None
    birthday_day = None
    birthday_month = None
    birthday_year = None

    if full_user is not None:
        if hasattr(full_user, "about"):
            about = full_user.about
        if hasattr(full_user, "phone"):
            phone = full_user.phone
        if hasattr(full_user, "business_work_hours") and full_user.business_work_hours:
            bwh = full_user.business_work_hours
            bh_data = {
                "timezone_id": getattr(bwh, "timezone_id", None),
                "open_now": getattr(bwh, "open_now", None),
                "weekly_open": [],
            }
            weekly = getattr(bwh, "weekly_open", None)
            if weekly:
                for day in weekly:
                    day_data = {
                        "start_minute": getattr(day, "start_minute", None),
                        "end_minute": getattr(day, "end_minute", None),
                        "day_of_week": getattr(day, "day_of_week", None),
                    }
                    bh_data["weekly_open"].append(day_data)
            import json

            business_work_hours = json.dumps(bh_data)
        if hasattr(full_user, "business_location") and full_user.business_location:
            bl = full_user.business_location
            bl_data = {
                "address": getattr(bl, "address", None),
                "geo": None,
            }
            geo = getattr(bl, "geo", None)
            if geo:
                geo_data = {
                    "lat": getattr(geo, "lat", None),
                    "long": getattr(geo, "long", None),
                    "accuracy_radius": getattr(geo, "accuracy_radius", None),
                }
                bl_data["geo"] = geo_data
            import json

            business_location = json.dumps(bl_data)
        if (
            hasattr(full_user, "business_greeting_message")
            and full_user.business_greeting_message
        ):
            bgm = full_user.business_greeting_message
            bgm_data = {
                "title": getattr(bgm, "title", None),
                "message": getattr(bgm, "message", None),
            }
            import json

            business_greeting_message = json.dumps(bgm_data)
        if (
            hasattr(full_user, "business_away_message")
            and full_user.business_away_message
        ):
            bam = full_user.business_away_message
            bam_data = {
                "title": getattr(bam, "title", None),
                "message": getattr(bam, "message", None),
            }
            import json

            business_away_message = json.dumps(bam_data)
        if hasattr(full_user, "business_intro") and full_user.business_intro:
            bi = full_user.business_intro
            bi_data = {
                "title": getattr(bi, "title", None),
                "message": getattr(bi, "message", None),
                "sticker": None,
            }
            sticker = getattr(bi, "sticker", None)
            if sticker:
                bi_data["sticker"] = {
                    "id": getattr(sticker, "id", None),
                    "access_hash": getattr(sticker, "access_hash", None),
                }
            import json

            business_intro = json.dumps(bi_data)
        if hasattr(full_user, "birthday") and full_user.birthday:
            bday = full_user.birthday
            birthday_day = getattr(bday, "day", None)
            birthday_month = getattr(bday, "month", None)
            birthday_year = getattr(bday, "year", None)

    if phone is None:
        phone = getattr(user, "phone", None)

    access_hash = None
    if hasattr(user, "access_hash"):
        access_hash = str(user.access_hash)

    lang_code = getattr(user, "lang_code", None)

    photo_id = None
    photo = getattr(user, "photo", None)
    if photo is not None and hasattr(photo, "photo_id"):
        photo_id = str(photo.photo_id)

    user_data = {
        "user_id": tg_user_id,
        "access_hash": access_hash,
        "username": getattr(user, "username", None),
        "first_name": getattr(user, "first_name", None),
        "last_name": getattr(user, "last_name", None),
        "phone": phone,
        "bot": getattr(user, "bot", False),
        "verified": getattr(user, "verified", False),
        "premium": getattr(user, "premium", False),
        "restricted": getattr(user, "restricted", False),
        "scam": getattr(user, "scam", False),
        "fake": getattr(user, "fake", False),
        "deleted": getattr(user, "deleted", False),
        "support": getattr(user, "support", False),
        "mutual_contact": getattr(user, "mutual_contact", False),
        "contact": getattr(user, "contact", False),
        "status": status_str,
        "was_online": was_online,
        "about": about,
        "photo_id": photo_id,
        "lang_code": lang_code,
        "business_work_hours": business_work_hours,
        "business_location": business_location,
        "business_greeting_message": business_greeting_message,
        "business_away_message": business_away_message,
        "business_intro": business_intro,
        "birthday_day": birthday_day,
        "birthday_month": birthday_month,
        "birthday_year": birthday_year,
    }

    if avatar_path is not None:
        user_data["avatar_path"] = avatar_path
    if avatar_paths is not None:
        user_data["avatar_paths"] = avatar_paths

    if db_user is None:
        user_data["created_at"] = datetime.now().isoformat()
        user_data["updated_at"] = datetime.now().isoformat()
        db_user = telegram_user_model(**user_data)
        session.add(db_user)
    else:
        user_data["updated_at"] = datetime.now().isoformat()
        for key, value in user_data.items():
            if value is None or value == "":
                continue
            current = getattr(db_user, key, None)
            if key in ("avatar_path", "avatar_paths"):
                setattr(db_user, key, value)
            elif key.startswith("business_") or key.startswith("birthday_"):
                if current is None or current == "":
                    setattr(db_user, key, value)
            else:
                setattr(db_user, key, value)

    session.commit()
    return db_user.user_id


async def save_member(
    session,
    member_model,
    telegram_user_model,
    participant,
    channel_id,
    full_user=None,
    member_type="member",
):
    """Save a channel member to the database.

    Also saves the user if not already present.

    Args:
        session: SQLAlchemy session.
        member_model: ChannelMember ORM model class.
        telegram_user_model: TelegramUser ORM model class.
        participant: Telegram participant object.
        channel_id: Numeric channel ID.
        full_user: Optional full user response.
        member_type: Type of membership (default: "member").

    Returns:
        The user ID if saved successfully, None otherwise.
    """
    try:
        user_obj = getattr(participant, "user", participant)

        user_id = await save_user(
            session, telegram_user_model, user_obj, full_user=full_user
        )
        if not user_id:
            user_id = getattr(participant, "id", None) or getattr(user_obj, "id", None)

        if not user_id:
            return None

        date = getattr(participant, "date", None)
        date = datetime_to_str(date)
        status = getattr(participant, "status", None)
        joined_at = getattr(participant, "joined_at", date)
        joined_at = datetime_to_str(joined_at)

        if status is not None:
            status = str(status)

        db_member = (
            session.query(member_model)
            .filter_by(channel_id=channel_id, user_id=user_id)
            .first()
        )

        if db_member is None:
            db_member = member_model(
                channel_id=channel_id,
                user_id=user_id,
                date=date,
                status=status,
                joined_at=joined_at,
                member_type=member_type,
            )
            session.add(db_member)
        else:
            if date is not None:
                db_member.date = date
            if status is not None:
                db_member.status = status
            if joined_at is not None:
                db_member.joined_at = joined_at
            if member_type:
                db_member.member_type = member_type

        session.commit()
        return user_id

    except Exception as e:
        session.rollback()
        print(f"Error saving member: {e}")
        return None


async def save_discussion_participant(
    session,
    member_model,
    telegram_user_model,
    channel_model,
    user_id,
    channel_id,
    username=None,
    first_name=None,
    last_name=None,
    member_type="discussion_author",
):
    """Save a discussion participant as a member.

    Creates a minimal user record if the user doesn't exist.

    Args:
        session: SQLAlchemy session.
        member_model: ChannelMember ORM model class.
        telegram_user_model: TelegramUser ORM model class.
        channel_model: Channel ORM model class.
        user_id: Numeric user ID.
        channel_id: Numeric channel ID.
        username: Optional username.
        first_name: Optional first name.
        last_name: Optional last name.
        member_type: Type of membership (default: "discussion_author").

    Returns:
        The user ID if saved successfully, None otherwise.
    """
    try:
        if not user_id:
            return None

        is_channel = (
            session.query(channel_model).filter_by(channel_id=user_id).first()
            is not None
        )
        if is_channel:
            db_member = (
                session.query(member_model)
                .filter_by(channel_id=channel_id, user_id=user_id)
                .first()
            )
            if db_member is None:
                db_member = member_model(
                    channel_id=channel_id,
                    user_id=user_id,
                    member_type=member_type,
                )
                session.add(db_member)
                session.commit()
            return user_id

        existing_user = (
            session.query(telegram_user_model).filter_by(user_id=user_id).first()
        )
        if not existing_user:
            user_data = {
                "user_id": user_id,
                "username": username,
                "first_name": first_name,
                "last_name": last_name,
                "created_at": datetime.now().isoformat(),
            }
            db_user = telegram_user_model(**user_data)
            session.add(db_user)
            session.commit()

        db_member = (
            session.query(member_model)
            .filter_by(channel_id=channel_id, user_id=user_id)
            .first()
        )

        if db_member is None:
            db_member = member_model(
                channel_id=channel_id,
                user_id=user_id,
                member_type=member_type,
            )
            session.add(db_member)
        elif (
            db_member.member_type is None
            or db_member.member_type == "discussion_author"
        ):
            db_member.member_type = member_type

        session.commit()
        return user_id

    except Exception as e:
        session.rollback()
        print(f"Error saving discussion participant: {e}")
        return None


def add_link(session, link_model, channel_id, **kwargs):
    """Add a link to the database.

    Args:
        session: SQLAlchemy session.
        link_model: ChannelLink ORM model class.
        channel_id: Numeric channel ID.
        **kwargs: Link attributes (url, post_id, message_id, date, text_context, link_type).

    Returns:
        The created link record.
    """
    if "date" in kwargs and kwargs["date"] is not None:
        kwargs["date"] = datetime_to_str(kwargs["date"])
    kwargs["channel_id"] = channel_id
    link = link_model(**kwargs)
    session.add(link)
    session.commit()
    return link


def get_existing_link(session, link_model, url, post_id=None, channel_id=None):
    """Check if a link already exists in the database.

    Args:
        session: SQLAlchemy session.
        link_model: ChannelLink ORM model class.
        url: URL string to check.
        post_id: Optional post ID to filter by.
        channel_id: Optional channel ID to filter by.

    Returns:
        Existing link record or None.
    """
    query = session.query(link_model).filter_by(url=url, channel_id=channel_id)
    if post_id:
        query = query.filter_by(post_id=post_id)
    return query.first()


def get_last_post_id(session, post_model, channel_id):
    """Get the highest post ID for a channel.

    Args:
        session: SQLAlchemy session.
        post_model: TelegramPost ORM model class.
        channel_id: Numeric channel ID.

    Returns:
        The highest post ID or 0 if no posts exist.
    """
    return (
        session.query(func.max(post_model.post_id))
        .filter_by(channel_id=channel_id)
        .scalar()
        or 0
    )


def get_existing_posts(session, post_model, post_ids, channel_id):
    """Get existing post IDs from the database.

    Args:
        session: SQLAlchemy session.
        post_model: TelegramPost ORM model class.
        post_ids: List of post IDs to check.
        channel_id: Numeric channel ID.

    Returns:
        Set of existing post IDs.
    """
    existing = (
        session.query(post_model.post_id)
        .filter(
            and_(post_model.channel_id == channel_id, post_model.post_id.in_(post_ids))
        )
        .all()
    )
    return {row[0] for row in existing}


def get_existing_post(session, post_model, post_id, channel_id):
    """Get a specific post from the database.

    Args:
        session: SQLAlchemy session.
        post_model: TelegramPost ORM model class.
        post_id: Post ID to look up.
        channel_id: Numeric channel ID.

    Returns:
        Post record or None.
    """
    return (
        session.query(post_model)
        .filter_by(channel_id=channel_id, post_id=post_id)
        .first()
    )


def get_existing_discussions(session, discussion_model, message_ids, channel_id):
    """Get existing discussion message IDs from the database.

    Args:
        session: SQLAlchemy session.
        discussion_model: Discussion ORM model class.
        message_ids: List of message IDs to check.
        channel_id: Numeric channel ID.

    Returns:
        Set of existing message IDs.
    """
    existing = (
        session.query(discussion_model.message_id)
        .filter(
            and_(
                discussion_model.channel_id == channel_id,
                discussion_model.message_id.in_(message_ids),
            )
        )
        .all()
    )
    return {row[0] for row in existing}


def get_existing_members(session, member_model, user_ids, channel_id):
    """Get existing member user IDs from the database.

    Args:
        session: SQLAlchemy session.
        member_model: ChannelMember ORM model class.
        user_ids: List of user IDs to check.
        channel_id: Numeric channel ID.

    Returns:
        Set of existing user IDs.
    """
    existing = (
        session.query(member_model.user_id)
        .filter(
            and_(
                member_model.channel_id == channel_id,
                member_model.user_id.in_(user_ids),
            )
        )
        .all()
    )
    return {row[0] for row in existing}


def get_last_discussion_message_id(session, discussion_model, channel_id):
    """Get the highest discussion message ID for a channel.

    Args:
        session: SQLAlchemy session.
        discussion_model: Discussion ORM model class.
        channel_id: Numeric channel ID.

    Returns:
        The highest message ID or 0 if no discussions exist.
    """
    return (
        session.query(func.max(discussion_model.message_id))
        .filter_by(channel_id=channel_id)
        .scalar()
        or 0
    )


def get_channel_last_member_sync(session, channel_model, channel_id):
    """Get the timestamp of the last member sync for a channel.

    Args:
        session: SQLAlchemy session.
        channel_model: Channel ORM model class.
        channel_id: Numeric channel ID.

    Returns:
        ISO timestamp string or None if never synced.
    """
    result = (
        session.query(channel_model.last_member_sync)
        .filter_by(channel_id=channel_id)
        .first()
    )
    return result[0] if result else None


def update_channel_member_sync(session, channel_model, channel_id, sync_time):
    """Update the last member sync timestamp for a channel.

    Args:
        session: SQLAlchemy session.
        channel_model: Channel ORM model class.
        channel_id: Numeric channel ID.
        sync_time: ISO timestamp string to set.
    """
    channel = session.query(channel_model).filter_by(channel_id=channel_id).first()
    if channel:
        channel.last_member_sync = sync_time
        session.commit()


def add_post(session, post_model, channel_id, **kwargs):
    """Add a post to the database.

    Args:
        session: SQLAlchemy session.
        post_model: TelegramPost ORM model class.
        channel_id: Numeric channel ID.
        **kwargs: Post attributes (post_id, text, media_path, date, views, etc.).

    Returns:
        The created post record.
    """
    if "date" in kwargs and kwargs["date"] is not None:
        kwargs["date"] = datetime_to_str(kwargs["date"])
    kwargs["channel_id"] = channel_id
    post = post_model(**kwargs)
    session.add(post)
    session.commit()
    return post


def add_discussion(session, discussion_model, channel_id, **kwargs):
    """Add a discussion message to the database.

    Args:
        session: SQLAlchemy session.
        discussion_model: Discussion ORM model class.
        channel_id: Numeric channel ID.
        **kwargs: Discussion attributes (message_id, post_id, text, date, user_id, etc.).

    Returns:
        The created discussion record.
    """
    if "date" in kwargs and kwargs["date"] is not None:
        kwargs["date"] = datetime_to_str(kwargs["date"])
    kwargs["channel_id"] = channel_id
    discussion = discussion_model(**kwargs)
    session.add(discussion)
    session.commit()
    return discussion


def get_existing_discussion(session, discussion_model, message_id, channel_id):
    """Get a specific discussion message from the database.

    Args:
        session: SQLAlchemy session.
        discussion_model: Discussion ORM model class.
        message_id: Message ID to look up.
        channel_id: Numeric channel ID.

    Returns:
        Discussion record or None.
    """
    return (
        session.query(discussion_model)
        .filter_by(channel_id=channel_id, message_id=message_id)
        .first()
    )


def bulk_insert_posts(session, post_model, posts_data, channel_id, batch_size=500):
    """Bulk insert posts into the database.

    Args:
        session: SQLAlchemy session.
        post_model: TelegramPost ORM model class.
        posts_data: List of post data dictionaries.
        channel_id: Numeric channel ID.
        batch_size: Number of records per batch (default: 500).

    Returns:
        Total number of posts inserted.
    """
    if not posts_data:
        return 0
    inserted = 0
    for i in range(0, len(posts_data), batch_size):
        batch = posts_data[i : i + batch_size]
        processed_batch = []
        for kwargs in batch:
            post_data = dict(kwargs)
            if "date" in post_data and post_data["date"] is not None:
                post_data["date"] = datetime_to_str(post_data["date"])
            post_data["channel_id"] = channel_id
            processed_batch.append(post_data)
        session.bulk_insert_mappings(post_model, processed_batch)
        session.commit()
        inserted += len(batch)
    return inserted


def bulk_insert_discussions(
    session, discussion_model, discussions_data, channel_id, batch_size=500
):
    """Bulk insert discussions into the database.

    Args:
        session: SQLAlchemy session.
        discussion_model: Discussion ORM model class.
        discussions_data: List of discussion data dictionaries.
        channel_id: Numeric channel ID.
        batch_size: Number of records per batch (default: 500).

    Returns:
        Total number of discussions inserted.
    """
    if not discussions_data:
        return 0
    inserted = 0
    for i in range(0, len(discussions_data), batch_size):
        batch = discussions_data[i : i + batch_size]
        processed_batch = []
        for kwargs in batch:
            disc_data = dict(kwargs)
            if "date" in disc_data and disc_data["date"] is not None:
                disc_data["date"] = datetime_to_str(disc_data["date"])
            disc_data["channel_id"] = channel_id
            processed_batch.append(disc_data)
        session.bulk_insert_mappings(discussion_model, processed_batch)
        session.commit()
        inserted += len(batch)
    return inserted


def bulk_insert_members(
    session, member_model, members_data, channel_id, batch_size=500
):
    """Bulk insert channel members into the database.

    Args:
        session: SQLAlchemy session.
        member_model: ChannelMember ORM model class.
        members_data: List of member data dictionaries.
        channel_id: Numeric channel ID.
        batch_size: Number of records per batch (default: 500).

    Returns:
        Total number of members inserted.
    """
    if not members_data:
        return 0
    inserted = 0
    for i in range(0, len(members_data), batch_size):
        batch = members_data[i : i + batch_size]
        processed_batch = []
        for kwargs in batch:
            mem_data = dict(kwargs)
            for key in ["date", "joined_at"]:
                if key in mem_data and mem_data[key] is not None:
                    mem_data[key] = datetime_to_str(mem_data[key])
            mem_data["channel_id"] = channel_id
            processed_batch.append(mem_data)
        session.bulk_insert_mappings(member_model, processed_batch)
        session.commit()
        inserted += len(batch)
    return inserted

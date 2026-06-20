import os

from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.types import User as TgUser

from src.modules.tg.cache import api_cache
from src.modules.tg.db import save_user


async def get_cached_entity(client, entity_id, entity_type="user"):
    cache_key = f"{entity_type}:{entity_id}"
    cached = api_cache.get(cache_key)
    if cached:
        return cached
    try:
        entity = await client.get_entity(entity_id)
        api_cache.set(cache_key, entity)
        return entity
    except ValueError:
        return None


async def fetch_and_save_full_user(
    client, session, telegram_user_model, user, media_dir=None
):
    if not user or not getattr(user, "id", None):
        return None

    avatar_path = None
    avatar_paths = None
    full_user = None

    try:
        if isinstance(user, TgUser):
            full_user = await client(GetFullUserRequest(user))
    except Exception:
        pass

    if media_dir and isinstance(user, TgUser):
        try:
            user_id = user.id
            profile_dir = os.path.join(media_dir, "avatars")
            os.makedirs(profile_dir, exist_ok=True)
            avatar_path = os.path.join(profile_dir, f"{user_id}.jpg")
            if not os.path.exists(avatar_path):
                photo = await client.download_profile_photo(user, file=avatar_path)
                if photo:
                    avatar_paths = avatar_path
                else:
                    avatar_path = None
        except Exception:
            avatar_path = None

    user_id = await save_user(
        session,
        telegram_user_model,
        user,
        full_user=full_user,
        avatar_path=avatar_path,
        avatar_paths=avatar_paths,
    )
    return user_id

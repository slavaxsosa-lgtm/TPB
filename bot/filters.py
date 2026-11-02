from aiogram.filters import BaseFilter
from aiogram.types import Message
from aiogram.enums import ChatType
import time
import logging

logger=logging.getLogger(__name__)
user_status_cache={}
CACHE_TTL=300

class PrivateChatFilter(BaseFilter):
    async def __call__(self, message:Message)->bool:
        return message.chat.type==ChatType.PRIVATE

class RoleFilter(BaseFilter):
    def __init__(self, required_status:int, sheets_manager):
        self.required_status=required_status
        self.sheets_manager=sheets_manager
    async def __call__(self, message:Message)->bool:
        user=message.from_user
        if not user:
            return False
        tg_id=user.id
        username=f"@{user.username}" if user.username else None
        if not username:
            logger.warning(f"User {tg_id} has no username")
            return False
        current_time=time.time()
        if tg_id in user_status_cache:
            cached_status, cached_time=user_status_cache[tg_id]
            if current_time-cached_time<CACHE_TTL:
                logger.debug(f"Status for {username} from cache: {cached_status}")
                return cached_status==self.required_status
        try:
            status=self.sheets_manager.get_user_status(username)
            if status is not None:
                user_status_cache[tg_id]=(status, current_time)
                logger.info(f"Status for {username}: {status}")
                return status==self.required_status
            else:
                logger.warning(f"Status for {username} not found")
                return False
        except Exception as e:
            logger.error(f"Error getting status for {username}: {e}")
            return False

def is_tutor(sheets_manager):
    return RoleFilter(required_status=5, sheets_manager=sheets_manager)

def is_link_admin(sheets_manager):
    return RoleFilter(required_status=2, sheets_manager=sheets_manager)

def is_senior_admin(sheets_manager):
    return RoleFilter(required_status=3, sheets_manager=sheets_manager)

def is_any_admin(sheets_manager):
    class AnyAdminFilter(BaseFilter):
        async def __call__(self, message:Message)->bool:
            user=message.from_user
            if not user:
                return False
            tg_id=user.id
            username=f"@{user.username}" if user.username else None
            if not username:
                return False
            current_time=time.time()
            if tg_id in user_status_cache:
                cached_status, cached_time=user_status_cache[tg_id]
                if current_time-cached_time<CACHE_TTL:
                    return cached_status in [2, 3]
            try:
                status=sheets_manager.get_user_status(username)
                if status is not None:
                    user_status_cache[tg_id]=(status, current_time)
                    return status in [2, 3]
                return False
            except Exception as e:
                logger.error(f"Error getting status: {e}")
                return False
    return AnyAdminFilter()

def get_user_status_cached(tg_id:int, username:str, sheets_manager)->int:
    current_time=time.time()
    if tg_id in user_status_cache:
        cached_status, cached_time=user_status_cache[tg_id]
        if current_time-cached_time<CACHE_TTL:
            return cached_status
    try:
        status=sheets_manager.get_user_status(username)
        if status is not None:
            user_status_cache[tg_id]=(status, current_time)
            return status
        return 0
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return 0

def is_private_chat():
    return PrivateChatFilter()

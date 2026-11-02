from aiogram import Bot
from typing import Dict, List
import logging

logger=logging.getLogger(__name__)

class MessageManager:
    def __init__(self):
        self.user_messages:Dict[int, List[int]]={}
    def add_message(self, user_id:int, message_id:int):
        if user_id not in self.user_messages:
            self.user_messages[user_id]=[]
        self.user_messages[user_id].append(message_id)
    async def clear_user_messages(self, bot:Bot, user_id:int, keep_last:int=0):
        if user_id not in self.user_messages:
            return
        messages=self.user_messages[user_id]
        if keep_last>0:
            to_delete=messages[:-keep_last]
            self.user_messages[user_id]=messages[-keep_last:]
        else:
            to_delete=messages
            self.user_messages[user_id]=[]
        for msg_id in to_delete:
            try:
                await bot.delete_message(chat_id=user_id, message_id=msg_id)
            except Exception as e:
                logger.debug(f"Не удалось удалить сообщение {msg_id}: {e}")
        logger.info(f"Удалено {len(to_delete)} сообщений для пользователя {user_id}")

message_manager=MessageManager()

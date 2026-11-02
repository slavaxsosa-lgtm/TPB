import asyncio
import logging
from datetime import datetime, time
from typing import List
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

logger=logging.getLogger(__name__)

class BroadcastScheduler:
    def __init__(self, bot:Bot, group_ids:List[int]):
        self.bot=bot
        self.group_ids=group_ids
        self.scheduler=AsyncIOScheduler(timezone=pytz.timezone('Europe/Moscow'))
    async def send_weekly_reminder(self):
        message=(
            "📢 <b>Сегодня выплатный день!</b>\n\n"
            "Проверьте сумму выплаты в таблице и выполните одно из действий:\n\n"
            "✅ <b>Если сумма верна:</b>\n"
            "Используйте команду /confirm_payout для подтверждения выплаты\n\n"
            "🎫 <b>Если сумма неверна:</b>\n"
            "Используйте команду /ticket для оформления тикета на корректировку\n\n"
            "📊 <b>Проверить баланс:</b> /balance\n"
            "📜 <b>История тикетов:</b> /history\n\n"
            "⏰ <i>Финансовый учет: четверг-среда</i>"
        )
        await self._broadcast_to_groups(message)
        logger.info("Отправлено еженедельное напоминание о выплатном дне")
    async def send_data_updated_notification(self):
        message=(
            "✅ <b>Данные в таблице обновлены</b>\n\n"
            "Информация о занятиях и выплатах актуализирована.\n"
            "Вы можете проверить свой баланс командой /balance"
        )
        await self._broadcast_to_groups(message)
        logger.info("Отправлено уведомление об обновлении данных")
    async def _broadcast_to_groups(self, message:str):
        if not self.group_ids:
            logger.warning("Список групп пуст, рассылка не выполнена")
            return
        success_count=0
        for group_id in self.group_ids:
            try:
                await self.bot.send_message(
                    chat_id=group_id,
                    text=message,
                    parse_mode='HTML'
                )
                success_count+=1
                logger.info(f"Сообщение отправлено в группу {group_id}")
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"Ошибка отправки в группу {group_id}: {e}")
        logger.info(f"Рассылка завершена: {success_count}/{len(self.group_ids)} групп")
    def start(self):
        self.scheduler.add_job(
            self.send_weekly_reminder,
            trigger=CronTrigger(
                day_of_week='thu',
                hour=12,
                minute=0,
                timezone=pytz.timezone('Europe/Moscow')
            ),
            id='weekly_reminder',
            name='Еженедельное напоминание о выплатах',
            replace_existing=True
        )
        self.scheduler.start()
        logger.info("Планировщик рассылок запущен")
        logger.info("Еженедельное напоминание: каждый четверг в 12:00 МСК")
    def stop(self):
        self.scheduler.shutdown()
        logger.info("Планировщик рассылок остановлен")

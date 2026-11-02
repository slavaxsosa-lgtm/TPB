from aiogram import Bot
from typing import Dict
import logging

logger=logging.getLogger(__name__)

async def notify_admins_payment_link(bot:Bot, sheets_manager, ticket_data:Dict):
    try:
        link_admins=sheets_manager.get_admins_by_status(2)
        senior_admins=sheets_manager.get_admins_by_status(3)
        all_admins=link_admins+senior_admins
        if not all_admins:
            logger.warning("Не найдено админов для уведомления о payment_link")
            return
        data=ticket_data['ticket_data']
        message=(
            f"🔔 Новая заявка на ссылку для оплаты\n\n"
            f"#Ticket_{ticket_data['id']}\n"
            f"👤 Репетитор: {ticket_data['username']} (TG_ID: {ticket_data['tg_id']})\n"
            f"📞 Номер чата: {data['chat_id']}\n"
            f"📅 Дата занятия: {data['date']}\n"
            f"💰 Сумма: {data['amount']}₽\n"
            f"📧 Email: {data['email']}\n\n"
            f"💡 Ответьте на это сообщение ссылкой ИЛИ используйте:\n"
            f"/reply {ticket_data['id']} <ссылка>"
        )
        sent_count=0
        for admin in all_admins:
            if admin.get('tg_id'):
                try:
                    await bot.send_message(chat_id=admin['tg_id'], text=message)
                    sent_count+=1
                    logger.info(f"Уведомление отправлено админу {admin['username']} (TG_ID: {admin['tg_id']})")
                except Exception as e:
                    logger.error(f"Ошибка отправки уведомления админу {admin['username']}: {e}")
            else:
                logger.warning(f"У админа {admin['username']} нет TG_ID")
        logger.info(f"Уведомления о тикете #{ticket_data['id']} отправлены ({sent_count}/{len(all_admins)})")
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомлений админам: {e}")

async def notify_senior_admin_payout(bot:Bot, sheets_manager, ticket_data:Dict):
    try:
        senior_admins=sheets_manager.get_admins_by_status(3)
        if not senior_admins:
            logger.warning("Не найдено старших админов для уведомления о выплате")
            return
        data=ticket_data['ticket_data']
        table_amount=data.get('table_amount', data.get('amount', '0'))
        correct_amount=data.get('correct_amount', table_amount)
        comment=data.get('comment', '')
        message=(
            f"🔔 Заявка на выплату\n\n"
            f"#Ticket_{ticket_data['id']}\n"
            f"👤 Репетитор: {ticket_data['username']}\n"
            f"💰 Сумма в таблице: {table_amount}₽\n"
            f"💰 Должна быть: {correct_amount}₽\n"
        )
        if comment:
            message+=f"\n💬 Комментарий:\n{comment}\n"
        message+=(
            f"\nКоманды:\n"
            f"/approve {ticket_data['id']} - подтвердить\n"
            f"/reject {ticket_data['id']} <причина> - отклонить"
        )
        sent_count=0
        for admin in senior_admins:
            if admin.get('tg_id'):
                try:
                    await bot.send_message(chat_id=admin['tg_id'], text=message)
                    sent_count+=1
                    logger.info(f"Уведомление о выплате отправлено старшему админу {admin['username']} (TG_ID: {admin['tg_id']})")
                except Exception as e:
                    logger.error(f"Ошибка отправки уведомления старшему админу {admin['username']}: {e}")
            else:
                logger.warning(f"У старшего админа {admin['username']} нет TG_ID")
        logger.info(f"Уведомления о тикете на выплату #{ticket_data['id']} отправлены ({sent_count}/{len(senior_admins)})")
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомлений старшим админам: {e}")

async def notify_tutor_link_sent(bot:Bot, tg_id:int, ticket_id:int, link:str):
    try:
        message=(
            f"✅ По вашей заявке #{ticket_id} сформирована ссылка:\n"
            f"{link}\n\n"
            f"Оплатите до указанной даты."
        )
        await bot.send_message(chat_id=tg_id, text=message)
        logger.info(f"Ссылка отправлена репетитору {tg_id} для тикета #{ticket_id}")
    except Exception as e:
        logger.error(f"Ошибка при отправке ссылки репетитору: {e}")

async def notify_admins_ticket_cancelled(bot:Bot, sheets_manager, ticket_id:int, username:str):
    try:
        link_admins=sheets_manager.get_admins_by_status(2)
        senior_admins=sheets_manager.get_admins_by_status(3)
        all_admins=link_admins+senior_admins
        if not all_admins:
            return
        message=f"⚠️ Тикет #{ticket_id} отменён пользователем {username}"
        for admin in all_admins:
            logger.info(f"Уведомление об отмене для админа {admin['username']}")
        logger.info(f"Уведомления об отмене тикета #{ticket_id} отправлены")
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомлений об отмене: {e}")

async def notify_tutor_payout_approved(bot:Bot, tg_id:int, ticket_id:int, amount:float):
    try:
        message=(
            f"✅ Ваша заявка на выплату #{ticket_id} одобрена!\n"
            f"💰 Сумма: {amount}₽\n\n"
            f"Ожидайте перевод."
        )
        await bot.send_message(chat_id=tg_id, text=message)
        logger.info(f"Уведомление об одобрении отправлено репетитору {tg_id}")
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления об одобрении: {e}")

async def notify_tutor_payout_rejected(bot:Bot, tg_id:int, ticket_id:int, reason:str):
    try:
        message=(
            f"❌ Ваша заявка на выплату #{ticket_id} отклонена.\n\n"
            f"Причина: {reason}\n\n"
            f"Обратитесь к администратору для уточнения."
        )
        await bot.send_message(chat_id=tg_id, text=message)
        logger.info(f"Уведомление об отклонении отправлено репетитору {tg_id}")
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления об отклонении: {e}")

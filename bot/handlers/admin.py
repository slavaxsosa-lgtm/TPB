from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from bot.filters import is_private_chat
from bot.utils.notifications import notify_tutor_link_sent, notify_tutor_payout_approved, notify_tutor_payout_rejected
import re
import logging

logger = logging.getLogger(__name__)

router = Router()


def register_admin_handlers(dp, sheets_manager, bot, broadcast_scheduler=None):

    @dp.message(Command("reply"), is_private_chat())
    async def cmd_reply(message: Message):
        user = message.from_user
        username = f"@{user.username}" if user.username else None

        if not username:
            await message.answer("❌ Для работы с ботом необходимо установить username")
            return

        args = message.text.split(maxsplit=2)
        if len(args) < 3:
            await message.answer(
                "❌ Использование: /reply <ID> <ссылка>\n"
                "Пример: /reply 123 https://pay.link/abc"
            )
            return

        try:
            ticket_id = int(args[1])
            link = args[2]
        except ValueError:
            await message.answer("❌ ID тикета должен быть числом")
            return

        try:
            ticket = sheets_manager.get_ticket(ticket_id)

            if not ticket:
                await message.answer(f"❌ Тикет #{ticket_id} не найден")
                return

            if ticket['ticket_type'] != 'payment_link':
                await message.answer(f"❌ Тикет #{ticket_id} не является заявкой на ссылку")
                return

            if ticket['status'] == 'закрыт':
                await message.answer(f"❌ Тикет #{ticket_id} уже закрыт")
                return

            sheets_manager.update_ticket_status(
                ticket_id=ticket_id,
                status='закрыт',
                admin_tg_id=user.id,
                comment='Ссылка отправлена'
            )

            sheets_manager.update_payment_link(ticket_id=ticket_id, link=link)

            await notify_tutor_link_sent(bot, ticket['tg_id'], ticket_id, link)

            await message.answer(f"✅ Ссылка отправлена репетитору по тикету #{ticket_id}")

            logger.info(f"Админ {username} отправил ссылку по тикету #{ticket_id}")

        except Exception as e:
            logger.error(f"Ошибка при обработке /reply для тикета #{ticket_id}: {e}")
            await message.answer("❌ Произошла ошибка. Попробуйте позже.")

    @dp.message(F.reply_to_message)
    async def handle_reply_to_bot(message: Message):
        user = message.from_user
        username = f"@{user.username}" if user.username else None

        if not username:
            return

        if not message.reply_to_message or not message.reply_to_message.from_user.is_bot:
            return

        original_text = message.reply_to_message.text or ""
        match = re.search(r'#Ticket_(\d+)', original_text)

        if not match:
            return

        ticket_id = int(match.group(1))
        link = message.text.strip()

        if not link.startswith('http'):
            await message.answer("❌ Пожалуйста, отправьте ссылку (начинается с http)")
            return

        try:
            ticket = sheets_manager.get_ticket(ticket_id)

            if not ticket:
                await message.answer(f"❌ Тикет #{ticket_id} не найден")
                return

            if ticket['ticket_type'] != 'payment_link':
                await message.answer(f"❌ Тикет #{ticket_id} не является заявкой на ссылку")
                return

            if ticket['status'] == 'закрыт':
                await message.answer(f"❌ Тикет #{ticket_id} уже закрыт")
                return

            sheets_manager.update_ticket_status(
                ticket_id=ticket_id,
                status='закрыт',
                admin_tg_id=user.id,
                comment='Ссылка отправлена'
            )

            sheets_manager.update_payment_link(ticket_id=ticket_id, link=link)

            await notify_tutor_link_sent(bot, ticket['tg_id'], ticket_id, link)

            await message.answer(f"✅ Ссылка отправлена репетитору по тикету #{ticket_id}")

            logger.info(f"Админ {username} отправил ссылку по тикету #{ticket_id} через реплай")

        except Exception as e:
            logger.error(f"Ошибка при обработке реплая для тикета #{ticket_id}: {e}")
            await message.answer("❌ Произошла ошибка. Попробуйте позже.")

    @dp.message(Command("approve"), is_private_chat())
    async def cmd_approve(message: Message):
        user = message.from_user
        username = f"@{user.username}" if user.username else None

        if not username:
            await message.answer("❌ Для работы с ботом необходимо установить username")
            return

        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.answer("❌ Использование: /approve <ID>\nПример: /approve 123")
            return

        try:
            ticket_id = int(args[1])
        except ValueError:
            await message.answer("❌ ID тикета должен быть числом")
            return

        try:
            ticket = sheets_manager.get_ticket(ticket_id)

            if not ticket:
                await message.answer(f"❌ Тикет #{ticket_id} не найден")
                return

            if ticket['ticket_type'] != 'payout_request':
                await message.answer(f"❌ Тикет #{ticket_id} не является заявкой на выплату")
                return

            if ticket['status'] == 'закрыт':
                await message.answer(f"❌ Тикет #{ticket_id} уже закрыт")
                return

            sheets_manager.update_ticket_status(
                ticket_id=ticket_id,
                status='закрыт',
                admin_tg_id=user.id,
                comment='Одобрено'
            )

            amount = float(ticket['ticket_data'].get('amount', 0))
            await notify_tutor_payout_approved(bot, ticket['tg_id'], ticket_id, amount)

            await message.answer(f"✅ Выплата по тикету #{ticket_id} одобрена")

            logger.info(f"Админ {username} одобрил выплату по тикету #{ticket_id}")

        except Exception as e:
            logger.error(f"Ошибка при одобрении тикета #{ticket_id}: {e}")
            await message.answer("❌ Произошла ошибка. Попробуйте позже.")

    @dp.message(Command("reject"), is_private_chat())
    async def cmd_reject(message: Message):
        user = message.from_user
        username = f"@{user.username}" if user.username else None

        if not username:
            await message.answer("❌ Для работы с ботом необходимо установить username")
            return

        args = message.text.split(maxsplit=2)
        if len(args) < 3:
            await message.answer(
                "❌ Использование: /reject <ID> <причина>\n"
                "Пример: /reject 123 Неверная сумма"
            )
            return

        try:
            ticket_id = int(args[1])
            reason = args[2]
        except ValueError:
            await message.answer("❌ ID тикета должен быть числом")
            return

        try:
            ticket = sheets_manager.get_ticket(ticket_id)

            if not ticket:
                await message.answer(f"❌ Тикет #{ticket_id} не найден")
                return

            if ticket['ticket_type'] != 'payout_request':
                await message.answer(f"❌ Тикет #{ticket_id} не является заявкой на выплату")
                return

            if ticket['status'] == 'закрыт':
                await message.answer(f"❌ Тикет #{ticket_id} уже закрыт")
                return

            sheets_manager.update_ticket_status(
                ticket_id=ticket_id,
                status='отменено',
                admin_tg_id=user.id,
                comment=f'Отклонено: {reason}'
            )

            await notify_tutor_payout_rejected(bot, ticket['tg_id'], ticket_id, reason)

            await message.answer(f"✅ Выплата по тикету #{ticket_id} отклонена")

            logger.info(f"Админ {username} отклонил выплату по тикету #{ticket_id}: {reason}")

        except Exception as e:
            logger.error(f"Ошибка при отклонении тикета #{ticket_id}: {e}")
            await message.answer("❌ Произошла ошибка. Попробуйте позже.")

    @dp.message(Command("notify_update"), is_private_chat())
    async def cmd_notify_update(message: Message):
        user = message.from_user
        username = f"@{user.username}" if user.username else None

        if not username:
            await message.answer("❌ Для работы с ботом необходимо установить username")
            return

        status = sheets_manager.get_user_status(username)
        if status != 3:
            await message.answer("❌ Эта команда доступна только старшим админам")
            return

        if not broadcast_scheduler:
            await message.answer("❌ Планировщик рассылок не настроен")
            logger.error("broadcast_scheduler не передан в register_admin_handlers")
            return

        try:
            await broadcast_scheduler.send_data_updated_notification()
            await message.answer("✅ Уведомление об обновлении данных отправлено во все группы")
            logger.info(f"Старший админ {username} отправил уведомление об обновлении данных")

        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления об обновлении: {e}")
            await message.answer("❌ Произошла ошибка при отправке уведомления. Попробуйте позже.")

    @dp.message(Command("open_payout"), is_private_chat())
    async def cmd_open_payout(message: Message):
        user = message.from_user
        username = f"@{user.username}" if user.username else None

        if not username:
            await message.answer("❌ Для работы с ботом необходимо установить username")
            return

        status = sheets_manager.get_user_status(username)
        if status != 3:
            await message.answer("❌ Эта команда доступна только старшим админам")
            return

        try:
            if sheets_manager.is_payout_form_open():
                await message.answer("⚠️ Форма подтверждения выплат уже открыта")
                return

            sheets_manager.set_payout_form_status(is_open=True)

            tutors = sheets_manager.get_all_tutors()

            sent_count = 0
            failed_count = 0

            notification_text = (
                "📢 <b>Открыта форма подтверждения выплат!</b>\n\n"
                "Пожалуйста, проверьте свой баланс и подтвердите получение акта в консоли.\n\n"
                "Используйте команды:\n"
                "💰 /balance - проверить баланс\n"
                "✅ /confirm_payout - подтвердить выплату\n"
                "💸 /ticket - создать тикет на выплату (если есть расхождения)"
            )

            for tutor in tutors:
                if tutor['tg_id']:
                    try:
                        await bot.send_message(
                            chat_id=tutor['tg_id'],
                            text=notification_text,
                            parse_mode='HTML'
                        )
                        sent_count += 1
                        logger.info(f"Уведомление о форме выплат отправлено {tutor['username']}")
                    except Exception as e:
                        failed_count += 1
                        logger.error(f"Не удалось отправить уведомление {tutor['username']}: {e}")
                else:
                    failed_count += 1
                    logger.warning(f"У репетитора {tutor['username']} не заполнен TG_ID")

            result_text = (
                f"✅ Форма подтверждения выплат открыта!\n\n"
                f"📊 Статистика рассылки:\n"
                f"✅ Отправлено: {sent_count}\n"
                f"❌ Не отправлено: {failed_count}\n"
                f"👥 Всего репетиторов: {len(tutors)}"
            )
            await message.answer(result_text)

            logger.info(f"Старший админ {username} открыл форму выплат. Отправлено уведомлений: {sent_count}/{len(tutors)}")

        except Exception as e:
            logger.error(f"Ошибка при открытии формы выплат: {e}")
            await message.answer("❌ Произошла ошибка. Попробуйте позже.")

    @dp.message(Command("close_payout"), is_private_chat())
    async def cmd_close_payout(message: Message):
        user = message.from_user
        username = f"@{user.username}" if user.username else None

        if not username:
            await message.answer("❌ Для работы с ботом необходимо установить username")
            return

        status = sheets_manager.get_user_status(username)
        if status != 3:
            await message.answer("❌ Эта команда доступна только старшим админам")
            return

        try:
            if not sheets_manager.is_payout_form_open():
                await message.answer("⚠️ Форма подтверждения выплат уже закрыта")
                return

            all_statuses = sheets_manager.get_payout_status()

            confirmed = sum(1 for s in all_statuses if s['status'] == 'подтверждение')
            tickets = sum(1 for s in all_statuses if s['status'] == 'тикет')
            waiting = sum(1 for s in all_statuses if s['status'] == 'ожидание')

            sheets_manager.set_payout_form_status(is_open=False)

            for status_data in all_statuses:
                if status_data['status'] != 'ожидание':
                    sheets_manager.update_payout_status(status_data['username'], 'ожидание')

            result_text = (
                f"✅ Форма подтверждения выплат закрыта!\n\n"
                f"📊 Итоговая статистика:\n"
                f"✅ Подтвердили: {confirmed}\n"
                f"🎫 Создали тикет: {tickets}\n"
                f"⏳ Не ответили: {waiting}\n"
                f"👥 Всего репетиторов: {len(all_statuses)}\n\n"
                f"Все статусы сброшены на 'ожидание'"
            )
            await message.answer(result_text)

            logger.info(f"Старший админ {username} закрыл форму выплат. Статистика: подтверждено={confirmed}, тикеты={tickets}, ожидание={waiting}")

        except Exception as e:
            logger.error(f"Ошибка при закрытии формы выплат: {e}")
            await message.answer("❌ Произошла ошибка. Попробуйте позже.")

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from bot.filters import is_private_chat
import logging

logger = logging.getLogger(__name__)

router = Router()


def register_admin_list_handlers(dp, sheets_manager, bot):

    @dp.message(Command("tickets"), is_private_chat())
    async def cmd_tickets(message: Message):
        user = message.from_user
        username = f"@{user.username}" if user.username else None

        if not username:
            await message.answer("❌ Для работы с ботом необходимо установить username")
            return

        try:
            status = sheets_manager.get_user_status(username)

            if status != 3:  # Только старший админ
                await message.answer("❌ У вас нет доступа к этой команде")
                return

            tickets = sheets_manager.get_all_active_tickets(ticket_type="payout_request")

            if not tickets:
                await message.answer("✅ Нет активных тикетов на выплату")
                return

            response = f"📋 Активные тикеты на выплату ({len(tickets)}):\n\n"

            for ticket in tickets:
                data = ticket['ticket_data']
                table_amount = data.get('table_amount', data.get('amount', '0'))
                correct_amount = data.get('correct_amount', table_amount)
                comment = data.get('comment', '')
                created = ticket['created_at'][:10] if ticket['created_at'] else 'Неизвестно'

                response += (
                    f"🎫 Тикет #{ticket['id']}\n"
                    f"👤 {ticket['username']}\n"
                    f"💰 В таблице: {table_amount}₽\n"
                    f"💰 Должна быть: {correct_amount}₽\n"
                )

                if comment:
                    response += f"💬 Комментарий: {comment}\n"

                response += (
                    f"📅 Создан: {created}\n"
                    f"Команды: /approve {ticket['id']} | /reject {ticket['id']} <причина>\n\n"
                )

            await message.answer(response)
            logger.info(f"Старший админ {username} запросил список тикетов")

        except Exception as e:
            logger.error(f"Ошибка при получении списка тикетов для {username}: {e}")
            await message.answer("❌ Произошла ошибка. Попробуйте позже.")

    @dp.message(Command("requests"), is_private_chat())
    async def cmd_requests(message: Message):
        user = message.from_user
        username = f"@{user.username}" if user.username else None

        if not username:
            await message.answer("❌ Для работы с ботом необходимо установить username")
            return

        try:
            status = sheets_manager.get_user_status(username)

            if status not in [2, 3]:  # Админ ссылок или старший админ
                await message.answer("❌ У вас нет доступа к этой команде")
                return

            requests = sheets_manager.get_all_active_tickets(ticket_type="payment_link")

            if not requests:
                await message.answer("✅ Нет активных заявок на ссылки")
                return

            response = f"📋 Активные заявки на ссылки ({len(requests)}):\n\n"

            for req in requests:
                data = req['ticket_data']
                chat_id = data.get('chat_id', 'Неизвестно')
                date = data.get('date', 'Неизвестно')
                amount = data.get('amount', '0')
                email = data.get('email', 'Неизвестно')
                created = req['created_at'][:10] if req['created_at'] else 'Неизвестно'

                response += (
                    f"🎫 Заявка #{req['id']}\n"
                    f"👤 {req['username']}\n"
                    f"📞 Чат: {chat_id}\n"
                    f"📅 Дата занятия: {date}\n"
                    f"💰 Сумма: {amount}₽\n"
                    f"📧 Email: {email}\n"
                    f"📅 Создана: {created}\n"
                    f"Команда: /reply {req['id']} <ссылка>\n\n"
                )

            await message.answer(response)
            logger.info(f"Админ {username} запросил список заявок на ссылки")

        except Exception as e:
            logger.error(f"Ошибка при получении списка заявок для {username}: {e}")
            await message.answer("❌ Произошла ошибка. Попробуйте позже.")

    @dp.message(Command("status"), is_private_chat())
    async def cmd_status(message: Message):
        user = message.from_user
        username = f"@{user.username}" if user.username else None

        if not username:
            await message.answer("❌ Для работы с ботом необходимо установить username")
            return

        try:
            status = sheets_manager.get_user_status(username)

            if status != 3:  # Только старший админ
                await message.answer("❌ У вас нет доступа к этой команде")
                return

            all_users = sheets_manager.get_admins_by_status(5)

            if not all_users:
                await message.answer("✅ Нет зарегистрированных репетиторов")
                return

            all_tickets = sheets_manager.get_all_active_tickets(ticket_type="payout_request")
            confirmation_tickets = []

            try:
                sheet = sheets_manager.spreadsheet.worksheet("Tickets")
                all_values = sheet.get_all_values()

                for row in all_values[1:]:
                    if len(row) >= 6:
                        ticket_type = row[3]
                        ticket_status = row[5]
                        if ticket_type == "confirmation" and ticket_status == "закрыт":
                            confirmation_tickets.append({
                                'tg_id': int(row[1]) if row[1] else 0,
                                'username': row[2],
                                'id': int(row[0]) if row[0] else 0
                            })
            except Exception as e:
                logger.error(f"Ошибка при получении подтвержденных выплат: {e}")

            response = f"📊 Статус выплат всех репетиторов ({len(all_users)}):\n\n"

            confirmed_count = 0
            waiting_count = 0
            ticket_count = 0

            for tutor in all_users:
                tutor_username = tutor['username']
                tutor_tg_id = tutor.get('tg_id')

                has_confirmation = any(t['username'] == tutor_username for t in confirmation_tickets)
                has_active_ticket = any(t['username'] == tutor_username for t in all_tickets)

                if has_confirmation:
                    status_emoji = "✅"
                    status_text = "Подтверждено"
                    confirmed_count += 1
                elif has_active_ticket:
                    status_emoji = "🎫"
                    status_text = "Оформлен тикет"
                    ticket_count += 1
                else:
                    status_emoji = "⏳"
                    status_text = "Ожидание"
                    waiting_count += 1

                response += f"{status_emoji} {tutor_username} - {status_text}\n"

            response += (
                f"\n📈 Статистика:\n"
                f"✅ Подтверждено: {confirmed_count}\n"
                f"🎫 Оформлен тикет: {ticket_count}\n"
                f"⏳ Ожидание: {waiting_count}"
            )

            await message.answer(response)
            logger.info(f"Старший админ {username} запросил статус выплат всех пользователей")

        except Exception as e:
            logger.error(f"Ошибка при получении статуса выплат для {username}: {e}")
            await message.answer("❌ Произошла ошибка. Попробуйте позже.")

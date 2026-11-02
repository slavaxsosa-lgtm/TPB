from aiogram import F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from bot.filters import is_private_chat
import logging

logger = logging.getLogger(__name__)


def register_button_handlers(dp, sheets_manager, bot):

    @dp.message(F.text == "💰 Баланс", is_private_chat())
    async def button_balance(message: Message):
        logger.info(f"Нажата кнопка 'Баланс' пользователем {message.from_user.id}")
        user = message.from_user
        username = f"@{user.username}" if user.username else None

        if not username:
            await message.answer("❌ Для работы с ботом необходимо установить username")
            return

        try:
            from bot.utils.message_manager import message_manager

            payout = sheets_manager.get_tutor_payout(username)
            lessons = sheets_manager.get_tutor_lessons(username)

            if payout is None:
                await message.answer("❌ Информация о выплате не найдена. Обратитесь к администратору.")
                return

            response = f"💰 Ваша выплата на текущую неделю: {payout:.0f}₽\n\n"

            if lessons:
                response += "📊 Детализация занятий:\n"
                paid_count = 0
                unpaid_count = 0

                for lesson in lessons:
                    date = lesson['date']
                    chat_id = lesson['chat_id']
                    amount = lesson['amount']
                    status = lesson['status']
                    status_emoji = "✅" if status == "Оплачено" else "❌"

                    if status == "Оплачено":
                        paid_count += 1
                    else:
                        unpaid_count += 1

                    response += f"{date} | Чат #{chat_id} | {amount}₽ | {status_emoji} {status}\n"

                response += f"\nВсего: {len(lessons)} занятий\n"
                response += f"Оплачено: {paid_count}\n"
                response += f"Неоплачено: {unpaid_count}"
            else:
                response += "📊 Занятий за текущую неделю не найдено"

            sent_message = await message.answer(response)
            message_manager.add_message(user.id, sent_message.message_id)
            logger.info(f"Пользователь {username} проверил баланс")

        except Exception as e:
            logger.error(f"Ошибка при получении баланса для {username}: {e}")
            await message.answer("❌ Произошла ошибка при получении данных. Попробуйте позже.")

    @dp.message(F.text == "🔗 Заявка на ссылку", is_private_chat())
    async def button_payment_link(message: Message, state: FSMContext):
        logger.info(f"Нажата кнопка 'Заявка на ссылку' пользователем {message.from_user.id}")
        user = message.from_user
        username = f"@{user.username}" if user.username else None

        if not username:
            await message.answer("❌ Для работы с ботом необходимо установить username")
            return

        try:
            from bot.states import PaymentLinkStates
            from bot.utils.message_manager import message_manager

            active_tickets = sheets_manager.get_active_tickets(
                user_tg_id=user.id,
                ticket_type="payment_link",
                today=True
            )

            if active_tickets:
                ticket_id = active_tickets[0]['id']
                await message.answer(
                    f"❌ У вас уже есть активная заявка #{ticket_id} на сегодня.\n"
                    f"Закройте её командой /cancel_ticket {ticket_id} или дождитесь ответа."
                )
                return

            await state.set_state(PaymentLinkStates.waiting_for_chat_id)
            sent_message = await message.answer("📝 Введите номер чата:")
            message_manager.add_message(user.id, sent_message.message_id)
            logger.info(f"Пользователь {username} начал создание заявки на ссылку")

        except Exception as e:
            logger.error(f"Ошибка при проверке активных тикетов для {username}: {e}")
            await message.answer("❌ Произошла ошибка. Попробуйте позже.")

    @dp.message(F.text == "💸 Тикет на выплату", is_private_chat())
    async def button_ticket(message: Message, state: FSMContext):
        logger.info(f"Нажата кнопка 'Тикет на выплату' пользователем {message.from_user.id}")
        user = message.from_user
        username = f"@{user.username}" if user.username else None

        if not username:
            await message.answer("❌ Для работы с ботом необходимо установить username")
            return

        try:
            from bot.states import PayoutTicketStates

            active_tickets = sheets_manager.get_active_tickets(
                user_tg_id=user.id,
                ticket_type="payout_request",
                today=True
            )

            if active_tickets:
                ticket_id = active_tickets[0]['id']
                await message.answer(
                    f"❌ У вас уже есть активная заявка на выплату #{ticket_id} за сегодня.\n"
                    f"Дождитесь ответа или отмените её командой /cancel_ticket {ticket_id}"
                )
                return

            await state.set_state(PayoutTicketStates.waiting_for_table_amount)
            await message.answer(
                "📝 Создание тикета на выплату\n\n"
                "💰 Введите сумму, которая указана в таблице:"
            )
            logger.info(f"Пользователь {username} начал создание тикета на выплату")

        except Exception as e:
            logger.error(f"Ошибка при начале создания тикета для {username}: {e}")
            await message.answer("❌ Произошла ошибка. Попробуйте позже.")

    @dp.message(F.text == "✅ Подтвердить выплату", is_private_chat())
    async def button_confirm_payout(message: Message, state: FSMContext):
        logger.info(f"Нажата кнопка 'Подтвердить выплату' пользователем {message.from_user.id}")
        user = message.from_user
        username = f"@{user.username}" if user.username else None

        if not username:
            await message.answer("❌ Для работы с ботом необходимо установить username")
            return

        try:
            from bot.states import ConfirmPayoutStates
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

            payout = sheets_manager.get_tutor_payout(username)

            if payout is None:
                await message.answer("❌ Информация о выплате не найдена.")
                return

            await state.update_data(payout=payout)
            await state.set_state(ConfirmPayoutStates.waiting_for_confirmation)

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Да, ожидаю акт", callback_data="confirm_payout_yes"),
                    InlineKeyboardButton(text="❌ Нет, оформить тикет", callback_data="confirm_payout_no")
                ]
            ])

            await message.answer(
                f"💰 Ваш баланс к выплате: {payout:.0f}₽\n\n"
                f"⚠️ Проверьте совпадение с задачей в консоли и подтвердите.\n\n"
                f"Вы уверены?",
                reply_markup=keyboard
            )

            logger.info(f"Пользователь {username} запросил подтверждение выплаты {payout}₽")

        except Exception as e:
            logger.error(f"Ошибка при подтверждении выплаты для {username}: {e}")
            await message.answer("❌ Произошла ошибка. Попробуйте позже.")

    @dp.message(F.text == "📋 Заявки на ссылки", is_private_chat())
    async def button_requests(message: Message):
        logger.info(f"Нажата кнопка 'Заявки на ссылки' пользователем {message.from_user.id}")
        user = message.from_user
        username = f"@{user.username}" if user.username else None

        if not username:
            await message.answer("❌ Для работы с ботом необходимо установить username")
            return

        try:
            from bot.filters import get_user_status_cached

            status = get_user_status_cached(user.id, username, sheets_manager)

            if status not in [2, 3]:
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

    @dp.message(F.text == "🎫 Тикеты на выплату", is_private_chat())
    async def button_tickets(message: Message):
        logger.info(f"Нажата кнопка 'Тикеты на выплату' пользователем {message.from_user.id}")
        user = message.from_user
        username = f"@{user.username}" if user.username else None

        if not username:
            await message.answer("❌ Для работы с ботом необходимо установить username")
            return

        try:
            from bot.filters import get_user_status_cached

            status = get_user_status_cached(user.id, username, sheets_manager)

            if status != 3:
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

    @dp.message(F.text == "📜 История", is_private_chat())
    async def button_history(message: Message):
        logger.info(f"Нажата кнопка 'История' пользователем {message.from_user.id}")
        user = message.from_user
        username = f"@{user.username}" if user.username else None

        if not username:
            await message.answer("❌ Для работы с ботом необходимо установить username")
            return

        try:
            from bot.utils.message_manager import message_manager

            tickets = sheets_manager.get_user_ticket_history(user.id)

            if not tickets:
                sent_message = await message.answer("📋 У вас пока нет тикетов")
                message_manager.add_message(user.id, sent_message.message_id)
                return

            response = f"📋 История ваших тикетов ({len(tickets)}):\n\n"

            for ticket in tickets:
                ticket_type = ticket['ticket_type']
                status = ticket['status']
                created = ticket['created_at'][:10] if ticket['created_at'] else 'Неизвестно'

                status_emoji = {
                    'ожидание': '⏳',
                    'в процессе': '🔄',
                    'закрыт': '✅',
                    'отменено': '❌'
                }.get(status, '❓')

                type_name = {
                    'payment_link': 'Заявка на ссылку',
                    'payout_request': 'Тикет на выплату',
                    'confirmation': 'Подтверждение выплаты'
                }.get(ticket_type, ticket_type)

                response += f"🎫 #{ticket['id']} | {type_name}\n"
                response += f"Статус: {status_emoji} {status}\n"
                response += f"Создан: {created}\n"

                data = ticket['ticket_data']
                if ticket_type == 'payment_link':
                    response += f"Чат: {data.get('chat_id', 'N/A')}, Сумма: {data.get('amount', 'N/A')}₽\n"
                elif ticket_type == 'payout_request':
                    response += f"Сумма: {data.get('correct_amount', data.get('amount', 'N/A'))}₽\n"

                if ticket['comment']:
                    response += f"💬 {ticket['comment']}\n"

                response += "\n"

            sent_message = await message.answer(response)
            message_manager.add_message(user.id, sent_message.message_id)
            logger.info(f"Пользователь {username} запросил историю тикетов")

        except Exception as e:
            logger.error(f"Ошибка при получении истории для {username}: {e}")
            await message.answer("❌ Произошла ошибка. Попробуйте позже.")

    @dp.message(F.text == "📋 Помощь", is_private_chat())
    async def button_help(message: Message):
        logger.info(f"Нажата кнопка 'Помощь' пользователем {message.from_user.id}")
        user = message.from_user
        username = f"@{user.username}" if user.username else None

        if not username:
            await message.answer("❌ Для работы с ботом необходимо установить username")
            return

        from bot.filters import get_user_status_cached

        status = get_user_status_cached(user.id, username, sheets_manager)

        if status == 0:
            await message.answer("❌ Вы не зарегистрированы в системе")
            return

        help_text = "📖 Справка по командам\n\n"

        if status == 5:  # Репетитор
            help_text += (
                "💰 /balance - Показывает вашу текущую выплату и детализацию занятий\n\n"
                "🔗 /payment_link - Создать заявку на генерацию ссылки для оплаты занятия. "
                "Бот запросит номер чата, дату, сумму и email родителя.\n\n"
                "💸 /ticket - Создать тикет на выплату. Бот запросит:\n"
                "  1. Сумму, которая указана в таблице\n"
                "  2. Сумму, которая должна быть\n"
                "  3. Покажет список ваших занятий для проверки\n"
                "  4. Вы можете добавить комментарий или написать 'ОК'\n"
                "  ℹ️ Финансовый учет ведется с четверга по среду включительно\n\n"
                "✅ /confirm_payout - Подтвердить получение выплаты без создания тикета\n\n"
                "📜 /history - Посмотреть историю всех ваших тикетов и заявок\n\n"
                "❌ /cancel_ticket <ID> - Отменить свой тикет по ID\n\n"
                "Пример: /cancel_ticket 123"
            )
        elif status == 2:  # Админ ссылок
            help_text += (
                "🔗 /payment_link - Создать заявку на ссылку\n\n"
                "📋 /requests - Показать список активных заявок на ссылки\n\n"
                "📜 /history - Посмотреть историю всех ваших тикетов и заявок\n\n"
                "📨 /reply <ID> <ссылка> - Ответить на заявку репетитора\n"
                "Пример: /reply 123 https://pay.link/abc\n\n"
                "Также можно ответить на сообщение бота с заявкой, отправив только ссылку"
            )
        elif status == 3:  # Старший админ
            help_text += (
                "🔗 /payment_link - Создать заявку на ссылку\n\n"
                "📋 /requests - Показать список активных заявок на ссылки\n\n"
                "📋 /tickets - Показать список активных тикетов на выплату\n\n"
                "📜 /history - Посмотреть историю всех ваших тикетов и заявок\n\n"
                "📨 /reply <ID> <ссылка> - Ответить на заявку репетитора\n"
                "Пример: /reply 123 https://pay.link/abc\n\n"
                "✅ /approve <ID> - Одобрить заявку на выплату\n"
                "Пример: /approve 123\n\n"
                "❌ /reject <ID> <причина> - Отклонить заявку на выплату\n"
                "Пример: /reject 123 Неверная сумма"
            )

        await message.answer(help_text)

    @dp.message(F.text == "📊 Статус выплат", is_private_chat())
    async def button_status(message: Message):
        logger.info(f"Нажата кнопка 'Статус выплат' пользователем {message.from_user.id}")
        user = message.from_user
        username = f"@{user.username}" if user.username else None

        if not username:
            await message.answer("❌ Для работы с ботом необходимо установить username")
            return

        try:
            from bot.filters import get_user_status_cached

            status = get_user_status_cached(user.id, username, sheets_manager)

            if status != 3:
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

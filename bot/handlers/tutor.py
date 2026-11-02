from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from bot.states import PaymentLinkStates, PayoutTicketStates, ConfirmPayoutStates
from bot.filters import is_private_chat
from bot.utils.validators import validate_date, validate_email, validate_amount, validate_chat_id
from bot.utils.notifications import notify_admins_payment_link, notify_senior_admin_payout, notify_admins_ticket_cancelled
from bot.utils.message_manager import message_manager
import logging

logger = logging.getLogger(__name__)

router = Router()


def register_tutor_handlers(dp, sheets_manager, bot):
    

    @dp.message(Command("balance"), is_private_chat())
    async def cmd_balance(message: Message):
        
        user = message.from_user
        username = f"@{user.username}" if user.username else None

        if not username:
            await message.answer("❌ Для работы с ботом необходимо установить username")
            return

        try:
            # Получаем сумму выплаты из листа week
            payout = sheets_manager.get_tutor_payout(username)

            # Получаем список занятий из листа current_day
            lessons = sheets_manager.get_tutor_lessons(username)

            if payout is None:
                await message.answer("❌ Информация о выплате не найдена. Обратитесь к администратору.")
                return

            # Формируем сообщение
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

                    # Определяем эмодзи статуса
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

    @dp.message(Command("payment_link"), is_private_chat())
    async def cmd_payment_link(message: Message, state: FSMContext):
        
        user = message.from_user
        username = f"@{user.username}" if user.username else None

        if not username:
            await message.answer("❌ Для работы с ботом необходимо установить username")
            return

        try:
            # Проверяем наличие активного тикета типа payment_link за сегодня
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

            # Начинаем FSM диалог
            await state.set_state(PaymentLinkStates.waiting_for_chat_id)
            sent_message = await message.answer("📝 Введите номер чата:")
            message_manager.add_message(user.id, sent_message.message_id)
            logger.info(f"Пользователь {username} начал создание заявки на ссылку")

        except Exception as e:
            logger.error(f"Ошибка при проверке активных тикетов для {username}: {e}")
            await message.answer("❌ Произошла ошибка. Попробуйте позже.")

    @dp.message(PaymentLinkStates.waiting_for_chat_id)
    async def process_chat_id(message: Message, state: FSMContext):
        
        is_valid, chat_id = validate_chat_id(message.text)

        if not is_valid:
            await message.answer("❌ Неверный формат. Введите целое число больше 0:")
            return

        # Сохраняем в FSM
        await state.update_data(chat_id=chat_id)
        await state.set_state(PaymentLinkStates.waiting_for_date)
        await message.answer("📅 Введите дату занятия (DD.MM.YYYY):")

    @dp.message(PaymentLinkStates.waiting_for_date)
    async def process_date(message: Message, state: FSMContext):
        
        is_valid, error_msg = validate_date(message.text)

        if not is_valid:
            await message.answer(error_msg)
            return

        # Сохраняем в FSM
        await state.update_data(date=message.text)
        await state.set_state(PaymentLinkStates.waiting_for_amount)
        await message.answer("💰 Введите сумму:")

    @dp.message(PaymentLinkStates.waiting_for_amount)
    async def process_amount(message: Message, state: FSMContext):
        
        is_valid, amount = validate_amount(message.text)

        if not is_valid:
            await message.answer("❌ Неверный формат. Введите число больше 0:")
            return

        # Сохраняем в FSM
        await state.update_data(amount=amount)
        await state.set_state(PaymentLinkStates.waiting_for_email)
        await message.answer("📧 Введите email родителя:")

    @dp.message(PaymentLinkStates.waiting_for_email)
    async def process_email(message: Message, state: FSMContext):
        
        if not validate_email(message.text):
            await message.answer("❌ Неверный формат email. Попробуйте снова:")
            return

        user = message.from_user
        username = f"@{user.username}" if user.username else None

        # Получаем все данные из FSM
        data = await state.get_data()
        email = message.text

        try:
            # Создаем тикет в Google Sheets
            ticket_id = sheets_manager.create_ticket({
                'tg_id': user.id,
                'username': username,
                'ticket_type': 'payment_link',
                'ticket_data': {
                    'chat_id': str(data['chat_id']),
                    'date': data['date'],
                    'amount': str(data['amount']),
                    'email': email
                },
                'status': 'ожидание'
            })

            # Добавляем заявку в лист payment_links
            sheets_manager.add_payment_link_request(
                ticket_id=ticket_id,
                username=username,
                tg_id=user.id,
                chat_id=str(data['chat_id']),
                date=data['date'],
                amount=str(data['amount']),
                email=email
            )

            # Отправляем подтверждение репетитору
            await message.answer(
                f"✅ Заявка #{ticket_id} принята. Ожидайте генерации ссылки."
            )

            # Уведомляем админов
            ticket_data = {
                'id': ticket_id,
                'tg_id': user.id,
                'username': username,
                'ticket_data': {
                    'chat_id': str(data['chat_id']),
                    'date': data['date'],
                    'amount': str(data['amount']),
                    'email': email
                }
            }
            await notify_admins_payment_link(bot, sheets_manager, ticket_data)

            logger.info(f"Создан тикет #{ticket_id} для {username}")

        except Exception as e:
            logger.error(f"Ошибка при создании тикета для {username}: {e}")
            await message.answer("❌ Произошла ошибка при создании заявки. Попробуйте позже.")

        # Завершаем FSM
        await state.clear()

    @dp.message(Command("ticket"), is_private_chat())
    async def cmd_ticket(message: Message, state: FSMContext):
        
        user = message.from_user
        username = f"@{user.username}" if user.username else None

        if not username:
            await message.answer("❌ Для работы с ботом необходимо установить username")
            return

        try:
            # Проверяем, открыта ли форма выплат
            if not sheets_manager.is_payout_form_open():
                await message.answer(
                    "❌ Форма подтверждения выплат закрыта.\n\n"
                    "Создание тикетов временно недоступно. "
                    "Дождитесь открытия формы от администратора."
                )
                logger.info(f"Пользователь {username} попытался создать тикет при закрытой форме")
                return

            # Проверяем наличие активного тикета типа payout_request за сегодня
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

            # Начинаем FSM диалог
            await state.set_state(PayoutTicketStates.waiting_for_table_amount)
            await message.answer(
                "📝 Создание тикета на выплату\n\n"
                "💰 Введите сумму, которая указана в таблице:"
            )
            logger.info(f"Пользователь {username} начал создание тикета на выплату")

        except Exception as e:
            logger.error(f"Ошибка при начале создания тикета для {username}: {e}")
            await message.answer("❌ Произошла ошибка. Попробуйте позже.")

    @dp.message(PayoutTicketStates.waiting_for_table_amount)
    async def process_table_amount(message: Message, state: FSMContext):
        
        is_valid, amount = validate_amount(message.text)

        if not is_valid:
            await message.answer("❌ Неверный формат. Введите число больше 0:")
            return

        # Сохраняем в FSM
        await state.update_data(table_amount=amount)
        await state.set_state(PayoutTicketStates.waiting_for_correct_amount)
        await message.answer("💰 Введите сумму, которая должна быть:")

    @dp.message(PayoutTicketStates.waiting_for_correct_amount)
    async def process_correct_amount(message: Message, state: FSMContext):
        
        is_valid, amount = validate_amount(message.text)

        if not is_valid:
            await message.answer("❌ Неверный формат. Введите число больше 0:")
            return

        user = message.from_user
        username = f"@{user.username}" if user.username else None

        # Сохраняем в FSM
        await state.update_data(correct_amount=amount)

        try:
            # Получаем список занятий
            lessons = sheets_manager.get_tutor_lessons(username)

            # Формируем сообщение со списком занятий
            response = "📊 Ваши занятия за период:\n\n"

            if lessons:
                paid_count = 0
                unpaid_count = 0

                for lesson in lessons:
                    date = lesson['date']
                    chat_id = lesson['chat_id']
                    amount_lesson = lesson['amount']
                    status = lesson['status']

                    status_emoji = "✅" if status == "Оплачено" else "❌"

                    if status == "Оплачено":
                        paid_count += 1
                    else:
                        unpaid_count += 1

                    response += f"{date} | Чат #{chat_id} | {amount_lesson}₽ | {status_emoji} {status}\n"

                response += f"\nВсего: {len(lessons)} занятий\n"
                response += f"Оплачено: {paid_count}\n"
                response += f"Неоплачено: {unpaid_count}\n"
            else:
                response += "Занятий не найдено\n"

            response += (
                "\n⚠️ Проверьте, все ли занесено!\n\n"
                "Если каких-то данных не хватает или есть разногласия, "
                "ответьте на это сообщение списком и рецензией.\n\n"
                "ℹ️ Финансовый учет ведется с четверга по среду включительно.\n\n"
                "Если всё верно, отправьте: ОК\n"
                "Если есть замечания, отправьте их текстом."
            )

            await message.answer(response)
            await state.set_state(PayoutTicketStates.waiting_for_comment)

        except Exception as e:
            logger.error(f"Ошибка при получении списка занятий для {username}: {e}")
            await message.answer("❌ Произошла ошибка. Попробуйте позже.")
            await state.clear()

    @dp.message(PayoutTicketStates.waiting_for_comment)
    async def process_comment_and_create_ticket(message: Message, state: FSMContext):
        
        user = message.from_user
        username = f"@{user.username}" if user.username else None

        comment = message.text.strip()

        # Получаем данные из FSM
        data = await state.get_data()
        table_amount = data['table_amount']
        correct_amount = data['correct_amount']

        try:
            # Создаем тикет
            ticket_id = sheets_manager.create_ticket({
                'tg_id': user.id,
                'username': username,
                'ticket_type': 'payout_request',
                'ticket_data': {
                    'table_amount': str(table_amount),
                    'correct_amount': str(correct_amount),
                    'comment': comment if comment.upper() != 'ОК' else ''
                },
                'status': 'ожидание'
            })

            # Отправляем подтверждение репетитору
            await message.answer(
                f"✅ Тикет #{ticket_id} создан.\n"
                f"Сумма в таблице: {table_amount:.0f}₽\n"
                f"Должна быть: {correct_amount:.0f}₽\n"
                f"Ожидайте подтверждения."
            )

            # Обновляем статус в payout_status
            sheets_manager.update_payout_status(username, 'тикет')

            # Уведомляем старшего админа
            ticket_data = {
                'id': ticket_id,
                'tg_id': user.id,
                'username': username,
                'ticket_data': {
                    'table_amount': str(table_amount),
                    'correct_amount': str(correct_amount),
                    'comment': comment if comment.upper() != 'ОК' else ''
                }
            }
            await notify_senior_admin_payout(bot, sheets_manager, ticket_data)

            logger.info(f"Создан тикет на выплату #{ticket_id} для {username}")

        except Exception as e:
            logger.error(f"Ошибка при создании тикета для {username}: {e}")
            await message.answer("❌ Произошла ошибка при создании тикета. Попробуйте позже.")

        # Завершаем FSM
        await state.clear()

    @dp.message(Command("confirm_payout"), is_private_chat())
    async def cmd_confirm_payout(message: Message, state: FSMContext):
        
        user = message.from_user
        username = f"@{user.username}" if user.username else None

        if not username:
            await message.answer("❌ Для работы с ботом необходимо установить username")
            return

        try:
            # Получаем сумму выплаты
            payout = sheets_manager.get_tutor_payout(username)

            if payout is None:
                await message.answer("❌ Информация о выплате не найдена.")
                return

            # Сохраняем сумму в FSM
            await state.update_data(payout=payout)
            await state.set_state(ConfirmPayoutStates.waiting_for_confirmation)

            # Создаем inline-кнопки
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Да, ожидаю акт", callback_data="confirm_payout_yes"),
                    InlineKeyboardButton(text="❌ Нет, оформить тикет", callback_data="confirm_payout_no")
                ]
            ])

            # Отправляем сообщение с балансом и кнопками
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

    @dp.callback_query(F.data == "confirm_payout_yes")
    async def callback_confirm_payout_yes(callback: CallbackQuery, state: FSMContext):
        
        user = callback.from_user
        username = f"@{user.username}" if user.username else None

        try:
            # Получаем сумму из FSM
            data = await state.get_data()
            payout = data.get('payout')

            if payout is None:
                await callback.message.answer("❌ Ошибка: сумма не найдена. Попробуйте снова.")
                await callback.answer()
                await state.clear()
                return

            # Создаем тикет типа confirmation со статусом "закрыт"
            ticket_id = sheets_manager.create_ticket({
                'tg_id': user.id,
                'username': username,
                'ticket_type': 'confirmation',
                'ticket_data': {
                    'amount': str(payout)
                },
                'status': 'закрыт'
            })

            # Обновляем статус в payout_status
            sheets_manager.update_payout_status(username, 'подтверждение')

            # Удаляем сообщение с кнопками
            await callback.message.delete()

            # Отправляем подтверждение репетитору
            await callback.message.answer(
                f"✅ Вы подтвердили выплату {payout:.0f}₽. Ожидайте акт."
            )

            await callback.answer("✅ Выплата подтверждена")
            logger.info(f"Пользователь {username} подтвердил выплату {payout}₽")

        except Exception as e:
            logger.error(f"Ошибка при подтверждении выплаты для {username}: {e}")
            await callback.message.answer("❌ Произошла ошибка. Попробуйте позже.")
            await callback.answer()

        # Завершаем FSM
        await state.clear()

    @dp.callback_query(F.data == "confirm_payout_no")
    async def callback_confirm_payout_no(callback: CallbackQuery, state: FSMContext):
        
        user = callback.from_user
        username = f"@{user.username}" if user.username else None

        try:
            # Удаляем сообщение с кнопками
            await callback.message.delete()

            # Проверяем наличие активного тикета типа payout_request за сегодня
            active_tickets = sheets_manager.get_active_tickets(
                user_tg_id=user.id,
                ticket_type="payout_request",
                today=True
            )

            if active_tickets:
                ticket_id = active_tickets[0]['id']
                await callback.message.answer(
                    f"❌ У вас уже есть активная заявка на выплату #{ticket_id} за сегодня.\n"
                    f"Дождитесь ответа или отмените её командой /cancel_ticket {ticket_id}"
                )
                await callback.answer()
                await state.clear()
                return

            # Начинаем FSM диалог для создания тикета
            await state.set_state(PayoutTicketStates.waiting_for_table_amount)
            await callback.message.answer(
                "📝 Создание тикета на выплату\n\n"
                "💰 Введите сумму, которая указана в таблице:"
            )

            await callback.answer("Начинаем оформление тикета")
            logger.info(f"Пользователь {username} начал создание тикета на выплату через confirm_payout")

        except Exception as e:
            logger.error(f"Ошибка при начале создания тикета для {username}: {e}")
            await callback.message.answer("❌ Произошла ошибка. Попробуйте позже.")
            await callback.answer()
            await state.clear()

    @dp.message(Command("cancel_ticket"), is_private_chat())
    async def cmd_cancel_ticket(message: Message):
        
        user = message.from_user
        username = f"@{user.username}" if user.username else None

        if not username:
            await message.answer("❌ Для работы с ботом необходимо установить username")
            return

        # Парсим ID тикета из аргументов
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.answer("❌ Использование: /cancel_ticket <ID>\nПример: /cancel_ticket 123")
            return

        try:
            ticket_id = int(args[1])
        except ValueError:
            await message.answer("❌ ID тикета должен быть числом")
            return

        try:
            # Отменяем тикет
            success = sheets_manager.cancel_ticket(ticket_id, user.id)

            if not success:
                await message.answer(
                    f"❌ Не удалось отменить тикет #{ticket_id}.\n"
                    f"Возможные причины:\n"
                    f"- Тикет не найден\n"
                    f"- Тикет не принадлежит вам\n"
                    f"- Тикет уже закрыт"
                )
                return

            # Отправляем подтверждение
            await message.answer(
                f"❌ Тикет #{ticket_id} отменён. Создайте новую заявку при необходимости."
            )

            # Уведомляем админов
            await notify_admins_ticket_cancelled(bot, sheets_manager, ticket_id, username)

            logger.info(f"Пользователь {username} отменил тикет #{ticket_id}")

        except Exception as e:
            logger.error(f"Ошибка при отмене тикета #{ticket_id} для {username}: {e}")
            await message.answer("❌ Произошла ошибка. Попробуйте позже.")

    @dp.message(Command("history"), is_private_chat())
    async def cmd_history(message: Message):
        
        user = message.from_user
        username = f"@{user.username}" if user.username else None

        if not username:
            await message.answer("❌ Для работы с ботом необходимо установить username")
            return

        try:
            # Получаем историю тикетов
            tickets = sheets_manager.get_user_ticket_history(user.id)

            if not tickets:
                sent_message = await message.answer("📋 У вас пока нет тикетов")
                message_manager.add_message(user.id, sent_message.message_id)
                return

            # Формируем сообщение
            response = f"📋 История ваших тикетов ({len(tickets)}):\n\n"

            for ticket in tickets:
                ticket_type = ticket['ticket_type']
                status = ticket['status']
                created = ticket['created_at'][:10] if ticket['created_at'] else 'Неизвестно'

                # Эмодзи статуса
                status_emoji = {
                    'ожидание': '⏳',
                    'в процессе': '🔄',
                    'закрыт': '✅',
                    'отменено': '❌'
                }.get(status, '❓')

                # Название типа тикета
                type_name = {
                    'payment_link': 'Заявка на ссылку',
                    'payout_request': 'Тикет на выплату',
                    'confirmation': 'Подтверждение выплаты'
                }.get(ticket_type, ticket_type)

                response += f"🎫 #{ticket['id']} | {type_name}\n"
                response += f"Статус: {status_emoji} {status}\n"
                response += f"Создан: {created}\n"

                # Дополнительная информация в зависимости от типа
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

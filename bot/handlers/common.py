from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from bot.filters import get_user_status_cached, is_private_chat
from bot.keyboards import get_tutor_keyboard, get_link_admin_keyboard, get_senior_admin_keyboard
from bot.utils.message_manager import message_manager
import logging

logger = logging.getLogger(__name__)

router = Router()


def register_common_handlers(dp, sheets_manager, bot):

    @dp.message(Command("start"), is_private_chat())
    async def cmd_start(message: Message, state: FSMContext):
        user = message.from_user
        username = f"@{user.username}" if user.username else None

        await state.clear()

        await message_manager.clear_user_messages(bot, user.id)

        if not username:
            await message.answer("❌ Для работы с ботом необходимо установить username в настройках Telegram")
            return

        status = get_user_status_cached(user.id, username, sheets_manager)

        if status == 0:
            await message.answer(
                "❌ Вы не зарегистрированы в системе.\n"
                "Обратитесь к администратору для получения доступа."
            )
            return

        try:
            sheets_manager.update_user_tg_id(username, user.id)
        except Exception as e:
            logger.error(f"Ошибка при обновлении TG_ID для {username}: {e}")

        role_name = {
            5: "Репетитор",
            2: "Администратор ссылок",
            3: "Старший администратор"
        }.get(status, "Пользователь")

        commands_text = ""
        keyboard = None

        if status == 5:  # Репетитор
            commands_text = (
                "\n📋 Доступные команды:\n\n"
                "💰 **Баланс** (/balance)\n"
                "Проверить баланс и историю занятий\n\n"
                "🔗 **Заявка на ссылку** (/payment_link)\n"
                "Создать заявку на ссылку для оплаты\n\n"
                "💸 **Тикет на выплату** (/ticket)\n"
                "Создать тикет на выплату\n\n"
                "✅ **Подтвердить выплату** (/confirm_payout)\n"
                "Подтвердить получение выплаты\n\n"
                "📜 **История** (/history)\n"
                "Посмотреть историю всех тикетов и заявок\n\n"
                "❌ **Отменить тикет** (/cancel_ticket <ID>)\n"
                "Отменить свой тикет\n\n"
                "📋 **Помощь** (/help)\n"
                "Справка по командам"
            )
            keyboard = get_tutor_keyboard()
        elif status == 2:  # Админ ссылок
            commands_text = (
                "\n📋 Доступные команды:\n\n"
                "🔗 **Заявка на ссылку** (/payment_link)\n"
                "Создать заявку на ссылку\n\n"
                "📋 **Заявки на ссылки** (/requests)\n"
                "Список активных заявок на ссылки\n\n"
                "📨 **Ответить на заявку** (/reply <ID> <ссылка>)\n"
                "Ответить на заявку репетитора\n\n"
                "📜 **История** (/history)\n"
                "Посмотреть историю всех тикетов\n\n"
                "📋 **Помощь** (/help)\n"
                "Справка по командам"
            )
            keyboard = get_link_admin_keyboard()
        elif status == 3:  # Старший админ
            commands_text = (
                "\n📋 Доступные команды:\n\n"
                "🔗 **Заявка на ссылку** (/payment_link)\n"
                "Создать заявку на ссылку\n\n"
                "📋 **Заявки на ссылки** (/requests)\n"
                "Список активных заявок на ссылки\n\n"
                "🎫 **Тикеты на выплату** (/tickets)\n"
                "Список активных тикетов на выплату\n\n"
                "📊 **Статус выплат** (/status)\n"
                "Список всех пользователей и статусов их выплат\n\n"
                "📢 **Открыть форму выплат** (/open_payout)\n"
                "Открыть форму подтверждения выплат для всех репетиторов\n\n"
                "🔒 **Закрыть форму выплат** (/close_payout)\n"
                "Закрыть форму и получить статистику\n\n"
                "📨 **Ответить на заявку** (/reply <ID> <ссылка>)\n"
                "Ответить на заявку репетитора\n\n"
                "✅ **Одобрить выплату** (/approve <ID>)\n"
                "Одобрить заявку на выплату\n\n"
                "❌ **Отклонить выплату** (/reject <ID> <причина>)\n"
                "Отклонить заявку на выплату\n\n"
                "📢 **Уведомление об обновлении** (/notify_update)\n"
                "Отправить уведомление об обновлении данных в группы\n\n"
                "📜 **История** (/history)\n"
                "Посмотреть историю всех тикетов\n\n"
                "📋 **Помощь** (/help)\n"
                "Справка по командам"
            )
            keyboard = get_senior_admin_keyboard()

        sent_message = await message.answer(
            f"👋 Добро пожаловать, {user.first_name}!\n\n"
            f"Ваша роль: {role_name}{commands_text}",
            reply_markup=keyboard
        )

        message_manager.add_message(user.id, sent_message.message_id)

        logger.info(f"Пользователь {username} ({user.id}) запустил бота, статус: {status}")

    @dp.message(Command("help"), is_private_chat())
    async def cmd_help(message: Message):
        user = message.from_user
        username = f"@{user.username}" if user.username else None

        if not username:
            await message.answer("❌ Для работы с ботом необходимо установить username")
            return

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
                "🎫 /tickets - Показать список активных тикетов на выплату\n\n"
                "📊 /status - Показать статус выплат всех пользователей\n\n"
                "📢 /open_payout - Открыть форму подтверждения выплат\n"
                "  • Отправляет уведомления всем репетиторам\n"
                "  • Разрешает создание тикетов на выплату\n"
                "  • Показывает статистику рассылки\n\n"
                "🔒 /close_payout - Закрыть форму подтверждения выплат\n"
                "  • Показывает итоговую статистику\n"
                "  • Блокирует создание новых тикетов\n"
                "  • Сбрасывает все статусы на 'ожидание'\n\n"
                "📜 /history - Посмотреть историю всех ваших тикетов и заявок\n\n"
                "📨 /reply <ID> <ссылка> - Ответить на заявку репетитора\n"
                "Пример: /reply 123 https://pay.link/abc\n\n"
                "✅ /approve <ID> - Одобрить заявку на выплату\n"
                "Пример: /approve 123\n\n"
                "❌ /reject <ID> <причина> - Отклонить заявку на выплату\n"
                "Пример: /reject 123 Неверная сумма\n\n"
                "📢 /notify_update - Отправить уведомление об обновлении данных в группы\n"
                "  • Уведомляет всех репетиторов в группах\n"
                "  • Доступно только старшим админам"
            )

        await message.answer(help_text)

    @dp.message(F.text == "🏠 Главное меню", is_private_chat())
    async def button_main_menu(message: Message, state: FSMContext):
        logger.info(f"Нажата кнопка 'Главное меню' пользователем {message.from_user.id}")
        await cmd_start(message, state)

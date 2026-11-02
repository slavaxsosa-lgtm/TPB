from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_tutor_keyboard()->ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="💰 Баланс"), KeyboardButton(text="🔗 Заявка на ссылку")], [KeyboardButton(text="💸 Тикет на выплату"), KeyboardButton(text="✅ Подтвердить выплату")], [KeyboardButton(text="📜 История"), KeyboardButton(text="📋 Помощь")], [KeyboardButton(text="🏠 Главное меню")]], resize_keyboard=True, input_field_placeholder="Выберите действие...")

def get_link_admin_keyboard()->ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🔗 Заявка на ссылку"), KeyboardButton(text="📋 Заявки на ссылки")], [KeyboardButton(text="📜 История"), KeyboardButton(text="📋 Помощь")], [KeyboardButton(text="🏠 Главное меню")]], resize_keyboard=True, input_field_placeholder="Выберите действие...")

def get_senior_admin_keyboard()->ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🔗 Заявка на ссылку"), KeyboardButton(text="📋 Заявки на ссылки")], [KeyboardButton(text="🎫 Тикеты на выплату"), KeyboardButton(text="📊 Статус выплат")], [KeyboardButton(text="📜 История"), KeyboardButton(text="📋 Помощь")], [KeyboardButton(text="🏠 Главное меню")]], resize_keyboard=True, input_field_placeholder="Выберите действие...")

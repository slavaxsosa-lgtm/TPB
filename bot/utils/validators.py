import re
from datetime import datetime
from typing import Tuple

def validate_date(date_str:str)->Tuple[bool, str]:
    try:
        date_obj=datetime.strptime(date_str, "%d.%m.%Y")
        today=datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if date_obj<today:
            return False, "❌ Дата не может быть в прошлом"
        return True, ""
    except ValueError:
        return False, "❌ Неверный формат даты. Используйте DD.MM.YYYY (например, 25.04.2026)"

def validate_email(email:str)->bool:
    pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_amount(amount_str:str)->Tuple[bool, float]:
    try:
        amount=float(amount_str.replace(',', '.'))
        if amount<=0:
            return False, 0
        return True, amount
    except ValueError:
        return False, 0

def validate_chat_id(chat_id_str:str)->Tuple[bool, int]:
    try:
        chat_id=int(chat_id_str)
        if chat_id<=0:
            return False, 0
        return True, chat_id
    except ValueError:
        return False, 0

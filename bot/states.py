from aiogram.fsm.state import State, StatesGroup

class PaymentLinkStates(StatesGroup):
    waiting_for_chat_id=State()
    waiting_for_date=State()
    waiting_for_amount=State()
    waiting_for_email=State()

class PayoutTicketStates(StatesGroup):
    waiting_for_table_amount=State()
    waiting_for_correct_amount=State()
    waiting_for_comment=State()

class ConfirmPayoutStates(StatesGroup):
    waiting_for_confirmation=State()

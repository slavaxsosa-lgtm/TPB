from typing import List, Dict, Optional

class MockSheetsManager:
    def __init__(self, *args, **kwargs):
        self.users={
            '@testuser': 5,
            '@testadmin': 2,
            '@testowner': 3
        }
        self.tutors={
            '@testuser': {'full_name': 'Тест Пользователь', 'tg_id': 123456}
        }

    def get_user_status(self, username:str)->Optional[int]:
        return self.users.get(username)

    def get_tutor_payout(self, username:str)->Optional[float]:
        return 5000.0

    def get_tutor_lessons(self, username:str)->List[Dict]:
        return [
            {'date': '2026-11-01', 'chat_id': '123', 'amount': '1000', 'status': 'Оплачено'},
            {'date': '2026-11-02', 'chat_id': '124', 'amount': '1500', 'status': 'Оплачено'},
            {'date': '2026-11-03', 'chat_id': '125', 'amount': '2000', 'status': 'Ожидание'},
        ]

    def get_active_tickets(self, user_tg_id:int, ticket_type:str, today:bool=False)->List[Dict]:
        return []

    def create_ticket(self, data:Dict)->int:
        return 1

    def get_ticket(self, ticket_id:int)->Optional[Dict]:
        return None

    def get_user_ticket_history(self, user_tg_id:int)->List[Dict]:
        return []

    def update_ticket_status(self, ticket_id:int, status:str, admin_tg_id:int=0, comment:str=""):
        pass

    def cancel_ticket(self, ticket_id:int, user_tg_id:int)->bool:
        return True

    def get_all_active_tickets(self, ticket_type:str=None)->List[Dict]:
        return []

    def add_payment_link_request(self, *args, **kwargs):
        pass

    def update_payment_link(self, *args, **kwargs):
        return True

    def get_payment_links_history(self, username:str=None)->List[Dict]:
        return []

    def get_admins_by_status(self, status:int)->List[Dict]:
        admins=[]
        for user, st in self.users.items():
            if st==status:
                admins.append({'username': user, 'full_name': 'Admin', 'tg_id': 123456, 'status': st})
        return admins

    def get_all_tutors(self)->List[Dict]:
        return [
            {'username': '@testuser', 'full_name': 'Тест Пользователь', 'tg_id': 123456}
        ]

    def update_user_tg_id(self, username:str, tg_id:int)->bool:
        return True

    def get_payout_status(self, username:str=None):
        if username:
            return {
                'username': username,
                'full_name': 'Test User',
                'tg_id': 123456,
                'status': 'ожидание',
                'updated_at': '2026-11-02',
                'form_open': 'да'
            }
        return []

    def update_payout_status(self, username:str, status:str):
        return True

    def set_payout_form_status(self, is_open:bool):
        pass

    def is_payout_form_open(self)->bool:
        return True

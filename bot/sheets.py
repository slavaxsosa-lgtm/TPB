import gspread
from oauth2client.service_account import ServiceAccountCredentials
from typing import List, Dict, Optional
import json
import time
import logging
from datetime import datetime

logger=logging.getLogger(__name__)

class SheetsManager:
    def __init__(self, credentials_file:str, spreadsheet_id:str):
        self.spreadsheet_id=spreadsheet_id
        scope=[
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        try:
            creds=ServiceAccountCredentials.from_json_keyfile_name(credentials_file, scope)
            self.client=gspread.authorize(creds)
            self.spreadsheet=self.client.open_by_key(spreadsheet_id)
            logger.info(f"Connected to spreadsheet {spreadsheet_id}")
        except Exception as e:
            logger.error(f"Error connecting to Google Sheets: {e}")
            raise
    def _retry_on_quota(self, func, *args, **kwargs):
        max_retries=3
        delay=2
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except gspread.exceptions.APIError as e:
                if "RESOURCE_EXHAUSTED" in str(e) or "quota" in str(e).lower():
                    if attempt<max_retries-1:
                        logger.warning(f"Quota exceeded, retry {attempt+1}/{max_retries}")
                        time.sleep(delay)
                        continue
                raise
            except Exception as e:
                logger.error(f"Error executing operation: {e}")
                raise
    def get_tutor_lessons(self, username:str)->List[Dict]:
        def _get():
            sheet=self.spreadsheet.worksheet("current_day")
            all_values=sheet.get_all_values()
            lessons=[]
            for row in all_values[1:]:
                if len(row)>=13:
                    row_username=row[5].strip()
                    if row_username==username:
                        lessons.append({
                            'username':row[5],
                            'full_name':row[6],
                            'date':row[7],
                            'chat_id':row[8],
                            'amount':row[11],
                            'status':row[12]
                        })
            logger.info(f"Found {len(lessons)} lessons for {username}")
            return lessons
        return self._retry_on_quota(_get)
    def get_tutor_payout(self, username:str)->Optional[float]:
        def _get():
            sheet=self.spreadsheet.worksheet("week")
            all_values=sheet.get_all_values()
            for row in all_values[1:]:
                if len(row)>=3:
                    row_username=row[0].strip()
                    if row_username==username:
                        try:
                            payout=float(row[2].replace(',', '.').replace(' ', ''))
                            logger.info(f"Payout for {username}: {payout}")
                            return payout
                        except (ValueError, IndexError):
                            logger.warning(f"Failed to parse payout for {username}")
                            return None
            logger.warning(f"Payout for {username} not found")
            return None
        return self._retry_on_quota(_get)
    def get_user_status(self, username:str)->Optional[int]:
        def _get():
            sheet=self.spreadsheet.worksheet("admins")
            all_values=sheet.get_all_values()
            for row in all_values[1:]:
                if len(row)>=3:
                    row_username=row[0].strip()
                    if row_username==username:
                        try:
                            status=int(row[2])
                            logger.info(f"Status for {username}: {status}")
                            return status
                        except (ValueError, IndexError):
                            logger.warning(f"Failed to parse status for {username}")
                            return None
            logger.warning(f"User {username} not found in admins")
            return None
        return self._retry_on_quota(_get)
    def update_user_tg_id(self, username:str, tg_id:int)->bool:
        def _update():
            sheet=self.spreadsheet.worksheet("admins")
            all_values=sheet.get_all_values()
            for idx, row in enumerate(all_values[1:], start=2):
                if len(row)>=3:
                    row_username=row[0].strip()
                    if row_username==username:
                        current_tg_id=row[3] if len(row)>3 else ''
                        if current_tg_id and str(current_tg_id)==str(tg_id):
                            logger.debug(f"TG_ID for {username} already current")
                            return True
                        cell=f"D{idx}"
                        sheet.update(range_name=cell, values=[[str(tg_id)]])
                        logger.info(f"TG_ID {tg_id} recorded for {username} in cell {cell}")
                        return True
            logger.warning(f"User {username} not found for TG_ID update")
            return False
        return self._retry_on_quota(_update)
    def add_payment_link_request(self, ticket_id:int, username:str, tg_id:int, chat_id:str, date:str, amount:str, email:str):
        def _add():
            sheet=self.spreadsheet.worksheet("payment_links")
            row=[
                str(ticket_id),
                username,
                str(tg_id),
                chat_id,
                date,
                amount,
                email,
                '',
                datetime.now().isoformat(),
                ''
            ]
            sheet.append_row(row)
            logger.info(f"Payment link request #{ticket_id} added")
        return self._retry_on_quota(_add)
    def update_payment_link(self, ticket_id:int, link:str):
        def _update():
            sheet=self.spreadsheet.worksheet("payment_links")
            all_values=sheet.get_all_values()
            for idx, row in enumerate(all_values[1:], start=2):
                if len(row)>=1 and row[0]==str(ticket_id):
                    sheet.update(range_name=f"H{idx}", values=[[link]])
                    sheet.update(range_name=f"J{idx}", values=[[datetime.now().isoformat()]])
                    logger.info(f"Link for ticket #{ticket_id} updated")
                    return True
            logger.warning(f"Ticket #{ticket_id} not found in payment_links")
            return False
        return self._retry_on_quota(_update)
    def get_payment_links_history(self, username:str=None)->List[Dict]:
        def _get():
            sheet=self.spreadsheet.worksheet("payment_links")
            all_values=sheet.get_all_values()
            links=[]
            for row in all_values[1:]:
                if len(row)>=9:
                    if username and row[1]!=username:
                        continue
                    links.append({
                        'ticket_id':row[0],
                        'username':row[1],
                        'tg_id':row[2],
                        'chat_id':row[3],
                        'date':row[4],
                        'amount':row[5],
                        'email':row[6],
                        'link':row[7] if len(row)>7 else '',
                        'created_at':row[8] if len(row)>8 else '',
                        'sent_at':row[9] if len(row)>9 else ''
                    })
            logger.info(f"Retrieved {len(links)} payment link requests"+(f" for {username}" if username else ""))
            return links
        return self._retry_on_quota(_get)
    def get_admins_by_status(self, status:int)->List[Dict]:
        def _get():
            sheet=self.spreadsheet.worksheet("admins")
            all_values=sheet.get_all_values()
            admins=[]
            for row in all_values[1:]:
                if len(row)>=3:
                    try:
                        row_status=int(row[2])
                        if row_status==status:
                            tg_id=None
                            if len(row)>=4 and row[3]:
                                try:
                                    tg_id=int(row[3])
                                except ValueError:
                                    pass
                            admins.append({
                                'username':row[0],
                                'full_name':row[1],
                                'status':row_status,
                                'tg_id':tg_id
                            })
                    except (ValueError, IndexError):
                        continue
            logger.info(f"Found {len(admins)} admins with status {status}")
            return admins
        return self._retry_on_quota(_get)
    def create_ticket(self, data:Dict)->int:
        def _create():
            sheet=self.spreadsheet.worksheet("Tickets")
            all_values=sheet.get_all_values()
            max_id=0
            for row in all_values[1:]:
                if row and row[0]:
                    try:
                        ticket_id=int(row[0])
                        max_id=max(max_id, ticket_id)
                    except ValueError:
                        continue
            new_id=max_id+1
            ticket_data_json=json.dumps(data.get('ticket_data', {}), ensure_ascii=False)
            created_at=datetime.now().isoformat()
            new_row=[
                new_id,
                data['tg_id'],
                data['username'],
                data['ticket_type'],
                ticket_data_json,
                data.get('status', 'ожидание'),
                '',
                '',
                '',
                created_at
            ]
            sheet.append_row(new_row)
            logger.info(f"Ticket #{new_id} created for {data['username']}")
            return new_id
        return self._retry_on_quota(_create)
    def get_ticket(self, ticket_id:int)->Optional[Dict]:
        def _get():
            sheet=self.spreadsheet.worksheet("Tickets")
            all_values=sheet.get_all_values()
            for idx, row in enumerate(all_values[1:], start=2):
                if row and row[0]:
                    try:
                        if int(row[0])==ticket_id:
                            return {
                                'id':int(row[0]),
                                'tg_id':int(row[1]) if row[1] else 0,
                                'username':row[2],
                                'ticket_type':row[3],
                                'ticket_data':json.loads(row[4]) if row[4] else {},
                                'status':row[5],
                                'responsible':row[6],
                                'closed_at':row[7],
                                'comment':row[8],
                                'created_at':row[9],
                                'row_index':idx
                            }
                    except (ValueError, IndexError, json.JSONDecodeError) as e:
                        logger.error(f"Error parsing ticket #{ticket_id}: {e}")
                        continue
            logger.warning(f"Ticket #{ticket_id} not found")
            return None
        return self._retry_on_quota(_get)
    def get_active_tickets(self, user_tg_id:int, ticket_type:str, today:bool=False)->List[Dict]:
        def _get():
            sheet=self.spreadsheet.worksheet("Tickets")
            all_values=sheet.get_all_values()
            today_date=datetime.now().date() if today else None
            active_tickets=[]
            for row in all_values[1:]:
                if len(row)>=10:
                    try:
                        tg_id=int(row[1])
                        t_type=row[3]
                        status=row[5]
                        created_at=row[9]
                        if tg_id==user_tg_id and t_type==ticket_type and status=="ожидание":
                            if today:
                                ticket_date=datetime.fromisoformat(created_at).date()
                                if ticket_date==today_date:
                                    active_tickets.append({
                                        'id':int(row[0]),
                                        'status':status,
                                        'created_at':created_at
                                    })
                            else:
                                active_tickets.append({
                                    'id':int(row[0]),
                                    'status':status,
                                    'created_at':created_at
                                })
                    except (ValueError, IndexError) as e:
                        continue
            return active_tickets
        return self._retry_on_quota(_get)
    def get_user_ticket_history(self, user_tg_id:int)->List[Dict]:
        def _get():
            sheet=self.spreadsheet.worksheet("Tickets")
            all_values=sheet.get_all_values()
            tickets=[]
            for row in all_values[1:]:
                if len(row)>=10:
                    try:
                        tg_id=int(row[1])
                        if tg_id==user_tg_id:
                            ticket_data={}
                            if row[4]:
                                try:
                                    ticket_data=json.loads(row[4])
                                except json.JSONDecodeError:
                                    pass
                            tickets.append({
                                'id':int(row[0]),
                                'username':row[2],
                                'ticket_type':row[3],
                                'ticket_data':ticket_data,
                                'status':row[5],
                                'admin':row[6] if len(row)>6 else '',
                                'closed_at':row[7] if len(row)>7 else '',
                                'comment':row[8] if len(row)>8 else '',
                                'created_at':row[9]
                            })
                    except (ValueError, IndexError) as e:
                        continue
            tickets.sort(key=lambda x: x['id'], reverse=True)
            logger.info(f"Found {len(tickets)} tickets for user {user_tg_id}")
            return tickets
        return self._retry_on_quota(_get)
    def update_ticket_status(self, ticket_id:int, status:str, admin_tg_id:int=0, comment:str=""):
        def _update():
            ticket=self.get_ticket(ticket_id)
            if not ticket:
                raise ValueError(f"Ticket #{ticket_id} not found")
            sheet=self.spreadsheet.worksheet("Tickets")
            row_index=ticket['row_index']
            sheet.update_cell(row_index, 6, status)
            if admin_tg_id:
                sheet.update_cell(row_index, 7, admin_tg_id)
            if status=="закрыт":
                closed_at=datetime.now().isoformat()
                sheet.update_cell(row_index, 8, closed_at)
            if comment:
                sheet.update_cell(row_index, 9, comment)
            logger.info(f"Ticket #{ticket_id} updated: status={status}")
        self._retry_on_quota(_update)
    def cancel_ticket(self, ticket_id:int, user_tg_id:int)->bool:
        def _cancel():
            ticket=self.get_ticket(ticket_id)
            if not ticket:
                return False
            if ticket['tg_id']!=user_tg_id:
                logger.warning(f"Attempt to cancel someone else's ticket #{ticket_id}")
                return False
            if ticket['status']=="закрыт":
                logger.warning(f"Attempt to cancel closed ticket #{ticket_id}")
                return False
            self.update_ticket_status(ticket_id, "отменено", comment="Cancelled by user")
            return True
        return self._retry_on_quota(_cancel)
    def get_all_active_tickets(self, ticket_type:str=None)->List[Dict]:
        def _get():
            sheet=self.spreadsheet.worksheet("Tickets")
            all_values=sheet.get_all_values()
            active_tickets=[]
            for idx, row in enumerate(all_values[1:], start=2):
                if len(row)>=10:
                    try:
                        ticket_id=int(row[0])
                        t_type=row[3]
                        status=row[5]
                        if ticket_type and t_type!=ticket_type:
                            continue
                        if status=="ожидание":
                            active_tickets.append({
                                'id':ticket_id,
                                'tg_id':int(row[1]) if row[1] else 0,
                                'username':row[2],
                                'ticket_type':t_type,
                                'ticket_data':json.loads(row[4]) if row[4] else {},
                                'status':status,
                                'created_at':row[9],
                                'row_index':idx
                            })
                    except (ValueError, IndexError, json.JSONDecodeError) as e:
                        logger.error(f"Error parsing ticket at row {idx}: {e}")
                        continue
            logger.info(f"Found {len(active_tickets)} active tickets (type: {ticket_type or 'all'})")
            return active_tickets
        return self._retry_on_quota(_get)
    def get_all_tutors(self)->List[Dict]:
        def _get():
            sheet=self.spreadsheet.worksheet("admins")
            all_values=sheet.get_all_values()
            tutors=[]
            for row in all_values[1:]:
                if len(row)>=3:
                    try:
                        status=int(row[2])
                        if status==5:
                            tg_id=None
                            if len(row)>=4 and row[3]:
                                try:
                                    tg_id=int(row[3])
                                except ValueError:
                                    pass
                            tutors.append({
                                'username':row[0],
                                'full_name':row[1],
                                'tg_id':tg_id
                            })
                    except (ValueError, IndexError):
                        continue
            logger.info(f"Found {len(tutors)} tutors")
            return tutors
        return self._retry_on_quota(_get)
    def get_payout_status(self, username:str=None):
        def _get():
            sheet=self.spreadsheet.worksheet("payout_status")
            all_values=sheet.get_all_values()
            if username:
                for idx, row in enumerate(all_values[1:], start=2):
                    if len(row)>=6 and row[0]==username:
                        return {
                            'username':row[0],
                            'full_name':row[1],
                            'tg_id':row[2],
                            'status':row[3],
                            'updated_at':row[4],
                            'form_open':row[5],
                            'row_index':idx
                        }
                return None
            else:
                statuses=[]
                for idx, row in enumerate(all_values[1:], start=2):
                    if len(row)>=6:
                        statuses.append({
                            'username':row[0],
                            'full_name':row[1],
                            'tg_id':row[2],
                            'status':row[3],
                            'updated_at':row[4],
                            'form_open':row[5],
                            'row_index':idx
                        })
                return statuses
        return self._retry_on_quota(_get)
    def update_payout_status(self, username:str, status:str):
        def _update():
            payout=self.get_payout_status(username)
            if not payout:
                logger.warning(f"Tutor {username} not found in payout_status")
                return False
            sheet=self.spreadsheet.worksheet("payout_status")
            row_index=payout['row_index']
            sheet.update_cell(row_index, 4, status)
            sheet.update_cell(row_index, 5, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            logger.info(f"Payout status for {username} updated: {status}")
            return True
        return self._retry_on_quota(_update)
    def set_payout_form_status(self, is_open:bool):
        def _update():
            sheet=self.spreadsheet.worksheet("payout_status")
            all_values=sheet.get_all_values()
            form_status='да' if is_open else 'нет'
            for idx in range(2, len(all_values)+1):
                sheet.update_cell(idx, 6, form_status)
            logger.info(f"Payout form status updated: {'open' if is_open else 'closed'}")
        return self._retry_on_quota(_update)
    def is_payout_form_open(self)->bool:
        def _check():
            sheet=self.spreadsheet.worksheet("payout_status")
            value=sheet.cell(2, 6).value
            return value=='да'
        return self._retry_on_quota(_check)

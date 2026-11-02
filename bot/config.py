import os
from typing import List
from dotenv import load_dotenv
load_dotenv()

class Config:
    def __init__(self):
        self.bot_token=os.getenv("BOT_TOKEN")
        if not self.bot_token:
            raise ValueError("BOT_TOKEN not found in .env")
        self.spreadsheet_id=os.getenv("SPREADSHEET_ID")
        if not self.spreadsheet_id:
            raise ValueError("SPREADSHEET_ID not found in .env")
        admin_ids_str=os.getenv("ADMIN_IDS", "")
        self.admin_ids:List[int]=[]
        if admin_ids_str:
            try:
                self.admin_ids=[int(aid.strip()) for aid in admin_ids_str.split(",") if aid.strip()]
            except ValueError:
                raise ValueError("ADMIN_IDS must contain numbers separated by commas")
        group_ids_str=os.getenv("GROUP_IDS", "")
        self.group_ids:List[int]=[]
        if group_ids_str:
            try:
                self.group_ids=[int(gid.strip()) for gid in group_ids_str.split(",") if gid.strip()]
            except ValueError:
                raise ValueError("GROUP_IDS must contain numbers separated by commas")
    def __repr__(self):
        return f"Config(bot_token={'*'*10}, spreadsheet_id={self.spreadsheet_id})"

config=Config()

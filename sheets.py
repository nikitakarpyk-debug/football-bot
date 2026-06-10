import json
import os
import gspread
from google.oauth2.service_account import Credentials
from config import SPREADSHEET_ID, GOOGLE_CREDS_JSON

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def get_sheet():
    creds_data = json.loads(GOOGLE_CREDS_JSON)
    creds = Credentials.from_service_account_info(creds_data, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(SPREADSHEET_ID).sheet1

def get_players():
    """Возвращает список игроков (только role=player)"""
    sheet = get_sheet()
    records = sheet.get_all_records()
    return [r for r in records if r.get("role") == "player"]

def get_unpaid_players():
    """Возвращает игроков у которых monthly_paid пустое"""
    players = get_players()
    return [p for p in players if not str(p.get("monthly_paid", "")).strip()]

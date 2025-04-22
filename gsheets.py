import os
import gspread
from dotenv import load_dotenv
from datetime import datetime
from zoneinfo import ZoneInfo

load_dotenv()

gc = gspread.service_account(filename="service_account.json")
sheet_id = os.getenv("GSHEET_ID")
TZ = os.getenv("TZ", "Europe/Moscow")
sh = gc.open_by_key(sheet_id)
ws = sh.sheet1

def append(source: str, text: str, product: str = ""):
    """Добавляет строку: время | источник | товар | текст/цена"""
    stamp = datetime.now(ZoneInfo(TZ)).strftime("%Y-%m-%d %H:%M:%S")
    ws.append_row([stamp, source, product, text], table_range="A1")

def get_all_wb_articles() -> list[str]:
    """Читает все артикулы из вкладки 'Артикулы'"""
    sheet = gc.open_by_key(os.getenv("GSHEET_ID"))
    ws = sheet.worksheet("Артикулы")
    data = ws.col_values(1)[1:]  # пропускаем заголовок
    return [a.strip() for a in data if a.strip().isdigit()]

def add_article(articul: str) -> bool:
    """Добавляет артикул в конец, если его ещё нет. Возвращает True, если добавлен."""
    sheet = gc.open_by_key(os.getenv("GSHEET_ID"))
    ws = sheet.worksheet("Артикулы")
    current = ws.col_values(1)
    if articul in current:
        return False
    ws.append_row([articul])
    return True

def get_articles_text() -> str:
    """Возвращает список артикулов в виде текста"""
    ws = gc.open_by_key(os.getenv("GSHEET_ID")).worksheet("Артикулы")
    articles = ws.col_values(1)[1:]  # пропускаем заголовок
    if not articles:
        return "📭 Список пуст."
    return "📦 Список артикулов:\n" + "\n".join(f"• {a}" for a in articles)

def remove_article(articul: str) -> bool:
    """Удаляет артикул из вкладки 'Артикулы'. Возвращает True, если найден и удалён."""
    ws = gc.open_by_key(os.getenv("GSHEET_ID")).worksheet("Артикулы")
    cells = ws.col_values(1)

    for i, val in enumerate(cells):
        if val.strip() == articul:
            ws.delete_rows(i + 1)  # индексация с 1
            return True
    return False


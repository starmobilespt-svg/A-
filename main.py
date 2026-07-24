import os
import sqlite3
import math
import logging
import pandas as pd
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Render Persistent Disk Path သတ်မှတ်ခြင်း (Data မပျောက်စေရန်)
DATA_DIR = "/var/data"
if os.path.exists(DATA_DIR):
    DB_NAME = os.path.join(DATA_DIR, 'shop_business.db')
else:
    DB_NAME = 'shop_business.db' # Local တွင် စမ်းပါက လက်ရှိ Folder တွင် သိမ်းမည်

# Database Setup
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, item_name TEXT,
            quantity INTEGER, buy_price REAL, total_cost REAL, date TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, customer_name TEXT,
            item_name TEXT, sale_type TEXT, total_sale_price REAL, down_payment REAL,
            remaining_amount REAL, monthly_min_amount REAL, months_left INTEGER,
            first_date TEXT, last_date TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# (ကျန်သည့် Bot Handler Codes များ အားလုံး အရင်အတိုင်း ထားပါ...)

if __name__ == '__main__':
    # Render Environment Variable ထဲမှ BOT_TOKEN ကို ယူသုံးပါမည်
    TOKEN = os.getenv("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN_HERE")
    
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("buy", buy_item))
    app.add_handler(CommandHandler("sell_cash", sell_cash))
    app.add_handler(CommandHandler("sell_installment", sell_installment))
    app.add_handler(CommandHandler("pay", pay_installment))
    app.add_handler(CommandHandler("monthly_report", monthly_report))
    app.add_handler(CommandHandler("list", list_all))
    app.add_handler(CommandHandler("export", export_excel))
    app.add_handler(CommandHandler("backup", backup_db))
    app.add_handler(MessageHandler(filters.Document.ALL & filters.Caption(["/restore"]), restore_db))
    
    print("Bot စတင်ပွင့်နေပါပြီ...")
    app.run_polling()

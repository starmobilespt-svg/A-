import sqlite3
import pandas as pd
import datetime
import os
import threading
import time
import requests
from flask import Flask
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters
)

# Configuration
BOT_TOKEN = "8939067464:AAFwfWTwtzJGlCS-Vh3aUlt55NRS2tgY4wg"
DB_FILE = "shop_management.db"

# ----------------------------------------------------
# 🌐 Auto Ping (Sleep မဖြစ်အောင် ထိန်းပေးမည့် စနစ်)
# ----------------------------------------------------
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Bot is running 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

def auto_ping():
    while True:
        time.sleep(14 * 60) # ၁၄ မိနစ်တိုင်း Auto Ping မည်
        render_url = os.environ.get("RENDER_EXTERNAL_URL")
        if render_url:
            try:
                requests.get(render_url)
            except Exception:
                pass

# ----------------------------------------------------
# 📦 Database Setup
# ----------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT UNIQUE,
            quantity INTEGER,
            cost_price REAL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT,
            item_name TEXT,
            sale_type TEXT,
            total_price REAL,
            paid_amount REAL,
            monthly_payment REAL,
            status TEXT,
            date TEXT,
            gift_item TEXT DEFAULT ''
        )
    ''')

    cursor.execute("PRAGMA table_info(sales)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'gift_item' not in columns:
        cursor.execute("ALTER TABLE sales ADD COLUMN gift_item TEXT DEFAULT ''")

    # Expenses Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            amount REAL,
            date TEXT
        )
    ''')

    # Capital / Initial Balance Table (ငွေလက်ကျန်)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS capital (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL,
            date TEXT
        )
    ''')

    # Purchases Table (ငွေလက်ကျန်ကို အတိအကျတွက်နိုင်ရန် ပစ္စည်းဝယ်စရိတ် မှတ်တမ်း)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT,
            quantity INTEGER,
            total_cost REAL,
            date TEXT
        )
    ''')

    conn.commit()
    conn.close()

init_db()

def get_db():
    return sqlite3.connect(DB_FILE)

# Custom Bottom Keyboard Menu
def get_main_keyboard():
    keyboard = [
        [KeyboardButton("📦 ဝယ်ယူမည်"), KeyboardButton("💸 အသုံးစရိတ်")],
        [KeyboardButton("💵 လက်ငင်းရောင်း"), KeyboardButton("⏳ ကြွေးရောင်း")],
        [KeyboardButton("🎁 လက်ဆောင်ပေးရောင်း"), KeyboardButton("📈 လချုပ်/နှစ်ချုပ်")],
        [KeyboardButton("📊 လက်ကျန် Stock"), KeyboardButton("⏳ ကြွေးကျန်သူများ")],
        [KeyboardButton("📁 Excel Backup"), KeyboardButton("📥 Excel Restore")],
        [KeyboardButton("💵 ငွေလက်ကျန်ထည့်"), KeyboardButton("⏳ ကြွေးလက်ကျန်ထည့်")],
        [KeyboardButton("📦 Stock လက်ကျန်ထည့်"), KeyboardButton("🗑️ စာရင်းဖျက်")],
        [KeyboardButton("💰 ငွေဆပ်မည်"), KeyboardButton("📜 Command ကြည့်ရန်")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "မင်္ဂလာပါ! စာရင်းကိုင် Bot မှ ကြိုဆိုပါသည်။\nအောက်ပါ ခလုတ်များကို နှိပ်၍ အသုံးပြုနိုင်ပါသည်။",
        reply_markup=get_main_keyboard()
    )

# Command List
async def show_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🛍️ **အသုံးပြုနိုင်သော Command များ:**\n\n"
        "📦 **၁။ ပစ္စည်းဝယ်ယူခြင်း:**\n"
        "`/buy iPhone 13 | 2 | 1200000`\n"
        "`/buy iPhone 13 | 2 | 1200000 | 5000` (Delivery ခ ပါပါက)\n\n"
        "💵 **၂။ ရောင်းချခြင်း:**\n"
        "`/sell_cash AungAung | iPhone 13 | 1500000`\n"
        "`/sell_gift AungAung | iPhone 13 | 1500000 | Cover`\n"
        "`/sell_installment MgMg | Phone | 1500000 | 300000 | 100000`\n"
        "`/sell_installment_gift MgMg | Phone | 1500000 | 300000 | 100000 | Cover`\n\n"
        "💰 **၃။ ငွေဆပ်ခြင်း / ငွေလက်ကျန် / အသုံးစရိတ်:**\n"
        "`/pay Mg Mg | 100000` (အကြွေးဆပ်ရန်)\n"
        "`/add_balance 150000` (ငွေလက်ကျန်ထည့်ရန်)\n"
        "`/expense မီးဖိုး | 50000` (အသုံးစရိတ်)\n\n"
        "⏳ **၄။ ယခင်စာရင်းဟောင်းများ ထည့်ရန်:**\n"
        "`/add_stock iPhone 12 | 5 | 800000` (Stock လက်ကျန်ထည့်ရန်)\n"
        "`/add_credit U Ba | Phone | 500000 | 100000` (ကြွေးလက်ကျန်ထည့်ရန်)\n\n"
        "📊 **၅။ စာရင်းများ စစ်ဆေးခြင်း:**\n"
        "`/stock`, `/list`, `/report 2026-07`, `/report 2026`\n\n"
        "🗑️ **၆။ စာရင်းဖျက်ခြင်း:**\n"
        "`/delete_sale 1`, `/delete_item iPhone 13`, `/reset_all`\n\n"
        "📁 **၇။ Excel:**\n"
        "`/export`"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

# Helper function to get available stock text
def get_available_stock_info():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT item_name, quantity FROM inventory WHERE quantity > 0")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return "⚠️ **လက်ရှိ ရောင်းရန် Stock ပစ္စည်း လုံးဝ မရှိသေးပါ!**"

    msg = "📦 **လက်ရှိ ရောင်းရန် ရှိသော Stock ပစ္စည်းများ:**\n"
    for r in rows:
        msg += f"• `{r[0]}` - ကျန် `{r[1]}` ခု\n"
    return msg

# Add Balance Command (ငွေလက်ကျန်ထည့်ရန်)
async def add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args:
            await update.message.reply_text("❌ **Standard Format:**\n`/add_balance <ပမာဏ>`\n\n👇 **နှိပ်ပြီး ကူးယူပါ:**\n`/add_balance 1000000`", parse_mode="Markdown")
            return
        amount = float(context.args[0].strip())
        today = datetime.date.today().strftime("%Y-%m-%d")

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO capital (amount, date) VALUES (?, ?)", (amount, today))
        conn.commit()
        conn.close()

        await update.message.reply_text(f"💵 **ငွေလက်ကျန် ထည့်သွင်းပြီးပါပြီ!**\n\n💰 ပမာဏ: `{amount:,.0f}` MMK\n📅 ရက်စွဲ: `{today}`", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ အမှားအယွင်းရှိပါသည်: {str(e)}")

# Buy Command
async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = " ".join(context.args).split("|")
        if len(args) not in [3, 4]:
            await update.message.reply_text("❌ **Standard Format:**\n`/buy <ပစ္စည်းအမည်> | <အရေအတွက်> | <ဝယ်ဈေး> | <Deliveryခ(optional)>`", parse_mode="Markdown")
            return

        item_name = args[0].strip()
        qty = int(args[1].strip())
        cost_price = float(args[2].strip())
        deli_fee = float(args[3].strip()) if len(args) == 4 else 0.0
        today = datetime.date.today().strftime("%Y-%m-%d")

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT quantity FROM inventory WHERE item_name = ?", (item_name,))
        row = cursor.fetchone()
        if row:
            cursor.execute("UPDATE inventory SET quantity = ?, cost_price = ? WHERE item_name = ?", (row[0] + qty, cost_price, item_name))
        else:
            cursor.execute("INSERT INTO inventory (item_name, quantity, cost_price) VALUES (?, ?, ?)", (item_name, qty, cost_price))

        total_purchase_cost = qty * cost_price
        cursor.execute("INSERT INTO purchases (item_name, quantity, total_cost, date) VALUES (?, ?, ?, ?)", (item_name, qty, total_purchase_cost, today))

        if deli_fee > 0:
            cursor.execute("INSERT INTO expenses (title, amount, date) VALUES (?, ?, ?)", (f"{item_name} ဝယ်ယူမှု Delivery ခ", deli_fee, today))

        conn.commit()
        conn.close()

        deli_msg = f"\n🚚 Delivery ခ: `{deli_fee:,.0f}` MMK (အသုံးစရိတ်ထဲ ပေါင်းထည့်ပြီး)" if deli_fee > 0 else ""
        await update.message.reply_text(f"✅ **ပစ္စည်းဝယ်ယူမှု မှတ်တမ်းတင်ပြီးပါပြီ!**\n\n📦 ပစ္စည်း: `{item_name}`\n🔢 အရေအတွက်: `{qty}` ခု\n💵 ဝယ်ဈေး (တစ်ခု): `{cost_price:,.0f}` MMK{deli_msg}", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ အမှားအယွင်းရှိပါသည်: {str(e)}")

# Expense Command
async def add_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = " ".join(context.args).split("|")
        if len(args) != 2:
            await update.message.reply_text("❌ **Standard Format:**\n`/expense <အကြောင်းအရာ> | <ပမာဏ>`", parse_mode="Markdown")
            return
        title = args[0].strip()
        amount = float(args[1].strip())
        today = datetime.date.today().strftime("%Y-%m-%d")

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO expenses (title, amount, date) VALUES (?, ?, ?)", (title, amount, today))
        conn.commit()
        conn.close()

        await update.message.reply_text(f"💸 **ဆိုင်အသုံးစရိတ် စာရင်းသွင်းပြီးပါပြီ!**\n\n📝 အကြောင်းအရာ: `{title}`\n💰 ကျသင့်ငွေ: `{amount:,.0f}` MMK\n📅 ရက်စွဲ: `{today}`", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ အမှားအယွင်းရှိပါသည်: {str(e)}")

# Add Old Stock Command
async def add_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = " ".join(context.args).split("|")
        if len(args) != 3:
            await update.message.reply_text("❌ **Standard Format:**\n`/add_stock <ပစ္စည်းအမည်> | <အရေအတွက်> | <ဝယ်ဈေး>`", parse_mode="Markdown")
            return
        item_name, qty, cost_price = args[0].strip(), int(args[1].strip()), float(args[2].strip())
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT quantity FROM inventory WHERE item_name = ?", (item_name,))
        row = cursor.fetchone()
        if row:
            cursor.execute("UPDATE inventory SET quantity = ?, cost_price = ? WHERE item_name = ?", (row[0] + qty, cost_price, item_name))
        else:
            cursor.execute("INSERT INTO inventory (item_name, quantity, cost_price) VALUES (?, ?, ?)", (item_name, qty, cost_price))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"📦 **Stock လက်ကျန် ထည့်သွင်းပြီးပါပြီ!**\n\n📦 ပစ္စည်း: `{item_name}`\n🔢 အရေအတွက်: `{qty}` ခု\n💵 ဝယ်ဈေး: `{cost_price:,.0f}` MMK", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ အမှားအယွင်းရှိပါသည်: {str(e)}")

# Add Old Credit Command
async def add_credit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = " ".join(context.args).split("|")
        if len(args) != 4:
            await update.message.reply_text("❌ **Standard Format:**\n`/add_credit <ဝယ်သူနာမည်> | <ပစ္စည်းအမည်> | <စုစုပေါင်းအကြွေး> | <တစ်လပေးရမည့်ငွေ>`", parse_mode="Markdown")
            return
        customer = args[0].strip()
        item_name = args[1].strip()
        total_price = float(args[2].strip())
        monthly_pay = float(args[3].strip())
        today = datetime.date.today().strftime("%Y-%m-%d")

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO sales (customer_name, item_name, sale_type, total_price, paid_amount, monthly_payment, status, date, gift_item)
            VALUES (?, ?, 'INSTALLMENT', ?, 0, ?, 'PENDING', ?, '')
        ''', (customer, item_name, total_price, monthly_pay, today))
        
        sale_id = cursor.lastrowid
        conn.commit()
        conn.close()

        await update.message.reply_text(
            f"⏳ **ကြွေးလက်ကျန် စာရင်းသွင်းပြီးပါပြီ!**\n\n🆔 အရောင်း ID: `{sale_id}`\n👤 ဝယ်သူ: `{customer}`\n📦 ပစ္စည်း: `{item_name}`\n📉 အကြွေးကျန်: `{total_price:,.0f}` MMK", parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ အမှားအယွင်းရှိပါသည်: {str(e)}")

async def sell_cash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = " ".join(context.args).split("|")
        if len(args) != 3:
            stock_info = get_available_stock_info()
            await update.message.reply_text(f"{stock_info}\n\n❌ **Format:**\n`/sell_cash <ဝယ်သူ> | <ပစ္စည်း> | <ရောင်းဈေး>`", parse_mode="Markdown")
            return
        customer, item_name, price = args[0].strip(), args[1].strip(), float(args[2].strip())
        today = datetime.date.today().strftime("%Y-%m-%d")
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT quantity FROM inventory WHERE item_name = ?", (item_name,))
        row = cursor.fetchone()
        if not row or row[0] < 1:
            await update.message.reply_text("❌ လက်ကျန် Stock မလုံလောက်ပါ။")
            conn.close()
            return
        cursor.execute("UPDATE inventory SET quantity = quantity - 1 WHERE item_name = ?", (item_name,))
        cursor.execute("INSERT INTO sales (customer_name, item_name, sale_type, total_price, paid_amount, monthly_payment, status, date, gift_item) VALUES (?, ?, 'CASH', ?, ?, 0, 'PAID', ?, '')", (customer, item_name, price, price, today))
        sale_id = cursor.lastrowid
        conn.commit()
        conn.close()
        await update.message.reply_text(f"💵 **လက်ငင်း ရောင်းချမှု အောင်မြင်ပါသည်။**\n\n🆔 ID: `{sale_id}`\n👤 ဝယ်သူ: `{customer}`\n📦 ပစ္စည်း: `{item_name}`\n💰 ဈေး: `{price:,.0f}` MMK", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def sell_gift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = " ".join(context.args).split("|")
        if len(args) != 4:
            stock_info = get_available_stock_info()
            await update.message.reply_text(f"{stock_info}\n\n❌ **Format:**\n`/sell_gift <ဝယ်သူ> | <ပစ္စည်း> | <ရောင်းဈေး> | <လက်ဆောင်>`", parse_mode="Markdown")
            return
        customer, item_name, price, gift = args[0].strip(), args[1].strip(), float(args[2].strip()), args[3].strip()
        today = datetime.date.today().strftime("%Y-%m-%d")
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT quantity FROM inventory WHERE item_name = ?", (item_name,))
        row = cursor.fetchone()
        if not row or row[0] < 1:
            await update.message.reply_text("❌ ရောင်းချမည့် ပစ္စည်း Stock မလုံလောက်ပါ။")
            conn.close()
            return

        cursor.execute("UPDATE inventory SET quantity = quantity - 1 WHERE item_name = ?", (item_name,))

        cursor.execute("SELECT quantity FROM inventory WHERE item_name = ?", (gift,))
        gift_row = cursor.fetchone()
        if gift_row and gift_row[0] > 0:
            cursor.execute("UPDATE inventory SET quantity = quantity - 1 WHERE item_name = ?", (gift,))

        cursor.execute("INSERT INTO sales (customer_name, item_name, sale_type, total_price, paid_amount, monthly_payment, status, date, gift_item) VALUES (?, ?, 'CASH', ?, ?, 0, 'PAID', ?, ?)", (customer, item_name, price, price, today, gift))
        sale_id = cursor.lastrowid
        conn.commit()
        conn.close()
        await update.message.reply_text(f"🎁 **လက်ဆောင်ပါ လက်ငင်း ရောင်းချပြီးပါပြီ**\n\n🆔 ID: `{sale_id}`\n👤 ဝယ်သူ: `{customer}`\n📦 ပစ္စည်း: `{item_name}`\n🎁 လက်ဆောင်: `{gift}`", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def sell_installment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = " ".join(context.args).split("|")
        if len(args) != 5:
            stock_info = get_available_stock_info()
            await update.message.reply_text(f"{stock_info}\n\n❌ **Format:**\n`/sell_installment <ဝယ်သူ> | <ပစ္စည်း> | <စုစုပေါင်းဈေး> | <စပေါ်> | <၁လပေး>`", parse_mode="Markdown")
            return
        customer, item_name, total_price, down_payment, monthly_pay = args[0].strip(), args[1].strip(), float(args[2].strip()), float(args[3].strip()), float(args[4].strip())
        today = datetime.date.today().strftime("%Y-%m-%d")
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT quantity FROM inventory WHERE item_name = ?", (item_name,))
        row = cursor.fetchone()
        if not row or row[0] < 1:
            await update.message.reply_text("❌ လက်ကျန် Stock မလုံလောက်ပါ။")
            conn.close()
            return
        cursor.execute("UPDATE inventory SET quantity = quantity - 1 WHERE item_name = ?", (item_name,))
        status = 'PAID' if down_payment >= total_price else 'PENDING'
        cursor.execute("INSERT INTO sales (customer_name, item_name, sale_type, total_price, paid_amount, monthly_payment, status, date, gift_item) VALUES (?, ?, 'INSTALLMENT', ?, ?, ?, ?, ?, '')", (customer, item_name, total_price, down_payment, monthly_pay, status, today))
        sale_id = cursor.lastrowid
        conn.commit()
        conn.close()
        await update.message.reply_text(f"⏳ **ကြွေးရောင်း မှတ်တမ်းဝင်သွားပါပြီ!**\n\n🆔 ID: `{sale_id}`\n👤 ဝယ်သူ: `{customer}`\n📦 ပစ္စည်း: `{item_name}`\n📉 ကျန်ငွေ: `{total_price - down_payment:,.0f}` MMK", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def sell_installment_gift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = " ".join(context.args).split("|")
        if len(args) != 6:
            stock_info = get_available_stock_info()
            await update.message.reply_text(f"{stock_info}\n\n❌ **Format:**\n`/sell_installment_gift <ဝယ်သူ> | <ပစ္စည်း> | <စုစုပေါင်းဈေး> | <စပေါ်> | <၁လပေး> | <လက်ဆောင်>`", parse_mode="Markdown")
            return
        customer, item_name, total_price, down_payment, monthly_pay, gift = args[0].strip(), args[1].strip(), float(args[2].strip()), float(args[3].strip()), float(args[4].strip()), args[5].strip()
        today = datetime.date.today().strftime("%Y-%m-%d")
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT quantity FROM inventory WHERE item_name = ?", (item_name,))
        row = cursor.fetchone()
        if not row or row[0] < 1:
            await update.message.reply_text("❌ ပစ္စည်း Stock မလုံလောက်ပါ။")
            conn.close()
            return

        cursor.execute("UPDATE inventory SET quantity = quantity - 1 WHERE item_name = ?", (item_name,))

        cursor.execute("SELECT quantity FROM inventory WHERE item_name = ?", (gift,))
        gift_row = cursor.fetchone()
        if gift_row and gift_row[0] > 0:
            cursor.execute("UPDATE inventory SET quantity = quantity - 1 WHERE item_name = ?", (gift,))

        status = 'PAID' if down_payment >= total_price else 'PENDING'
        cursor.execute("INSERT INTO sales (customer_name, item_name, sale_type, total_price, paid_amount, monthly_payment, status, date, gift_item) VALUES (?, ?, 'INSTALLMENT', ?, ?, ?, ?, ?, ?)", (customer, item_name, total_price, down_payment, monthly_pay, status, today, gift))
        sale_id = cursor.lastrowid
        conn.commit()
        conn.close()
        await update.message.reply_text(f"⏳ **လက်ဆောင်ပါ ကြွေးရောင်း မှတ်တမ်းဝင်ပါပြီ!**\n\n🆔 ID: `{sale_id}`\n👤 ဝယ်သူ: `{customer}`\n📦 ပစ္စည်း: `{item_name}`\n🎁 လက်ဆောင်: `{gift}`", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        raw_input = " ".join(context.args).strip()
        if not raw_input:
            await update.message.reply_text("❌ **Format:**\n`/pay <ဝယ်သူနာမည် သို့မဟုတ် ID> | <ပေးသည့်ပမာဏ>`", parse_mode="Markdown")
            return

        if "|" in raw_input:
            parts = raw_input.split("|")
            target_str = parts[0].strip()
            amount_str = parts[1].strip()
        else:
            parts = raw_input.rsplit(" ", 1)
            if len(parts) != 2:
                await update.message.reply_text("❌ **Format:**\n`/pay <ဝယ်သူ> | <ပမာဏ>`", parse_mode="Markdown")
                return
            target_str = parts[0].strip()
            amount_str = parts[1].strip()

        amount = float(amount_str)
        conn = get_db()
        cursor = conn.cursor()

        if target_str.isdigit():
            sale_id = int(target_str)
            cursor.execute("SELECT id, customer_name, item_name, total_price, paid_amount, gift_item FROM sales WHERE id = ? AND status = 'PENDING'", (sale_id,))
            rows = cursor.fetchall()
        else:
            customer = target_str
            cursor.execute("SELECT id, customer_name, item_name, total_price, paid_amount, gift_item FROM sales WHERE customer_name = ? AND status = 'PENDING' AND sale_type = 'INSTALLMENT'", (customer,))
            rows = cursor.fetchall()

        if not rows:
            await update.message.reply_text(f"❌ `{target_str}` အတွက် အကြွေးစာရင်း မတွေ့ပါ။", parse_mode="Markdown")
            conn.close()
            return

        if len(rows) > 1:
            msg = f"⚠️ **'{target_str}' အမည်ဖြင့် စာရင်း ({len(rows)}) ခု ရှိနေပါသည်:**\n\n"
            for r in rows:
                rem = r[3] - r[4]
                gift_info = f" (🎁 {r[5]})" if r[5] else ""
                msg += f"🆔 ID: `{r[0]}` | {r[1]} ({r[2]}{gift_info})\n  ကျန်ငွေ: `{rem:,.0f}`\n👉 `/pay {r[0]} | {amount:,.0f}`\n\n"
            await update.message.reply_text(msg, parse_mode="Markdown")
            conn.close()
            return

        sale_id, customer_name, item_name, total_price, current_paid, gift_item = rows[0]
        new_paid = current_paid + amount
        new_status = 'PAID' if new_paid >= total_price else 'PENDING'

        cursor.execute("UPDATE sales SET paid_amount = ?, status = ? WHERE id = ?", (new_paid, new_status, sale_id))
        conn.commit()
        conn.close()

        rem = total_price - new_paid
        rem_str = "0" if rem <= 0 else f"{rem:,.0f} MMK"

        await update.message.reply_text(f"💰 **ငွေဆပ်မှု အောင်မြင်ပါသည်။**\n\n🆔 ID: `{sale_id}`\n👤 ဝယ်သူ: `{customer_name}`\n💵 ပေးသွင်းငွေ: `{amount:,.0f}` MMK\n📉 ပေးရန်ကျန်ငွေ: `{rem_str}`", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT item_name, quantity, cost_price FROM inventory WHERE quantity > 0")
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        await update.message.reply_text("📦 လက်ရှိ Stock လုံးဝ မရှိသေးပါ။")
        return
    
    total_stock_value = 0
    msg = "📊 **ဆိုင်ရှိ လက်ကျန် Stock စာရင်း:**\n\n"
    for r in rows:
        val = r[1] * r[2]
        total_stock_value += val
        msg += f"• `{r[0]}` - `{r[1]}` ခု (တန်ဖိုး: `{val:,.0f}` MMK)\n"
    
    msg += "\n───────────────────\n"
    msg += f"📦 **စုစုပေါင်း Stock တန်ဖိုးငွေ:** `{total_stock_value:,.0f}` MMK\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def list_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, customer_name, item_name, total_price, paid_amount, monthly_payment, gift_item FROM sales WHERE status = 'PENDING'")
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        await update.message.reply_text("🎉 အရစ်ကျ ကျန်ရှိသူ စာရင်း မရှိပါ။")
        return
    msg = "⏳ **ကြွေးကျန်သူများ စာရင်း:**\n\n"
    for r in rows:
        msg += f"🆔 ID: `{r[0]}` | 👤 **{r[1]}** ({r[2]})\n  ကျန်ငွေ: `{r[3] - r[4]:,.0f}` MMK\n\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = context.args
        if args:
            period = args[0].strip()
            if len(period) == 4:
                date_format = '%Y'
                period_label = f"{period} ခုနှစ်ချုပ်"
            else:
                date_format = '%Y-%m'
                period_label = f"{period} လချုပ်"
        else:
            period = datetime.date.today().strftime("%Y-%m")
            date_format = '%Y-%m'
            period_label = f"{period} လချုပ်"

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute(f'''
            SELECT s.item_name, s.total_price, s.paid_amount, COALESCE(i.cost_price, 0)
            FROM sales s
            LEFT JOIN inventory i ON s.item_name = i.item_name
            WHERE strftime('{date_format}', s.date) = ?
        ''', (period,))
        sales_rows = cursor.fetchall()

        cursor.execute(f"SELECT SUM(amount) FROM expenses WHERE strftime('{date_format}', date) = ?", (period,))
        expense_row = cursor.fetchone()
        total_expense = expense_row[0] if expense_row[0] else 0.0

        cursor.execute(f"SELECT SUM(amount) FROM capital WHERE strftime('{date_format}', date) = ?", (period,))
        capital_row = cursor.fetchone()
        added_capital = capital_row[0] if capital_row[0] else 0.0

        cursor.execute(f"SELECT SUM(total_cost) FROM purchases WHERE strftime('{date_format}', date) = ?", (period,))
        purchase_row = cursor.fetchone()
        total_purchases_cash = purchase_row[0] if purchase_row[0] else 0.0

        cursor.execute("SELECT SUM(quantity * cost_price) FROM inventory WHERE quantity > 0")
        stock_row = cursor.fetchone()
        total_current_stock_value = stock_row[0] if stock_row[0] else 0.0

        conn.close()

        if not sales_rows and total_expense == 0 and added_capital == 0 and total_purchases_cash == 0:
            await update.message.reply_text(f"⚠️ **{period}** အတွက် စာရင်း မရှိသေးပါ။", parse_mode="Markdown")
            return

        total_sales_value = sum(r[1] for r in sales_rows)
        total_collected_cash = sum(r[2] for r in sales_rows)
        total_cogs = sum(r[3] for r in sales_rows)

        net_profit = total_sales_value - total_cogs - total_expense
        profit_status = "🟢 အမြတ်" if net_profit >= 0 else "🔴 အရှုံး"

        cash_balance = added_capital + total_collected_cash - total_expense - total_purchases_cash

        msg = f"📊 **{period_label} အရှုံးအမြတ်နှင့် လက်ကျန် စာရင်း**\n\n"
        msg += f"🛒 အရောင်းပမာဏ (စုစုပေါင်း): `{total_sales_value:,.0f}` MMK\n"
        msg += f"💵 ရောင်းရငွေ (လက်ဝယ်ရငွေ): `{total_collected_cash:,.0f}` MMK\n"
        msg += f"📉 ရရန်ကျန် အကြွေးငွေ: `{(total_sales_value - total_collected_cash):,.0f}` MMK\n"
        msg += f"📦 ရောင်းရပစ္စည်း ရင်းနှီးစရိတ် (COGS): `{total_cogs:,.0f}` MMK\n"
        msg += "───────────────────\n"
        msg += f"📥 ယခုကာလ ထည့်သွင်းငွေ/အရင်း: `{added_capital:,.0f}` MMK\n"
        msg += f"📤 ပစ္စည်းအသစ် ဝယ်ယူစရိတ်: `{total_purchases_cash:,.0f}` MMK\n"
        msg += f"💸 ဆိုင်အသုံးစရိတ် စုစုပေါင်း: `{total_expense:,.0f}` MMK\n"
        msg += "───────────────────\n"
        msg += f"{profit_status} (အသားတင်): `{abs(net_profit):,.0f}` MMK\n"
        msg += f"💰 **စာရင်းအရ လက်ကျန်ငွေ**: `{cash_balance:,.0f}` MMK\n"
        msg += f"   *(အရင်း + ရောင်းရငွေ - အသုံးစရိတ် - ပစ္စည်းဝယ်စရိတ်)*\n\n"
        msg += f"📦 **ဆိုင်ရှိ စုစုပေါင်း Stock တန်ဖိုးငွေ:** `{total_current_stock_value:,.0f}` MMK"

        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ အမှားအယွင်းရှိပါသည်: {str(e)}")

# Delete Commands mapping removed to make way for Interactive Inline Buttons
async def delete_sale(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Backward compatibility if user still types it manually
    try:
        if not context.args:
            return
        sale_id = int(context.args[0].strip())
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sales WHERE id = ?", (sale_id,))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"🗑️ ID `{sale_id}` စာရင်းကို ဖျက်လိုက်ပါပြီ။", parse_mode="Markdown")
    except:
        pass

async def delete_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args:
            return
        item_name = " ".join(context.args).strip()
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM inventory WHERE item_name = ?", (item_name,))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"🗑️ Stock ထဲမှ `{item_name}` ကို ဖျက်လိုက်ပါပြီ။", parse_mode="Markdown")
    except:
        pass

async def reset_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[
        InlineKeyboardButton("✅ အကုန်ဖျက်မည် (Confirm)", callback_data="confirm_reset_all"),
        InlineKeyboardButton("❌ မဖျက်တော့ပါ (Cancel)", callback_data="cancel_action")
    ]]
    await update.message.reply_text("⚠️ စာရင်းအားလုံး ဖျက်ပစ်ပါမည်။ ဧကန်မုချ ဖျက်လိုပါသလား?", reply_markup=InlineKeyboardMarkup(keyboard))

# ----------------------------------------------------
# 🔘 Unified Callback Handler for Buttons (Delete Menus, Reset)
# ----------------------------------------------------
async def main_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "confirm_reset_all":
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM inventory")
        cursor.execute("DELETE FROM sales")
        cursor.execute("DELETE FROM expenses")
        cursor.execute("DELETE FROM capital")
        cursor.execute("DELETE FROM purchases")
        conn.commit()
        conn.close()
        await query.edit_message_text("💥 **စာရင်း အားလုံးကို အောင်မြင်စွာ ဖျက်ပစ်ပြီးပါပြီ!**", parse_mode="Markdown")
    
    elif data == "cancel_action":
        await query.edit_message_text("❌ လုပ်ဆောင်ချက်ကို ပယ်ဖျက်လိုက်ပါပြီ။")

    # --- Interactive Delete Menus ---
    elif data == "menu_del_sale":
        conn = get_db()
        cursor = conn.cursor()
        # Fetch last 10 sales
        cursor.execute("SELECT id, customer_name, item_name FROM sales ORDER BY id DESC LIMIT 10")
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            await query.edit_message_text("ဖျက်စရာ အရောင်းစာရင်း မရှိသေးပါ။")
            return
        
        keyboard = []
        for r in rows:
            btn_text = f"ID:{r[0]} | {r[1]} ({r[2]})"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"do_del_sale_{r[0]}")])
        keyboard.append([InlineKeyboardButton("🔙 နောက်သို့", callback_data="cancel_action")])
        
        await query.edit_message_text("🗑️ **နောက်ဆုံးသွင်းထားသော အရောင်းစာရင်းများ:**\nဖျက်လိုသော စာရင်းကို နှိပ်ပါ -", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "menu_del_stock":
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, item_name FROM inventory")
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            await query.edit_message_text("ဖျက်စရာ Stock ပစ္စည်း မရှိသေးပါ။")
            return
        
        keyboard = []
        for r in rows:
            btn_text = f"📦 {r[1]}"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"do_del_stock_{r[0]}")])
        keyboard.append([InlineKeyboardButton("🔙 နောက်သို့", callback_data="cancel_action")])
        
        await query.edit_message_text("🗑️ **ဖျက်လိုသော Stock ပစ္စည်းကို ရွေးပါ:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    # --- Execute Deletions ---
    elif data.startswith("do_del_sale_"):
        sale_id = data.split("_")[3]
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT customer_name, item_name FROM sales WHERE id = ?", (sale_id,))
        row = cursor.fetchone()
        if row:
            cursor.execute("DELETE FROM sales WHERE id = ?", (sale_id,))
            conn.commit()
            await query.edit_message_text(f"✅ အရောင်းစာရင်း ID: `{sale_id}` ({row[0]} - {row[1]}) ကို ဖျက်လိုက်ပါပြီ။", parse_mode="Markdown")
        else:
            await query.edit_message_text("❌ စာရင်းရှာမတွေ့ပါ။ ဖျက်ပြီးသား ဖြစ်နိုင်ပါသည်။")
        conn.close()

    elif data.startswith("do_del_stock_"):
        stock_id = data.split("_")[3]
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT item_name FROM inventory WHERE id = ?", (stock_id,))
        row = cursor.fetchone()
        if row:
            cursor.execute("DELETE FROM inventory WHERE id = ?", (stock_id,))
            conn.commit()
            await query.edit_message_text(f"✅ Stock ပစ္စည်း `{row[0]}` ကို ဖျက်လိုက်ပါပြီ။", parse_mode="Markdown")
        else:
            await query.edit_message_text("❌ ပစ္စည်းရှာမတွေ့ပါ။ ဖျက်ပြီးသား ဖြစ်နိုင်ပါသည်။")
        conn.close()

# Excel Import / Export
async def export_excel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        conn = get_db()
        df_inventory = pd.read_sql_query("SELECT * FROM inventory", conn)
        df_sales = pd.read_sql_query("SELECT * FROM sales", conn)
        df_expenses = pd.read_sql_query("SELECT * FROM expenses", conn)
        df_capital = pd.read_sql_query("SELECT * FROM capital", conn)
        df_purchases = pd.read_sql_query("SELECT * FROM purchases", conn)
        conn.close()
        file_path = "Shop_Data_Export.xlsx"
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            df_inventory.to_excel(writer, sheet_name='Inventory', index=False)
            df_sales.to_excel(writer, sheet_name='Sales', index=False)
            df_expenses.to_excel(writer, sheet_name='Expenses', index=False)
            df_capital.to_excel(writer, sheet_name='Capital', index=False)
            df_purchases.to_excel(writer, sheet_name='Purchases', index=False)
        await update.message.reply_document(document=open(file_path, 'rb'), filename=file_path)
    except Exception as e:
        await update.message.reply_text(f"❌ Excel export Error: {str(e)}")

async def handle_excel_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    if not document.file_name.endswith('.xlsx'):
        await update.message.reply_text("❌ `.xlsx` Excel File ကိုသာ ပို့ပေးပါ။")
        return
    status_msg = await update.message.reply_text("🔄 Restore လုပ်နေပါသည်...")
    try:
        file = await context.bot.get_file(document.file_id)
        temp_path = "temp_restore.xlsx"
        await file.download_to_drive(temp_path)
        xls = pd.ExcelFile(temp_path)
        conn = get_db()
        cursor = conn.cursor()

        if 'Inventory' in xls.sheet_names:
            df_inv = pd.read_excel(xls, sheet_name='Inventory')
            cursor.execute("DELETE FROM inventory")
            for _, row in df_inv.iterrows():
                cursor.execute('INSERT INTO inventory (id, item_name, quantity, cost_price) VALUES (?, ?, ?, ?)', (row.get('id'), row['item_name'], row['quantity'], row['cost_price']))
        
        if 'Sales' in xls.sheet_names:
            df_sales = pd.read_excel(xls, sheet_name='Sales')
            cursor.execute("DELETE FROM sales")
            for _, row in df_sales.iterrows():
                gift_val = str(row.get('gift_item', '')) if pd.notna(row.get('gift_item')) else ''
                cursor.execute('INSERT INTO sales (id, customer_name, item_name, sale_type, total_price, paid_amount, monthly_payment, status, date, gift_item) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', (
                    row.get('id'), row['customer_name'], row['item_name'], row['sale_type'], row['total_price'], row['paid_amount'], row['monthly_payment'], row['status'], str(row['date']), gift_val))

        if 'Expenses' in xls.sheet_names:
            df_exp = pd.read_excel(xls, sheet_name='Expenses')
            cursor.execute("DELETE FROM expenses")
            for _, row in df_exp.iterrows():
                cursor.execute('INSERT INTO expenses (id, title, amount, date) VALUES (?, ?, ?, ?)', (row.get('id'), row['title'], row['amount'], str(row['date'])))

        if 'Capital' in xls.sheet_names:
            df_cap = pd.read_excel(xls, sheet_name='Capital')
            cursor.execute("DELETE FROM capital")
            for _, row in df_cap.iterrows():
                cursor.execute('INSERT INTO capital (id, amount, date) VALUES (?, ?, ?)', (row.get('id'), row['amount'], str(row['date'])))
                
        if 'Purchases' in xls.sheet_names:
            df_pur = pd.read_excel(xls, sheet_name='Purchases')
            cursor.execute("DELETE FROM purchases")
            for _, row in df_pur.iterrows():
                cursor.execute('INSERT INTO purchases (id, item_name, quantity, total_cost, date) VALUES (?, ?, ?, ?, ?)', (row.get('id'), row['item_name'], row['quantity'], row['total_cost'], str(row['date'])))

        conn.commit()
        conn.close()
        os.remove(temp_path)
        await status_msg.edit_text("✅ **Excel File မှ စာရင်းများကို Restore လုပ်ပြီးပါပြီ!**")
    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {str(e)}")

# Handles custom buttons from keyboard
async def handle_button_clicks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "📦 ဝယ်ယူမည်":
        await update.message.reply_text("📦 **ဝယ်ယူမှု စာရင်းသွင်းရန်:**\n`/buy <ပစ္စည်းအမည်> | <အရေအတွက်> | <ဝယ်ဈေး>`\n👇 `/buy iPhone 13 | 2 | 1200000`", parse_mode="Markdown")
    elif text == "💸 အသုံးစရိတ်":
        await update.message.reply_text("💸 **အသုံးစရိတ် စာရင်းသွင်းရန်:**\n`/expense <အကြောင်းအရာ> | <ပမာဏ>`\n👇 `/expense မီးဖိုး | 50000`", parse_mode="Markdown")
    elif text == "💵 လက်ငင်းရောင်း":
        stock_info = get_available_stock_info()
        await update.message.reply_text(f"{stock_info}\n\n💵 **လက်ငင်း ရောင်းချရန်:**\n`/sell_cash <ဝယ်သူ> | <ပစ္စည်း> | <ရောင်းဈေး>`\n👇 `/sell_cash AungAung | iPhone 13 | 1500000`", parse_mode="Markdown")
    elif text == "⏳ ကြွေးရောင်း":
        stock_info = get_available_stock_info()
        await update.message.reply_text(f"{stock_info}\n\n⏳ **ကြွေးရောင်းရန်:**\n`/sell_installment <ဝယ်သူ> | <ပစ္စည်း> | <စုစုပေါင်းဈေး> | <စပေါ်ငွေ> | <၁လပေးရမည့်ငွေ>`\n👇 `/sell_installment MgMg | Phone | 1500000 | 300000 | 100000`", parse_mode="Markdown")
    elif text == "🎁 လက်ဆောင်ပေးရောင်း":
        stock_info = get_available_stock_info()
        await update.message.reply_text(f"{stock_info}\n\n🎁 **လက်ဆောင်ပါဝင်သော ရောင်းချမှု ပုံစံ:**\n\n၁။ **လက်ငင်းရောင်း:**\n`/sell_gift <ဝယ်သူ> | <ပစ္စည်း> | <ရောင်းဈေး> | <လက်ဆောင်>`\n\n၂။ **ကြွေးရောင်း:**\n`/sell_installment_gift <ဝယ်သူ> | <ပစ္စည်း> | <စုစုပေါင်း> | <စပေါ်> | <၁လပေး> | <လက်ဆောင်>`", parse_mode="Markdown")
    elif text in ["📈 လချုပ်အရှုံးအမြတ်", "📈 လချုပ်/နှစ်ချုပ်"]:
        await update.message.reply_text(
            "📈 **စာရင်းချုပ် ကြည့်ရန် (လအလိုက် / နှစ်အလိုက်):**\n\n"
            "၁။ **ယခုလအတွက် ကြည့်ရန်:**\n`/report`\n\n"
            "၂။ **လအလိုက် ကြည့်ရန် (ဥပမာ - ၂၀၂၆ ဇူလိုင်):**\n`/report 2026-07`\n\n"
            "၃။ **နှစ်အလိုက် ကြည့်ရန် (ဥပမာ - ၂၀၂၆ တစ်နှစ်လုံး):**\n`/report 2026`", 
            parse_mode="Markdown"
        )
    elif text == "📊 လက်ကျန် Stock":
        await stock(update, context)
    elif text == "⏳ ကြွေးကျန်သူများ":
        await list_pending(update, context)
    elif text == "📁 Excel Backup":
        await export_excel(update, context)
    elif text == "📥 Excel Restore":
        await update.message.reply_text("📥 `📁 Excel Backup` ဖြင့် ရလာသော ဖိုင်ကို ပြင်ဆင်ပြီး ဤ Chat ထဲသို့ File အနေဖြင့် Send / Upload ပြုလုပ်ပေးပါ။")
    elif text == "💵 ငွေလက်ကျန်ထည့်":
        await update.message.reply_text("💵 **ဆိုင်၏ ငွေလက်ကျန်(အရင်း) ထည့်ရန်:**\n`/add_balance <ပမာဏ>`\n👇 `/add_balance 1000000`", parse_mode="Markdown")
    elif text == "⏳ ကြွေးလက်ကျန်ထည့်":
        await update.message.reply_text("⏳ **အရင်က ကြွေးဟောင်း ထည့်ရန်:**\n`/add_credit <ဝယ်သူနာမည်> | <ပစ္စည်းအမည်> | <စုစုပေါင်းအကြွေး> | <တစ်လပေးရမည့်ငွေ>`\n👇 `/add_credit U Ba | Phone | 500000 | 100000`", parse_mode="Markdown")
    elif text == "📦 Stock လက်ကျန်ထည့်":
        await update.message.reply_text("📦 **ဆိုင်ရှိ ပစ္စည်းဟောင်း ထည့်ရန်:**\n`/add_stock <ပစ္စည်းအမည်> | <အရေအတွက်> | <ဝယ်ဈေး>`\n👇 `/add_stock iPhone 12 | 5 | 800000`", parse_mode="Markdown")
    
    # --- စာရင်းဖျက် Interactive UI ---
    elif text == "🗑️ စာရင်းဖျက်":
        keyboard = [
            [InlineKeyboardButton("📝 အရောင်းစာရင်း ဖျက်မည်", callback_data="menu_del_sale")],
            [InlineKeyboardButton("📦 Stock ပစ္စည်း ဖျက်မည်", callback_data="menu_del_stock")],
            [InlineKeyboardButton("💥 စာရင်းအားလုံး ဖျက်မည်", callback_data="confirm_reset_all")]
        ]
        await update.message.reply_text("🗑️ **ဘာကိုဖျက်ချင်တာလဲ ရွေးချယ်ပါ:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    
    elif text == "💰 ငွေဆပ်မည်":
        await update.message.reply_text("💰 **အကြွေး ငွေလာဆပ်ရန်:**\n`/pay <ဝယ်သူနာမည်> | <ပေးသည့်ပမာဏ>`\n👇 `/pay Mg Mg | 100000`", parse_mode="Markdown")
    elif text == "📜 Command ကြည့်ရန်":
        await show_commands(update, context)

def main():
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=auto_ping, daemon=True).start()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("command", show_commands))
    app.add_handler(CommandHandler("add_balance", add_balance))
    app.add_handler(CommandHandler("buy", buy))
    app.add_handler(CommandHandler("expense", add_expense))
    app.add_handler(CommandHandler("add_stock", add_stock))
    app.add_handler(CommandHandler("add_credit", add_credit))
    app.add_handler(CommandHandler("sell_cash", sell_cash))
    app.add_handler(CommandHandler("sell_gift", sell_gift))
    app.add_handler(CommandHandler("sell_installment", sell_installment))
    app.add_handler(CommandHandler("sell_installment_gift", sell_installment_gift))
    app.add_handler(CommandHandler("pay", pay))
    app.add_handler(CommandHandler("stock", stock))
    app.add_handler(CommandHandler("list", list_pending))
    app.add_handler(CommandHandler("report", report))
    app.add_handler(CommandHandler("monthly_report", report))
    app.add_handler(CommandHandler("delete_sale", delete_sale))
    app.add_handler(CommandHandler("delete_item", delete_item))
    app.add_handler(CommandHandler("reset_all", reset_all))
    app.add_handler(CommandHandler("export", export_excel))

    # Unified Callback Handler for interactive buttons
    app.add_handler(CallbackQueryHandler(main_callback_handler))
    app.add_handler(MessageHandler(filters.Document.MimeType("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"), handle_excel_upload))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_button_clicks))

    print("Bot is running...")
    app.run_polling()

if __name__ == '__main__':
    main()

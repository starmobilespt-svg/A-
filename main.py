import os
import sqlite3
import math
import logging
import threading
import pandas as pd
from datetime import datetime
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler, 
    filters, 
    ContextTypes
)

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- 1. KEEP-ALIVE SERVER (FLASK PING SERVER) ---
app_flask = Flask('')

@app_flask.route('/')
def home():
    return "Bot is alive and running!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app_flask.run(host='0.0.0.0', port=port)

def keep_alive():
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()

# --- 2. DATABASE SETUP ---
DATA_DIR = "/var/data"
if os.path.exists(DATA_DIR):
    DB_NAME = os.path.join(DATA_DIR, 'shop_business.db')
else:
    DB_NAME = 'shop_business.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            item_name TEXT,
            quantity INTEGER,
            buy_price REAL,
            total_cost REAL,
            date TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            customer_name TEXT,
            item_name TEXT,
            sale_type TEXT,
            quantity INTEGER DEFAULT 1,
            total_sale_price REAL,
            down_payment REAL,
            remaining_amount REAL,
            monthly_min_amount REAL,
            months_left INTEGER,
            first_date TEXT,
            last_date TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# --- 3. BOT COMMAND HANDLERS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📋 Command မီနူးများ ကြည့်ရန်", callback_data="show_commands")],
        [InlineKeyboardButton("💾 Backup / Restore ပြုလုပ်ရန်", callback_data="show_backup_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "👋 **မင်္ဂလာပါ! အရောင်း/အဝယ် စာရင်းကိုင် Bot မှ ကြိုဆိုပါတယ်။**\n\n"
        "လိုရာ လုပ်ဆောင်ချက်ကို အောက်ပါ ခလုတ်များမှတစ်ဆင့် ရွေးချယ်နိုင်ပါသည်။",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def buy_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    raw_text = " ".join(context.args)
    try:
        parts = [p.strip() for p in raw_text.split('|')]
        item_name = parts[0]
        qty = int(parts[1])
        buy_price = float(parts[2])
        total_cost = qty * buy_price
        today = datetime.now().strftime("%Y-%m-%d")

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO purchases (user_id, item_name, quantity, buy_price, total_cost, date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, item_name, qty, buy_price, total_cost, today))
        conn.commit()
        conn.close()

        msg = (
            f"✅ **ပစ္စည်းဝယ်ယူမှု စာရင်းမှတ်ပြီးပါပြီ!**\n\n"
            f"📦 **ပစ္စည်း:** {item_name}\n"
            f"🔢 **အရေအတွက်:** {qty}\n"
            f"💵 **တစ်ခုချင်း ဝယ်ဈေး:** {buy_price:,.0f} ကျပ်\n"
            f"💰 **စုစုပေါင်း စရိတ်:** {total_cost:,.0f} ကျပ်\n"
            f"📅 **ရက်စွဲ:** {today}"
        )
        await update.message.reply_text(msg, parse_mode='Markdown')
    except Exception:
        await update.message.reply_text("❌ **ပုံစံ မှားယွင်းနေပါသည်။**\n`/buy <ပစ္စည်းအမည်> | <အရေအတွက်> | <ဝယ်ဈေး>`", parse_mode='Markdown')

async def sell_cash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    raw_text = " ".join(context.args)
    try:
        parts = [p.strip() for p in raw_text.split('|')]
        customer_name = parts[0]
        item_name = parts[1]
        sale_price = float(parts[2])
        today = datetime.now().strftime("%Y-%m-%d")

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sales (user_id, customer_name, item_name, sale_type, quantity, total_sale_price, down_payment, remaining_amount, monthly_min_amount, months_left, first_date, last_date)
            VALUES (?, ?, ?, 'CASH', 1, ?, ?, 0, 0, 0, ?, ?)
        """, (user_id, customer_name, item_name, sale_price, sale_price, today, today))
        conn.commit()
        conn.close()

        msg = (
            f"✅ **လက်ငင်း အရောင်းမှတ်ပြီးပါပြီ!**\n\n"
            f"👤 **ဝယ်သူ:** {customer_name}\n"
            f"📦 **ပစ္စည်း:** {item_name}\n"
            f"💰 **ရောင်းရငွေ:** {sale_price:,.0f} ကျပ်\n"
            f"📅 **ရက်စွဲ:** {today}"
        )
        await update.message.reply_text(msg, parse_mode='Markdown')
    except Exception:
        await update.message.reply_text("❌ **ပုံစံ မှားယွင်းနေပါသည်။**\n`/sell_cash <ဝယ်သူနာမည်> | <ပစ္စည်းအမည်> | <ရောင်းဈေး>`", parse_mode='Markdown')

async def sell_installment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    raw_text = " ".join(context.args)
    try:
        parts = [p.strip() for p in raw_text.split('|')]
        customer_name = parts[0]
        item_name = parts[1]
        total_price = float(parts[2])
        down_payment = float(parts[3])
        monthly_min = float(parts[4])

        remaining = total_price - down_payment
        months_left = math.ceil(remaining / monthly_min) if monthly_min > 0 else 0
        today = datetime.now().strftime("%Y-%m-%d")

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sales (user_id, customer_name, item_name, sale_type, quantity, total_sale_price, down_payment, remaining_amount, monthly_min_amount, months_left, first_date, last_date)
            VALUES (?, ?, ?, 'INSTALLMENT', 1, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, customer_name, item_name, total_price, down_payment, remaining, monthly_min, months_left, today, today))
        conn.commit()
        conn.close()

        msg = (
            f"✅ **အရစ်ကျ အရောင်းမှတ်ပြီးပါပြီ!**\n\n"
            f"👤 **ဝယ်သူ:** {customer_name}\n"
            f"📦 **ပစ္စည်း:** {item_name}\n"
            f"💰 **စုစုပေါင်း ရောင်းဈေး:** {total_price:,.0f} ကျပ်\n"
            f"💵 **စပေါ်ငွေ ရရှိပြီး:** {down_payment:,.0f} ကျပ်\n"
            f"📉 **ကျန်ရှိသည့် အကြွေးငွေ:** {remaining:,.0f} ကျပ်\n"
            f"⏳ **ခန့်မှန်း ကျန်သည့်လ:** {months_left} လ\n"
            f"📅 **ရက်စွဲ:** {today}"
        )
        await update.message.reply_text(msg, parse_mode='Markdown')
    except Exception:
        await update.message.reply_text("❌ **ပုံစံ မှားယွင်းနေပါသည်။**\n`/sell_installment <ဝယ်သူနာမည်> | <ပစ္စည်းအမည်> | <စုစုပေါင်းရောင်းဈေး> | <စပေါ်ငွေ> | <တစ်လ ပုံမှန်ပေးရမည့်ငွေ>`", parse_mode='Markdown')

async def pay_installment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        customer_name = context.args[0].strip()
        paid_amount = float(context.args[1])
    except (IndexError, ValueError):
        await update.message.reply_text("❌ **ပုံစံ မှားယွင်းနေပါသည်!**\nဥပမာ - `/pay MgMg 100000`", parse_mode='Markdown')
        return

    today = datetime.now().strftime("%Y-%m-%d")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, remaining_amount, monthly_min_amount FROM sales WHERE user_id=? AND customer_name=? AND sale_type='INSTALLMENT' AND remaining_amount > 0", (user_id, customer_name))
    record = cursor.fetchone()

    if not record:
        conn.close()
        await update.message.reply_text(f"❌ '{customer_name}' ၏ အကြွေးကျန် စာရင်းကို ရှာမတွေ့ပါ။")
        return

    sale_id = record[0]
    remaining = record[1]
    monthly_min = record[2]

    new_remaining = max(0, remaining - paid_amount)
    new_months_left = math.ceil(new_remaining / monthly_min) if monthly_min > 0 else 0

    cursor.execute("""
        UPDATE sales 
        SET remaining_amount = ?, months_left = ?, last_date = ?
        WHERE id = ?
    """, (new_remaining, new_months_left, today, sale_id))
    
    conn.commit()
    conn.close()

    status_msg = "🎉 **အကြွေးကျေသွားပါပြီ!**" if new_remaining == 0 else f"⏳ **ခန့်မှန်း ကျန်သည့်လ:** {new_months_left} လ"

    msg = (
        f"✅ **{customer_name} ၏ ငွေပေးချေမှု မှတ်ပြီးပါပြီ!**\n\n"
        f"💵 **ယခု ပေးသည့်ပမာဏ:** {paid_amount:,.0f} ကျပ်\n"
        f"💰 **နောက်ဆုံး ကျန်သည့်ပမာဏ:** {new_remaining:,.0f} ကျပ်\n"
        f"{status_msg}\n"
        f"📅 **ရက်စွဲ:** {today}"
    )
    await update.message.reply_text(msg, parse_mode='Markdown')

async def check_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT item_name, SUM(quantity) FROM purchases WHERE user_id=? GROUP BY item_name", (user_id,))
    purchases = {row[0]: row[1] for row in cursor.fetchall()}

    cursor.execute("SELECT item_name, SUM(quantity) FROM sales WHERE user_id=? GROUP BY item_name", (user_id,))
    sales = {row[0]: row[1] for row in cursor.fetchall()}

    conn.close()

    if not purchases:
        await update.message.reply_text("📦 လက်ရှိတွင် ဝယ်ယူထားသော Stock ပစ္စည်းများ မရှိသေးပါ။")
        return

    report = "📦 **ဆိုင်ရှိ ပစ္စည်း Stock လက်ကျန် စာရင်းများ:**\n━━━━━━━━━━━━━━━━━━\n"

    for item, bought_qty in purchases.items():
        sold_qty = sales.get(item, 0)
        stock_left = bought_qty - sold_qty
        
        status = "🟢" if stock_left > 0 else "🔴 Stock ကုန်ပြီ"
        report += f"• **{item}**\n  - ဝယ်ယူခဲ့သည်: `{bought_qty}` ခု\n  - ရောင်းပြီး: `{sold_qty}` ခု\n  - **လက်ကျန်:** `{stock_left}` ခု ({status})\n\n"

    await update.message.reply_text(report, parse_mode='Markdown')

async def monthly_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if context.args:
        month_str = context.args[0].strip()
    else:
        month_str = datetime.now().strftime("%Y-%m")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT SUM(total_cost) FROM purchases WHERE user_id=? AND date LIKE ?", (user_id, f"{month_str}%"))
    total_purchase_cost = cursor.fetchone()[0] or 0

    cursor.execute("SELECT SUM(total_sale_price) FROM sales WHERE user_id=? AND sale_type='CASH' AND first_date LIKE ?", (user_id, f"{month_str}%"))
    cash_sales = cursor.fetchone()[0] or 0

    cursor.execute("SELECT SUM(down_payment) FROM sales WHERE user_id=? AND sale_type='INSTALLMENT' AND first_date LIKE ?", (user_id, f"{month_str}%"))
    down_payment_sales = cursor.fetchone()[0] or 0

    cursor.execute("SELECT SUM(remaining_amount) FROM sales WHERE user_id=? AND sale_type='INSTALLMENT'", (user_id,))
    total_uncollected_debt = cursor.fetchone()[0] or 0

    conn.close()

    total_income_collected = cash_sales + down_payment_sales
    net_cash_flow = total_income_collected - total_purchase_cost

    report = (
        f"📊 **လချုပ် စာရင်းချုပ် ({month_str})**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📦 **စုစုပေါင်း ပစ္စည်းအဝယ်စရိတ်:** `{total_purchase_cost:,.0f}` ကျပ်\n"
        f"💵 **လက်ငင်း ရောင်းရငွေ:** `{cash_sales:,.0f}` ကျပ်\n"
        f"📥 **အရစ်ကျ စပေါ်ငွေ ရရှိမှု:** `{down_payment_sales:,.0f}` ကျပ်\n"
        f"──────────────────\n"
        f"💰 **လက်ဝယ် ရရှိထားသော ဝင်ငွေစုစုပေါင်း:** `{total_income_collected:,.0f}` ကျပ်\n"
        f"💸 **အသားတင် ငွေစီးဆင်းမှု (Income - Expense):** `{net_cash_flow:,.0f}` ကျပ်\n"
        f"──────────────────\n"
        f"⏳ **လက်ရှိ ရရန်ကျန်ရှိသော အရစ်ကျအကြွေး စုစုပေါင်း:** `{total_uncollected_debt:,.0f}` ကျပ်"
    )
    await update.message.reply_text(report, parse_mode='Markdown')

async def list_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT customer_name, item_name, remaining_amount, months_left FROM sales WHERE user_id=? AND sale_type='INSTALLMENT' AND remaining_amount > 0", (user_id,))
    records = cursor.fetchall()
    conn.close()

    if not records:
        await update.message.reply_text("📝 အရစ်ကျ ကျန်ရှိသူ စာရင်း မရှိသေးပါ။")
        return

    report = "📋 **လက်ရှိ အရစ်ကျ အကြွေးကျန် စာရင်းများ:**\n\n"
    for r in records:
        report += f"• **{r[0]}** ({r[1]}) - ကျန်ငွေ: `{r[2]:,.0f}` ကျပ် ({r[3]} လကျန်)\n"
    
    await update.message.reply_text(report, parse_mode='Markdown')

async def export_excel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = sqlite3.connect(DB_NAME)
    
    df_buy = pd.read_sql_query("SELECT item_name AS 'ပစ္စည်း', quantity AS 'အရေအတွက်', buy_price AS 'ဝယ်ဈေး', total_cost AS 'စုစုပေါင်းစရိတ်', date AS 'ရက်စွဲ' FROM purchases WHERE user_id=?", conn, params=(user_id,))
    df_sales = pd.read_sql_query("SELECT customer_name AS 'ဝယ်သူ', item_name AS 'ပစ္စည်း', sale_type AS 'ရောင်းချမှုပုံစံ', total_sale_price AS 'ရောင်းဈေး', down_payment AS 'စပေါ်ငွေ', remaining_amount AS 'ကျန်ငွေ', months_left AS 'ကျန်လ', first_date AS 'စတင်ရက်', last_date AS 'နောက်ဆုံးရက်' FROM sales WHERE user_id=?", conn, params=(user_id,))
    conn.close()

    excel_file = "Shop_Records.xlsx"
    with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
        df_sales.to_excel(writer, sheet_name='Sales', index=False)
        df_buy.to_excel(writer, sheet_name='Purchases', index=False)

    with open(excel_file, 'rb') as f:
        await update.message.reply_document(document=f, filename=excel_file, caption="📊 အရောင်း/အဝယ် စာရင်း Excel File")
    
    os.remove(excel_file)

async def send_backup_file(context, chat_id):
    if not os.path.exists(DB_NAME):
        await context.bot.send_message(chat_id=chat_id, text="❌ Backup လုပ်ရန် Database မရှိသေးပါ။")
        return

    today = datetime.now().strftime("%Y-%m-%d")
    backup_filename = f"shop_backup_{today}.db"

    with open(DB_NAME, 'rb') as f:
        await context.bot.send_document(
            chat_id=chat_id, 
            document=f, 
            filename=backup_filename, 
            caption="📦 **Shop Database Backup File ဖြစ်ပါသည်။**"
        )

async def backup_db(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_backup_file(context, update.effective_chat.id)

# --- 4. BUTTON CALLBACK & FILE HANDLERS ---

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc or not doc.file_name:
        return

    if doc.file_name.endswith('.db'):
        keyboard = [
            [InlineKeyboardButton("🔄 စာရင်းများ ပြန်လည် Recover (Restore) လုပ်မည်", callback_data=f"do_restore_db_{doc.file_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "📦 **Database Backup File ရရှိပါသည်။**\n"
            "စာရင်းများကို ပြန်လည် Restore လုပ်လိုပါက အောက်ပါ ခလုတ်ကို နှိပ်ပါ။",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    elif doc.file_name.endswith('.xlsx'):
        keyboard = [
            [InlineKeyboardButton("🔄 ပြင်ဆင်ထားသော Excel မှ စာရင်းများ Recover လုပ်မည်", callback_data=f"do_restore_excel_{doc.file_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "📊 **Excel စာရင်း File ရရှိပါသည်။**\n"
            "Excel ထဲရှိ ပြင်ဆင်ထားသော စာရင်းများဖြင့် Database ထဲသို့ ပြောင်းလဲ Restore လုပ်လိုပါက အောက်ပါ ခလုတ်ကို နှိပ်ပါ။",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

def restore_from_excel_file(excel_file_path, user_id):
    xls = pd.ExcelFile(excel_file_path)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    if 'Sales' in xls.sheet_names:
        df_sales = pd.read_excel(xls, 'Sales')
        cursor.execute("DELETE FROM sales WHERE user_id=?", (user_id,))
        for _, r in df_sales.iterrows():
            cursor.execute("""
                INSERT INTO sales (user_id, customer_name, item_name, sale_type, quantity, total_sale_price, down_payment, remaining_amount, monthly_min_amount, months_left, first_date, last_date)
                VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id, str(r.get('ဝယ်သူ', '')), str(r.get('ပစ္စည်း', '')), str(r.get('ရောင်းချမှုပုံစံ', 'CASH')),
                float(r.get('ရောင်းဈေး', 0)), float(r.get('စပေါ်ငွေ', 0)), float(r.get('ကျန်ငွေ', 0)),
                0, int(r.get('ကျန်လ', 0)), str(r.get('စတင်ရက်', '')), str(r.get('နောက်ဆုံးရက်', ''))
            ))

    if 'Purchases' in xls.sheet_names:
        df_purchases = pd.read_excel(xls, 'Purchases')
        cursor.execute("DELETE FROM purchases WHERE user_id=?", (user_id,))
        for _, r in df_purchases.iterrows():
            cursor.execute("""
                INSERT INTO purchases (user_id, item_name, quantity, buy_price, total_cost, date)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user_id, str(r.get('ပစ္စည်း', '')), int(r.get('အရေအတွက်', 1)),
                float(r.get('ဝယ်ဈေး', 0)), float(r.get('စုစုပေါင်းစရိတ်', 0)), str(r.get('ရက်စွဲ', ''))
            ))

    conn.commit()
    conn.close()

async def button_click_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    await query.answer()

    if query.data == "show_commands":
        welcome_text = (
            "🛍️ **အသုံးပြုနိုင်သော Command များ အပြည့်အစုံ:**\n\n"
            "📦 **၁။ အပြင်မှ ပစ္စည်းဝယ်ယူခြင်း:**\n"
            "`/buy <ပစ္စည်းအမည်> | <အရေအတွက်> | <ဝယ်ဈေး>`\n\n"
            "💵 **၂။ လက်ငင်း ရောင်းချခြင်း:**\n"
            "`/sell_cash <ဝယ်သူနာမည်> | <ပစ္စည်းအမည်> | <ရောင်းဈေး>`\n\n"
            "⏳ **၃။ အရစ်ကျ ရောင်းချခြင်း:**\n"
            "`/sell_installment <ဝယ်သူနာမည်> | <ပစ္စည်းအမည်> | <စုစုပေါင်းရောင်းဈေး> | <စပေါ်ငွေ> | <တစ်လ ပုံမှန်ပေးရမည့်ငွေ>`\n\n"
            "💰 **၄။ အရစ်ကျ ငွေလာဆပ်ခြင်း:**\n"
            "`/pay <ဝယ်သူနာမည်> <ပေးသည့်ပမာဏ>`\n\n"
            "📊 **၅။ စာရင်းများ/Stock ကြည့်ခြင်း:**\n"
            "`/stock` - ဆိုင်ရှိ ပစ္စည်း Stock လက်ကျန်ကြည့်ရန်\n"
            "`/list` - အရစ်ကျ ကျန်သူများ စာရင်းကြည့်ရန်\n"
            "`/monthly_report <YYYY-MM>` - လချုပ် ကြည့်ရန်\n\n"
            "📁 **၆။ Excel & Backup:**\n"
            "`/export` - Excel File ထုတ်ယူရန်\n"
            "`/backup` - Database Backup ထုတ်ယူရန်"
        )
        await query.message.reply_text(welcome_text, parse_mode='Markdown')

    elif query.data == "show_backup_menu":
        keyboard = [
            [InlineKeyboardButton("📥 Backup File ရယူမည်", callback_data="download_backup")],
            [InlineKeyboardButton("📤 Recover (Restore) ပြုလုပ်နည်း", callback_data="show_restore_info")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(
            "⚙️ **Backup & Restore စနစ်:**\n\n"
            "• **Backup File ရယူရန်:** အောက်ပါ ခလုတ်ကို နှိပ်ပါ\n"
            "• **Restore ပြုလုပ်ရန်:** `.db` Backup File သို့မဟုတ် `.xlsx` Excel File ကို Bot ဆီသို့ ပို့ပေးပါ",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    elif query.data == "download_backup":
        await query.message.reply_text("💾 Backup File ကို ထုတ်ပေးနေပါသည်။...")
        await send_backup_file(context, query.message.chat_id)

    elif query.data == "show_restore_info":
        info_text = (
            "🔄 **Recover (Restore) ပြုလုပ်နည်း အဆင့်ဆင့်:**\n\n"
        

import sqlite3
import pandas as pd
import datetime
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters
)

# Configuration
BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN_HERE"  # မိမိ Telegram Bot Token ထည့်ပါ
DB_FILE = "shop_management.db"

# Database Setup
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Inventory Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT UNIQUE,
            quantity INTEGER,
            cost_price REAL
        )
    ''')
    
    # Sales Table
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
            date TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def get_db():
    return sqlite3.connect(DB_FILE)

# Command 1: /buy
async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = " ".join(context.args).split("|")
        if len(args) != 3:
            await update.message.reply_text(
                "❌ **Standard Format:**\n`/buy <ပစ္စည်းအမည်> | <အရေအတွက်> | <ဝယ်ဈေး>`\n\n"
                "👇 **နှိပ်ပြီး ကူးယူပါ:**\n`/buy iPhone 13 | 2 | 1200000`",
                parse_mode="Markdown"
            )
            return

        item_name = args[0].strip()
        qty = int(args[1].strip())
        cost_price = float(args[2].strip())

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT quantity FROM inventory WHERE item_name = ?", (item_name,))
        row = cursor.fetchone()

        if row:
            new_qty = row[0] + qty
            cursor.execute("UPDATE inventory SET quantity = ?, cost_price = ? WHERE item_name = ?", (new_qty, cost_price, item_name))
        else:
            cursor.execute("INSERT INTO inventory (item_name, quantity, cost_price) VALUES (?, ?, ?)", (item_name, qty, cost_price))

        conn.commit()
        conn.close()

        await update.message.reply_text(f"✅ **ပစ္စည်းဝယ်ယူမှု မှတ်တမ်းတင်ပြီးပါပြီ!**\n\n📦 ပစ္စည်း: `{item_name}`\n🔢 အရေအတွက်: `{qty}` ခု\n💵 ဝယ်ဈေး: `{cost_price:,.0f}` MMK", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ အမှားအယွင်းရှိပါသည်: {str(e)}")

# Command 2: /sell_cash
async def sell_cash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = " ".join(context.args).split("|")
        if len(args) != 3:
            await update.message.reply_text(
                "❌ **Standard Format:**\n`/sell_cash <ဝယ်သူနာမည်> | <ပစ္စည်းအမည်> | <ရောင်းဈေး>`\n\n"
                "👇 **နှိပ်ပြီး ကူးယူပါ:**\n`/sell_cash AungAung | iPhone 13 | 1500000`",
                parse_mode="Markdown"
            )
            return

        customer = args[0].strip()
        item_name = args[1].strip()
        price = float(args[2].strip())
        today = datetime.date.today().strftime("%Y-%m-%d")

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT quantity FROM inventory WHERE item_name = ?", (item_name,))
        row = cursor.fetchone()

        if not row or row[0] < 1:
            await update.message.reply_text("❌ လက်ကျန် Stock မလုံလောက်ပါ သို့မဟုတ် ပစ္စည်းရှာမတွေ့ပါ။")
            conn.close()
            return

        cursor.execute("UPDATE inventory SET quantity = quantity - 1 WHERE item_name = ?", (item_name,))
        cursor.execute('''
            INSERT INTO sales (customer_name, item_name, sale_type, total_price, paid_amount, monthly_payment, status, date)
            VALUES (?, ?, 'CASH', ?, ?, 0, 'PAID', ?)
        ''', (customer, item_name, price, price, today))

        sale_id = cursor.lastrowid
        conn.commit()
        conn.close()

        await update.message.reply_text(
            f"💵 **လက်ငင်း ရောင်းချမှု အောင်မြင်ပါသည်။**\n\n"
            f"🆔 အရောင်း ID: `{sale_id}`\n"
            f"👤 ဝယ်သူ: `{customer}`\n"
            f"📦 ပစ္စည်း: `{item_name}`\n"
            f"💰 ရောင်းဈေး: `{price:,.0f}` MMK",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ အမှားအယွင်းရှိပါသည်: {str(e)}")

# Command 3: /sell_installment
async def sell_installment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = " ".join(context.args).split("|")
        if len(args) != 5:
            await update.message.reply_text(
                "❌ **Standard Format:**\n`/sell_installment <ဝယ်သူနာမည်> | <ပစ္စည်းအမည်> | <စုစုပေါင်းရောင်းဈေး> | <စပေါ်ငွေ> | <တစ်လ ပုံမှန်ပေးရမည့်ငွေ>`\n\n"
                "👇 **နှိပ်ပြီး ကူးယူပါ:**\n`/sell_installment MgMg | Phone | 1500000 | 300000 | 100000`",
                parse_mode="Markdown"
            )
            return

        customer = args[0].strip()
        item_name = args[1].strip()
        total_price = float(args[2].strip())
        down_payment = float(args[3].strip())
        monthly_pay = float(args[4].strip())
        today = datetime.date.today().strftime("%Y-%m-%d")

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT quantity FROM inventory WHERE item_name = ?", (item_name,))
        row = cursor.fetchone()

        if not row or row[0] < 1:
            await update.message.reply_text("❌ လက်ကျန် Stock မလုံလောက်ပါ သို့မဟုတ် ပစ္စည်းရှာမတွေ့ပါ။")
            conn.close()
            return

        cursor.execute("UPDATE inventory SET quantity = quantity - 1 WHERE item_name = ?", (item_name,))
        status = 'PAID' if down_payment >= total_price else 'PENDING'

        cursor.execute('''
            INSERT INTO sales (customer_name, item_name, sale_type, total_price, paid_amount, monthly_payment, status, date)
            VALUES (?, ?, 'INSTALLMENT', ?, ?, ?, ?, ?)
        ''', (customer, item_name, total_price, down_payment, monthly_pay, status, today))

        sale_id = cursor.lastrowid
        conn.commit()
        conn.close()

        remaining = total_price - down_payment
        await update.message.reply_text(
            f"⏳ **အရစ်ကျ ရောင်းချမှု မှတ်တမ်းဝင်သွားပါပြီ!**\n\n"
            f"🆔 အရောင်း ID: `{sale_id}`\n"
            f"👤 ဝယ်သူ: `{customer}`\n"
            f"📦 ပစ္စည်း: `{item_name}`\n"
            f"💰 စုစုပေါင်း: `{total_price:,.0f}` MMK\n"
            f"💵 စပေါ်ငွေ: `{down_payment:,.0f}` MMK\n"
            f"📉 ကျန်ငွေ: `{remaining:,.0f}` MMK\n"
            f"🗓️ တစ်လပေးရမည်: `{monthly_pay:,.0f}` MMK",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ အမှားအယွင်းရှိပါသည်: {str(e)}")

# Command 4: /pay
async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(context.args) < 2:
            await update.message.reply_text(
                "❌ **Standard Format:**\n`/pay <ဝယ်သူနာမည်> <ပေးသည့်ပမာဏ>`\n\n"
                "👇 **နှိပ်ပြီး ကူးယူပါ:**\n`/pay MgMg 100000`",
                parse_mode="Markdown"
            )
            return

        customer = context.args[0].strip()
        amount = float(context.args[1].strip())

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, total_price, paid_amount FROM sales 
            WHERE customer_name = ? AND status = 'PENDING' AND sale_type = 'INSTALLMENT'
            ORDER BY id ASC LIMIT 1
        ''', (customer,))
        
        row = cursor.fetchone()

        if not row:
            await update.message.reply_text(f"❌ {customer} အတွက် အရစ်ကျ ပေးရန်ကျန်သော စာရင်း ရှာမတွေ့ပါ။")
            conn.close()
            return

        sale_id, total_price, current_paid = row
        new_paid = current_paid + amount
        new_status = 'PAID' if new_paid >= total_price else 'PENDING'

        cursor.execute('''
            UPDATE sales SET paid_amount = ?, status = ? WHERE id = ?
        ''', (new_paid, new_status, sale_id))

        conn.commit()
        conn.close()

        rem = total_price - new_paid
        rem_str = "0 (ပေးချေမှု ပြီးဆုံးပါပြီ)" if rem <= 0 else f"{rem:,.0f} MMK"

        await update.message.reply_text(
            f"💰 **ငွေဆပ်မှု အဆင်ပြေပါသည်။**\n\n"
            f"🆔 အရောင်း ID: `{sale_id}`\n"
            f"👤 ဝယ်သူ: `{customer}`\n"
            f"💵 ပေးသွင်းငွေ: `{amount:,.0f}` MMK\n"
            f"📊 ပေးပြီး စုစုပေါင်း: `{new_paid:,.0f}` / `{total_price:,.0f}` MMK\n"
            f"📉 ပေးရန်ကျန်ငွေ: `{rem_str}`",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ အမှားအယွင်းရှိပါသည်: {str(e)}")

# Command 5: Stock / List / Report
async def stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, item_name, quantity, cost_price FROM inventory")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("📦 လက်ရှိ Stock လုံးဝ မရှိသေးပါ။")
        return

    msg = "📊 **ဆိုင်ရှိ လက်ကျန် Stock စာရင်း:**\n\n"
    for r in rows:
        msg += f"• `{r[1]}` - `{r[2]}` ခု (ဝယ်ဈေး: `{r[3]:,.0f}` MMK)\n"

    msg += "\n💡 *Stock ဖျက်လိုပါက:* `/delete_item <ပစ္စည်းအမည်>`"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def list_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, customer_name, item_name, total_price, paid_amount, monthly_payment 
        FROM sales WHERE status = 'PENDING'
    ''')
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("🎉 အရစ်ကျ ကျန်ရှိသူ စာရင်း မရှိပါ။")
        return

    msg = "⏳ **အရစ်ကျ ပေးရန်ကျန်သူများ စာရင်း:**\n\n"
    for r in rows:
        rem = r[3] - r[4]
        msg += f"🆔 ID: `{r[0]}` | 👤 **{r[1]}** ({r[2]})\n"
        msg += f"  ကျန်ငွေ: `{rem:,.0f}` / `{r[3]:,.0f}` MMK (၁ လပေး: `{r[5]:,.0f}` MMK)\n\n"

    msg += "💡 *စာရင်းမှား၍ ဖျက်လိုပါက:* `/delete_sale <ID>`"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def monthly_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args:
            await update.message.reply_text(
                "❌ **Standard Format:**\n`/monthly_report YYYY-MM`\n\n"
                "👇 **နှိပ်ပြီး ကူးယူပါ:**\n`/monthly_report 2026-07`",
                parse_mode="Markdown"
            )
            return

        year_month = context.args[0].strip()

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT total_price, paid_amount FROM sales 
            WHERE strftime('%Y-%m', date) = ?
        ''', (year_month,))
        
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            await update.message.reply_text(f"📅 {year_month} လအတွက် စာရင်း မရှိသေးပါ။")
            return

        total_sales_value = sum(r[0] for r in rows)
        total_collected_cash = sum(r[1] for r in rows)

        msg = f"📊 **{year_month} လချုပ် စာရင်းအကျဉ်း**\n\n"
        msg += f"🛒 စုစုပေါင်း ရောင်းချရမှု ပမာဏ: `{total_sales_value:,.0f}` MMK\n"
        msg += f"💵 လက်ဝယ် ရရှိပြီးသော ငွေစုစုပေါင်း: `{total_collected_cash:,.0f}` MMK\n"
        msg += f"📉 ရရန်ကျန်ငွေ ပမာဏ: `{(total_sales_value - total_collected_cash):,.0f}` MMK\n"

        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ အမှားအယွင်းရှိပါသည်: {str(e)}")

# Delete Specific Sale Entry (/delete_sale <ID>)
async def delete_sale(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args:
            await update.message.reply_text(
                "❌ **Standard Format:**\n`/delete_sale <ID>`\n\n"
                "👇 **နှိပ်ပြီး ကူးယူပါ:**\n`/delete_sale 1`",
                parse_mode="Markdown"
            )
            return

        sale_id = int(context.args[0].strip())

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT customer_name, item_name FROM sales WHERE id = ?", (sale_id,))
        row = cursor.fetchone()

        if not row:
            await update.message.reply_text(f"❌ ID `{sale_id}` ဖြင့် အရောင်းစာရင်း ရှာမတွေ့ပါ။", parse_mode="Markdown")
            conn.close()
            return

        cursor.execute("DELETE FROM sales WHERE id = ?", (sale_id,))
        conn.commit()
        conn.close()

        await update.message.reply_text(f"🗑️ ID `{sale_id}` ({row[0]} - {row[1]}) အရောင်းစာရင်းကို ဖျက်လိုက်ပါပြီ။", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ အမှားအယွင်းရှိပါသည်: {str(e)}")

# Delete Specific Stock Item (/delete_item <item_name>)
async def delete_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args:
            await update.message.reply_text(
                "❌ **Standard Format:**\n`/delete_item <ပစ္စည်းအမည်>`\n\n"
                "👇 **နှိပ်ပြီး ကူးယူပါ:**\n`/delete_item iPhone 13`",
                parse_mode="Markdown"
            )
            return

        item_name = " ".join(context.args).strip()

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT item_name FROM inventory WHERE item_name = ?", (item_name,))
        row = cursor.fetchone()

        if not row:
            await update.message.reply_text(f"❌ Stock ထဲတွင် `{item_name}` အမည်ဖြင့် ပစ္စည်း ရှာမတွေ့ပါ။", parse_mode="Markdown")
            conn.close()
            return

        cursor.execute("DELETE FROM inventory WHERE item_name = ?", (item_name,))
        conn.commit()
        conn.close()

        await update.message.reply_text(f"🗑️ Stock ထဲမှ `{item_name}` စာရင်းကို ဖျက်လိုက်ပါပြီ။", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ အမှားအယွင်းရှိပါသည်: {str(e)}")

# Reset All Data (/reset_all) with Confirmation Button
async def reset_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("✅ အကုန်ဖျက်မည် (Confirm)", callback_data="confirm_reset_all"),
            InlineKeyboardButton("❌ မဖျက်တော့ပါ (Cancel)", callback_data="cancel_reset_all")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "⚠️ **သတိပေးချက်:** စာရင်းအားလုံး (Stock နှင့် အရောင်းစာရင်း အားလုံး) ကို လုံးဝ ဖျက်ပစ်ပါမည်။\n\n"
        "ဧကန်မုချ ဖျက်လိုပါသလား?",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def reset_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "confirm_reset_all":
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM inventory")
        cursor.execute("DELETE FROM sales")
        conn.commit()
        conn.close()
        await query.message.edit_text("💥 **စာရင်း အားလုံးကို အောင်မြင်စွာ ဖျက်ပစ်ပြီးပါပြီ!** (Reset Completed)", parse_mode="Markdown")
    elif query.data == "cancel_reset_all":
        await query.message.edit_text("❌ စာရင်းဖျက်ခြင်းကို ပယ်ဖျက်လိုက်ပါပြီ။")

# Export Excel
async def export_excel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        conn = get_db()
        df_inventory = pd.read_sql_query("SELECT * FROM inventory", conn)
        df_sales = pd.read_sql_query("SELECT * FROM sales", conn)
        conn.close()

        file_path = "Shop_Data_Export.xlsx"
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            df_inventory.to_excel(writer, sheet_name='Inventory', index=False)
            df_sales.to_excel(writer, sheet_name='Sales', index=False)

        await update.message.reply_document(document=open(file_path, 'rb'), filename=file_path)
    except Exception as e:
        await update.message.reply_text(f"❌ Excel export မလုပ်နိုင်ပါ: {str(e)}")

# Excel Import Guide
async def import_excel_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📥 **Excel Restore / Update ပြုလုပ်နည်း:**\n\n"
        "၁။ `/export` ဖြင့် ထုတ်ယူထားသော Excel file ကို ပြင်ဆင်ပါ။\n"
        "၂။ ပြင်ဆင်ပြီးပါက ထို Excel File (`.xlsx`) ကို Bot Chat သို့ တိုက်ရိုက် File ပို့ပေးလိုက်ပါ။\n"
        "၃။ Bot မှ စာရင်းများကို Database ထဲသို့ 自動 ပြန်လည် အစားထိုးပေးပါမည်။",
        parse_mode="Markdown"
    )

# Excel File Handler
async def handle_excel_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    if not document.file_name.endswith('.xlsx'):
        await update.message.reply_text("❌ ကျေးဇူးပြု၍ `.xlsx` Excel File များကိုသာ ပို့ပေးပါ။")
        return

    status_msg = await update.message.reply_text("🔄 Excel File ကို ဖတ်ရှုပြီး Database သို့ အစားထိုး ပြင်ဆင်နေပါသည်...")

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
                cursor.execute('''
                    INSERT INTO inventory (id, item_name, quantity, cost_price)
                    VALUES (?, ?, ?, ?)
                ''', (row.get('id'), row['item_name'], row['quantity'], row['cost_price']))

        if 'Sales' in xls.sheet_names:
            df_sales = pd.read_excel(xls, sheet_name='Sales')
            cursor.execute("DELETE FROM sales")
            for _, row in df_sales.iterrows():
                cursor.execute('''
                    INSERT INTO sales (id, customer_name, item_name, sale_type, total_price, paid_amount, monthly_payment, status, date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    row.get('id'), row['customer_name'], row['item_name'], row['sale_type'],
                    row['total_price'], row['paid_amount'], row['monthly_payment'],
                    row['status'], str(row['date'])
                ))

        conn.commit()
        conn.close()

        if os.path.exists(temp_path):
            os.remove(temp_path)

        await status_msg.edit_text("✅ **Excel File မှ စာရင်းများကို Database သို့ အောင်မြင်စွာ Restore / Update လုပ်ပြီးပါပြီ!**")
    except Exception as e:
        await status_msg.edit_text(f"❌ Excel မှ စာရင်းသွင်းရာတွင် အမှားဖြစ်ပေါ်ပါသည်: {str(e)}")

# Backup Database
async def backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_document(
            document=open(DB_FILE, 'rb'),
            filename="database_backup.db",
            caption="📁 **Database Backup File ရရှိပါပြီ!**"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Backup မထုတ်ယူနိုင်ပါ: {str(e)}")

# Ping
async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏓 **Pong! Bot သည် အလုပ်လုပ်နေဆဲ ဖြစ်ပါသည်။**")

# Start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🛍️ **အသုံးပြုနိုင်သော Command များ (ထိလိုက်ပါက Copy ရပါသည်):**\n\n"
        "📦 **၁။ ဝယ်ယူခြင်း:**\n"
        "`/buy iPhone 13 | 2 | 1200000`\n\n"
        "💵 **၂။ လက်ငင်း ရောင်းချခြင်း:**\n"
        "`/sell_cash AungAung | iPhone 13 | 1500000`\n\n"
        "⏳ **၃။ အရစ်ကျ ရောင်းချခြင်း:**\n"
   

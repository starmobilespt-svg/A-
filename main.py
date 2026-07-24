import sqlite3
import pandas as pd
import datetime
import os
import threading
import time
import requests
from flask import Flask
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters
)

# Configuration
BOT_TOKEN = "8939067464:AAFwfWTwtzJGlCS-Vh3aUlt55NRS2tgY4wg"
DB_FILE = "shop_management.db"

# ----------------------------------------------------
# 🌐 Render Sleep မဖြစ်အောင် ထိန်းပေးမည့် Web Server & Ping စနစ်
# ----------------------------------------------------
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Bot is alive and running!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

# ၁၅ မိနစ်တစ်ခါ Auto Ping ပို့ပေးမည့် Function
def auto_ping():
    while True:
        time.sleep(14 * 60) # ၁၄ မိနစ်တိုင်း Ping မည်
        render_url = os.environ.get("RENDER_EXTERNAL_URL")
        if render_url:
            try:
                requests.get(render_url)
                print("Auto Ping sent to keep bot alive.")
            except Exception as e:
                print(f"Auto Ping Error: {e}")

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
            date TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def get_db():
    return sqlite3.connect(DB_FILE)

# ----------------------------------------------------
# 📱 Telegram Bot Layout & Keyboards
# ----------------------------------------------------
def get_main_keyboard():
    keyboard = [
        [KeyboardButton("📦 ဝယ်ယူမည်"), KeyboardButton("💵 လက်ငင်းရောင်းမည်")],
        [KeyboardButton("⏳ အရစ်ကျရောင်းမည်"), KeyboardButton("💰 ငွေဆပ်မည်")],
        [KeyboardButton("📊 လက်ကျန် Stock"), KeyboardButton("⏳ ပေးရန်ကျန်သူများ")],
        [KeyboardButton("📈 လချုပ်ကြည့်မည်"), KeyboardButton("🗑️ စာရင်းဖျက်မည်")],
        [KeyboardButton("📁 Excel ထုတ်မည်"), KeyboardButton("💾 Backup ယူမည်")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "မင်္ဂလာပါ! စာရင်းကိုင် Bot မှ ကြိုဆိုပါသည်။\nအောက်ပါ ခလုတ်များကို နှိပ်၍ အသုံးပြုနိုင်ပါသည်။\n\n(စာရင်းသွင်းနည်း ပုံစံများကို ကြည့်လိုပါက `command` ဟု စာရိုက်ပါ)",
        reply_markup=get_main_keyboard()
    )

# Command List ( command ဟု ရိုက်မှ ပေါ်မည် )
async def show_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🛍️ **အသုံးပြုနိုင်သော Command များ (ထိလိုက်ပါက Copy ရပါသည်):**\n\n"
        "📦 **၁။ ဝယ်ယူခြင်း:**\n"
        "`/buy iPhone 13 | 2 | 1200000`\n\n"
        "💵 **၂။ လက်ငင်း ရောင်းချခြင်း:**\n"
        "`/sell_cash AungAung | iPhone 13 | 1500000`\n\n"
        "⏳ **၃။ အရစ်ကျ ရောင်းချခြင်း:**\n"
        "`/sell_installment MgMg | Phone | 1500000 | 300000 | 100000`\n\n"
        "💰 **၄။ အရစ်ကျ ငွေလာဆပ်ခြင်း:**\n"
        "`/pay MgMg 100000`\n\n"
        "📊 **၅။ စာရင်းများ စစ်ဆေးခြင်း:**\n"
        "`/stock` - Stock စာရင်းကြည့်ရန်\n"
        "`/list` - အရစ်ကျကျန်သူများ စာရင်းကြည့်ရန်\n"
        "`/monthly_report 2026-07` - လချုပ်ကြည့်ရန်\n\n"
        "🗑️ **၆။ စာရင်းမှား ဖျက်ခြင်း:**\n"
        "`/delete_sale 1` - အရောင်း ID ဖြင့် စာရင်းတစ်ခုဖျက်ရန်\n"
        "`/delete_item iPhone 13` - Stock ပစ္စည်းတစ်ခုဖျက်ရန်\n"
        "`/reset_all` - စာရင်း အားလုံး ဖျက်ပစ်ရန်\n\n"
        "📁 **၇။ Excel & Backup:**\n"
        "`/export` - Excel File ထုတ်ယူရန်\n"
        "`/backup` - Database Backup ယူရန်"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

# Command Handlers
async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = " ".join(context.args).split("|")
        if len(args) != 3:
            await update.message.reply_text("❌ **Standard Format:**\n`/buy <ပစ္စည်းအမည်> | <အရေအတွက်> | <ဝယ်ဈေး>`\n\n👇 **နှိပ်ပြီး ကူးယူပါ:**\n`/buy iPhone 13 | 2 | 1200000`", parse_mode="Markdown")
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
        await update.message.reply_text(f"✅ **ပစ္စည်းဝယ်ယူမှု မှတ်တမ်းတင်ပြီးပါပြီ!**\n\n📦 ပစ္စည်း: `{item_name}`\n🔢 အရေအတွက်: `{qty}` ခု\n💵 ဝယ်ဈေး: `{cost_price:,.0f}` MMK", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ အမှားအယွင်းရှိပါသည်: {str(e)}")

async def sell_cash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = " ".join(context.args).split("|")
        if len(args) != 3:
            await update.message.reply_text("❌ **Standard Format:**\n`/sell_cash <ဝယ်သူနာမည်> | <ပစ္စည်းအမည်> | <ရောင်းဈေး>`\n\n👇 **နှိပ်ပြီး ကူးယူပါ:**\n`/sell_cash AungAung | iPhone 13 | 1500000`", parse_mode="Markdown")
            return
        customer, item_name, price = args[0].strip(), args[1].strip(), float(args[2].strip())
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
        cursor.execute("INSERT INTO sales (customer_name, item_name, sale_type, total_price, paid_amount, monthly_payment, status, date) VALUES (?, ?, 'CASH', ?, ?, 0, 'PAID', ?)", (customer, item_name, price, price, today))
        sale_id = cursor.lastrowid
        conn.commit()
        conn.close()
        await update.message.reply_text(f"💵 **လက်ငင်း ရောင်းချမှု အောင်မြင်ပါသည်။**\n\n🆔 အရောင်း ID: `{sale_id}`\n👤 ဝယ်သူ: `{customer}`\n📦 ပစ္စည်း: `{item_name}`\n💰 ရောင်းဈေး: `{price:,.0f}` MMK", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ အမှားအယွင်းရှိပါသည်: {str(e)}")

async def sell_installment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = " ".join(context.args).split("|")
        if len(args) != 5:
            await update.message.reply_text("❌ **Standard Format:**\n`/sell_installment <ဝယ်သူနာမည်> | <ပစ္စည်းအမည်> | <စုစုပေါင်းရောင်းဈေး> | <စပေါ်ငွေ> | <တစ်လ ပုံမှန်ပေးရမည့်ငွေ>`\n\n👇 **နှိပ်ပြီး ကူးယူပါ:**\n`/sell_installment MgMg | Phone | 1500000 | 300000 | 100000`", parse_mode="Markdown")
            return
        customer, item_name, total_price, down_payment, monthly_pay = args[0].strip(), args[1].strip(), float(args[2].strip()), float(args[3].strip()), float(args[4].strip())
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
        cursor.execute("INSERT INTO sales (customer_name, item_name, sale_type, total_price, paid_amount, monthly_payment, status, date) VALUES (?, ?, 'INSTALLMENT', ?, ?, ?, ?, ?)", (customer, item_name, total_price, down_payment, monthly_pay, status, today))
        sale_id = cursor.lastrowid
        conn.commit()
        conn.close()
        await update.message.reply_text(f"⏳ **အရစ်ကျ ရောင်းချမှု မှတ်တမ်းဝင်သွားပါပြီ!**\n\n🆔 အရောင်း ID: `{sale_id}`\n👤 ဝယ်သူ: `{customer}`\n📦 ပစ္စည်း: `{item_name}`\n💰 စုစုပေါင်း: `{total_price:,.0f}` MMK\n💵 စပေါ်ငွေ: `{down_payment:,.0f}` MMK\n📉 ကျန်ငွေ: `{total_price - down_payment:,.0f}` MMK\n🗓️ တစ်လပေးရမည်: `{monthly_pay:,.0f}` MMK", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ အမှားအယွင်းရှိပါသည်: {str(e)}")

async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(context.args) < 2:
            await update.message.reply_text("❌ **Standard Format:**\n`/pay <ဝယ်သူနာမည်> <ပေးသည့်ပမာဏ>`\n\n👇 **နှိပ်ပြီး ကူးယူပါ:**\n`/pay MgMg 100000`", parse_mode="Markdown")
            return
        customer, amount = context.args[0].strip(), float(context.args[1].strip())
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, total_price, paid_amount FROM sales WHERE customer_name = ? AND status = 'PENDING' AND sale_type = 'INSTALLMENT' ORDER BY id ASC LIMIT 1", (customer,))
        row = cursor.fetchone()
        if not row:
            await update.message.reply_text(f"❌ {customer} အတွက် အရစ်ကျ ပေးရန်ကျန်သော စာရင်း ရှာမတွေ့ပါ။")
            conn.close()
            return
        sale_id, total_price, current_paid = row
        new_paid = current_paid + amount
        new_status = 'PAID' if new_paid >= total_price else 'PENDING'
        cursor.execute("UPDATE sales SET paid_amount = ?, status = ? WHERE id = ?", (new_paid, new_status, sale_id))
        conn.commit()
        conn.close()
        rem = total_price - new_paid
        rem_str = "0 (ပေးချေမှု ပြီးဆုံးပါပြီ)" if rem <= 0 else f"{rem:,.0f} MMK"
        await update.message.reply_text(f"💰 **ငွေဆပ်မှု အဆင်ပြေပါသည်။**\n\n🆔 အရောင်း ID: `{sale_id}`\n👤 ဝယ်သူ: `{customer}`\n💵 ပေးသွင်းငွေ: `{amount:,.0f}` MMK\n📊 ပေးပြီး စုစုပေါင်း: `{new_paid:,.0f}` / `{total_price:,.0f}` MMK\n📉 ပေးရန်ကျန်ငွေ: `{rem_str}`", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ အမှားအယွင်းရှိပါသည်: {str(e)}")

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
    cursor.execute("SELECT id, customer_name, item_name, total_price, paid_amount, monthly_payment FROM sales WHERE status = 'PENDING'")
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        await update.message.reply_text("🎉 အရစ်ကျ ကျန်ရှိသူ စာရင်း မရှိပါ။")
        return
    msg = "⏳ **အရစ်ကျ ပေးရန်ကျန်သူများ စာရင်း:**\n\n"
    for r in rows:
        msg += f"🆔 ID: `{r[0]}` | 👤 **{r[1]}** ({r[2]})\n  ကျန်ငွေ: `{r[3] - r[4]:,.0f}` / `{r[3]:,.0f}` MMK (၁ လပေး: `{r[5]:,.0f}` MMK)\n\n"
    msg += "💡 *စာရင်းမှား၍ ဖျက်လိုပါက:* `/delete_sale <ID>`"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def monthly_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        year_month = context.args[0].strip() if context.args else datetime.date.today().strftime("%Y-%m")
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT total_price, paid_amount FROM sales WHERE strftime('%Y-%m', date) = ?", (year_month,))
        rows = cursor.fetchall()
        conn.close()
        if not rows:
            await update.message.reply_text(f"📅 {year_month} လအတွက် စာရင်း မရှိသေးပါ။")
            return
        total_sales_value = sum(r[0] for r in rows)
        total_collected_cash = sum(r[1] for r in rows)
        msg = f"📊 **{year_month} လချုပ် စာရင်းအကျဉ်း**\n\n🛒 စုစုပေါင်း ရောင်းချရမှု ပမာဏ: `{total_sales_value:,.0f}` MMK\n💵 လက်ဝယ် ရရှိပြီးသော ငွေစုစုပေါင်း: `{total_collected_cash:,.0f}` MMK\n📉 ရရန်ကျန်ငွေ ပမာဏ: `{(total_sales_value - total_collected_cash):,.0f}` MMK\n"
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ အမှားအယွင်းရှိပါသည်: {str(e)}")

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

async def backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_document(document=open(DB_FILE, 'rb'), filename="database_backup.db", caption="📁 **Database Backup File ရရှိပါပြီ!**")
    except Exception as e:
        await update.message.reply_text(f"❌ Backup မထုတ်ယူနိုင်ပါ: {str(e)}")

# Bottom Button Click Handler
async def handle_button_clicks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "📦 ဝယ်ယူမည်":
        await update.message.reply_text("📦 **ဝယ်ယူမှု စာရင်းသွင်းရန်:**\n`/buy <ပစ္စည်းအမည်> | <အရေအတွက်> | <ဝယ်ဈေး>`\n\n👇 **နှိပ်ပြီး ကူးယူပါ:**\n`/buy iPhone 13 | 2 | 1200000`", parse_mode="Markdown")
    elif text == "💵 လက်ငင်းရောင်းမည်":
        await update.message.reply_text("💵 **လက်ငင်း ရောင်းချရန်:**\n`/sell_cash <ဝယ်သူနာမည်> | <ပစ္စည်းအမည်> | <ရောင်းဈေး>`\n\n👇 **နှိပ်ပြီး ကူးယူပါ:**\n`/sell_cash AungAung | iPhone 13 | 1500000`", parse_mode="Markdown")
    elif text == "⏳ အရစ်ကျရောင်းမည်":
        await update.message.reply_text("⏳ **အရစ်ကျ ရောင်းချရန်:**\n`/sell_installment <ဝယ်သူနာမည်> | <ပစ္စည်းအမည်> | <စုစုပေါင်းရောင်းဈေး> | <စပေါ်ငွေ> | <တစ်လ ပုံမှန်ပေးရမည့်ငွေ>`\n\n👇 **နှိပ်ပြီး ကူးယူပါ:**\n`/sell_installment MgMg | Phone | 1500000 | 300000 | 100000`", parse_mode="Markdown")
    elif text == "💰 ငွေဆပ်မည်":
        await update.message.reply_text("💰 **အရစ်ကျ ငွေလာဆပ်ရန်:**\n`/pay <ဝယ်သူနာမည်> <ပေးသည့်ပမာဏ>`\n\n👇 **နှိပ်ပြီး ကူးယူပါ:**\n`/pay MgMg 100000`", parse_mode="Markdown")
    elif text == "📊 လက်ကျန် Stock":
        await stock(update, context)
    elif text == "⏳ ပေးရန်ကျန်သူများ":
        await list_pending(update, context)
    elif text == "📈 လချုပ်ကြည့်မည်":
        await monthly_report(update, context)
    elif text == "🗑️ စာရင်းဖျက်မည်":
        await update.message.reply_text("🗑️ **စာရင်းမှား ဖျက်လိုပါက:**\n• အရောင်းစာရင်းဖျက်ရန်: `/delete_sale <ID>`\n• Stock ပစ္စည်းဖျက်ရန်: `/delete_item <ပစ္စည်းအမည်>`\n• စာရင်းအားလုံးဖျက်ရန်: `/reset_all`", parse_mode="Markdown")
    elif text == "📁 Excel ထုတ်မည်":
        await export_excel(update, context)
    elif text == "💾 Backup ယူမည်":
        await backup(update, context)
    elif text.lower() == "command":
        await show_commands(update, context)

# ----------------------------------------------------
# 🚀 Main App Start Function
# ----------------------------------------------------
def main():
    # 1. Start Flask Web Server
    threading.Thread(target=run_flask, daemon=True).start()

    # 2. Start Auto Ping Thread
    threading.Thread(target=auto_ping, daemon=True).start()

    # 3. Start Telegram Bot
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("command", show_commands))
    app.add_handler(CommandHandler("buy", buy))
    app.add_handler(CommandHandler("sell_cash", sell_cash))
    app.add_handler(CommandHandler("sell_installment", sell_installment))
    app.add_handler(CommandHandler("pay", pay))
    app.add_handler(CommandHandler("stock", stock))
    app.add_handler(CommandHandler("list", list_pending))
    app.add_handler(CommandHandler("monthly_report", monthly_report))
    app.add_handler(CommandHandler("export", export_excel))
    app.add_handler(CommandHandler("backup", backup))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_button_clicks))

    print("Bot is running with Auto-Ping Keep Alive...")
    app.run_polling()

if __name__ == '__main__':
    main()
        

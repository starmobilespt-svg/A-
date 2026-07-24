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
            await update.message.reply_text("❌ Standard Format: /buy <ပစ္စည်းအမည်> | <အရေအတွက်> | <ဝယ်ဈေး>\n(ဥပမာ: /buy iPhone 13 | 2 | 1200000)")
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

        await update.message.reply_text(f"✅ **ပစ္စည်းဝယ်ယူမှု မှတ်တမ်းတင်ပြီးပါပြီ!**\n\n📦 ပစ္စည်း: {item_name}\n🔢 အရေအတွက်: {qty} ခု\n💵 ဝယ်ဈေး: {cost_price:,.0f} MMK")
    except Exception as e:
        await update.message.reply_text(f"❌ အမှားအယွင်းရှိပါသည်: {str(e)}")

# Command 2: /sell_cash
async def sell_cash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = " ".join(context.args).split("|")
        if len(args) != 3:
            await update.message.reply_text("❌ Standard Format: /sell_cash <ဝယ်သူနာမည်> | <ပစ္စည်းအမည်> | <ရောင်းဈေး>\n(ဥပမာ: /sell_cash AungAung | iPhone 13 | 1500000)")
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
            await update.message.reply_text(f"❌ လက်ကျန် Stock မလုံလောက်ပါ သို့မဟုတ် ပစ္စည်းရှာမတွေ့ပါ။")
            conn.close()
            return

        cursor.execute("UPDATE inventory SET quantity = quantity - 1 WHERE item_name = ?", (item_name,))
        cursor.execute('''
            INSERT INTO sales (customer_name, item_name, sale_type, total_price, paid_amount, monthly_payment, status, date)
            VALUES (?, ?, 'CASH', ?, ?, 0, 'PAID', ?)
        ''', (customer, item_name, price, price, today))

        conn.commit()
        conn.close()

        await update.message.reply_text(f"💵 **လက်ငင်း ရောင်းချမှု အောင်မြင်ပါသည်။**\n\n👤 ဝယ်သူ: {customer}\n📦 ပစ္စည်း: {item_name}\n💰 ရောင်းဈေး: {price:,.0f} MMK")
    except Exception as e:
        await update.message.reply_text(f"❌ အမှားအယွင်းရှိပါသည်: {str(e)}")

# Command 3: /sell_installment
async def sell_installment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = " ".join(context.args).split("|")
        if len(args) != 5:
            await update.message.reply_text("❌ Standard Format: /sell_installment <ဝယ်သူနာမည်> | <ပစ္စည်းအမည်> | <စုစုပေါင်းရောင်းဈေး> | <စပေါ်ငွေ> | <တစ်လ ပုံမှန်ပေးရမည့်ငွေ>")
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
            await update.message.reply_text(f"❌ လက်ကျန် Stock မလုံလောက်ပါ သို့မဟုတ် ပစ္စည်းရှာမတွေ့ပါ။")
            conn.close()
            return

        cursor.execute("UPDATE inventory SET quantity = quantity - 1 WHERE item_name = ?", (item_name,))
        status = 'PAID' if down_payment >= total_price else 'PENDING'

        cursor.execute('''
            INSERT INTO sales (customer_name, item_name, sale_type, total_price, paid_amount, monthly_payment, status, date)
            VALUES (?, ?, 'INSTALLMENT', ?, ?, ?, ?, ?)
        ''', (customer, item_name, total_price, down_payment, monthly_pay, status, today))

        conn.commit()
        conn.close()

        remaining = total_price - down_payment
        await update.message.reply_text(
            f"⏳ **အရစ်ကျ ရောင်းချမှု မှတ်တမ်းဝင်သွားပါပြီ!**\n\n"
            f"👤 ဝယ်သူ: {customer}\n📦 ပစ္စည်း: {item_name}\n💰 စုစုပေါင်း: {total_price:,.0f} MMK\n"
            f"💵 စပေါ်ငွေ: {down_payment:,.0f} MMK\n📉 ကျန်ငွေ: {remaining:,.0f} MMK\n"
            f"🗓️ တစ်လပေးရမည်: {monthly_pay:,.0f} MMK"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ အမှားအယွင်းရှိပါသည်: {str(e)}")

# Command 4: /pay
async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(context.args) < 2:
            await update.message.reply_text("❌ Standard Format: /pay <ဝယ်သူနာမည်> <ပေးသည့်ပမာဏ>")
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
            f"👤 ဝယ်သူ: {customer}\n"
            f"💵 ပေးသွင်းငွေ: {amount:,.0f} MMK\n"
            f"📊 ပေးပြီး စုစုပေါင်း: {new_paid:,.0f} / {total_price:,.0f} MMK\n"
            f"📉 ပေးရန်ကျန်ငွေ: {rem_str}"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ အမှားအယွင်းရှိပါသည်: {str(e)}")

# Command 5: Stock / List / Report
async def stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT item_name, quantity, cost_price FROM inventory")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("📦 လက်ရှိ Stock လုံးဝ မရှိသေးပါ။")
        return

    msg = "📊 **ဆိုင်ရှိ လက်ကျန် Stock စာရင်း:**\n\n"
    for r in rows:
        msg += f"• **{r[0]}** - {r[1]} ခု (ဝယ်ဈေး: {r[2]:,.0f} MMK)\n"

    await update.message.reply_text(msg, parse_mode="Markdown")

async def list_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT customer_name, item_name, total_price, paid_amount, monthly_payment 
        FROM sales WHERE status = 'PENDING'
    ''')
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("🎉 အရစ်ကျ ကျန်ရှိသူ စာရင်း မရှိပါ။")
        return

    msg = "⏳ **အရစ်ကျ ပေးရန်ကျန်သူများ စာရင်း:**\n\n"
    for r in rows:
        rem = r[2] - r[3]
        msg += f"👤 **{r[0]}** ({r[1]})\n"
        msg += f"  ကျန်ငွေ: {rem:,.0f} / {r[2]:,.0f} MMK (၁ လပေး: {r[4]:,.0f} MMK)\n\n"

    await update.message.reply_text(msg, parse_mode="Markdown")

async def monthly_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args:
            await update.message.reply_text("❌ Standard Format: /monthly_report YYYY-MM")
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
        msg += f"🛒 စုစုပေါင်း ရောင်းချရမှု ပမာဏ: {total_sales_value:,.0f} MMK\n"
        msg += f"💵 လက်ဝယ် ရရှိပြီးသော ငွေစုစုပေါင်း: {total_collected_cash:,.0f} MMK\n"
        msg += f"📉 ရရန်ကျန်ငွေ ပမာဏ: {(total_sales_value - total_collected_cash):,.0f} MMK\n"

        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ အမှားအယွင်းရှိပါသည်: {str(e)}")

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

# Excel Import Guide Command
async def import_excel_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📥 **Excel Restore / Update ပြုလုပ်နည်း:**\n\n"
        "၁။ `/export` ဖြင့် ထုတ်ယူထားသော Excel file ကို Computer သို့မဟုတ် Phone တွင် ပြင်ဆင်ပါ။\n"
        "၂။ ပြင်ဆင်ပြီးပါက ထို Excel File (`.xlsx`) ကို Bot Chat သို့ တိုက်ရိုက် File အဖြစ် Send ပို့ပေးလိုက်ပါ။\n"
        "၃။ Bot မှ Excel ထဲရှိ စာရင်းများကို Database ထဲသို့ 自動 ပြန်လည် အစားထိုး/ပြင်ဆင် ပေးသွားပါမည်။"
    )

# Excel File Handler (Direct Restore from Excel upload)
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

        # Read Excel Sheets
        xls = pd.ExcelFile(temp_path)
        
        conn = get_db()
        cursor = conn.cursor()

        # Update Inventory Sheet
        if 'Inventory' in xls.sheet_names:
            df_inv = pd.read_excel(xls, sheet_name='Inventory')
            cursor.execute("DELETE FROM inventory")  # Clear old data
            for _, row in df_inv.iterrows():
                cursor.execute('''
                    INSERT INTO inventory (id, item_name, quantity, cost_price)
                    VALUES (?, ?, ?, ?)
                ''', (row.get('id'), row['item_name'], row['quantity'], row['cost_price']))

        # Update Sales Sheet
        if 'Sales' in xls.sheet_names:
            df_sales = pd.read_excel(xls, sheet_name='Sales')
            cursor.execute("DELETE FROM sales")  # Clear old data
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
        "🛍️ **အသုံးပြုနိုင်သော Command များ:**\n\n"
        "/buy - ပစ္စည်းဝယ်ယူခြင်း\n"
        "/sell_cash - လက်ငင်းရောင်းခြင်း\n"
        "/sell_installment - အရစ်ကျရောင်းခြင်း\n"
        "/pay - အရစ်ကျငွေဆပ်ခြင်း\n"
        "/stock - Stock စာရင်းကြည့်ရန်\n"
        "/list - အရစ်ကျကျန်သူများကြည့်ရန်\n"
        "/monthly_report - လချုပ်ကြည့်ရန်\n"
        "/export - Excel File ထုတ်ယူရန်\n"
        "/import_excel - Excel မှ ပြန်လည်ပြင်ဆင်/Restore လုပ်ရန်\n"
        "/backup - DB Backup ယူရန်\n"
        "/ping - Status စစ်ရန်"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

# Main Function
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("buy", buy))
    app.add_handler(CommandHandler("sell_cash", sell_cash))
    app.add_handler(CommandHandler("sell_installment", sell_installment))
    app.add_handler(CommandHandler("pay", pay))
    app.add_handler(CommandHandler("stock", stock))
    app.add_handler(CommandHandler("list", list_pending))
    app.add_handler(CommandHandler("monthly_report", monthly_report))
    app.add_handler(CommandHandler("export", export_excel))
    app.add_handler(CommandHandler("import_excel", import_excel_info))
    app.add_handler(CommandHandler("backup", backup))
    app.add_handler(CommandHandler("ping", ping))

    # Excel File Handler
    app.add_handler(MessageHandler(filters.Document.MimeType("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"), handle_excel_upload))

    print("Bot is running...")
    app.run_polling()

if __name__ == '__main__':
    main()
            

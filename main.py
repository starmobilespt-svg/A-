[file-tag: code-generated-file-c8097466-fea4-44e3-9d13-11143b846083]
တောင်းဆိုထားသည့်အတိုင်း **Stock စာရင်းများကို အလိုအလျောက် ပြသပေးသည့် စနစ်**၊ **Delivery ခ ထည့်သွင်းသည့် စနစ်**၊ **လက်ဆောင်ပစ္စည်း ထည့်ပေးသည့် စနစ်**၊ **အသုံးစရိတ် စာရင်း** နှင့် **လူနာမည် ခွဲရေး/နာမည်တူ စစ်ဆေးသည့် စနစ်** များ အားလုံး အပြည့်အစုံ ပါဝင်သော main.py Source Code နှင့် ရှင်းပြချက် ဖြစ်ပါသည်။
### 🌟 အသစ်ပါဝင်လာသော စနစ်များ ရှင်းပြချက်
 1. **ရောင်းသည့်အခါ Stock စာရင်း အလိုအလျောက် ပြသပေးခြင်း:**
   * **💵 လက်ငင်းရောင်းမည်**၊ **⏳ အရစ်ကျရောင်းမည်** သို့မဟုတ် **🎁 လက်ဆောင်ပေးရောင်းမည်** ခလုတ်များကို နှိပ်လိုက်သည်နှင့် လက်ရှိ ဆိုင်ထဲတွင် ရောင်းရန်ကျန်ရှိနေသော **Stock စာရင်းအမည်များနှင့် အရေအတွက်များ** ကို အရင်ဆုံး အဆင်သင့် ပြသပေးပါမည်။
 2. **ပစ္စည်းဝယ်ရာတွင် Delivery ခ ထည့်သွင်းခြင်း (/buy):**
   * ပစ္စည်းဝယ်သည့်အခါ Delivery ခ ပါပါက အောက်ပါအတိုင်း ရိုက်နိုင်ပါသည်။
   * **ပုံစံ:** /buy iPhone 13 | 2 | 1200000 | 5000
   * *(ထည့်လိုက်သော 5,000 MMK Delivery ခကို ဆိုင်အသုံးစရိတ်ထဲသို့ Auto ထည့်ပေးပြီး လချုပ် အမြတ်/အရှုံးတွင် အလိုအလျောက် နှုတ်ပေးသွားပါမည်)*
 3. **လက်ဆောင် (Gift) ပါဝင်သော ရောင်းချမှု (/sell_gift & /sell_installment_gift):**
   * **လက်ငင်းရောင်း ပုံစံ:** /sell_gift AungAung | iPhone 13 | 1500000 | Phone Cover
   * **အရစ်ကျရောင်း ပုံစံ:** /sell_installment_gift MgMg | Phone | 1500000 | 300000 | 100000 | Screen Protector
   * *(ထည့်ပေးလိုက်သော လက်ဆောင်ပစ္စည်းသည် Stock ထဲရှိနေပါက Stock ထဲမှ ၁ ခု Auto လျှော့ပေးသွားပါမည်)*
 4. **ကြွေးဆပ်ရာတွင် နာမည်ခွဲရေးရလွယ်ကူခြင်း နှင့် နာမည်တူစစ်ဆေးခြင်း (/pay):**
   * နာမည်တွင် Space ပါသူများကို | ခံ၍ ရိုက်နိုင်ပါသည်။ (ဥပမာ - /pay Mg Mg | 100000)
   * အကယ်၍ Mg Mg ဆိုသူ ၂ ယောက် သို့မဟုတ် စာရင်း ၂ ခု ဖြစ်နေပါက Bot မှ ဘာမှမလုပ်ဘဲ စာရင်း ID များကို ခွဲခြားပြပေးမည် ဖြစ်ပြီး ID ဖြင့် ပြန်လည် ပေးချေနိုင်ပါမည်။ (ဥပမာ - /pay 1 | 100000)
### 💻 main.py Python Source Code အပြည့်အစုံ
```python
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

    # Migration for gift_item column if not exists
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
    conn.commit()
    conn.close()

init_db()

def get_db():
    return sqlite3.connect(DB_FILE)

# Custom Bottom Keyboard Menu
def get_main_keyboard():
    keyboard = [
        [KeyboardButton("📦 ဝယ်ယူမည်"), KeyboardButton("💵 လက်ငင်းရောင်းမည်")],
        [KeyboardButton("⏳ အရစ်ကျရောင်းမည်"), KeyboardButton("🎁 လက်ဆောင်ပေးရောင်းမည်")],
        [KeyboardButton("💰 ငွေဆပ်မည်"), KeyboardButton("💸 အသုံးစရိတ်ထည့်မည်")],
        [KeyboardButton("📦 ပစ္စည်းဟောင်းထည့်မည်"), KeyboardButton("⏳ အကြွေးဟောင်းထည့်မည်")],
        [KeyboardButton("📊 လက်ကျန် Stock"), KeyboardButton("⏳ ပေးရန်ကျန်သူများ")],
        [KeyboardButton("📈 လချုပ် အရှုံးအမြတ်ကြည့်မည်"), KeyboardButton("🗑️ စာရင်းဖျက်မည်")],
        [KeyboardButton("📁 Excel Backup ယူမည်"), KeyboardButton("📥 Excel Restore လုပ်မည်")],
        [KeyboardButton("💾 DB Backup ယူမည်"), KeyboardButton("📜 Command များကြည့်မည်")]
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
        "🛍️ **အသုံးပြုနိုင်သော Command များ (ထိလိုက်ပါက Copy ရပါသည်):**\n\n"
        "📦 **၁။ ပစ္စည်းဝယ်ယူခြင်း / ထည့်သွင်းခြင်း:**\n"
        "`/buy iPhone 13 | 2 | 1200000` (Delivery ခ မပါပါက)\n"
        "`/buy iPhone 13 | 2 | 1200000 | 5000` (Delivery ခ ပါပါက Auto အသုံးစရိတ်ထဲ ပေါင်းစပ်မည်)\n"
        "`/add_stock iPhone 12 | 5 | 800000` (ပစ္စည်းဟောင်း/Stock ထည့်ရန်)\n\n"
        "💵 **၂။ ရောင်းချခြင်း (လက်ဆောင်ပါဝင်မှု အပါအဝင်):**\n"
        "`/sell_cash AungAung | iPhone 13 | 1500000` (လက်ငင်းရောင်း)\n"
        "`/sell_gift AungAung | iPhone 13 | 1500000 | Cover` (လက်ဆောင်ပါသော လက်ငင်းရောင်း)\n"
        "`/sell_installment MgMg | Phone | 1500000 | 300000 | 100000` (အရစ်ကျ)\n"
        "`/sell_installment_gift MgMg | Phone | 1500000 | 300000 | 100000 | Screen Protector` (လက်ဆောင်ပါ အရစ်ကျ)\n\n"
        "💸 **၃။ ဆိုင်အသုံးစရိတ် ထည့်သွင်းခြင်း:**\n"
        "`/expense မီးဖိုး | 50000`\n\n"
        "⏳ **၄။ အကြွေးဟောင်း ထည့်သွင်းခြင်း:**\n"
        "`/add_credit U Ba | Phone | 500000 | 100000`\n\n"
        "💰 **၅။ အရစ်ကျ ငွေလာဆပ်ခြင်း:**\n"
        "`/pay Mg Mg | 100000` (သို့မဟုတ် `/pay 1 | 100000` ID ဖြင့်)\n\n"
        "📊 **၆။ စာရင်းများ စစ်ဆေးခြင်း:**\n"
        "`/stock` - Stock စာရင်းကြည့်ရန်\n"
        "`/list` - အရစ်ကျကျန်သူများ စာရင်းကြည့်ရန်\n"
        "`/monthly_report 2026-07` - လချုပ် အရှုံးအမြတ်ကြည့်ရန်\n\n"
        "🗑️ **၇။ စာရင်းမှား ဖျက်ခြင်း:**\n"
        "`/delete_sale 1` - အရောင်း ID ဖြင့် စာရင်းတစ်ခုဖျက်ရန်\n"
        "`/delete_item iPhone 13` - Stock ပစ္စည်းတစ်ခုဖျက်ရန်\n"
        "`/reset_all` - စာရင်း အားလုံး ဖျက်ပစ်ရန်\n\n"
        "📁 **၈။ Excel & Backup:**\n"
        "`/export` - Excel File ထုတ်ယူရန်\n"
        "`/backup` - Database Backup ယူရန်"
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
        return "⚠️ **လက်ရှိ ရောင်းရန် Stock ပစ္စည်း လုံးဝ မရှိသေးပါ!** (ကျေးဇူးပြု၍ ပစ္စည်း စာရင်းသွင်းပါ)"

    msg = "📦 **လက်ရှိ ရောင်းရန် ရှိသော Stock မူရင်း ပစ္စည်းများ:**\n"
    for r in rows:
        msg += f"• `{r[0]}` - ကျန် `{r[1]}` ခု\n"
    return msg

# Command 1: /buy (Updated to support optional Delivery Fee)
async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = " ".join(context.args).split("|")
        if len(args) not in [3, 4]:
            await update.message.reply_text(
                "❌ **Standard Format:**\n"
                "• Delivery ခ မပါပါက:\n`/buy <ပစ္စည်းအမည်> | <အရေအတွက်> | <ဝယ်ဈေး>`\n"
                "• Delivery ခ ပါပါက:\n`/buy <ပစ္စည်းအမည်> | <အရေအတွက်> | <ဝယ်ဈေး> | <Deliveryခ>`\n\n"
                "👇 **နှိပ်ပြီး ကူးယူပါ:**\n`/buy iPhone 13 | 2 | 1200000 | 5000`", 
                parse_mode="Markdown"
            )
            return

        item_name = args[0].strip()
        qty = int(args[1].strip())
        cost_price = float(args[2].strip())
        deli_fee = float(args[3].strip()) if len(args) == 4 else 0.0
        today = datetime.date.today().strftime("%Y-%m-%d")

        conn = get_db()
        cursor = conn.cursor()

        # Stock Update/Insert
        cursor.execute("SELECT quantity FROM inventory WHERE item_name = ?", (item_name,))
        row = cursor.fetchone()
        if row:
            cursor.execute("UPDATE inventory SET quantity = ?, cost_price = ? WHERE item_name = ?", (row[0] + qty, cost_price, item_name))
        else:
            cursor.execute("INSERT INTO inventory (item_name, quantity, cost_price) VALUES (?, ?, ?)", (item_name, qty, cost_price))

        # Record Delivery Fee in Expenses if provided
        if deli_fee > 0:
            cursor.execute("INSERT INTO expenses (title, amount, date) VALUES (?, ?, ?)", (f"{item_name} ဝယ်ယူမှု Delivery ခ", deli_fee, today))

        conn.commit()
        conn.close()

        deli_msg = f"\n🚚 Delivery ခ: `{deli_fee:,.0f}` MMK (အသုံးစရိတ်ထဲ ပေါင်းထည့်ပြီး)" if deli_fee > 0 else ""
        await update.message.reply_text(
            f"✅ **ပစ္စည်းဝယ်ယူမှု မှတ်တမ်းတင်ပြီးပါပြီ!**\n\n"
            f"📦 ပစ္စည်း: `{item_name}`\n"
            f"🔢 အရေအတွက်: `{qty}` ခု\n"
            f"💵 ဝယ်ဈေး (တစ်ခု): `{cost_price:,.0f}` MMK{deli_msg}", 
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ အမှားအယွင်းရှိပါသည်: {str(e)}")

# Expense Command (/expense)
async def add_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = " ".join(context.args).split("|")
        if len(args) != 2:
            await update.message.reply_text("❌ **Standard Format:**\n`/expense <အကြောင်းအရာ> | <ပမာဏ>`\n\n👇 **နှိပ်ပြီး ကူးယူပါ:**\n`/expense မီးဖိုး | 50000`", parse_mode="Markdown")
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

# Add Old Stock Command (/add_stock)
async def add_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = " ".join(context.args).split("|")
        if len(args) != 3:
            await update.message.reply_text("❌ **Standard Format:**\n`/add_stock <ပစ္စည်းအမည်> | <အရေအတွက်> | <ဝယ်ဈေး>`\n\n👇 **နှိပ်ပြီး ကူးယူပါ:**\n`/add_stock iPhone 12 | 5 | 800000`", parse_mode="Markdown")
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
        await update.message.reply_text(f"📦 **ပစ္စည်းဟောင်း / Stock ဟောင်း ထည့်သွင်းပြီးပါပြီ!**\n\n📦 ပစ္စည်း: `{item_name}`\n🔢 အရေအတွက်: `{qty}` ခု\n💵 ဝယ်ဈေး: `{cost_price:,.0f}` MMK", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ အမှားအယွင်းရှိပါသည်: {str(e)}")

# Add Old Credit Command (/add_credit)
async def add_credit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = " ".join(context.args).split("|")
        if len(args) != 4:
            await update.message.reply_text("❌ **Standard Format:**\n`/add_credit <ဝယ်သူနာမည်> | <ပစ္စည်းအမည်> | <စုစုပေါင်းအကြွေး> | <တစ်လပေးရမည့်ငွေ>`\n\n👇 **နှိပ်ပြီး ကူးယူပါ:**\n`/add_credit U Ba | Phone | 500000 | 100000`", parse_mode="Markdown")
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
            f"⏳ **ယခင်အကြွေးဟောင်း စာရင်းသွင်းပြီးပါပြီ!**\n\n"
            f"🆔 အရောင်း ID: `{sale_id}`\n"
            f"👤 ဝယ်သူ: `{customer}`\n"
            f"📦 ပစ္စည်း: `{item_name}`\n"
            f"📉 စုစုပေါင်း အကြွေးကျန်: `{total_price:,.0f}` MMK\n"
            f"🗓️ တစ်လပေးရမည်: `{monthly_pay:,.0f}` MMK",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ အမှားအယွင်းရှိပါသည်: {str(e)}")

async def sell_cash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = " ".join(context.args).split("|")
        if len(args) != 3:
            stock_info = get_available_stock_info()
            await update.message.reply_text(
                f"{stock_info}\n\n"
                "❌ **Standard Format:**\n`/sell_cash <ဝယ်သူနာမည်> | <ပစ္စည်းအမည်> | <ရောင်းဈေး>`\n\n"
                "👇 **နှိပ်ပြီး ကူးယူပါ:**\n`/sell_cash AungAung | iPhone 13 | 1500000`", 
                parse_mode="Markdown"
            )
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
        cursor.execute("INSERT INTO sales (customer_name, item_name, sale_type, total_price, paid_amount, monthly_payment, status, date, gift_item) VALUES (?, ?, 'CASH', ?, ?, 0, 'PAID', ?, '')", (customer, item_name, price, price, today))
        sale_id = cursor.lastrowid
        conn.commit()
        conn.close()
        await update.message.reply_text(f"💵 **လက်ငင်း ရောင်းချမှု အောင်မြင်ပါသည်။**\n\n🆔 အရောင်း ID: `{sale_id}`\n👤 ဝယ်သူ: `{customer}`\n📦 ပစ္စည်း: `{item_name}`\n💰 ရောင်းဈေး: `{price:,.0f}` MMK", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ အမှားအယွင်းရှိပါသည်: {str(e)}")

async def sell_gift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = " ".join(context.args).split("|")
        if len(args) != 4:
            stock_info = get_available_stock_info()
            await update.message.reply_text(
                f"{stock_info}\n\n"
                "❌ **Standard Format:**\n`/sell_gift <ဝယ်သူနာမည်> | <ပစ္စည်းအမည်> | <ရောင်းဈေး> | <လက်ဆောင်ပစ္စည်း>`\n\n"
                "👇 **နှိပ်ပြီး ကူးယူပါ:**\n`/sell_gift AungAung | iPhone 13 | 1500000 | Phone Cover`", 
                parse_mode="Markdown"
            )
            return
        customer, item_name, price, gift = args[0].strip(), args[1].strip(), float(args[2].strip()), args[3].strip()
        today = datetime.date.today().strftime("%Y-%m-%d")
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT quantity FROM inventory WHERE item_name = ?", (item_name,))
        row = cursor.fetchone()
        if not row or row[0] < 1:
            await update.message.reply_text("❌ ရောင်းချမည့် ပစ္စည်း လက်ကျန် Stock မလုံလောက်ပါ သို့မဟုတ် ပစ္စည်းရှာမတွေ့ပါ။")
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
        await update.message.reply_text(f"🎁 **လက်ဆောင်ပါဝင်သော လက်ငင်း ရောင်းချမှု အောင်မြင်ပါသည်။**\n\n🆔 အရောင်း ID: `{sale_id}`\n👤 ဝယ်သူ: `{customer}`\n📦 ပစ္စည်း: `{item_name}`\n💰 ရောင်းဈေး: `{price:,.0f}` MMK\n🎁 ထည့်ပေးသော လက်ဆောင်: `{gift}`", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ အမှားအယွင်းရှိပါသည်: {str(e)}")

async def sell_installment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = " ".join(context.args).split("|")
        if len(args) != 5:
            stock_info = get_available_stock_info()
            await update.message.reply_text(
                f"{stock_info}\n\n"
                "❌ **Standard Format:**\n`/sell_installment <ဝယ်သူနာမည်> | <ပစ္စည်းအမည်> | <စုစုပေါင်းရောင်းဈေး> | <စပေါ်ငွေ> | <တစ်လ ပုံမှန်ပေးရမည့်ငွေ>`\n\n"
                "👇 **နှိပ်ပြီး ကူးယူပါ:**\n`/sell_installment MgMg | Phone | 1500000 | 300000 | 100000`", 
                parse_mode="Markdown"
            )
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
        cursor.execute("INSERT INTO sales (customer_name, item_name, sale_type, total_price, paid_amount, monthly_payment, status, date, gift_item) VALUES (?, ?, 'INSTALLMENT', ?, ?, ?, ?, ?, '')", (customer, item_name, total_price, down_payment, monthly_pay, status, today))
        sale_id = cursor.lastrowid
        conn.commit()
        conn.close()
        await update.message.reply_text(f"⏳ **အရစ်ကျ ရောင်းချမှု မှတ်တမ်းဝင်သွားပါပြီ!**\n\n🆔 အရောင်း ID: `{sale_id}`\n👤 ဝယ်သူ: `{customer}`\n📦 ပစ္စည်း: `{item_name}`\n💰 စုစုပေါင်း: `{total_price:,.0f}` MMK\n💵 စပေါ်ငွေ: `{down_payment:,.0f}` MMK\n📉 ကျန်ငွေ: `{total_price - down_payment:,.0f}` MMK\n🗓️ တစ်လပေးရမည်: `{monthly_pay:,.0f}` MMK", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ အမှားအယွင်းရှိပါသည်: {str(e)}")

async def sell_installment_gift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = " ".join(context.args).split("|")
        if len(args) != 6:
            stock_info = get_available_stock_info()
            await update.message.reply_text(
                f"{stock_info}\n\n"
                "❌ **Standard Format:**\n`/sell_installment_gift <ဝယ်သူနာမည်> | <ပစ္စည်းအမည်> | <စုစုပေါင်းရောင်းဈေး> | <စပေါ်ငွေ> | <တစ်လ ပုံမှန်ပေးရမည့်ငွေ> | <လက်ဆောင်ပစ္စည်း>`\n\n"
                "👇 **နှိပ်ပြီး ကူးယူပါ:**\n`/sell_installment_gift MgMg | Phone | 1500000 | 300000 | 100000 | Screen Protector`", 
                parse_mode="Markdown"
            )
            return
        customer, item_name, total_price, down_payment, monthly_pay, gift = args[0].strip(), args[1].strip(), float(args[2].strip()), float(args[3].strip()), float(args[4].strip()), args[5].strip()
        today = datetime.date.today().strftime("%Y-%m-%d")
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT quantity FROM inventory WHERE item_name = ?", (item_name,))
        row = cursor.fetchone()
        if not row or row[0] < 1:
            await update.message.reply_text("❌ ရောင်းချမည့် ပစ္စည်း လက်ကျန် Stock မလုံလောက်ပါ သို့မဟုတ် ပစ္စည်းရှာမတွေ့ပါ။")
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
        await update.message.reply_text(f"⏳ **လက်ဆောင်ပါသော အရစ်ကျ ရောင်းချမှု မှတ်တမ်းဝင်သွားပါပြီ!**\n\n🆔 အရောင်း ID: `{sale_id}`\n👤 ဝယ်သူ: `{customer}`\n📦 ပစ္စည်း: `{item_name}`\n💰 စုစုပေါင်း: `{total_price:,.0f}` MMK\n💵 စပေါ်ငွေ: `{down_payment:,.0f}` MMK\n📉 ကျန်ငွေ: `{total_price - down_payment:,.0f}` MMK\n🗓️ တစ်လပေးရမည်: `{monthly_pay:,.0f}` MMK\n🎁 ထည့်ပေးသော လက်ဆောင်: `{gift}`", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ အမှားအယွင်းရှိပါသည်: {str(e)}")

async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        raw_input = " ".join(context.args).strip()
        if not raw_input:
            await update.message.reply_text("❌ **Standard Format:**\n`/pay <ဝယ်သူနာမည် သို့မဟုတ် ID> | <ပေးသည့်ပမာဏ>`\n\n👇 **နှိပ်ပြီး ကူးယူပါ:**\n`/pay Mg Mg | 100000`", parse_mode="Markdown")
            return

        if "|" in raw_input:
            parts = raw_input.split("|")
            target_str = parts[0].strip()
            amount_str = parts[1].strip()
        else:
            parts = raw_input.rsplit(" ", 1)
            if len(parts) != 2:
                await update.message.reply_text("❌ **Standard Format:**\n`/pay <ဝယ်သူနာမည်> | <ပေးသည့်ပမာဏ>`\n\n👇 **နှိပ်ပြီး ကူးယူပါ:**\n`/pay Mg Mg | 100000`", parse_mode="Markdown")
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
            await update.message.reply_text(f"❌ `{target_str}` အတွက် အရစ်ကျ ပေးရန်ကျန်သော စာရင်း ရှာမတွေ့ပါ။", parse_mode="Markdown")
            conn.close()
            return

        if len(rows) > 1:
            msg = f"⚠️ **'{target_str}' အမည်ဖြင့် အကြွေးကျန် စာရင်း ({len(rows)}) ခု တွေ့ရှိနေပါသည်။**\n\n"
            msg += "ဘယ်စာရင်းအတွက် ငွေဆပ်မည်နည်း? အောက်ပါ ID ဖြင့် ပြန်ပေးချေပါ:\n\n"
            for r in rows:
                rem = r[3] - r[4]
                gift_info = f" (🎁 {r[5]})" if r[5] else ""
                msg += f"🆔 ID: `{r[0]}` | 👤 **{r[1]}** ({r[2]}{gift_info})\n  ကျန်ငွေ: `{rem:,.0f}` MMK\n👉 `/pay {r[0]} | {amount:,.0f}`\n\n"
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
        rem_str = "0 (ပေးချေမှု ပြီးဆုံးပါပြီ)" if rem <= 0 else f"{rem:,.0f} MMK"
        gift_str = f"\n🎁 လက်ဆောင်ပါရှိခဲ့သူ: `{gift_item}`" if gift_item else ""

        await update.message.reply_text(
            f"💰 **ငွေဆပ်မှု အဆင်ပြေပါသည်။**\n\n"
            f"🆔 အရောင်း ID: `{sale_id}`\n"
            f"👤 ဝယ်သူ: `{customer_name}`\n"
            f"📦 ပစ္စည်း: `{item_name}`{gift_str}\n"
            f"💵 ပေးသွင်းငွေ: `{amount:,.0f}` MMK\n"
            f"📊 ပေးပြီး စုစုပေါင်း: `{new_paid:,.0f}` / `{total_price:,.0f}` MMK\n"
            f"📉 ပေးရန်ကျန်ငွေ: `{rem_str}`",
            parse_mode="Markdown"
        )
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
    cursor.execute("SELECT id, customer_name, item_name, total_price, paid_amount, monthly_payment, gift_item FROM sales WHERE status = 'PENDING'")
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        await update.message.reply_text("🎉 အရစ်ကျ ကျန်ရှိသူ စာရင်း မရှိပါ။")
        return
    msg = "⏳ **အရစ်ကျ ပေးရန်ကျန်သူများ စာရင်း:**\n\n"
    for r in rows:
        gift_info = f" | 🎁 `{r[6]}`" if r[6] else ""
        msg += f"🆔 ID: `{r[0]}` | 👤 **{r[1]}** ({r[2]}{gift_info})\n  ကျန်ငွေ: `{r[3] - r[4]:,.0f}` / `{r[3]:,.0f}` MMK (၁ လပေး: `{r[5]:,.0f}` MMK)\n\n"
    msg += "💡 *စာရင်းမှား၍ ဖျက်လိုပါက:* `/delete_sale <ID>`"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def monthly_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        year_month = context.args[0].strip() if context.args else datetime.date.today().strftime("%Y-%m")
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT s.item_name, s.total_price, s.paid_amount, COALESCE(i.cost_price, 0)
            FROM sales s
            LEFT JOIN inventory i ON s.item_name = i.item_name
            WHERE strftime('%Y-%m', s.date) = ?
        ''', (year_month,))
        sales_rows = cursor.fetchall()

        cursor.execute('''
            SELECT SUM(amount) FROM expenses WHERE strftime('%Y-%m', date) = ?
        ''', (year_month,))
        expense_row = cursor.fetchone()
        total_expense = expense_row[0] if expense_row[0] else 0.0

        conn.close()

        if not sales_rows and total_expense == 0:
            await update.message.reply_text(f"📅 **{year_month}** လအတွက် စာရင်း မရှိသေးပါ။", parse_mode="Markdown")
            return

        total_sales_value = sum(r[1] for r in sales_rows)
        total_collected_cash = sum(r[2] for r in sales_rows)
        total_cost = sum(r[3] for r in sales_rows)

        net_profit = total_sales_value - total_cost - total_expense
        cash_profit = total_collected_cash - total_cost - total_expense

        profit_status = "🟢 အမြတ်" if net_profit >= 0 else "🔴 အရှုံး"

        msg = f"📊 **{year_month} လချုပ် အရှုံးအမြတ် စာရင်း**\n\n"
        msg += f"🛒 စုစုပေါင်း အရောင်းပမာဏ: `{total_sales_value:,.0f}` MMK\n"
        msg += f"💵 လက်ဝယ် ရရှိပြီးငွေ: `{total_collected_cash:,.0f}` MMK\n"
        msg += f"📉 ပေးရန်ကျန် အရစ်ကျငွေ: `{(total_sales_value - total_collected_cash):,.0f}` MMK\n"
        msg += f"📦 ရောင်းရ ပစ္စည်းဝယ်ရင်းစရိတ်: `{total_cost:,.0f}` MMK\n"
        msg += f"💸 ဆိုင်အသုံးစရိတ် စုစုပေါင်း: `{total_expense:,.0f}` MMK\n"
        msg += "───────────────────\n"
        msg += f"{profit_status} (ခန့်မှန်း အသားတင်): `{abs(net_profit):,.0f}` MMK\n"
        msg += f"💡 လက်ရှိ လက်ဝယ် အမြတ်/အရှုံး: `{cash_profit:,.0f}` MMK"

        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ အမှားအယွင်းရှိပါသည်: {str(e)}")

async def delete_sale(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args:
            await update.message.reply_text("❌ **Standard Format:**\n`/delete_sale <ID>`\n\n💡 စာရင်း ID များ သိရှိလိုပါက **`⏳ ပေးရန်ကျန်သူများ`** ခလုတ်ကို နှိပ်ပြီး ကြည့်နိုင်ပါသည်။", parse_mode="Markdown")
            return
        sale_id = int(context.args[0].strip())
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT customer_name, item_name, total_price, paid_amount FROM sales WHERE id = ?", (sale_id,))
        row = cursor.fetchone()
        if not row:
            await update.message.reply_text(f"❌ ID `{sale_id}` ဖြင့် အရောင်းစာရင်း ရှာမတွေ့ပါ။", parse_mode="Markdown")
            conn.close()
            return
        cursor.execute("DELETE FROM sales WHERE id = ?", (sale_id,))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"🗑️ ID `{sale_id}` ({row[0]} - {row[1]} / ကျန်ငွေ: {row[2]-row[3]:,.0f} MMK) စာရင်းကို ဖျက်လိုက်ပါပြီ။", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ အမှားအယွင်းရှိပါသည်: {str(e)}")

async def delete_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args:
            await update.message.reply_text("❌ **Standard Format:**\n`/delete_item <ပစ္စည်းအမည်>`\n\n👇 **နှိပ်ပြီး ကူးယူပါ:**\n`/delete_item iPhone 13`", parse_mode="Markdown")
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

async def reset_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[
        InlineKeyboardButton("✅ အကုန်ဖျက်မည် (Confirm)", callback_data="confirm_reset_all"),
        InlineKeyboardButton("❌ မဖျက်တော့ပါ (Cancel)", callback_data="cancel_reset_all")
    ]]
    await update.message.reply_text("⚠️ **သတိပေးချက်:** စာရင်းအားလုံး ဖျက်ပစ်ပါမည်။ ဧကန်မုချ ဖျက်လိုပါသလား?", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def reset_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "confirm_reset_all":
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM inventory")
        cursor.execute("DELETE FROM sales")
        cursor.execute("DELETE FROM expenses")
        conn.commit()
        conn.close()
        await query.message.edit_text("💥 **စာရင်း အားလုံးကို အောင်မြင်စွာ ဖျက်ပစ်ပြီးပါပြီ!**", parse_mode="Markdown")
    elif query.data == "cancel_reset_all":
        await query.message.edit_text("❌ စာရင်းဖျက်ခြင်းကို ပယ်ဖျက်လိုက်ပါပြီ။")

async def export_excel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        conn = get_db()
        df_inventory = pd.read_sql_query("SELECT * FROM inventory", conn)
        df_sales = pd.read_sql_query("SELECT * FROM sales", conn)
        df_expenses = pd.read_sql_query("SELECT * FROM expenses", conn)
        conn.close()
        file_path = "Shop_Data_Export.xlsx"
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            df_inventory.to_excel(writer, sheet_name='Inventory', index=False)
            df_sales.to_excel(writer, sheet_name='Sales', index=False)
            df_expenses.to_excel(writer, sheet_name='Expenses', index=False)
        await update.message.reply_document(
            document=open(file_path, 'rb'), 
            filename=file_path,
            caption="📊 **Excel File စာရင်းများ ထုတ်ယူပြီးပါပြီ!**"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Excel export မလုပ်နိုင်ပါ: {str(e)}")

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
                cursor.execute('INSERT INTO inventory (id, item_name, quantity, cost_price) VALUES (?, ?, ?, ?)', (row.get('id'), row['item_name'], row['quantity'], row['cost_price']))

        if 'Sales' in xls.sheet_names:
            df_sales = pd.read_excel(xls, sheet_name='Sales')
            cursor.execute("DELETE FROM sales")
            for _, row in df_sales.iterrows():
                gift_val = str(row.get('gift_item', '')) if pd.notna(row.get('gift_item')) else ''
                cursor.execute('INSERT INTO sales (id, customer_name, item_name, sale_type, total_price, paid_amount, monthly_payment, status, date, gift_item) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', (
                    row.get('id'), row['customer_name'], row['item_name'], row['sale_type'],
                    row['total_price'], row['paid_amount'], row['monthly_payment'],
                    row['status'], str(row['date']), gift_val
                ))

        if 'Expenses' in xls.sheet_names:
            df_exp = pd.read_excel(xls, sheet_name='Expenses')
            cursor.execute("DELETE FROM expenses")
            for _, row in df_exp.iterrows():
                cursor.execute('INSERT INTO expenses (id, title, amount, date) VALUES (?, ?, ?, ?)', (
                    row.get('id'), row['title'], row['amount'], str(row['date'])
                ))

        conn.commit()
        conn.close()

        if os.path.exists(temp_path):
            os.remove(temp_path)

        await status_msg.edit_text("✅ **Excel File မှ စာရင်းများကို Database သို့ အောင်မြင်စွာ Restore / Recover လုပ်ပြီးပါပြီ!**")
    except Exception as e:
        await status_msg.edit_text(f"❌ Excel မှ စာရင်းသွင်းရာတွင် အမှားဖြစ်ပေါ်ပါသည်: {str(e)}")

async def backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_document(document=open(DB_FILE, 'rb'), filename="database_backup.db", caption="📁 **Database Backup File ရရှိပါပြီ!**")
    except Exception as e:
        await update.message.reply_text(f"❌ Backup မထုတ်ယူနိုင်ပါ: {str(e)}")

async def handle_button_clicks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "📦 ဝယ်ယူမည်":
        await update.message.reply_text("📦 **ဝယ်ယူမှု စာရင်းသွင်းရန်:**\n\n• Delivery ခ မပါပါက:\n`/buy <ပစ္စည်းအမည်> | <အရေအတွက်> | <ဝယ်ဈေး>`\n👇 `/buy iPhone 13 | 2 | 1200000`\n\n• Delivery ခ ပါပါက:\n`/buy <ပစ္စည်းအမည်> | <အရေအတွက်> | <ဝယ်ဈေး> | <Deliveryခ>`\n👇 `/buy iPhone 13 | 2 | 1200000 | 5000`", parse_mode="Markdown")
    elif text == "💵 လက်ငင်းရောင်းမည်":
        stock_info = get_available_stock_info()
        await update.message.reply_text(
            f"{stock_info}\n\n"
            "💵 **လက်ငင်း ရောင်းချရန်:**\n`/sell_cash <ဝယ်သူနာမည်> | <ပစ္စည်းအမည်> | <ရောင်းဈေး>`\n\n"
            "👇 **နှိပ်ပြီး ကူးယူပါ:**\n`/sell_cash AungAung | iPhone 13 | 1500000`", 
            parse_mode="Markdown"
        )
    elif text == "🎁 လက်ဆောင်ပေးရောင်းမည်":
        stock_info = get_available_stock_info()
        await update.message.reply_text(
            f"{stock_info}\n\n"
            "🎁 **လက်ဆောင်ပါဝင်သော ရောင်းချမှု ပုံစံများ:**\n\n"
            "၁။ **လက်ငင်းရောင်းချပါက:**\n`/sell_gift <ဝယ်သူနာမည်> | <ပစ္စည်းအမည်> | <ရောင်းဈေး> | <လက်ဆောင်ပစ္စည်း>`\n👇 `/sell_gift AungAung | iPhone 13 | 1500000 | Phone Cover`\n\n"
            "၂။ **အရစ်ကျရောင်းချပါက:**\n`/sell_installment_gift <ဝယ်သူနာမည်> | <ပစ္စည်းအမည်> | <စုစုပေါင်းရောင်းဈေး> | <စပေါ်ငွေ> | <တစ်လပေးရမည့်ငွေ> | <လက်ဆောင်ပစ္စည်း>`\n👇 `/sell_installment_gift MgMg | Phone | 1500000 | 300000 | 100000 | Screen Protector`", 
            parse_mode="Markdown"
        )
    elif text == "⏳ အရစ်ကျရောင်းမည်":
        stock_info = get_available_stock_info()
        await update.message.reply_text(
            f"{stock_info}\n\n"
            "⏳ **အရစ်ကျ ရောင်းချရန်:**\n`/sell_installment <ဝယ်သူနာမည်> | <ပစ္စည်းအမည်> | <စုစုပေါင်းရောင်းဈေး> | <စပေါ်ငွေ> | <တစ်လ ပုံမှန်ပေးရမည့်ငွေ>`\n\n"
            "👇 **နှိပ်ပြီး ကူးယူပါ:**\n`/sell_installment MgMg | Phone | 1500000 | 300000 | 100000`", 
            parse_mode="Markdown"
        )
    elif text == "💰 ငွေဆပ်မည်":
        await update.message.reply_text("💰 **အရစ်ကျ ငွေလာဆပ်ရန်:**\n`/pay <ဝယ်သူနာမည်> | <ပေးသည့်ပမာဏ>`\n\n👇 **နှိပ်ပြီး ကူးယူပါ:**\n`/pay Mg Mg | 100000`", parse_mode="Markdown")
    elif text == "💸 အသုံးစရိတ်ထည့်မည်":
        await update.message.reply_text("💸 **ဆိုင်အသုံးစရိတ် စာရင်းသွင်းရန်:**\n`/expense <အကြောင်းအရာ> | <ပမာဏ>`\n\n👇 **နှိပ်ပြီး ကူးယူပါ:**\n`/expense မီးဖိုး | 50000`", parse_mode="Markdown")
    elif text == "📦 ပစ္စည်းဟောင်းထည့်မည်":
        await update.message.reply_text("📦 **ပစ္စည်းဟောင်း/Stock ဟောင်း ထည့်ရန်:**\n`/add_stock <ပစ္စည်းအမည်> | <အရေအတွက်> | <ဝယ်ဈေး>`\n\n👇 **နှိပ်ပြီး ကူးယူပါ:**\n`/add_stock iPhone 12 | 5 | 800000`", parse_mode="Markdown")
    elif text == "⏳ အကြွေးဟောင်းထည့်မည်":
        await update.message.reply_text("⏳ **အကြွေးဟောင်း ထည့်ရန်:**\n`/add_credit <ဝယ်သူနာမည်> | <ပစ္စည်းအမည်> | <စုစုပေါင်းအကြွေး> | <တစ်လပေးရမည့်ငွေ>`\n\n👇 **နှိပ်ပြီး ကူးယူပါ:**\n`/add_credit U Ba | Phone | 500000 | 100000`", parse_mode="Markdown")
    elif text == "📊 လက်ကျန် Stock":
        await stock(update, context)
    elif text == "⏳ ပေးရန်ကျန်သူများ":
        await list_pending(update, context)
    elif text in ["📈 လချုပ် အရှုံးအမြတ်ကြည့်မည်", "📈 လချုပ်ကြည့်မည်"]:
        await monthly_report(update, context)
    elif text == "🗑️ စာရင်းဖျက်မည်":
        await update.message.reply_text("🗑️ **စာရင်းမှား ဖျက်လိုပါက:**\n• အရောင်းစာရင်းဖျက်ရန်: `/delete_sale <ID>`\n• Stock ပစ္စည်းဖျက်ရန်: `/delete_item <ပစ္စည်းအမည်>`\n• စာရင်းအားလုံးဖျက်ရန်: `/reset_all`", parse_mode="Markdown")
    elif text in ["📁 Excel Backup ယူမည်", "📁 Excel ထုတ်မည်"]:
        await export_excel(update, context)
    elif text == "📥 Excel Restore လုပ်မည်":
        await update.message.reply_text(
            "📥 **Excel စာရင်းများ ပြန်လည် Restore လုပ်ရန်:**\n\n"
            "၁။ `📁 Excel Backup ယူမည်` ဖြင့် ရလာသော Excel ဖိုင်ကို မိမိစိတ်ကြိုက် ပြင်ဆင်ပါ။\n"
            "၂။ ပြင်ဆင်ပြီးသွားသော Excel ဖိုင် (`.xlsx`) ကို ဒီ Chat ထဲသို့ File အနေဖြင့် Send/Upload ပြုလုပ်ပေးလိုက်ပါ။\n"
            "၃။ Bot မှ အလိုအလျောက် ဖတ်ရှုပြီး စာရင်းများကို Update / Restore လုပ်ပေးသွားပါမည်။"
        )
    elif text in ["💾 DB Backup ယူမည်", "💾 Backup ယူမည်"]:
        await backup(update, context)
    elif text in ["📜 Command များကြည့်မည်", "command", "/command"]:
        await show_commands(update, context)

def main():
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=auto_ping, daemon=True).start()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("command", show_commands))
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
    app.add_handler(CommandHandler("monthly_report", monthly_report))
    app.add_handler(CommandHandler("delete_sale", delete_sale))
    app.add_handler(CommandHandler("delete_item", delete_item))
    app.add_handler(CommandHandler("reset_all", reset_all))
    app.add_handler(CommandHandler("export", export_excel))
    app.add_handler(CommandHandler("backup", backup))

    app.add_handler(CallbackQueryHandler(reset_callback_handler))
    app.add_handler(MessageHandler(filters.Document.MimeType("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"), handle_excel_upload))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_button_clicks))

    print("Bot is running...")
    app.run_polling()

if __name__ == '__main__':
    main()

```

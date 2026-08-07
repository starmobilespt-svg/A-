import sqlite3
import pandas as pd
import os
import threading
import time
import requests
from flask import Flask
from datetime import datetime, timezone, timedelta
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
BOT_TOKEN = "8939067464:AAHVrArTZKEt5nwRlhvyhgRPNIRuzRjR2gA"
DB_FILE = "shop_management.db"

# 🇲🇲 မြန်မာစံတော်ချိန် (UTC +6:30) သတ်မှတ်ခြင်း
MM_TZ = timezone(timedelta(hours=6, minutes=30))

# ====================================================
# 🌐 Auto Ping (Bot အိပ်မသွားစေရန်)
# ====================================================
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Bot is running 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

def auto_ping():
    while True:
        time.sleep(14 * 60)
        render_url = os.environ.get("RENDER_EXTERNAL_URL")
        if render_url:
            try:
                requests.get(render_url)
            except Exception:
                pass

# ====================================================
# 📦 Multi-User Database Setup
# ====================================================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS inventory (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, item_name TEXT, quantity INTEGER, cost_price REAL, UNIQUE(user_id, item_name))''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS sales (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, customer_name TEXT, item_name TEXT, sale_type TEXT, total_price REAL, paid_amount REAL, monthly_payment REAL, status TEXT, date TEXT, gift_item TEXT DEFAULT '')''')
    
    cursor.execute("PRAGMA table_info(sales)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'gift_item' not in columns:
        cursor.execute("ALTER TABLE sales ADD COLUMN gift_item TEXT DEFAULT ''")
    if 'last_payment_date' not in columns:
        cursor.execute("ALTER TABLE sales ADD COLUMN last_payment_date TEXT DEFAULT ''")
    
    # 📱 ဖုန်းနံပါတ်အတွက် Column အသစ်ထည့်ခြင်း
    if 'phone_number' not in columns:
        cursor.execute("ALTER TABLE sales ADD COLUMN phone_number TEXT DEFAULT ''")

    cursor.execute('''CREATE TABLE IF NOT EXISTS expenses (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, title TEXT, amount REAL, date TEXT)''')
    
    cursor.execute("PRAGMA table_info(expenses)")
    exp_columns = [column[1] for column in cursor.fetchall()]
    if 'category' not in exp_columns:
        cursor.execute("ALTER TABLE expenses ADD COLUMN category TEXT DEFAULT 'အထွေထွေ'")

    cursor.execute('''CREATE TABLE IF NOT EXISTS capital (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL, date TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS purchases (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, item_name TEXT, quantity INTEGER, total_cost REAL, date TEXT)''')

    conn.commit()
    conn.close()

init_db()

def get_db():
    return sqlite3.connect(DB_FILE)

# ====================================================
# 🎛️ Keyboard Menu (အကြွေးဆုံး ခလုတ် အသစ်ပါဝင်သည်)
# ====================================================
def get_main_keyboard():
    keyboard = [
        [KeyboardButton("📦 ဝယ်ယူမည်"), KeyboardButton("💸 အသုံးစရိတ်")],
        [KeyboardButton("💵 လက်ငင်းရောင်း"), KeyboardButton("⏳ ကြွေးရောင်း")],
        [KeyboardButton("📊 လက်ကျန် Stock"), KeyboardButton("⏳ ကြွေးကျန်သူများ")],
        [KeyboardButton("🔍 ဝယ်သူရှာရန်"), KeyboardButton("💰 ငွေဆပ်မည်")],
        [KeyboardButton("❌ အကြွေးဆုံး"), KeyboardButton("📈 လချုပ်/နှစ်ချုပ်")],
        [KeyboardButton("📁 Excel Backup"), KeyboardButton("📥 Excel Restore")],
        [KeyboardButton("💵 ငွေလက်ကျန်"), KeyboardButton("⏳ ကြွေးလက်ကျန်")],
        [KeyboardButton("📦 Stock အဟောင်း"), KeyboardButton("🗑️/✏️ ဖျက်/ပြင်")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ====================================================
# 🚀 Commands & Handlers
# ====================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("မင်္ဂလာပါ! သင်၏ ကိုယ်ပိုင် စာရင်းကိုင် Bot မှ ကြိုဆိုပါသည်။", reply_markup=get_main_keyboard())

async def show_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🛍️ **အသုံးပြုနိုင်သော Command များ:**\n\n"
        "📦 **၁။ ပစ္စည်းဝယ်ယူခြင်း:**\n`/buy iPhone 13 | 2 | 1200000 | 3000` (Delivery ခ မပါလျှင် နောက်ဆုံးက 3000 ကို ချန်ထားခဲ့ပါ)\n\n"
        "💵 **၂။ ရောင်းချခြင်း:**\n`/sell_cash AungAung | iPhone 13 | 1500000 | 091234567 | -`\n`/sell_installment MgMg | Phone | 1500000 | 300000 | 100000 | - | Cover`\n\n"
        "💰 **၃။ ငွေဆပ်ခြင်း / ငွေသွင်းမှားပါက ပြန်နှုတ်ခြင်း:**\n`/pay 10 | 100000`\n`/undo_pay 10 | 50000`\n\n"
        "❌ **၄။ အကြွေးဆုံး သတ်မှတ်ခြင်း:**\n`/bad_debt 10` (ID 10 အား အကြွေးဆုံးပြောင်းရန်)\n`/undo_bad_debt 10` (ပုံမှန်အကြွေးသို့ ပြန်ပြောင်းရန်)\n\n"
        "💸 **၅။ အသုံးစရိတ်စာရင်း:**\n`/expense မီးလင်းခ | ဇူလိုင်အတွက် | 15000`\n\n"
        "🔍 **၆။ ဝယ်သူအမည်ဖြင့် ရှာရန်:**\n`/search Mg Mg`\n\n"
        "⏳ **၇။ ယခင်စာရင်းဟောင်းများ:**\n`/add_stock iPhone | 5 | 800000`\n`/add_credit U Ba | Phone | 500000 | 100000 | 098765432`\n\n"
        "📊 **၈။ စာရင်းများ စစ်ဆေးခြင်း:**\n`/stock`, `/list`, `/report`"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

def get_available_stock_info(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT item_name, quantity FROM inventory WHERE user_id = ? AND quantity > 0", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    if not rows: return "⚠️ **လက်ရှိ ရောင်းရန် Stock ပစ္စည်း လုံးဝ မရှိသေးပါ!**"
    msg = "📦 **လက်ရှိ ရောင်းရန် ရှိသော Stock ပစ္စည်းများ:**\n"
    for r in rows: msg += f"• `{r[0]}` - ကျန် `{r[1]}` ခု\n"
    return msg

async def add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    try:
        amount = float(context.args[0].strip())
        if amount < 0:
            return await update.message.reply_text("❌ ဂဏန်းများသည် အပေါင်းလက္ခဏာ (Positive) သာ ဖြစ်ရပါမည်။")
        
        today = datetime.now(MM_TZ).strftime("%Y-%m-%d")
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO capital (user_id, amount, date) VALUES (?, ?, ?)", (user_id, amount, today))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"💵 **ငွေလက်ကျန် ထည့်သွင်းပြီးပါပြီ!**\n💰 ပမာဏ: `{amount:,.0f}` MMK", parse_mode="Markdown")
    except Exception:
        await update.message.reply_text("❌ `/add_balance <ပမာဏ>` ဟုသာ ရိုက်ပါ။")

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    try:
        args = " ".join(context.args).split("|")
        item_name = args[0].strip()
        qty = int(args[1].strip())
        cost_price = float(args[2].strip())
        deli_fee = float(args[3].strip()) if len(args) == 4 else 0.0
        
        if qty <= 0 or cost_price < 0 or deli_fee < 0:
            return await update.message.reply_text("❌ အရေအတွက်နှင့် ဈေးနှုန်းများသည် အပေါင်းလက္ခဏာသာ ဖြစ်ရပါမည်။")

        today = datetime.now(MM_TZ).strftime("%Y-%m-%d")
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, item_name))
        row = cursor.fetchone()
        if row:
            cursor.execute("UPDATE inventory SET quantity = ?, cost_price = ? WHERE user_id = ? AND item_name = ?", (row[0] + qty, cost_price, user_id, item_name))
        else:
            cursor.execute("INSERT INTO inventory (user_id, item_name, quantity, cost_price) VALUES (?, ?, ?, ?)", (user_id, item_name, qty, cost_price))
            
        cursor.execute("INSERT INTO purchases (user_id, item_name, quantity, total_cost, date) VALUES (?, ?, ?, ?, ?)", (user_id, item_name, qty, qty * cost_price, today))
        
        if deli_fee > 0:
            cursor.execute("INSERT INTO expenses (user_id, category, title, amount, date) VALUES (?, ?, ?, ?, ?)", (user_id, "ပို့ဆောင်ခ (Deli)", f"{item_name} ဝယ်ယူမှု Delivery", deli_fee, today))
            
        conn.commit()
        conn.close()
        
        deli_msg = f"\n🚚 Delivery ခ: `{deli_fee:,.0f}` MMK" if deli_fee > 0 else ""
        await update.message.reply_text(f"✅ **ပစ္စည်းဝယ်ယူမှု မှတ်တမ်းတင်ပြီးပါပြီ!**\n\n📦 ပစ္စည်း: `{item_name}`\n🔢 အရေအတွက်: `{qty}` ခု\n💵 ဝယ်ဈေး (တစ်ခု): `{cost_price:,.0f}` MMK{deli_msg}", parse_mode="Markdown")
    except Exception:
        await update.message.reply_text("❌ မှားယွင်းနေပါသည်။\nပုံစံ: `/buy <ပစ္စည်း> | <အရေအတွက်> | <ဝယ်ဈေး> | <Deliveryခ (Optional)>`\n\n👇 ဥပမာ\n`/buy iPhone | 5 | 100000 | 3000`\n(သို့မဟုတ်)\n`/buy iPhone | 5 | 100000`", parse_mode="Markdown")

async def add_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    try:
        args = " ".join(context.args).split("|")
        if len(args) == 3:
            category, title, amount = args[0].strip(), args[1].strip(), float(args[2].strip())
        elif len(args) == 2:
            category, title, amount = "အထွေထွေ", args[0].strip(), float(args[1].strip())
        else:
            raise ValueError

        if amount < 0:
            return await update.message.reply_text("❌ အသုံးစရိတ်ပမာဏသည် အပေါင်းလက္ခဏာသာ ဖြစ်ရပါမည်။")

        today = datetime.now(MM_TZ).strftime("%Y-%m-%d")
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO expenses (user_id, category, title, amount, date) VALUES (?, ?, ?, ?, ?)", (user_id, category, title, amount, today))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"💸 **ဆိုင်အသုံးစရိတ် စာရင်းသွင်းပြီးပါပြီ!**\n📂 အမျိုးအစား: `{category}`\n📝 အကြောင်းအရာ: `{title}`\n💰 ကျသင့်ငွေ: `{amount:,.0f}` MMK", parse_mode="Markdown")
    except Exception:
        await update.message.reply_text("❌ မှားယွင်းနေပါသည်။\nပုံစံ - `/expense <အမျိုးအစား> | <အကြောင်းအရာ> | <ပမာဏ>`\nဥပမာ - `/expense မီးလင်းခ | ဇူလိုင်လအတွက် | 15000`")

async def add_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    try:
        args = " ".join(context.args).split("|")
        item_name, qty, cost_price = args[0].strip(), int(args[1].strip()), float(args[2].strip())
        if qty <= 0 or cost_price < 0:
            return await update.message.reply_text("❌ အရေအတွက်နှင့် ဈေးနှုန်းသည် မှန်ကန်ရပါမည်။")

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, item_name))
        row = cursor.fetchone()
        if row: cursor.execute("UPDATE inventory SET quantity = ?, cost_price = ? WHERE user_id = ? AND item_name = ?", (row[0] + qty, cost_price, user_id, item_name))
        else: cursor.execute("INSERT INTO inventory (user_id, item_name, quantity, cost_price) VALUES (?, ?, ?, ?)", (user_id, item_name, qty, cost_price))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"📦 **Stock လက်ကျန် ထည့်သွင်းပြီးပါပြီ!**\n📦 ပစ္စည်း: `{item_name}`\n🔢 အရေအတွက်: `{qty}` ခု", parse_mode="Markdown")
    except Exception:
        await update.message.reply_text("❌ `/add_stock <ပစ္စည်းအမည်> | <အရေအတွက်> | <ဝယ်ဈေး>` ဟုသာ ရိုက်ပါ။")

async def add_credit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    try:
        args = " ".join(context.args).split("|")
        customer, item_name, total_price, monthly_pay = args[0].strip(), args[1].strip(), float(args[2].strip()), float(args[3].strip())
        phone = args[4].strip() if len(args) > 4 else ""
        if phone == '-': phone = ""

        if total_price < 0 or monthly_pay < 0:
            return await update.message.reply_text("❌ ငွေပမာဏသည် အပေါင်းလက္ခဏာသာ ဖြစ်ရပါမည်။")

        today = datetime.now(MM_TZ).strftime("%Y-%m-%d")
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO sales (user_id, customer_name, item_name, sale_type, total_price, paid_amount, monthly_payment, status, date, gift_item, phone_number) VALUES (?, ?, ?, 'INSTALLMENT', ?, 0, ?, 'PENDING', ?, '', ?)", (user_id, customer, item_name, total_price, monthly_pay, today, phone))
        sale_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        ph_text = f"\n📱 ဖုန်း: `{phone}`" if phone else ""
        await update.message.reply_text(f"⏳ **ကြွေးလက်ကျန် စာရင်းသွင်းပြီးပါပြီ!**\n🆔 ID: `{sale_id}`\n👤 ဝယ်သူ: `{customer}`{ph_text}\n📉 အကြွေးကျန်: `{total_price:,.0f}` MMK", parse_mode="Markdown")
    except Exception:
        await update.message.reply_text("❌ `/add_credit <ဝယ်သူ> | <ပစ္စည်း> | <အကြွေးစုစုပေါင်း> | <တစ်လပေးရမည့်ငွေ> | <ဖုန်း>` ဟုသာ ရိုက်ပါ။")

async def sell_cash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    try:
        args = " ".join(context.args).split("|")
        if len(args) < 3:
            raise ValueError
        
        customer = args[0].strip()
        item_name = args[1].strip()
        price = float(args[2].strip())
        phone = args[3].strip() if len(args) > 3 else ""
        gift = args[4].strip() if len(args) > 4 else ""

        if phone == '-': phone = ""
        if gift == '-': gift = ""

        if price < 0:
            return await update.message.reply_text("❌ ရောင်းဈေးသည် အပေါင်းလက္ခဏာသာ ဖြစ်ရပါမည်။")

        today = datetime.now(MM_TZ).strftime("%Y-%m-%d")
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, item_name))
        row = cursor.fetchone()
        if not row or row[0] < 1:
            return await update.message.reply_text("❌ လက်ကျန် Stock မလုံလောက်ပါ။")
            
        cursor.execute("UPDATE inventory SET quantity = quantity - 1 WHERE user_id = ? AND item_name = ?", (user_id, item_name))
        
        if gift:
            for g_item in [g.strip() for g in gift.split(',') if g.strip()]:
                cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, g_item))
                g_row = cursor.fetchone()
                if g_row and g_row[0] > 0:
                    cursor.execute("UPDATE inventory SET quantity = quantity - 1 WHERE user_id = ? AND item_name = ?", (user_id, g_item))
                    
        cursor.execute("INSERT INTO sales (user_id, customer_name, item_name, sale_type, total_price, paid_amount, monthly_payment, status, date, gift_item, phone_number) VALUES (?, ?, ?, 'CASH', ?, ?, 0, 'PAID', ?, ?, ?)", (user_id, customer, item_name, price, price, today, gift, phone))
        sale_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        ph_msg = f"\n📱 ဖုန်း: `{phone}`" if phone else ""
        gift_msg = f"\n🎁 လက်ဆောင်: `{gift}`" if gift else ""
        await update.message.reply_text(f"💵 **လက်ငင်း ရောင်းချမှု အောင်မြင်ပါသည်။**\n🆔 ID: `{sale_id}`\n👤 ဝယ်သူ: `{customer}`{ph_msg}\n📦 ပစ္စည်း: `{item_name}`{gift_msg}", parse_mode="Markdown")
    except Exception:
        await update.message.reply_text("❌ မှားယွင်းနေပါသည်။\nပုံစံ: `/sell_cash <ဝယ်သူ> | <ပစ္စည်း> | <ရောင်းဈေး> | <ဖုန်း> | <လက်ဆောင်>`\nမထည့်လိုပါက `-` ဟု ထည့်ပါ။", parse_mode="Markdown")

async def sell_installment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    try:
        args = " ".join(context.args).split("|")
        if len(args) < 5:
            raise ValueError
        
        customer = args[0].strip()
        item_name = args[1].strip()
        total_price = float(args[2].strip())
        down_payment = float(args[3].strip())
        monthly_pay = float(args[4].strip())
        phone = args[5].strip() if len(args) > 5 else ""
        gift = args[6].strip() if len(args) > 6 else ""

        if phone == '-': phone = ""
        if gift == '-': gift = ""

        if total_price < 0 or down_payment < 0 or monthly_pay < 0:
            return await update.message.reply_text("❌ ငွေပမာဏများသည် အပေါင်းလက္ခဏာသာ ဖြစ်ရပါမည်။")

        today = datetime.now(MM_TZ).strftime("%Y-%m-%d")
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, item_name))
        row = cursor.fetchone()
        if not row or row[0] < 1:
            return await update.message.reply_text("❌ Stock မလုံလောက်ပါ။")
            
        cursor.execute("UPDATE inventory SET quantity = quantity - 1 WHERE user_id = ? AND item_name = ?", (user_id, item_name))
        
        if gift:
            for g_item in [g.strip() for g in gift.split(',') if g.strip()]:
                cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, g_item))
                g_row = cursor.fetchone()
                if g_row and g_row[0] > 0:
                    cursor.execute("UPDATE inventory SET quantity = quantity - 1 WHERE user_id = ? AND item_name = ?", (user_id, g_item))
                    
        status = 'PAID' if down_payment >= total_price else 'PENDING'
        cursor.execute("INSERT INTO sales (user_id, customer_name, item_name, sale_type, total_price, paid_amount, monthly_payment, status, date, gift_item, phone_number) VALUES (?, ?, ?, 'INSTALLMENT', ?, ?, ?, ?, ?, ?, ?)", (user_id, customer, item_name, total_price, down_payment, monthly_pay, status, today, gift, phone))
        sale_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        ph_msg = f"\n📱 ဖုန်း: `{phone}`" if phone else ""
        gift_msg = f"\n🎁 လက်ဆောင်: `{gift}`" if gift else ""
        await update.message.reply_text(f"⏳ **ကြွေးရောင်း မှတ်တမ်းဝင်သွားပါပြီ!**\n🆔 ID: `{sale_id}`\n👤 ဝယ်သူ: `{customer}`{ph_msg}\n📉 ကျန်ငွေ: `{total_price - down_payment:,.0f}` MMK{gift_msg}", parse_mode="Markdown")
    except Exception:
        await update.message.reply_text("❌ `/sell_installment <ဝယ်သူ> | <ပစ္စည်း> | <စုစုပေါင်းဈေး> | <စပေါ်> | <၁လပေး> | <ဖုန်း> | <လက်ဆောင်>`\nမထည့်လိုပါက `-` ဟု ထည့်ပါ။", parse_mode="Markdown")

async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    try:
        raw_input = " ".join(context.args).strip()
        if "|" in raw_input:
            target_str, amount_str = [p.strip() for p in raw_input.split("|")]
        else:
            target_str, amount_str = [p.strip() for p in raw_input.rsplit(" ", 1)]
        
        amount = float(amount_str)
        if amount < 0:
            return await update.message.reply_text("❌ ငွေဆပ်ပမာဏသည် အပေါင်းလက္ခဏာသာ ဖြစ်ရပါမည်။")

        conn = get_db()
        cursor = conn.cursor()

        if target_str.isdigit():
            cursor.execute("SELECT id, customer_name, item_name, total_price, paid_amount FROM sales WHERE user_id = ? AND id = ? AND status = 'PENDING'", (user_id, int(target_str)))
            rows = cursor.fetchall()
        else:
            norm_target = " ".join(target_str.split()).lower()
            cursor.execute("SELECT id, customer_name, item_name, total_price, paid_amount FROM sales WHERE user_id = ? AND status = 'PENDING' AND sale_type = 'INSTALLMENT'", (user_id,))
            rows = [r for r in cursor.fetchall() if " ".join(r[1].split()).lower() == norm_target]

        if not rows:
            return await update.message.reply_text(f"❌ `{target_str}` အတွက် အကြွေးစာရင်း မတွေ့ပါ။", parse_mode="Markdown")

        if len(rows) > 1:
            msg = f"⚠️ **စာရင်း ({len(rows)}) ခု ရှိနေပါသည်:**\n\n"
            for r in rows: msg += f"🆔 ID: `{r[0]}` | {r[1]} ({r[2]}) - ကျန်ငွေ: `{(r[3]-r[4]):,.0f}`\n👉 `/pay {r[0]} | {amount:,.0f}`\n\n"
            return await update.message.reply_text(msg, parse_mode="Markdown")

        sale_id, customer_name, item_name, total_price, current_paid = rows[0]
        
        remaining_debt = total_price - current_paid
        if amount > remaining_debt:
            conn.close()
            return await update.message.reply_text(
                f"❌ **ပေးသွင်းငွေ မှားယွင်းနေပါသည်။**\n"
                f"ယခုစာရင်းအတွက် ပေးရန်ကျန်ငွေမှာ `{remaining_debt:,.0f}` MMK သာဖြစ်ပါသည်။\n\n"
                f"👉 ကျေးဇူးပြု၍ `{remaining_debt:,.0f}` သို့မဟုတ် ထိုထက်နည်းသော ပမာဏကိုသာ ထည့်သွင်းပါ။", 
                parse_mode="Markdown"
            )

        new_paid = current_paid + amount
        new_status = 'PAID' if new_paid >= total_price else 'PENDING'
        today = datetime.now(MM_TZ).strftime("%Y-%m-%d")

        cursor.execute("UPDATE sales SET paid_amount = ?, status = ?, last_payment_date = ? WHERE user_id = ? AND id = ?", (new_paid, new_status, today, user_id, sale_id))
        conn.commit()
        conn.close()
        
        rem = total_price - new_paid
        await update.message.reply_text(f"💰 **ငွေဆပ်မှု အောင်မြင်ပါသည်။**\n🆔 ID: `{sale_id}`\n👤 ဝယ်သူ: `{customer_name}`\n💵 ပေးသွင်းငွေ: `{amount:,.0f}` MMK\n📉 ပေးရန်ကျန်ငွေ: `{0 if rem <= 0 else f'{rem:,.0f}'} MMK`\n📅 ဆပ်သည့်ရက်စွဲ: `{today}`", parse_mode="Markdown")
    except Exception:
        await update.message.reply_text("❌ Format မှားယွင်းနေပါသည်။\n`/pay <ဝယ်သူနာမည် သို့မဟုတ် ID> | <ပေးသည့်ပမာဏ>`")

async def undo_pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    try:
        raw_input = " ".join(context.args).strip()
        if "|" in raw_input:
            target_str, amount_str = [p.strip() for p in raw_input.split("|")]
        else:
            target_str, amount_str = [p.strip() for p in raw_input.rsplit(" ", 1)]
        
        amount = float(amount_str)
        if amount < 0:
            return await update.message.reply_text("❌ ငွေပမာဏသည် အပေါင်းလက္ခဏာသာ ဖြစ်ရပါမည်။")

        conn = get_db()
        cursor = conn.cursor()

        if target_str.isdigit():
            cursor.execute("SELECT id, customer_name, item_name, total_price, paid_amount FROM sales WHERE user_id = ? AND id = ?", (user_id, int(target_str)))
            rows = cursor.fetchall()
        else:
            norm_target = " ".join(target_str.split()).lower()
            cursor.execute("SELECT id, customer_name, item_name, total_price, paid_amount FROM sales WHERE user_id = ? AND sale_type = 'INSTALLMENT'", (user_id,))
            rows = [r for r in cursor.fetchall() if " ".join(r[1].split()).lower() == norm_target]

        if not rows:
            return await update.message.reply_text(f"❌ `{target_str}` အတွက် စာရင်း မတွေ့ပါ။", parse_mode="Markdown")

        if len(rows) > 1:
            msg = f"⚠️ **စာရင်း ({len(rows)}) ခု ရှိနေပါသည်:**\n\n"
            for r in rows: msg += f"🆔 ID: `{r[0]}` | {r[1]} ({r[2]}) - သွင်းပြီးငွေ: `{r[4]:,.0f}`\n👉 `/undo_pay {r[0]} | {amount:,.0f}`\n\n"
            return await update.message.reply_text(msg, parse_mode="Markdown")

        sale_id, customer_name, item_name, total_price, current_paid = rows[0]
        
        if amount > current_paid:
            conn.close()
            return await update.message.reply_text(
                f"❌ **ပြန်နှုတ်မည့်ငွေ မှားယွင်းနေပါသည်။**\n"
                f"ယခုစာရင်းတွင် ပေးသွင်းထားသောငွေမှာ စုစုပေါင်း `{current_paid:,.0f}` MMK သာရှိပါသည်။\n"
                f"👉 ကျေးဇူးပြု၍ `{current_paid:,.0f}` ထက်မပိုသော ပမာဏကိုသာ ပြန်နှုတ်ပါ။", 
                parse_mode="Markdown"
            )

        new_paid = current_paid - amount
        new_status = 'PAID' if new_paid >= total_price else 'PENDING'
        
        cursor.execute("UPDATE sales SET paid_amount = ?, status = ? WHERE user_id = ? AND id = ?", (new_paid, new_status, user_id, sale_id))
        conn.commit()
        conn.close()
        
        rem = total_price - new_paid
        await update.message.reply_text(f"✅ **ငွေသွင်းမှားယွင်းမှု ပြန်လည်ပြင်ဆင်ပြီးပါပြီ။**\n🆔 ID: `{sale_id}`\n👤 ဝယ်သူ: `{customer_name}`\n⏪ ပြန်နှုတ်လိုက်သည့်ငွေ: `{amount:,.0f}` MMK\n📉 ယခုပေးရန်ကျန်ငွေ: `{rem:,.0f} MMK`", parse_mode="Markdown")
    except Exception:
        await update.message.reply_text("❌ Format မှားယွင်းနေပါသည်။\n`/undo_pay <ဝယ်သူနာမည် သို့မဟုတ် ID> | <ပြန်နှုတ်မည့်ပမာဏ>`\nဥပမာ - `/undo_pay 10 | 50000`")

# ====================================================
# ❌ အကြွေးဆုံးစာရင်း Command များ (Bad Debt)
# ====================================================
async def mark_bad_debt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    try:
        sale_id = int(context.args[0].strip())
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("SELECT customer_name, total_price, paid_amount FROM sales WHERE user_id = ? AND id = ? AND status = 'PENDING'", (user_id, sale_id))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return await update.message.reply_text("❌ သက်ဆိုင်ရာ ID ဖြင့် ပေးရန်ကျန်ငွေ (PENDING) စာရင်း မတွေ့ပါ။ ID မှန်/မမှန် စစ်ဆေးပါ။")
        
        customer_name, total_price, paid_amount = row
        lost_amount = total_price - paid_amount
        
        cursor.execute("UPDATE sales SET status = 'BAD_DEBT' WHERE user_id = ? AND id = ?", (user_id, sale_id))
        conn.commit()
        conn.close()
        
        await update.message.reply_text(f"❌ **အကြွေးဆုံးစာရင်းသို့ ပြောင်းရွှေ့ပြီးပါပြီ!**\n\n🆔 ID: `{sale_id}`\n👤 ဝယ်သူ: `{customer_name}`\n💸 ဆုံးရှုံးငွေ: `{lost_amount:,.0f}` MMK", parse_mode="Markdown")
    except Exception:
        await update.message.reply_text("❌ ပုံစံမှားယွင်းနေပါသည်။ `/bad_debt <Sale ID>` ဟုသာ ရိုက်ထည့်ပါ။\n(ဥပမာ - `/bad_debt 15`)", parse_mode="Markdown")

async def undo_bad_debt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    try:
        sale_id = int(context.args[0].strip())
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("SELECT customer_name FROM sales WHERE user_id = ? AND id = ? AND status = 'BAD_DEBT'", (user_id, sale_id))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return await update.message.reply_text("❌ သက်ဆိုင်ရာ ID ဖြင့် အကြွေးဆုံးစာရင်း မတွေ့ပါ။")
            
        cursor.execute("UPDATE sales SET status = 'PENDING' WHERE user_id = ? AND id = ?", (user_id, sale_id))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"✅ **အကြွေးဆုံးစာရင်းမှ ပုံမှန်အကြွေးသို့ ပြန်ပြောင်းပြီးပါပြီ!**\n🆔 ID: `{sale_id}`\n👤 ဝယ်သူ: `{row[0]}`", parse_mode="Markdown")
    except Exception:
        await update.message.reply_text("❌ ပုံစံမှားယွင်းနေပါသည်။ `/undo_bad_debt <Sale ID>` ဟုသာ ရိုက်ပါ။", parse_mode="Markdown")


async def search_customer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not context.args:
        return await update.message.reply_text("❌ **Format:**\n`/search <ဝယ်သူအမည်>`\n👇 ဥပမာ - `/search Mg Mg`", parse_mode="Markdown")
    
    search_name = " ".join(context.args).strip()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, item_name, total_price, paid_amount, status, date, gift_item, phone_number FROM sales WHERE user_id = ? AND customer_name LIKE ? ORDER BY date DESC", (user_id, '%'+search_name+'%'))
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        return await update.message.reply_text(f"🔍 `{search_name}` အမည်ဖြင့် ဝယ်ယူထားသော စာရင်း လုံးဝမတွေ့ပါ။", parse_mode="Markdown")
    
    total_bought = 0
    total_debt = 0
    total_bad_debt = 0
    msg = f"🔍 **'{search_name}' ၏ စာရင်းများ:**\n\n"
    
    for r in rows:
        sale_id, item_name, total_price, paid_amount, status, date, gift_item, phone_number = r
        rem = total_price - paid_amount
        total_bought += total_price
        
        if status == 'PENDING': 
            total_debt += rem
            status_icon = "🔴 အကြွေး"
        elif status == 'BAD_DEBT':
            total_bad_debt += rem
            status_icon = "❌ အကြွေးဆုံး"
        else:
            status_icon = "🟢 ရှင်းပြီး"
            
        gift_txt = f"\n🎁 လက်ဆောင်: `{gift_item}`" if gift_item else ""
        ph_txt = f"\n📱 ဖုန်း: `{phone_number}`" if phone_number else ""
        
        msg += f"🆔 ID: `{sale_id}` | 📅 စရောင်းရက်: {date}{ph_txt}\n📦 ပစ္စည်း: `{item_name}`{gift_txt}\n💰 တန်ဖိုး: `{total_price:,.0f}` | ကျန်ငွေ: `{rem:,.0f}` ({status_icon})\n\n"
    
    msg += "───────────────────\n"
    msg += f"🛒 စုစုပေါင်း ဝယ်ယူမှု: `{total_bought:,.0f}` MMK\n"
    msg += f"⚠️ စုစုပေါင်း ပေးရန်ကျန်ငွေ: `{total_debt:,.0f}` MMK\n"
    if total_bad_debt > 0:
        msg += f"❌ စုစုပေါင်း အကြွေးဆုံး: `{total_bad_debt:,.0f}` MMK\n"
    
    if len(msg) > 4000:
        await update.message.reply_text("⚠️ စာရင်းအရမ်းများနေပါသည်။ အချို့ကိုသာ ပြသနိုင်ပါသည်။")
    else:
        await update.message.reply_text(msg, parse_mode="Markdown")

# ====================================================
# 🗂️ Pagination Helper Functions
# ====================================================
async def send_stock_page(update, context, user_id, page=0, is_callback=False):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT item_name, quantity, cost_price FROM inventory WHERE user_id = ? AND quantity > 0", (user_id,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        msg = "📦 လက်ရှိ Stock လုံးဝ မရှိသေးပါ။"
        if is_callback: return await update.callback_query.edit_message_text(msg)
        else: return await update.message.reply_text(msg)

    total_stock_value = sum(r[1] * r[2] for r in rows)
    ITEMS_PER_PAGE = 15
    total_pages = (len(rows) - 1) // ITEMS_PER_PAGE + 1
    page = max(0, min(page, total_pages - 1))
    
    start_idx = page * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    page_rows = rows[start_idx:end_idx]

    msg = f"📊 **ဆိုင်ရှိ လက်ကျန် Stock စာရင်း (စာမျက်နှာ {page+1}/{total_pages}):**\n\n"
    for r in page_rows:
        val = r[1] * r[2]
        msg += f"• `{r[0]}` - `{r[1]}` ခု (တန်ဖိုး: `{val:,.0f}` MMK)\n"
    
    msg += "\n───────────────────\n"
    msg += f"📦 **စုစုပေါင်း Stock တန်ဖိုးငွေ:** `{total_stock_value:,.0f}` MMK\n"

    buttons = []
    if page > 0: buttons.append(InlineKeyboardButton("⬅️ ယခင်", callback_data=f"stock_page_{page-1}"))
    if page < total_pages - 1: buttons.append(InlineKeyboardButton("နောက်သို့ ➡️", callback_data=f"stock_page_{page+1}"))
    reply_markup = InlineKeyboardMarkup([buttons]) if buttons else None

    if is_callback:
        await update.callback_query.edit_message_text(msg, parse_mode="Markdown", reply_markup=reply_markup)
    else:
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=reply_markup)

async def send_list_page(update, context, user_id, page=0, is_callback=False):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, customer_name, item_name, total_price, paid_amount, monthly_payment, last_payment_date, date, phone_number FROM sales WHERE user_id = ? AND status = 'PENDING'", (user_id,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        msg = "🎉 အရစ်ကျ ကျန်ရှိသူ စာရင်း မရှိပါ။"
        if is_callback: return await update.callback_query.edit_message_text(msg)
        else: return await update.message.reply_text(msg)

    total_pending_amount = sum((r[3] - r[4]) for r in rows)
    ITEMS_PER_PAGE = 10
    total_pages = (len(rows) - 1) // ITEMS_PER_PAGE + 1
    page = max(0, min(page, total_pages - 1))
    
    start_idx = page * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    page_rows = rows[start_idx:end_idx]

    msg = f"⏳ **ကြွေးကျန်သူများ စာရင်း (စာမျက်နှာ {page+1}/{total_pages}):**\n\n"
    for r in page_rows:
        rem = r[3] - r[4]
        monthly_pay = r[5] if r[5] is not None else 0.0
        
        last_pay_date = r[6] if len(r) > 6 and r[6] else "မဆပ်ရသေးပါ"
        sale_date = r[7] if len(r) > 7 and r[7] else "မသိရပါ"
        ph_txt = f" | 📱 {r[8]}" if r[8] else ""
        
        msg += f"ID: {r[0]} | နာမည်: `{r[1]}`{ph_txt}\n📦 ပစ္စည်း: {r[2]} | ကျန်ငွေ: {rem:,.0f} | ၁လပေး: {monthly_pay:,.0f}\n🛒 စရောင်းရက်: {sale_date} | 📅 ဆပ်ရက်: {last_pay_date}\n\n"
    
    msg += "───────────────────\n"
    msg += f"💰 **စုစုပေါင်း ရရန်ရှိသော ကြွေးကျန်ငွေ:** `{total_pending_amount:,.0f}` MMK\n"

    buttons = []
    if page > 0: buttons.append(InlineKeyboardButton("⬅️ ယခင်", callback_data=f"list_page_{page-1}"))
    if page < total_pages - 1: buttons.append(InlineKeyboardButton("နောက်သို့ ➡️", callback_data=f"list_page_{page+1}"))
    reply_markup = InlineKeyboardMarkup([buttons]) if buttons else None

    if is_callback:
        await update.callback_query.edit_message_text(msg, parse_mode="Markdown", reply_markup=reply_markup)
    else:
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=reply_markup)

# ❌ အကြွေးဆုံး Pagination အသစ်
async def send_bad_debt_page(update, context, user_id, page=0, is_callback=False):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, customer_name, item_name, total_price, paid_amount, phone_number, date FROM sales WHERE user_id = ? AND status = 'BAD_DEBT'", (user_id,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        msg = "🎉 အကြွေးဆုံးစာရင်း လုံးဝ မရှိသေးပါ။"
        if is_callback: return await update.callback_query.edit_message_text(msg)
        else: return await update.message.reply_text(msg)

    total_lost_amount = sum((r[3] - r[4]) for r in rows)
    ITEMS_PER_PAGE = 10
    total_pages = (len(rows) - 1) // ITEMS_PER_PAGE + 1
    page = max(0, min(page, total_pages - 1))
    
    start_idx = page * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    page_rows = rows[start_idx:end_idx]

    msg = f"❌ **အကြွေးဆုံးစာရင်း (စာမျက်နှာ {page+1}/{total_pages}):**\n\n"
    for r in page_rows:
        rem = r[3] - r[4]
        ph_txt = f" | 📱 {r[5]}" if r[5] else ""
        msg += f"ID: {r[0]} | 👤 `{r[1]}`{ph_txt}\n📦 {r[2]} | ဆုံးရှုံးငွေ: `{rem:,.0f}` (ရက်စွဲ: {r[6]})\n\n"
    
    msg += "───────────────────\n"
    msg += f"⚠️ **စုစုပေါင်း အကြွေးဆုံးငွေ:** `{total_lost_amount:,.0f}` MMK\n"

    buttons = []
    if page > 0: buttons.append(InlineKeyboardButton("⬅️ ယခင်", callback_data=f"bad_debt_page_{page-1}"))
    if page < total_pages - 1: buttons.append(InlineKeyboardButton("နောက်သို့ ➡️", callback_data=f"bad_debt_page_{page+1}"))
    reply_markup = InlineKeyboardMarkup([buttons]) if buttons else None

    if is_callback:
        await update.callback_query.edit_message_text(msg, parse_mode="Markdown", reply_markup=reply_markup)
    else:
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=reply_markup)


async def stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_stock_page(update, context, update.message.from_user.id, page=0, is_callback=False)

async def list_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_list_page(update, context, update.message.from_user.id, page=0, is_callback=False)

# ====================================================
# 📊 အရှုံးအမြတ် လချုပ် Report (အကြွေးဆုံးငွေကို အကျုံးဝင်တွက်ချက်သည်)
# ====================================================
async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    try:
        args = context.args
        if args:
            period = args[0].strip()
            if len(period) == 4:
                date_format, period_label = '%Y', f"{period} ခုနှစ်ချုပ်"
            else:
                date_format, period_label = '%Y-%m', f"{period} လချုပ်"
        else:
            period = datetime.now(MM_TZ).strftime("%Y-%m")
            date_format, period_label = '%Y-%m', f"{period} လချုပ်"

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute(f"SELECT s.total_price, s.paid_amount, COALESCE(i.cost_price, 0) FROM sales s LEFT JOIN inventory i ON s.item_name = i.item_name AND s.user_id = i.user_id WHERE s.user_id = ? AND strftime('{date_format}', s.date) = ? AND s.status != 'BAD_DEBT'", (user_id, period))
        sales_rows = cursor.fetchall()
        
        # အကြွေးဆုံးငွေများ (Net Profit မှ နှုတ်ရန်)
        cursor.execute(f"SELECT SUM(total_price - paid_amount) FROM sales WHERE user_id = ? AND strftime('{date_format}', date) = ? AND status = 'BAD_DEBT'", (user_id, period))
        bad_debt_loss = cursor.fetchone()[0] or 0.0
        
        cursor.execute(f"SELECT SUM(amount) FROM expenses WHERE user_id = ? AND strftime('{date_format}', date) = ?", (user_id, period))
        total_expense = cursor.fetchone()[0] or 0.0
        
        cursor.execute(f"SELECT category, SUM(amount) FROM expenses WHERE user_id = ? AND strftime('{date_format}', date) = ? GROUP BY category", (user_id, period))
        expense_breakdown = cursor.fetchall()

        cursor.execute(f"SELECT SUM(amount) FROM capital WHERE user_id = ? AND strftime('{date_format}', date) = ?", (user_id, period))
        added_capital = cursor.fetchone()[0] or 0.0
        cursor.execute(f"SELECT SUM(total_cost) FROM purchases WHERE user_id = ? AND strftime('{date_format}', date) = ?", (user_id, period))
        total_purchases = cursor.fetchone()[0] or 0.0

        cursor.execute(f"SELECT SUM(paid_amount) FROM sales WHERE user_id = ? AND strftime('{date_format}', date) < ?", (user_id, period))
        past_collected = cursor.fetchone()[0] or 0.0
        cursor.execute(f"SELECT SUM(amount) FROM expenses WHERE user_id = ? AND strftime('{date_format}', date) < ?", (user_id, period))
        past_expense = cursor.fetchone()[0] or 0.0
        cursor.execute(f"SELECT SUM(amount) FROM capital WHERE user_id = ? AND strftime('{date_format}', date) < ?", (user_id, period))
        past_capital = cursor.fetchone()[0] or 0.0
        cursor.execute(f"SELECT SUM(total_cost) FROM purchases WHERE user_id = ? AND strftime('{date_format}', date) < ?", (user_id, period))
        past_purchases = cursor.fetchone()[0] or 0.0

        cursor.execute("SELECT SUM(quantity * cost_price) FROM inventory WHERE user_id = ? AND quantity > 0", (user_id,))
        total_stock = cursor.fetchone()[0] or 0.0
        
        cursor.execute("SELECT SUM(total_price - paid_amount) FROM sales WHERE user_id = ? AND status = 'PENDING'", (user_id,))
        total_pending_debt = cursor.fetchone()[0] or 0.0
        
        cursor.execute("SELECT SUM(total_price - paid_amount) FROM sales WHERE user_id = ? AND status = 'BAD_DEBT'", (user_id,))
        total_bad_debt_all_time = cursor.fetchone()[0] or 0.0

        conn.close()

        total_sales_value = sum(r[0] for r in sales_rows)
        total_collected = sum(r[1] for r in sales_rows)
        total_cogs = sum(r[2] for r in sales_rows)

        net_profit = total_sales_value - total_cogs - total_expense - bad_debt_loss
        profit_status = "🟢 အမြတ်" if net_profit >= 0 else "🔴 အရှုံး"

        opening_balance = past_capital + past_collected - past_expense - past_purchases
        current_month_cashflow = added_capital + total_collected - total_expense - total_purchases
        closing_balance = opening_balance + current_month_cashflow

        exp_breakdown_str = ""
        if expense_breakdown:
            exp_breakdown_str = "\n".join([f"   • {r[0]}: `{r[1]:,.0f}`" for r in expense_breakdown])
            exp_breakdown_str = f"\n📂 **အသုံးစရိတ် အသေးစိတ်:**\n{exp_breakdown_str}\n"
            
        bad_debt_txt = f"\n❌ အကြွေးဆုံး (ယခုလဆုံးရှုံးငွေ): `{bad_debt_loss:,.0f}` MMK" if bad_debt_loss > 0 else ""

        msg = (
            f"📊 **{period_label} အရှုံးအမြတ်နှင့် လက်ကျန် စာရင်း**\n\n"
            f"🏦 **ယခင်လ လက်ကျန်ငွေ (Opening):** `{opening_balance:,.0f}` MMK\n"
            "───────────────────\n"
            f"🛒 အရောင်းပမာဏ (စုစုပေါင်း): `{total_sales_value:,.0f}` MMK\n"
            f"💵 ရောင်းရငွေ (လက်ဝယ်ရငွေ): `{total_collected:,.0f}` MMK\n"
            f"📉 ယခုလအတွက် ရရန်ကျန်ငွေ: `{(total_sales_value - total_collected):,.0f}` MMK\n"
            f"📦 ရောင်းရပစ္စည်း ရင်းနှီးစရိတ်: `{total_cogs:,.0f}` MMK\n"
            "───────────────────\n"
            f"📥 ထည့်သွင်းငွေ/အရင်း: `{added_capital:,.0f}` MMK\n"
            f"📤 အဝယ်စရိတ်: `{total_purchases:,.0f}` MMK\n"
            f"💸 အသုံးစရိတ် (စုစုပေါင်း): `{total_expense:,.0f}` MMK\n"
            f"{exp_breakdown_str}{bad_debt_txt}\n"
            "───────────────────\n"
            f"{profit_status} (ယခုလ အသားတင်): `{abs(net_profit):,.0f}` MMK\n"
            f"💰 **စုစုပေါင်း နောက်ဆုံးငွေလက်ကျန်**: `{closing_balance:,.0f}` MMK\n"
            f"   *(ယခင်လက်ကျန် + ယခုလဝင်ငွေ - ယခုလထွက်ငွေ)*\n\n"
            "───────────────────\n"
            f"📦 **ဆိုင်ရှိ Stock တန်ဖိုးငွေ:** `{total_stock:,.0f}` MMK\n"
            f"⏳ **စုစုပေါင်း ရရန်ရှိသော ကြွေးကျန်ငွေ:** `{total_pending_debt:,.0f}` MMK\n"
            f"❌ **စုစုပေါင်း အကြွေးဆုံးငွေ:** `{total_bad_debt_all_time:,.0f}` MMK"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def export_excel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    await update.message.reply_text("🔄 Excel ဖိုင်ထုတ်ပေးနေပါသည် ခဏစောင့်ပါ...")
    try:
        conn = get_db()
        file_path = f"Shop_Data_{user_id}.xlsx"
        cursor = conn.cursor()
        
        cursor.execute("SELECT SUM(total_price), SUM(paid_amount) FROM sales WHERE user_id = ? AND status != 'BAD_DEBT'", (user_id,))
        s_res = cursor.fetchone()
        t_sales, t_collected = s_res[0] or 0.0, s_res[1] or 0.0
        cursor.execute("SELECT SUM(amount) FROM expenses WHERE user_id = ?", (user_id,))
        t_expense = cursor.fetchone()[0] or 0.0
        cursor.execute("SELECT SUM(amount) FROM capital WHERE user_id = ?", (user_id,))
        t_capital = cursor.fetchone()[0] or 0.0
        cursor.execute("SELECT SUM(total_cost) FROM purchases WHERE user_id = ?", (user_id,))
        t_purchases = cursor.fetchone()[0] or 0.0
        cursor.execute("SELECT SUM(quantity * cost_price) FROM inventory WHERE user_id = ? AND quantity > 0", (user_id,))
        t_stock = cursor.fetchone()[0] or 0.0
        final_cash = t_capital + t_collected - t_expense - t_purchases
        
        df_summary = pd.DataFrame({
            "အကြောင်းအရာ (Description)": ["စုစုပေါင်း အရောင်း", "ရောင်းရငွေ", "ရရန်ကျန်ငွေ", "ထည့်သွင်းငွေ/အရင်း", "အဝယ်စရိတ်", "အသုံးစရိတ်", "✅ နောက်ဆုံး ငွေလက်ကျန်", "📦 ဆိုင်ရှိ Stock တန်ဖိုး"],
            "ပမာဏ (Amount MMK)": [t_sales, t_collected, t_sales - t_collected, t_capital, t_purchases, t_expense, final_cash, t_stock]
        })
        
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            df_summary.to_excel(writer, sheet_name='Summary (စာရင်းချုပ်)', index=False)
            
            pd.read_sql_query(f"SELECT id, item_name, quantity, cost_price FROM inventory WHERE user_id={user_id}", conn).to_excel(writer, sheet_name='Inventory', index=False)
            
            df_sales = pd.read_sql_query(f"SELECT id, customer_name, phone_number, item_name, sale_type, total_price, paid_amount, monthly_payment, status, date as sale_date, gift_item, last_payment_date FROM sales WHERE user_id={user_id}", conn)
            df_sales.rename(columns={
                'id': 'ID',
                'customer_name': 'ဝယ်သူအမည်',
                'phone_number': 'ဖုန်းနံပါတ်',
                'item_name': 'ပစ္စည်း',
                'sale_type': 'အရောင်းအမျိုးအစား',
                'total_price': 'စုစုပေါင်းတန်ဖိုး',
                'paid_amount': 'ပေးသွင်းပြီးငွေ',
                'monthly_payment': 'တစ်လပေးသွင်းငွေ',
                'status': 'အခြေအနေ',
                'sale_date': 'စရောင်းသည့်ရက်',
                'gift_item': 'လက်ဆောင်',
                'last_payment_date': 'နောက်ဆုံးငွေဆပ်ရက်'
            }, inplace=True)
            df_sales.to_excel(writer, sheet_name='Sales', index=False)
            
            # ❌ Bad Debts (အကြွေးဆုံး) Sheet အသစ်
            df_bad = pd.read_sql_query(f"SELECT id, customer_name, phone_number, item_name, total_price, paid_amount, (total_price - paid_amount) as lost_amount, date as bad_debt_date FROM sales WHERE user_id={user_id} AND status='BAD_DEBT'", conn)
            if not df_bad.empty:
                df_bad.rename(columns={
                    'id': 'ID',
                    'customer_name': 'ဝယ်သူအမည်',
                    'phone_number': 'ဖုန်းနံပါတ်',
                    'item_name': 'ပစ္စည်း',
                    'total_price': 'စုစုပေါင်းတန်ဖိုး',
                    'paid_amount': 'ပေးသွင်းပြီးငွေ',
                    'lost_amount': 'ဆုံးရှုံးငွေ (အကြွေးဆုံး)',
                    'bad_debt_date': 'စရောင်းသည့်ရက်'
                }, inplace=True)
                df_bad.to_excel(writer, sheet_name='Bad Debts (အကြွေးဆုံး)', index=False)
            
            df_expenses = pd.read_sql_query(f"SELECT id, category, title, amount, date as expense_date FROM expenses WHERE user_id={user_id}", conn)
            df_expenses.rename(columns={
                'id': 'ID',
                'category': 'အမျိုးအစား',
                'title': 'အကြောင်းအရာ',
                'amount': 'ပမာဏ',
                'expense_date': 'ရက်စွဲ'
            }, inplace=True)
            df_expenses.to_excel(writer, sheet_name='Expenses', index=False)
            
            pd.read_sql_query(f"SELECT id, amount, date FROM capital WHERE user_id={user_id}", conn).to_excel(writer, sheet_name='Capital', index=False)
            pd.read_sql_query(f"SELECT id, item_name, quantity, total_cost, date FROM purchases WHERE user_id={user_id}", conn).to_excel(writer, sheet_name='Purchases', index=False)
            
        conn.close()
        await update.message.reply_document(document=open(file_path, 'rb'), caption="📊 သင့်စာရင်းများနှင့် နောက်ဆုံးငွေလက်ကျန် အချုပ်ပါဝင်သော Excel ဖိုင်ဖြစ်ပါသည်။ ('Sales' Sheet တွင် စရောင်းရက်နှင့် နောက်ဆုံးဆပ်ရက်များကို ကြည့်ရှုနိုင်ပါသည်။)")
        os.remove(file_path)
    except Exception as e:
        await update.message.reply_text(f"❌ Excel export Error: {str(e)}")

# ====================================================
# 🔘 Callback Handler for Buttons & Pagination
# ====================================================
async def main_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    data = query.data

    if data.startswith("stock_page_"):
        page = int(data.split("_")[2])
        await send_stock_page(update, context, user_id, page=page, is_callback=True)
    elif data.startswith("list_page_"):
        page = int(data.split("_")[2])
        await send_list_page(update, context, user_id, page=page, is_callback=True)
    elif data.startswith("bad_debt_page_"):
        page = int(data.split("_")[3])
        await send_bad_debt_page(update, context, user_id, page=page, is_callback=True)

    elif data == "confirm_reset_all":
        conn = get_db()
        cursor = conn.cursor()
        for table in ["inventory", "sales", "expenses", "capital", "purchases"]:
            cursor.execute(f"DELETE FROM {table} WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        await query.edit_message_text("💥 **စာရင်း အားလုံးကို ဖျက်ပစ်ပြီးပါပြီ!**", parse_mode="Markdown")
    elif data == "cancel_action":
        await query.edit_message_text("❌ လုပ်ဆောင်ချက်ကို ပယ်ဖျက်လိုက်ပါပြီ။")
    elif data == "guide_edit":
        await query.edit_message_text("✏️ **စာရင်းပြင်ရန်:**\n၁။ မှားယွင်းသော စာရင်းကို အရင်ဖျက်ပါ။ ပြီးမှ အသစ်ပြန်သွင်းပါ။\n၂။ သို့မဟုတ် Excel Backup ယူပြီး ပြင်ဆင်ကာ Bot ထဲသို့ File အဖြစ် ပြန်ပို့ပါ။", parse_mode="Markdown")
    elif data == "guide_undo_pay":
        await query.edit_message_text("⏪ **ငွေသွင်းမှားတာ ပြန်နှုတ်ရန်:**\n`/undo_pay <ID သို့မဟုတ် အမည်> | <ပြန်နှုတ်မည့်ပမာဏ>` ဟု ရိုက်ထည့်ပါ။\n\n👇 ဥပမာ - (ID 10 ကို ၄သောင်း ပြန်နှုတ်လိုလျှင်)\n`/undo_pay 10 | 40000`", parse_mode="Markdown")
    
    elif data == "menu_del_sale":
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, customer_name, item_name FROM sales WHERE user_id = ? ORDER BY id DESC LIMIT 10", (user_id,))
        rows = cursor.fetchall()
        conn.close()
        if not rows: return await query.edit_message_text("ဖျက်စရာ မရှိပါ။")
        keyboard = [[InlineKeyboardButton(f"ID:{r[0]} | {r[1]} ({r[2]})", callback_data=f"do_del_sale_{r[0]}")] for r in rows]
        keyboard.append([InlineKeyboardButton("🔙 နောက်သို့", callback_data="cancel_action")])
        await query.edit_message_text("🗑️ **ဖျက်လိုသော အရောင်းစာရင်းကို ရွေးပါ:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    elif data == "menu_del_purchase":
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, item_name, quantity, total_cost FROM purchases WHERE user_id = ? ORDER BY id DESC LIMIT 10", (user_id,))
        rows = cursor.fetchall()
        conn.close()
        if not rows: return await query.edit_message_text("ဖျက်စရာ အဝယ်စာရင်း မရှိသေးပါ။")
        keyboard = [[InlineKeyboardButton(f"ID:{r[0]} | {r[1]} ({r[2]}ခု) - {r[3]:,.0f}", callback_data=f"do_del_pur_{r[0]}")] for r in rows]
        keyboard.append([InlineKeyboardButton("🔙 နောက်သို့", callback_data="cancel_action")])
        await query.edit_message_text("🗑️ **နောက်ဆုံး အဝယ်စာရင်းများ:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    elif data == "menu_del_expense":
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, category, title, amount FROM expenses WHERE user_id = ? ORDER BY id DESC LIMIT 10", (user_id,))
        rows = cursor.fetchall()
        conn.close()
        if not rows: return await query.edit_message_text("ဖျက်စရာ အသုံးစရိတ်စာရင်း မရှိသေးပါ။")
        keyboard = [[InlineKeyboardButton(f"ID:{r[0]} | {r[1]} ({r[2]}) - {r[3]:,.0f}", callback_data=f"do_del_exp_{r[0]}")] for r in rows]
        keyboard.append([InlineKeyboardButton("🔙 နောက်သို့", callback_data="cancel_action")])
        await query.edit_message_text("🗑️ **နောက်ဆုံး အသုံးစရိတ်စာရင်းများ:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    elif data == "menu_del_stock":
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, item_name FROM inventory WHERE user_id = ?", (user_id,))
        rows = cursor.fetchall()
        conn.close()
        if not rows: return await query.edit_message_text("ဖျက်စရာ Stock ပစ္စည်း မရှိသေးပါ။")
        keyboard = [[InlineKeyboardButton(f"📦 {r[1]}", callback_data=f"do_del_stock_{r[0]}")] for r in rows]
        keyboard.append([InlineKeyboardButton("🔙 နောက်သို့", callback_data="cancel_action")])
        await query.edit_message_text("🗑️ **ဖျက်လိုသော Stock ပစ္စည်းကို ရွေးပါ:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith("do_del_sale_"):
        sale_id = data.split("_")[3]
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT item_name, gift_item FROM sales WHERE user_id = ? AND id = ?", (user_id, sale_id))
        row = cursor.fetchone()
        if row:
            cursor.execute("DELETE FROM sales WHERE user_id = ? AND id = ?", (user_id, sale_id))
            cursor.execute("UPDATE inventory SET quantity = quantity + 1 WHERE user_id = ? AND item_name = ?", (user_id, row[0]))
            if row[1]:
                for g in [x.strip() for x in row[1].split(',') if x.strip()]:
                    cursor.execute("UPDATE inventory SET quantity = quantity + 1 WHERE user_id = ? AND item_name = ?", (user_id, g))
            conn.commit()
            await query.edit_message_text("✅ အရောင်းစာရင်း ဖျက်လိုက်ပါပြီ။ Stock သို့ ပစ္စည်းများ ပြန်ပေါင်းထည့်ပေးပါပြီ။")
        else:
            await query.edit_message_text("❌ စာရင်းရှာမတွေ့ပါ။")
        conn.close()
    elif data.startswith("do_del_pur_"):
        pur_id = data.split("_")[3]
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT item_name, quantity FROM purchases WHERE user_id = ? AND id = ?", (user_id, pur_id))
        row = cursor.fetchone()
        if row:
            cursor.execute("DELETE FROM purchases WHERE user_id = ? AND id = ?", (user_id, pur_id))
            cursor.execute("UPDATE inventory SET quantity = quantity - ? WHERE user_id = ? AND item_name = ?", (row[1], user_id, row[0]))
            conn.commit()
            await query.edit_message_text(f"✅ အဝယ်စာရင်း ID: `{pur_id}` ကို ဖျက်လိုက်ပါပြီ။ Stock မှလည်း ပြန်နှုတ်ပေးပါပြီ။", parse_mode="Markdown")
        else:
            await query.edit_message_text("❌ စာရင်းရှာမတွေ့ပါ။")
        conn.close()
    elif data.startswith("do_del_exp_"):
        exp_id = data.split("_")[3]
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT title FROM expenses WHERE user_id = ? AND id = ?", (user_id, exp_id))
        row = cursor.fetchone()
        if row:
            cursor.execute("DELETE FROM expenses WHERE user_id = ? AND id = ?", (user_id, exp_id))
            conn.commit()
            await query.edit_message_text(f"✅ အသုံးစရိတ် `{row[0]}` ကို ဖျက်လိုက်ပါပြီ။", parse_mode="Markdown")
        else:
            await query.edit_message_text("❌ စာရင်းရှာမတွေ့ပါ။")
        conn.close()
    elif data.startswith("do_del_stock_"):
        stock_id = data.split("_")[3]
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT item_name FROM inventory WHERE user_id = ? AND id = ?", (user_id, stock_id))
        row = cursor.fetchone()
        if row:
            cursor.execute("DELETE FROM inventory WHERE user_id = ? AND id = ?", (user_id, stock_id))
            conn.commit()
            await query.edit_message_text(f"✅ Stock ပစ္စည်း `{row[0]}` ကို အပြီးတိုင် ဖျက်လိုက်ပါပြီ။", parse_mode="Markdown")
        else:
            await query.edit_message_text("❌ ပစ္စည်းရှာမတွေ့ပါ။")
        conn.close()

async def handle_excel_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    document = update.message.document
    if not document.file_name.endswith('.xlsx'):
        return await update.message.reply_text("❌ `.xlsx` Excel File ကိုသာ ပို့ပေးပါ။")
    
    status_msg = await update.message.reply_text("🔄 Restore လုပ်နေပါသည်...")
    try:
        temp_path = f"temp_restore_{user_id}.xlsx"
        file = await context.bot.get_file(document.file_id)
        await file.download_to_drive(temp_path)
        xls = pd.ExcelFile(temp_path)
        conn = get_db()
        cursor = conn.cursor()

        tables = ['Inventory', 'Sales', 'Expenses', 'Capital', 'Purchases']
        for table in tables:
            if table in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name=table)
                
                if table == 'Sales':
                    reverse_rename = {
                        'ID': 'id',
                        'ဝယ်သူအမည်': 'customer_name',
                        'ဖုန်းနံပါတ်': 'phone_number',
                        'ပစ္စည်း': 'item_name',
                        'အရောင်းအမျိုးအစား': 'sale_type',
                        'စုစုပေါင်းတန်ဖိုး': 'total_price',
                        'ပေးသွင်းပြီးငွေ': 'paid_amount',
                        'တစ်လပေးသွင်းငွေ': 'monthly_payment',
                        'အခြေအနေ': 'status',
                        'စရောင်းသည့်ရက်': 'date',
                        'လက်ဆောင်': 'gift_item',
                        'နောက်ဆုံးငွေဆပ်ရက်': 'last_payment_date'
                    }
                    df.rename(columns={k: v for k, v in reverse_rename.items() if k in df.columns}, inplace=True)
                
                elif table == 'Expenses':
                    reverse_rename_exp = {
                        'ID': 'id',
                        'အမျိုးအစား': 'category',
                        'အကြောင်းအရာ': 'title',
                        'ပမာဏ': 'amount',
                        'ရက်စွဲ': 'date'
                    }
                    df.rename(columns={k: v for k, v in reverse_rename_exp.items() if k in df.columns}, inplace=True)
                
                df['user_id'] = user_id
                cursor.execute(f"DELETE FROM {table.lower()} WHERE user_id = ?", (user_id,))
                df.to_sql(table.lower(), conn, if_exists='append', index=False)

        conn.commit()
        conn.close()
        os.remove(temp_path)
        await status_msg.edit_text("✅ **Excel File မှ စာရင်းများကို Restore လုပ်ပြီးပါပြီ!**")
    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {str(e)}")

async def handle_button_clicks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.message.from_user.id
    
    if text == "📦 ဝယ်ယူမည်":
        await update.message.reply_text("📦 `/buy <ပစ္စည်းအမည်> | <အရေအတွက်> | <ဝယ်ဈေး> | <Deliveryခ (Optional)>`\n\n(Deliveryခ မရှိပါက နောက်ဆုံးကပမာဏကို ချန်လှပ်ထားခဲ့ပါ)", parse_mode="Markdown")
    elif text == "💸 အသုံးစရိတ်":
        await update.message.reply_text("💸 `/expense <အမျိုးအစား> | <အကြောင်းအရာ> | <ပမာဏ>`\n\n👇 ဥပမာ\n`/expense မီးလင်းခ | ဇူလိုင်လအတွက် | 15000`\n`/expense Delivery | ပစ္စည်းပို့ခ | 3000`", parse_mode="Markdown")
    elif text == "💵 လက်ငင်းရောင်း":
        await update.message.reply_text(f"{get_available_stock_info(user_id)}\n\n💵 `/sell_cash <ဝယ်သူ> | <ပစ္စည်း> | <ရောင်းဈေး> | <ဖုန်း (Optional)> | <လက်ဆောင် (Optional)>`\n\n💡 (ဖုန်းနံပါတ် သို့မဟုတ် လက်ဆောင် မထည့်လိုပါက `-` ဟု ထည့်ပေးပါ။)\n👇 ဥပမာ\n`/sell_cash Mg Mg | Phone | 150000 | 09123456 | Cover`\n`/sell_cash Mg Mg | Phone | 150000 | - | Cover`\n`/sell_cash Mg Mg | Phone | 150000 | - | -`", parse_mode="Markdown")
    elif text == "⏳ ကြွေးရောင်း":
        await update.message.reply_text(f"{get_available_stock_info(user_id)}\n\n⏳ `/sell_installment <ဝယ်သူ> | <ပစ္စည်း> | <စုစုပေါင်းဈေး> | <စပေါ်ငွေ> | <၁လပေးရမည့်ငွေ> | <ဖုန်း (Optional)> | <လက်ဆောင် (Optional)>`\n\n💡 (ဖုန်းနံပါတ် သို့မဟုတ် လက်ဆောင် မထည့်လိုပါက `-` ဟု ထည့်ပေးပါ။)", parse_mode="Markdown")
    elif text == "🔍 ဝယ်သူရှာရန်":
        await update.message.reply_text("🔍 **ဝယ်သူအမည်ဖြင့် စာရင်းရှာရန်:**\n`/search <ဝယ်သူနာမည်>`\n👇 `/search Mg Mg`\n(အကြွေးဆုံး စာရင်းများကိုပါ ဤနေရာတွင် ရှာဖွေတွေ့ရှိနိုင်ပါသည်)", parse_mode="Markdown")
    elif text == "📈 လချုပ်/နှစ်ချုပ်":
        await update.message.reply_text("📈 `/report` (သို့) `/report 2026-07`", parse_mode="Markdown")
    elif text == "📊 လက်ကျန် Stock":
        await stock(update, context)
    elif text == "⏳ ကြွေးကျန်သူများ":
        await list_pending(update, context)
    elif text == "❌ အကြွေးဆုံး":
        await send_bad_debt_page(update, context, user_id, page=0, is_callback=False)
        await update.message.reply_text("💡 အကြွေးဆုံးအဖြစ် ပြောင်းလဲသတ်မှတ်လိုပါက `/bad_debt <Sale ID>` ကို အသုံးပြုပါ။\nဥပမာ - `/bad_debt 15`", parse_mode="Markdown")
    elif text == "📁 Excel Backup":
        await export_excel(update, context)
    elif text == "📥 Excel Restore":
        await update.message.reply_text("📥 `📁 Excel Backup` ဖြင့် ရလာသော ဖိုင်ကို ပြင်ဆင်ပြီး ဤ Chat ထဲသို့ File အနေဖြင့် ပို့ပေးပါ။")
    elif text in ["🗑️ စာရင်းဖျက်", "🗑️/✏️ ဖျက်/ပြင်"]:
        keyboard = [
            [InlineKeyboardButton("📝 အရောင်းစာရင်း ဖျက်မည်", callback_data="menu_del_sale")],
            [InlineKeyboardButton("🛒 အဝယ်စာရင်း ဖျက်မည်", callback_data="menu_del_purchase")],
            [InlineKeyboardButton("💸 အသုံးစရိတ် ဖျက်မည်", callback_data="menu_del_expense")],
            [InlineKeyboardButton("📦 Stock ပစ္စည်း ဖျက်မည်", callback_data="menu_del_stock")],
            [InlineKeyboardButton("⏪ ငွေသွင်းမှားတာ ပြန်နှုတ်မည်", callback_data="guide_undo_pay")],
            [InlineKeyboardButton("✏️ စာရင်းပြင်ရန် လမ်းညွှန်", callback_data="guide_edit")],
            [InlineKeyboardButton("💥 စာရင်းအားလုံး ဖျက်မည်", callback_data="confirm_reset_all")]
        ]
        await update.message.reply_text("🗑️/✏️ **ဖျက်လို/ပြင်လိုသည့် အမျိုးအစားကို ရွေးချယ်ပါ:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    elif text == "💰 ငွေဆပ်မည်":
        await update.message.reply_text("💰 `/pay <ဝယ်သူနာမည် သို့မဟုတ် ID> | <ပေးသည့်ပမာဏ>`\n👇 `/pay 10 | 100000`", parse_mode="Markdown")
    elif text == "📜 Command ကြည့်ရန်":
        await show_commands(update, context)
    elif text == "💵 ငွေလက်ကျန်":
        await update.message.reply_text("💵 `/add_balance <ပမာဏ>`", parse_mode="Markdown")
    elif text == "⏳ ကြွေးလက်ကျန်":
        await update.message.reply_text("⏳ `/add_credit <ဝယ်သူနာမည်> | <ပစ္စည်းအမည်> | <စုစုပေါင်းအကြွေး> | <တစ်လပေးရမည့်ငွေ> | <ဖုန်းနံပါတ်>`", parse_mode="Markdown")
    elif text == "📦 Stock အဟောင်း":
        await update.message.reply_text("📦 `/add_stock <ပစ္စည်းအမည်> | <အရေအတွက်> | <ဝယ်ဈေး>`", parse_mode="Markdown")


def main():
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=auto_ping, daemon=True).start()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("command", show_commands))
    app.add_handler(CommandHandler("search", search_customer))
    app.add_handler(CommandHandler("add_balance", add_balance))
    app.add_handler(CommandHandler("buy", buy))
    app.add_handler(CommandHandler("expense", add_expense))
    app.add_handler(CommandHandler("add_stock", add_stock))
    app.add_handler(CommandHandler("add_credit", add_credit))
    app.add_handler(CommandHandler("sell_cash", sell_cash))
    app.add_handler(CommandHandler("sell_installment", sell_installment))
    app.add_handler(CommandHandler("pay", pay))
    
    app.add_handler(CommandHandler("undo_pay", undo_pay))
    app.add_handler(CommandHandler("bad_debt", mark_bad_debt))
    app.add_handler(CommandHandler("undo_bad_debt", undo_bad_debt))
    
    app.add_handler(CommandHandler("stock", stock))
    app.add_handler(CommandHandler("list", list_pending))
    app.add_handler(CommandHandler("report", report))
    app.add_handler(CommandHandler("monthly_report", report))
    app.add_handler(CommandHandler("export", export_excel))

    app.add_handler(CallbackQueryHandler(main_callback_handler))
    app.add_handler(MessageHandler(filters.Document.MimeType("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"), handle_excel_upload))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_button_clicks))

    print("Bot is running...")
    app.run_polling()

if __name__ == '__main__':
    main()

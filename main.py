import os
import threading
import time
import requests
import re
import math
import pandas as pd
from pymongo import MongoClient
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

# ====================================================
# ⚙️ Configuration
# ====================================================
BOT_TOKEN = "8939067464:AAFlW3XMzoodS5eMwJs63jXDPRPRgFAzddE"
MONGO_URI = "mongodb+srv://User:310199@cluster0.oys0fgi.mongodb.net/?appName=Cluster0"  

client = MongoClient(MONGO_URI)
db = client["shop_management_db"]

# 🇲🇲 မြန်မာစံတော်ချိန် (UTC +6:30) သတ်မှတ်ခြင်း
MM_TZ = timezone(timedelta(hours=6, minutes=30))

# ====================================================
# 🌐 Auto Ping (Bot အိပ်မသွားစေရန်)
# ====================================================
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Bot is running 24/7 with MongoDB!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

def auto_ping():
    while True:
        time.sleep(10 * 60)
        render_url = os.environ.get("RENDER_EXTERNAL_URL")
        if render_url:
            try:
                requests.get(render_url)
            except Exception:
                pass

# ====================================================
# 📦 MongoDB Indexes & ID Sequence Helper
# ====================================================
def init_db():
    db.inventory.create_index([("user_id", 1), ("item_name", 1)], unique=True)
    db.sales.create_index([("user_id", 1), ("id", 1)])
    db.expenses.create_index([("user_id", 1), ("id", 1)])
    db.capital.create_index([("user_id", 1), ("id", 1)])
    db.purchases.create_index([("user_id", 1), ("id", 1)])

init_db()

def get_next_sequence(sequence_name):
    counter_col = db["counters"]
    counter = counter_col.find_one_and_update(
        {"_id": sequence_name},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True
    )
    return counter["seq"]

# ====================================================
# 🧰 Multi-Item Parser Helpers
# ====================================================
def parse_multi_items(raw_str, default_qty=1):
    items = []
    # Unicode အမှားများနှင့် အသုံးများသည့် အမှတ်အသားများကို Replace လုပ်ခြင်း
    raw_str = raw_str.replace('၊', ',').replace('：', ':')
    parts = [p.strip() for p in raw_str.split(",") if p.strip()]
    for part in parts:
        # 'x' သည် Gerlax ကဲ့သို့ နာမည်ထဲတွင် ပါနေပါက မခွဲရန် \s+[xX]\s+ ကို အသုံးပြုထားသည်
        subparts = [s.strip() for s in re.split(r':|\*|\s+[xX]\s+', part) if s.strip()]
        
        try:
            if len(subparts) >= 3:
                name = " ".join(subparts[:-2]).strip()
                qty = int(subparts[-2])
                price = float(subparts[-1])
            elif len(subparts) == 2:
                name = subparts[0]
                val = float(subparts[1])
                if val.is_integer() and val < 500:
                    qty = int(val)
                    price = 0.0
                else:
                    qty = default_qty
                    price = val
            elif len(subparts) == 1:
                name = subparts[0]
                qty = default_qty
                price = 0.0
            else:
                continue
            items.append({'name': name, 'qty': qty, 'price': price})
        except ValueError:
            # မှားယွင်းစွာ ထည့်မိပါက ကျော်မသွားဘဲ နာမည်အဖြစ် သတ်မှတ်ပေးရန်
            items.append({'name': part, 'qty': default_qty, 'price': 0.0})
    return items

def restore_sale_stock(user_id, item_str):
    if not item_str: return
    parts = [p.strip() for p in item_str.split(",") if p.strip()]
    for part in parts:
        match = re.search(r'^(.*?)\s*\((?:(\d+)\s*ခု|\s*(\d+))\)$', part)
        if match:
            name = match.group(1).strip()
            qty = int(match.group(2) or match.group(3))
        else:
            name = part.strip()
            qty = 1
        db.inventory.update_one(
            {"user_id": user_id, "item_name": name},
            {"$inc": {"quantity": qty}}
        )

# ====================================================
# 🎛️ Keyboard Menu
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
    await update.message.reply_text("မင်္ဂလာပါ! သင်၏ ကိုယ်ပိုင် စာရင်းကိုင် Bot (MongoDB) မှ ကြိုဆိုပါသည်။", reply_markup=get_main_keyboard())

async def show_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🛍️ **အသုံးပြုနိုင်သော Command များ:**\n\n"
        "📦 **၁။ ပစ္စည်း ဝယ်ယူခြင်း:**\n"
        "`/buy iPhone 13 : 2 : 1200000 , Cover : 10 : 5000 | 5000 | Screen Guard : 5`\n\n"
        "💵 **၂။ လက်ငင်း ရောင်းချခြင်း (လက်ဆောင်အမျိုးအစား/အရေအတွက် စိတ်ကြိုက်):**\n"
        "`/sell_cash AungAung | iPhone 13 : 2 : 1500000 | 091234567 | Cover : 2`\n\n"
        "⏳ **၃။ ကြွေးရောင်းချခြင်း (ကျန်သောလ ထည့်သွင်းခြင်း):**\n"
        "`/sell_installment MgMg | Phone : 1 : 1500000 | 300000 | 5 | 100000 | 091234567 | Cover : 2`\n\n"
        "💰 **၄။ ငွေဆပ်ခြင်း / ပြန်နှုတ်ခြင်း:**\n`/pay 10 | 100000`\n`/undo_pay 10 | 50000`\n\n"
        "❌ **၅။ အကြွေးဆုံး သတ်မှတ်ခြင်း:**\n`/bad_debt 10`\n`/undo_bad_debt 10`\n\n"
        "💸 **၆။ အသုံးစရိတ်စာရင်း:**\n`/expense မီးလင်းခ | ဇူလိုင်အတွက် | 15000`\n\n"
        "🔍 **၇။ ဝယ်သူအမည်ဖြင့် ရှာရန်:**\n`/search Mg Mg`\n\n"
        "📊 **၈။ စာရင်းများ စစ်ဆေးခြင်း:**\n`/stock`, `/list`, `/report`"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

def get_available_stock_info(user_id):
    rows = list(db.inventory.find({"user_id": user_id, "quantity": {"$gt": 0}}))
    if not rows: return "⚠️ **လက်ရှိ ရောင်းရန် Stock ပစ္စည်း လုံးဝ မရှိသေးပါ!**"
    msg = "📦 **လက်ရှိ ရောင်းရန် ရှိသော Stock ပစ္စည်းများ:**\n"
    for r in rows: msg += f"• `{r['item_name']}` - ကျန် `{r['quantity']}` ခု\n"
    return msg

async def add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    try:
        amount = float(context.args[0].strip())
        if amount < 0:
            return await update.message.reply_text("❌ ဂဏန်းများသည် အပေါင်းလက္ခဏာ (Positive) သာ ဖြစ်ရပါမည်။")
        
        today = datetime.now(MM_TZ).strftime("%Y-%m-%d")
        cap_id = get_next_sequence("capital_id")
        db.capital.insert_one({"id": cap_id, "user_id": user_id, "amount": amount, "date": today})
        
        await update.message.reply_text(f"💵 **ငွေလက်ကျန် ထည့်သွင်းပြီးပါပြီ!**\n💰 ပမာဏ: `{amount:,.0f}` MMK", parse_mode="Markdown")
    except Exception:
        await update.message.reply_text("❌ `/add_balance <ပမာဏ>` ဟုသာ ရိုက်ပါ။")

# ====================================================
# 📦 ပစ္စည်းဝယ်ယူခြင်း
# ====================================================
async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    try:
        args = " ".join(context.args).split("|")
        if len(args) < 1: 
            return await update.message.reply_text("❌ ဝယ်ယူမှု အချက်အလက် ထည့်သွင်းပါ။")
        
        raw_items_str = args[0].strip()
        items_list = []
        
        if len(args) >= 3 and args[1].strip().isdigit() and not (":" in raw_items_str or "," in raw_items_str):
            item_name = args[0].strip()
            qty = int(args[1].strip())
            cost_price = float(args[2].strip())
            items_list.append({'name': item_name, 'qty': qty, 'price': cost_price})
            
            deli_fee_str = args[3].strip() if len(args) > 3 else ""
            deli_fee = float(deli_fee_str) if deli_fee_str and deli_fee_str != '-' else 0.0
            gift_str = args[4].strip() if len(args) > 4 else ""
        else:
            items_list = parse_multi_items(raw_items_str)
            deli_fee_str = args[1].strip() if len(args) > 1 else ""
            deli_fee = float(deli_fee_str) if deli_fee_str and deli_fee_str != '-' else 0.0
            gift_str = args[2].strip() if len(args) > 2 else ""

        if gift_str == '-': gift_str = ""
        if not items_list:
            return await update.message.reply_text("❌ ဝယ်ယူသည့် ပစ္စည်းအချက်အလက် မှားယွင်းနေပါသည်။")

        today = datetime.now(MM_TZ).strftime("%Y-%m-%d")
        items_summary_txt = ""
        items_total_cost = 0.0

        for item in items_list:
            i_name, i_qty, i_price = item['name'], item['qty'], item['price']
            subtotal = i_qty * i_price
            items_total_cost += subtotal
            items_summary_txt += f"• `{i_name}` - {i_qty} ခု x {i_price:,.0f} = `{subtotal:,.0f}` MMK\n"
            
            db.inventory.update_one(
                {"user_id": user_id, "item_name": i_name},
                {"$inc": {"quantity": i_qty}, "$set": {"cost_price": i_price}},
                upsert=True
            )
            
            pur_id = get_next_sequence("purchases_id")
            db.purchases.insert_one({
                "id": pur_id,
                "user_id": user_id,
                "item_name": i_name,
                "quantity": i_qty,
                "total_cost": subtotal,
                "date": today,
                "gift_item": gift_str if item == items_list[-1] else "",
                "gift_quantity": 1
            })

        final_gift_summary = ""
        if gift_str:
            gift_list = parse_multi_items(gift_str)
            db_gift_names = []
            for g in gift_list:
                g_name, g_qty = g['name'], g['qty']
                db.inventory.update_one(
                    {"user_id": user_id, "item_name": g_name},
                    {"$inc": {"quantity": g_qty}, "$setOnInsert": {"cost_price": 0.0}},
                    upsert=True
                )
                db_gift_names.append(f"{g_name} ({g_qty}ခု)")
            final_gift_summary = ", ".join(db_gift_names)

        if deli_fee > 0:
            exp_id = get_next_sequence("expenses_id")
            db.expenses.insert_one({
                "id": exp_id,
                "user_id": user_id,
                "category": "ပို့ဆောင်ခ (Deli)",
                "title": "ဝယ်ယူမှု Delivery ခ",
                "amount": deli_fee,
                "date": today
            })

        grand_total = items_total_cost + deli_fee
        deli_msg = f"\n🚚 Delivery ခ: `{deli_fee:,.0f}` MMK" if deli_fee > 0 else ""
        gift_msg = f"\n🎁 လက်ဆောင်ပစ္စည်းများ: `{final_gift_summary}`" if final_gift_summary else ""

        reply_msg = (
            f"✅ **ပစ္စည်းဝယ်ယူမှု မှတ်တမ်းတင်ပြီးပါပြီ!**\n\n"
            f"📦 **ဝယ်ယူသည့် ပစ္စည်းများ:**\n{items_summary_txt}"
            f"───────────────────\n"
            f"💵 ပစ္စည်းစုစုပေါင်း တန်ဖိုး: `{items_total_cost:,.0f}` MMK"
            f"{deli_msg}{gift_msg}\n"
            f"───────────────────\n"
            f"💰 **စုစုပေါင်း ကျသင့်ငွေ (Grand Total):** `{grand_total:,.0f}` MMK"
        )
        await update.message.reply_text(reply_msg, parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(
            f"❌ **ဝယ်ယူမှု ပုံစံ မှားယွင်းနေပါသည်။**\n`Error: {str(e)}`\n\n"
            "👉 **ပုံစံ:** `/buy ပစ္စည်း : အရေအတွက် : ဝယ်ဈေး | Deliခ | လက်ဆောင်`",
            parse_mode="Markdown"
        )

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
        exp_id = get_next_sequence("expenses_id")
        db.expenses.insert_one({"id": exp_id, "user_id": user_id, "category": category, "title": title, "amount": amount, "date": today})
        
        await update.message.reply_text(f"💸 **ဆိုင်အသုံးစရိတ် စာရင်းသွင်းပြီးပါပြီ!**\n📂 အမျိုးအစား: `{category}`\n📝 အကြောင်းအရာ: `{title}`\n💰 ကျသင့်ငွေ: `{amount:,.0f}` MMK", parse_mode="Markdown")
    except Exception:
        await update.message.reply_text("❌ မှားယွင်းနေပါသည်။\nပုံစံ - `/expense <အမျိုးအစား> | <အကြောင်းအရာ> | <ပမာဏ>`")

async def add_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    try:
        args = " ".join(context.args).split("|")
        item_name, qty, cost_price = args[0].strip(), int(args[1].strip()), float(args[2].strip())
        if qty <= 0 or cost_price < 0:
            return await update.message.reply_text("❌ အရေအတွက်နှင့် ဈေးနှုန်းသည် မှန်ကန်ရပါမည်။")

        db.inventory.update_one(
            {"user_id": user_id, "item_name": item_name},
            {"$inc": {"quantity": qty}, "$set": {"cost_price": cost_price}},
            upsert=True
        )
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
        sale_id = get_next_sequence("sales_id")
        
        db.sales.insert_one({
            "id": sale_id,
            "user_id": user_id,
            "customer_name": customer,
            "item_name": item_name,
            "sale_type": "INSTALLMENT",
            "total_price": total_price,
            "paid_amount": 0.0,
            "monthly_payment": monthly_pay,
            "remaining_months": 0,
            "status": "PENDING",
            "date": today,
            "gift_item": "",
            "last_payment_date": "",
            "phone_number": phone
        })
        
        ph_text = f"\n📱 ဖုန်း: `{phone}`" if phone else ""
        await update.message.reply_text(f"⏳ **ကြွေးလက်ကျန် စာရင်းသွင်းပြီးပါပြီ!**\n🆔 ID: `{sale_id}`\n👤 ဝယ်သူ: `{customer}`{ph_text}\n📉 အကြွေးကျန်: `{total_price:,.0f}` MMK", parse_mode="Markdown")
    except Exception:
        await update.message.reply_text("❌ `/add_credit <ဝယ်သူ> | <ပစ္စည်း> | <အကြွေးစုစုပေါင်း> | <တစ်လပေးရမည့်ငွေ> | <ဖုန်း>` ဟုသာ ရိုက်ပါ။")

# ====================================================
# 💵 လက်ငင်း ရောင်းချခြင်း
# ====================================================
async def sell_cash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    try:
        args = " ".join(context.args).split("|")
        if len(args) < 2: 
            return await update.message.reply_text("❌ ရောင်းချမှု ပုံစံ မှားယွင်းနေပါသည်။ (ဝယ်သူ နှင့် ပစ္စည်း လိုအပ်ပါသည်)")
        
        customer = args[0].strip()
        raw_items_str = args[1].strip()
        
        # ယခင် Format အဟောင်းကို လက်ခံနိုင်ရန်
        if len(args) >= 3 and not (":" in raw_items_str or "," in raw_items_str):
            item_name = args[1].strip()
            price = float(args[2].strip())
            items_list = [{'name': item_name, 'qty': 1, 'price': price}]
            phone = args[3].strip() if len(args) > 3 else ""
            gift = args[4].strip() if len(args) > 4 else ""
        else:
            items_list = parse_multi_items(raw_items_str)
            phone = args[2].strip() if len(args) > 2 else ""
            gift = args[3].strip() if len(args) > 3 else ""

        if phone == '-': phone = ""
        if gift == '-': gift = ""

        if not items_list:
            return await update.message.reply_text("❌ ရောင်းချသည့် ပစ္စည်းအချက်အလက် မှားယွင်းနေပါသည်။")

        for item in items_list:
            i_name, i_qty = item['name'], item['qty']
            inv = db.inventory.find_one({"user_id": user_id, "item_name": i_name})
            avail = inv['quantity'] if inv else 0
            if not inv or avail < i_qty:
                return await update.message.reply_text(f"❌ **Stock မလုံလောက်ပါ!**\n`{i_name}` ပစ္စည်းမှာ လက်ရှိ `{avail}` ခုသာ ရှိပါသည်။", parse_mode="Markdown")

        gift_list = []
        if gift:
            gift_list = parse_multi_items(gift)
            for g in gift_list:
                g_name, g_qty = g['name'], g['qty']
                g_inv = db.inventory.find_one({"user_id": user_id, "item_name": g_name})
                g_avail = g_inv['quantity'] if g_inv else 0
                if not g_inv or g_avail < g_qty:
                    return await update.message.reply_text(f"❌ **လက်ဆောင် Stock မလုံလောက်ပါ!**\nလက်ဆောင်ပစ္စည်း `{g_name}` တွင် လက်ရှိ `{g_avail}` ခုသာ ရှိပါသည်။", parse_mode="Markdown")

        grand_total = 0.0
        items_summary_txt = ""
        db_items_names = []

        for item in items_list:
            i_name, i_qty, i_price = item['name'], item['qty'], item['price']
            subtotal = i_qty * i_price
            grand_total += subtotal
            items_summary_txt += f"• `{i_name}` - {i_qty} ခု x {i_price:,.0f} = `{subtotal:,.0f}` MMK\n"
            db_items_names.append(f"{i_name} ({i_qty}ခု)")
            db.inventory.update_one({"user_id": user_id, "item_name": i_name}, {"$inc": {"quantity": -i_qty}})

        final_gift_str = ""
        if gift_list:
            db_gift_names = []
            for g in gift_list:
                g_name, g_qty = g['name'], g['qty']
                db.inventory.update_one({"user_id": user_id, "item_name": g_name}, {"$inc": {"quantity": -g_qty}})
                db_gift_names.append(f"{g_name} ({g_qty}ခု)")
            final_gift_str = ", ".join(db_gift_names)

        today = datetime.now(MM_TZ).strftime("%Y-%m-%d")
        combined_item_str = ", ".join(db_items_names)
        sale_id = get_next_sequence("sales_id")

        db.sales.insert_one({
            "id": sale_id,
            "user_id": user_id,
            "customer_name": customer,
            "item_name": combined_item_str,
            "sale_type": "CASH",
            "total_price": grand_total,
            "paid_amount": grand_total,
            "monthly_payment": 0.0,
            "remaining_months": 0,
            "status": "PAID",
            "date": today,
            "gift_item": final_gift_str,
            "last_payment_date": "",
            "phone_number": phone
        })

        ph_msg = f"\n📱 ဖုန်း: `{phone}`" if phone else ""
        gift_msg = f"\n🎁 လက်ဆောင်ပစ္စည်းများ: `{final_gift_str}`" if final_gift_str else ""

        reply_msg = (
            f"💵 **လက်ငင်း ရောင်းချမှု အောင်မြင်ပါသည်။**\n"
            f"🆔 ID: `{sale_id}`\n"
            f"👤 ဝယ်သူ: `{customer}`{ph_msg}\n\n"
            f"📦 **ရောင်းချသည့် ပစ္စည်းများ:**\n{items_summary_txt}"
            f"{gift_msg}\n"
            f"───────────────────\n"
            f"💰 **စုစုပေါင်း ကျသင့်ငွေ (Grand Total):** `{grand_total:,.0f}` MMK"
        )
        await update.message.reply_text(reply_msg, parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(
            f"❌ **ရောင်းချမှု ပုံစံ မှားယွင်းနေပါသည်။**\n`Error: {str(e)}`\n\n"
            "👉 **ပုံစံ:** `/sell_cash ဝယ်သူ | ပစ္စည်း၁ : အရေအတွက်၁ : ရောင်းဈေး၁ | ဖုန်း | လက်ဆောင်`",
            parse_mode="Markdown"
        )

# ====================================================
# ⏳ ကြွေးရောင်းချခြင်း
# ====================================================
async def sell_installment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    try:
        args = " ".join(context.args).split("|")
        if len(args) < 5: 
            return await update.message.reply_text("❌ ကြွေးရောင်း ပုံစံ မှားယွင်းနေပါသည်။ (အနည်းဆုံး ဝယ်သူ, ပစ္စည်း, စပေါ်ငွေ, လ, ၁လပေး လိုအပ်ပါသည်)")
        
        customer = args[0].strip()
        raw_items_str = args[1].strip()
        down_payment = float(args[2].strip())
        months = int(args[3].strip())
        monthly_pay = float(args[4].strip())
        
        phone = args[5].strip() if len(args) > 5 else ""
        gift = args[6].strip() if len(args) > 6 else ""

        if phone == '-': phone = ""
        if gift == '-': gift = ""

        items_list = parse_multi_items(raw_items_str)
        if not items_list:
            return await update.message.reply_text("❌ ရောင်းချသည့် ပစ္စည်းအချက်အလက် မှားယွင်းနေပါသည်။")

        for item in items_list:
            i_name, i_qty = item['name'], item['qty']
            inv = db.inventory.find_one({"user_id": user_id, "item_name": i_name})
            avail = inv['quantity'] if inv else 0
            if not inv or avail < i_qty:
                return await update.message.reply_text(f"❌ **Stock မလုံလောက်ပါ!** `{i_name}` တွင် `{avail}` ခုသာ ရှိပါသည်။", parse_mode="Markdown")

        gift_list = []
        if gift:
            gift_list = parse_multi_items(gift)
            for g in gift_list:
                g_name, g_qty = g['name'], g['qty']
                g_inv = db.inventory.find_one({"user_id": user_id, "item_name": g_name})
                g_avail = g_inv['quantity'] if g_inv else 0
                if not g_inv or g_avail < g_qty:
                    return await update.message.reply_text(f"❌ **လက်ဆောင် Stock မလုံလောက်ပါ!** လက်ဆောင် `{g_name}` တွင် `{g_avail}` ခုသာ ရှိပါသည်။", parse_mode="Markdown")

        remaining_debt = months * monthly_pay
        grand_total = down_payment + remaining_debt

        db_items_names = []
        items_summary_txt = ""
        for item in items_list:
            i_name, i_qty = item['name'], item['qty']
            db_items_names.append(f"{i_name} ({i_qty}ခု)")
            items_summary_txt += f"• `{i_name}` - {i_qty} ခု\n"
            db.inventory.update_one({"user_id": user_id, "item_name": i_name}, {"$inc": {"quantity": -i_qty}})

        final_gift_str = ""
        if gift_list:
            db_gift_names = []
            for g in gift_list:
                g_name, g_qty = g['name'], g['qty']
                db.inventory.update_one({"user_id": user_id, "item_name": g_name}, {"$inc": {"quantity": -g_qty}})
                db_gift_names.append(f"{g_name} ({g_qty}ခု)")
            final_gift_str = ", ".join(db_gift_names)

        today = datetime.now(MM_TZ).strftime("%Y-%m-%d")
        combined_item_str = ", ".join(db_items_names)
        status = 'PAID' if down_payment >= grand_total else 'PENDING'
        sale_id = get_next_sequence("sales_id")

        db.sales.insert_one({
            "id": sale_id,
            "user_id": user_id,
            "customer_name": customer,
            "item_name": combined_item_str,
            "sale_type": "INSTALLMENT",
            "total_price": grand_total,
            "paid_amount": down_payment,
            "monthly_payment": monthly_pay,
            "remaining_months": months,
            "status": status,
            "date": today,
            "gift_item": final_gift_str,
            "last_payment_date": "",
            "phone_number": phone
        })

        ph_msg = f"\n📱 ဖုန်း: `{phone}`" if phone else ""
        gift_msg = f"\n🎁 လက်ဆောင်ပစ္စည်းများ: `{final_gift_str}`" if final_gift_str else ""

        reply_msg = (
            f"⏳ **ကြွေးရောင်း မှတ်တမ်းဝင်သွားပါပြီ!**\n"
            f"🆔 ID: `{sale_id}`\n"
            f"👤 ဝယ်သူ: `{customer}`{ph_msg}\n\n"
            f"📦 **ရောင်းချသည့် ပစ္စည်းများ:**\n{items_summary_txt}"
            f"{gift_msg}\n"
            f"───────────────────\n"
            f"💰 စုစုပေါင်း တန်ဖိုး: `{grand_total:,.0f}` MMK\n"
            f"💵 စပေါ်ငွေ: `{down_payment:,.0f}` MMK\n"
            f"📉 ပေးရန်ကျန်ငွေ ({months} လ x {monthly_pay:,.0f}): `{remaining_debt:,.0f}` MMK\n"
            f"📅 ကျန်ရှိသည့်လ: `{months} လ` (၁လပေး: `{monthly_pay:,.0f}`)"
        )
        await update.message.reply_text(reply_msg, parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(
            f"❌ **ကြွေးရောင်းမှု ပုံစံ မှားယွင်းနေပါသည်။**\n`Error: {str(e)}`\n\n"
            "👉 **ပုံစံ:** `/sell_installment ဝယ်သူ | ပစ္စည်း | စပေါ်ငွေ | ကျန်သောလ | ၁လပေး | ဖုန်း | လက်ဆောင်`\n",
            parse_mode="Markdown"
        )

# ====================================================
# 💰 ငွေဆပ်ခြင်း နှင့် ပြန်နှုတ်ခြင်း
# ====================================================
async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    try:
        raw_input = " ".join(context.args).strip()
        if not raw_input:
            return await update.message.reply_text("❌ ငွေဆပ်ပမာဏ ထည့်ပါ။\n`/pay <ID> | <ပမာဏ>`")

        if "|" in raw_input:
            target_str, amount_str = [p.strip() for p in raw_input.split("|")]
        else:
            parts = raw_input.rsplit(" ", 1)
            if len(parts) < 2:
                return await update.message.reply_text("❌ ငွေဆပ်ပမာဏ ထည့်ပါ။\n`/pay <ID> | <ပမာဏ>`")
            target_str, amount_str = parts[0].strip(), parts[1].strip()
        
        amount = float(amount_str)
        if amount < 0:
            return await update.message.reply_text("❌ ငွေဆပ်ပမာဏသည် အပေါင်းလက္ခဏာသာ ဖြစ်ရပါမည်။")

        if target_str.isdigit():
            rows = list(db.sales.find({"user_id": user_id, "id": int(target_str), "status": "PENDING"}))
        else:
            norm_target = " ".join(target_str.split()).lower()
            all_pending = list(db.sales.find({"user_id": user_id, "status": "PENDING", "sale_type": "INSTALLMENT"}))
            rows = [r for r in all_pending if " ".join(r['customer_name'].split()).lower() == norm_target]

        if not rows:
            return await update.message.reply_text(f"❌ `{target_str}` အတွက် အကြွေးစာရင်း မတွေ့ပါ။", parse_mode="Markdown")

        if len(rows) > 1:
            msg = f"⚠️ **စာရင်း ({len(rows)}) ခု ရှိနေပါသည်:**\n\n"
            for r in rows: msg += f"🆔 ID: `{r['id']}` | {r['customer_name']} ({r['item_name']}) - ကျန်ငွေ: `{(r['total_price']-r['paid_amount']):,.0f}`\n👉 `/pay {r['id']} | {amount:,.0f}`\n\n"
            return await update.message.reply_text(msg, parse_mode="Markdown")

        sale = rows[0]
        sale_id, customer_name, total_price, current_paid = sale['id'], sale['customer_name'], sale['total_price'], sale['paid_amount']
        
        remaining_debt = total_price - current_paid
        if amount > remaining_debt:
            return await update.message.reply_text(f"❌ ပေးရန်ကျန်ငွေ (`{remaining_debt:,.0f}` MMK) ထက် ပိုနေပါသည်။", parse_mode="Markdown")

        new_paid = current_paid + amount
        new_status = 'PAID' if new_paid >= total_price else 'PENDING'
        today = datetime.now(MM_TZ).strftime("%Y-%m-%d")

        rem = total_price - new_paid
        monthly_payment = sale.get('monthly_payment', 0)
        rem_months_str = ""
        
        update_fields = {"paid_amount": new_paid, "status": new_status, "last_payment_date": today}
        if monthly_payment > 0 and rem > 0:
            new_rem_months = math.ceil(rem / monthly_payment)
            update_fields["remaining_months"] = new_rem_months
            rem_months_str = f"\n🗓️ ကျန်သောလ: `{new_rem_months} လ` (ခန့်မှန်း)"
        elif rem <= 0:
            update_fields["remaining_months"] = 0

        db.sales.update_one({"user_id": user_id, "id": sale_id}, {"$set": update_fields})
        
        await update.message.reply_text(
            f"💰 **ငွေဆပ်မှု အောင်မြင်ပါသည်။**\n"
            f"🆔 ID: `{sale_id}`\n"
            f"👤 ဝယ်သူ: `{customer_name}`\n"
            f"💵 ပေးသွင်းငွေ: `{amount:,.0f}` MMK\n"
            f"📉 ကျန်ငွေ: `{0 if rem <= 0 else f'{rem:,.0f}'} MMK`{rem_months_str}", 
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Command အသုံးပြုမှု မှားယွင်းနေပါသည်။\n`/pay <ID> | <ပမာဏ>`\n`Error: {str(e)}`")

async def undo_pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    try:
        raw_input = " ".join(context.args).strip()
        if not raw_input: raise ValueError
        if "|" in raw_input:
            target_str, amount_str = [p.strip() for p in raw_input.split("|")]
        else:
            target_str, amount_str = [p.strip() for p in raw_input.rsplit(" ", 1)]
        
        amount = float(amount_str)
        if target_str.isdigit():
            rows = list(db.sales.find({"user_id": user_id, "id": int(target_str)}))
        else:
            norm_target = " ".join(target_str.split()).lower()
            all_sales = list(db.sales.find({"user_id": user_id, "sale_type": "INSTALLMENT"}))
            rows = [r for r in all_sales if " ".join(r['customer_name'].split()).lower() == norm_target]

        if not rows:
            return await update.message.reply_text(f"❌ `{target_str}` စာရင်း မတွေ့ပါ။", parse_mode="Markdown")

        if len(rows) > 1:
            msg = f"⚠️ **စာရင်း ({len(rows)}) ခု ရှိနေပါသည်:**\n\n"
            for r in rows: msg += f"🆔 ID: `{r['id']}` | {r['customer_name']} - သွင်းပြီး: `{r['paid_amount']:,.0f}`\n👉 `/undo_pay {r['id']} | {amount:,.0f}`\n\n"
            return await update.message.reply_text(msg, parse_mode="Markdown")

        sale = rows[0]
        sale_id, customer_name, total_price, current_paid = sale['id'], sale['customer_name'], sale['total_price'], sale['paid_amount']
        
        if amount > current_paid:
            return await update.message.reply_text(f"❌ သွင်းပြီးငွေ (`{current_paid:,.0f}`) ထက် ပိုမနှုတ်နိုင်ပါ။", parse_mode="Markdown")

        new_paid = current_paid - amount
        new_status = 'PAID' if new_paid >= total_price else 'PENDING'
        
        rem = total_price - new_paid
        monthly_payment = sale.get('monthly_payment', 0)
        rem_months_str = ""
        
        update_fields = {"paid_amount": new_paid, "status": new_status}
        if monthly_payment > 0 and rem > 0:
            new_rem_months = math.ceil(rem / monthly_payment)
            update_fields["remaining_months"] = new_rem_months
            rem_months_str = f"\n🗓️ ကျန်သောလ: `{new_rem_months} လ` (ခန့်မှန်း)"
        elif rem <= 0:
            update_fields["remaining_months"] = 0
            
        db.sales.update_one({"user_id": user_id, "id": sale_id}, {"$set": update_fields})
        
        await update.message.reply_text(
            f"✅ ပြန်လည်ပြင်ဆင်ပြီးပါပြီ။\n"
            f"🆔 ID: `{sale_id}`\n"
            f"⏪ ပြန်နှုတ်ငွေ: `{amount:,.0f}` MMK\n"
            f"📉 ကျန်ငွေ: `{rem:,.0f} MMK`{rem_months_str}", 
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ `/undo_pay <ID> | <ပမာဏ>` ဟု ရိုက်ပါ။\n`Error: {str(e)}`")

async def mark_bad_debt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    try:
        sale_id = int(context.args[0].strip())
        sale = db.sales.find_one({"user_id": user_id, "id": sale_id, "status": "PENDING"})
        if not sale:
            return await update.message.reply_text("❌ သက်ဆိုင်ရာ ID ဖြင့် PENDING စာရင်း မတွေ့ပါ။")
        
        lost_amount = sale['total_price'] - sale['paid_amount']
        db.sales.update_one({"user_id": user_id, "id": sale_id}, {"$set": {"status": 'BAD_DEBT'}})
        
        await update.message.reply_text(f"❌ **အကြွေးဆုံးစာရင်းသို့ ပြောင်းရွှေ့ပြီးပါပြီ!**\n🆔 ID: `{sale_id}`\n👤 ဝယ်သူ: `{sale['customer_name']}`\n💸 ဆုံးရှုံးငွေ: `{lost_amount:,.0f}` MMK", parse_mode="Markdown")
    except Exception:
        await update.message.reply_text("❌ `/bad_debt <Sale ID>` ဟု ရိုက်ပါ။")

async def undo_bad_debt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    try:
        sale_id = int(context.args[0].strip())
        sale = db.sales.find_one({"user_id": user_id, "id": sale_id, "status": 'BAD_DEBT'})
        if not sale:
            return await update.message.reply_text("❌ သက်ဆိုင်ရာ ID ဖြင့် အကြွေးဆုံးစာရင်း မတွေ့ပါ။")
            
        db.sales.update_one({"user_id": user_id, "id": sale_id}, {"$set": {"status": 'PENDING'}})
        await update.message.reply_text(f"✅ ID `{sale_id}` ကို ပုံမှန်အကြွေးသို့ ပြန်ပြောင်းပြီးပါပြီ။", parse_mode="Markdown")
    except Exception:
        await update.message.reply_text("❌ `/undo_bad_debt <Sale ID>` ဟု ရိုက်ပါ။")

async def search_customer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not context.args:
        return await update.message.reply_text("❌ `/search <ဝယ်သူအမည်>`", parse_mode="Markdown")
    
    search_name = " ".join(context.args).strip()
    regex = re.compile(re.escape(search_name), re.IGNORECASE)
    rows = list(db.sales.find({"user_id": user_id, "customer_name": {"$regex": regex}}).sort("date", -1))
    
    if not rows:
        return await update.message.reply_text(f"🔍 `{search_name}` အမည်ဖြင့် စာရင်း မတွေ့ပါ။", parse_mode="Markdown")
    
    total_bought, total_debt, total_bad_debt = 0, 0, 0
    msg = f"🔍 **'{search_name}' ၏ စာရင်းများ:**\n\n"
    
    for r in rows:
        rem = r['total_price'] - r['paid_amount']
        total_bought += r['total_price']
        status = r.get('status', 'PAID')
        
        if status == 'PENDING': 
            total_debt += rem
            status_icon = "🔴 အကြွေး"
            rem_months = r.get('remaining_months', 0)
            if rem_months > 0: status_icon += f" ({rem_months} လကျန်)"
        elif status == 'BAD_DEBT':
            total_bad_debt += rem
            status_icon = "❌ အကြွေးဆုံး"
        else:
            status_icon = "🟢 ရှင်းပြီး"
            
        gift_txt = f"\n🎁 လက်ဆောင်: `{r.get('gift_item', '')}`" if r.get('gift_item') else ""
        ph_txt = f"\n📱 ဖုန်း: `{r.get('phone_number', '')}`" if r.get('phone_number') else ""
        
        msg += f"🆔 ID: `{r['id']}` | 📅 စရောင်းရက်: {r['date']}{ph_txt}\n📦 ပစ္စည်း: `{r['item_name']}`{gift_txt}\n💰 တန်ဖိုး: `{r['total_price']:,.0f}` | ကျန်ငွေ: `{rem:,.0f}` ({status_icon})\n\n"
    
    msg += "───────────────────\n"
    msg += f"🛒 စုစုပေါင်း ဝယ်ယူမှု: `{total_bought:,.0f}` MMK\n"
    msg += f"⚠️ စုစုပေါင်း ပေးရန်ကျန်ငွေ: `{total_debt:,.0f}` MMK\n"
    if total_bad_debt > 0:
        msg += f"❌ စုစုပေါင်း အကြွေးဆုံး: `{total_bad_debt:,.0f}` MMK\n"
        
    await update.message.reply_text(msg, parse_mode="Markdown")

# ====================================================
# 🗂️ Pagination Helpers
# ====================================================
async def send_stock_page(update, context, user_id, page=0, is_callback=False):
    rows = list(db.inventory.find({"user_id": user_id, "quantity": {"$gt": 0}}))
    if not rows:
        msg = "📦 လက်ရှိ Stock လုံးဝ မရှိသေးပါ။"
        return await (update.callback_query.edit_message_text(msg) if is_callback else update.message.reply_text(msg))

    total_stock_value = sum(r['quantity'] * r.get('cost_price', 0.0) for r in rows)
    ITEMS_PER_PAGE = 15
    total_pages = (len(rows) - 1) // ITEMS_PER_PAGE + 1
    page = max(0, min(page, total_pages - 1))
    page_rows = rows[page * ITEMS_PER_PAGE : (page + 1) * ITEMS_PER_PAGE]

    msg = f"📊 **လက်ကျန် Stock (စာမျက်နှာ {page+1}/{total_pages}):**\n\n"
    for r in page_rows:
        val = r['quantity'] * r.get('cost_price', 0.0)
        msg += f"• `{r['item_name']}` - `{r['quantity']}` ခု (တန်ဖိုး: `{val:,.0f}` MMK)\n"
    
    msg += "\n───────────────────\n"
    msg += f"📦 **စုစုပေါင်း Stock တန်ဖိုး:** `{total_stock_value:,.0f}` MMK\n"

    buttons = []
    if page > 0: buttons.append(InlineKeyboardButton("⬅️ ယခင်", callback_data=f"stock_page_{page-1}"))
    if page < total_pages - 1: buttons.append(InlineKeyboardButton("နောက်သို့ ➡️", callback_data=f"stock_page_{page+1}"))
    reply_markup = InlineKeyboardMarkup([buttons]) if buttons else None

    if is_callback:
        await update.callback_query.edit_message_text(msg, parse_mode="Markdown", reply_markup=reply_markup)
    else:
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=reply_markup)

async def send_list_page(update, context, user_id, page=0, is_callback=False):
    rows = list(db.sales.find({"user_id": user_id, "status": 'PENDING'}))
    if not rows:
        msg = "🎉 အရစ်ကျ ကျန်ရှိသူ စာရင်း မရှိပါ။"
        return await (update.callback_query.edit_message_text(msg) if is_callback else update.message.reply_text(msg))

    total_pending = sum((r['total_price'] - r['paid_amount']) for r in rows)
    ITEMS_PER_PAGE = 10
    total_pages = (len(rows) - 1) // ITEMS_PER_PAGE + 1
    page = max(0, min(page, total_pages - 1))
    page_rows = rows[page * ITEMS_PER_PAGE : (page + 1) * ITEMS_PER_PAGE]

    msg = f"⏳ **ကြွေးကျန်သူများ (စာမျက်နှာ {page+1}/{total_pages}):**\n\n"
    for r in page_rows:
        rem = r['total_price'] - r['paid_amount']
        months_str = f" | ကျန်လ: {r.get('remaining_months', 0)}လ" if r.get('remaining_months') else ""
        msg += f"ID: {r['id']} | နာမည်: `{r['customer_name']}`\n📦 {r['item_name']} | ကျန်ငွေ: {rem:,.0f}{months_str} | ၁လပေး: {r.get('monthly_payment', 0):,.0f}\n\n"
    
    msg += f"💰 **စုစုပေါင်း ရရန်ရှိကြွေး:** `{total_pending:,.0f}` MMK\n"

    buttons = []
    if page > 0: buttons.append(InlineKeyboardButton("⬅️ ယခင်", callback_data=f"list_page_{page-1}"))
    if page < total_pages - 1: buttons.append(InlineKeyboardButton("နောက်သို့ ➡️", callback_data=f"list_page_{page+1}"))
    reply_markup = InlineKeyboardMarkup([buttons]) if buttons else None

    if is_callback:
        await update.callback_query.edit_message_text(msg, parse_mode="Markdown", reply_markup=reply_markup)
    else:
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=reply_markup)

async def send_bad_debt_page(update, context, user_id, page=0, is_callback=False):
    rows = list(db.sales.find({"user_id": user_id, "status": 'BAD_DEBT'}))
    if not rows:
        msg = "🎉 အကြွေးဆုံးစာရင်း လုံးဝ မရှိသေးပါ။"
        return await (update.callback_query.edit_message_text(msg) if is_callback else update.message.reply_text(msg))

    total_lost = sum((r['total_price'] - r['paid_amount']) for r in rows)
    ITEMS_PER_PAGE = 10
    total_pages = (len(rows) - 1) // ITEMS_PER_PAGE + 1
    page = max(0, min(page, total_pages - 1))
    page_rows = rows[page * ITEMS_PER_PAGE : (page + 1) * ITEMS_PER_PAGE]

    msg = f"❌ **အကြွေးဆုံးစာရင်း (စာမျက်နှာ {page+1}/{total_pages}):**\n\n"
    for r in page_rows:
        rem = r['total_price'] - r['paid_amount']
        msg += f"ID: {r['id']} | 👤 `{r['customer_name']}`\n📦 {r['item_name']} | ဆုံးရှုံးငွေ: `{rem:,.0f}`\n\n"
    
    msg += f"⚠️ **စုစုပေါင်း အကြွေးဆုံးငွေ:** `{total_lost:,.0f}` MMK\n"

    buttons = []
    if page > 0: buttons.append(InlineKeyboardButton("⬅️ ယခင်", callback_data=f"bad_debt_page_{page-1}"))
    if page < total_pages - 1: buttons.append(InlineKeyboardButton("နောက်သို့ ➡️️", callback_data=f"bad_debt_page_{page+1}"))
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
# 📊 အရှုံးအမြတ် Report
# ====================================================
async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    try:
        args = context.args
        if args:
            period = args[0].strip()
            period_label = f"{period} ခုနှစ်ချုပ်" if len(period) == 4 else f"{period} လချုပ်"
        else:
            period = datetime.now(MM_TZ).strftime("%Y-%m")
            period_label = f"{period} လချုပ်"

        sales_all = list(db.sales.find({"user_id": user_id}))
        expenses_all = list(db.expenses.find({"user_id": user_id}))
        capital_all = list(db.capital.find({"user_id": user_id}))
        purchases_all = list(db.purchases.find({"user_id": user_id}))
        inventory_all = list(db.inventory.find({"user_id": user_id, "quantity": {"$gt": 0}}))

        sales_period = [s for s in sales_all if s.get("date", "").startswith(period) and s.get("status") != 'BAD_DEBT']
        bad_debt_period = [s for s in sales_all if s.get("date", "").startswith(period) and s.get("status") == 'BAD_DEBT']
        bad_debt_loss = sum((s['total_price'] - s['paid_amount']) for s in bad_debt_period)

        expenses_period = [e for e in expenses_all if e.get("date", "").startswith(period)]
        total_expense = sum(e['amount'] for e in expenses_period)

        expense_breakdown = {}
        for e in expenses_period:
            cat = e.get('category', 'အထွေထွေ')
            expense_breakdown[cat] = expense_breakdown.get(cat, 0.0) + e['amount']

        added_capital = sum(c['amount'] for c in capital_all if c.get("date", "").startswith(period))
        total_purchases = sum(p['total_cost'] for p in purchases_all if p.get("date", "").startswith(period))

        past_collected = sum(s['paid_amount'] for s in sales_all if s.get("date", "") < period)
        past_expense = sum(e['amount'] for e in expenses_all if e.get("date", "") < period)
        past_capital = sum(c['amount'] for c in capital_all if c.get("date", "") < period)
        past_purchases = sum(p['total_cost'] for p in purchases_all if p.get("date", "") < period)

        total_stock = sum(i['quantity'] * i.get('cost_price', 0.0) for i in inventory_all)
        total_pending_debt = sum((s['total_price'] - s['paid_amount']) for s in sales_all if s.get("status") == 'PENDING')
        total_bad_debt_all_time = sum((s['total_price'] - s['paid_amount']) for s in sales_all if s.get("status") == 'BAD_DEBT')

        inv_map = {i['item_name']: i.get('cost_price', 0.0) for i in db.inventory.find({"user_id": user_id})}
        total_cogs = 0.0
        for s in sales_period:
            items = parse_multi_items(s.get('item_name', ''))
            for it in items:
                total_cogs += it['qty'] * inv_map.get(it['name'], 0.0)

        total_sales_value = sum(s['total_price'] for s in sales_period)
        total_collected = sum(s['paid_amount'] for s in sales_period)

        net_profit = total_sales_value - total_cogs - total_expense - bad_debt_loss
        profit_status = "🟢 အမြတ်" if net_profit >= 0 else "🔴 အရှုံး"

        opening_balance = past_capital + past_collected - past_expense - past_purchases
        current_month_cashflow = added_capital + total_collected - total_expense - total_purchases
        closing_balance = opening_balance + current_month_cashflow

        exp_breakdown_str = ""
        if expense_breakdown:
            exp_breakdown_str = "\n".join([f"   • {k}: `{v:,.0f}`" for k, v in expense_breakdown.items()])
            exp_breakdown_str = f"\n📂 **အသုံးစရိတ် အသေးစိတ်:**\n{exp_breakdown_str}\n"

        bad_debt_txt = f"\n❌ အကြွေးဆုံး: `{bad_debt_loss:,.0f}` MMK" if bad_debt_loss > 0 else ""

        msg = (
            f"📊 **{period_label} အရှုံးအမြတ်နှင့် လက်ကျန် စာရင်း**\n\n"
            f"🏦 **ယခင်လ လက်ကျန်ငွေ:** `{opening_balance:,.0f}` MMK\n"
            "───────────────────\n"
            f"🛒 အရောင်းပမာဏ: `{total_sales_value:,.0f}` MMK\n"
            f"💵 ရောင်းရငွေ (လက်ဝယ်ရငွေ): `{total_collected:,.0f}` MMK\n"
            f"📉 ရရန်ကျန်ငွေ: `{(total_sales_value - total_collected):,.0f}` MMK\n"
            f"📦 ရောင်းရပစ္စည်း ရင်းနှီးစရိတ်: `{total_cogs:,.0f}` MMK\n"
            "───────────────────\n"
            f"📥 အရင်းထည့်ငွေ: `{added_capital:,.0f}` MMK\n"
            f"📤 အဝယ်စရိတ်: `{total_purchases:,.0f}` MMK\n"
            f"💸 အသုံးစရိတ်: `{total_expense:,.0f}` MMK\n"
            f"{exp_breakdown_str}{bad_debt_txt}\n"
            "───────────────────\n"
            f"{profit_status} (အသားတင်): `{abs(net_profit):,.0f}` MMK\n"
            f"💰 **နောက်ဆုံး ငွေလက်ကျန်**: `{closing_balance:,.0f}` MMK\n"
            "───────────────────\n"
            f"📦 **Stock တန်ဖိုး:** `{total_stock:,.0f}` MMK\n"
            f"⏳ **စုစုပေါင်း ကြွေးကျန်:** `{total_pending_debt:,.0f}` MMK\n"
            f"❌ **စုစုပေါင်း အကြွေးဆုံး:** `{total_bad_debt_all_time:,.0f}` MMK"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

# ====================================================
# 📁 Excel Export & Restore
# ====================================================
def get_df_from_collection(collection_name, user_id):
    data = list(db[collection_name].find({"user_id": user_id}))
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    if "_id" in df.columns:
        df.drop(columns=["_id"], inplace=True)
    return df

async def export_excel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    await update.message.reply_text("🔄 Excel ဖိုင်ထုတ်ပေးနေပါသည် ခဏစောင့်ပါ...")
    try:
        file_path = f"Shop_Data_{user_id}.xlsx"
        
        sales_data = list(db.sales.find({"user_id": user_id, "status": {"$ne": "BAD_DEBT"}}))
        t_sales = sum(s.get('total_price', 0) for s in sales_data)
        t_collected = sum(s.get('paid_amount', 0) for s in sales_data)
        t_expense = sum(e.get('amount', 0) for e in db.expenses.find({"user_id": user_id}))
        t_capital = sum(c.get('amount', 0) for c in db.capital.find({"user_id": user_id}))
        t_purchases = sum(p.get('total_cost', 0) for p in db.purchases.find({"user_id": user_id}))
        t_stock = sum(i['quantity'] * i.get('cost_price', 0) for i in db.inventory.find({"user_id": user_id, "quantity": {"$gt": 0}}))
        final_cash = t_capital + t_collected - t_expense - t_purchases
        
        df_summary = pd.DataFrame({
            "အကြောင်းအရာ (Description)": ["စုစုပေါင်း အရောင်း", "ရောင်းရငွေ", "ရရန်ကျန်ငွေ", "ထည့်သွင်းငွေ/အရင်း", "အဝယ်စရိတ်", "အသုံးစရိတ်", "✅ နောက်ဆုံး ငွေလက်ကျန်", "📦 ဆိုင်ရှိ Stock တန်ဖိုး"],
            "ပမာဏ (Amount MMK)": [t_sales, t_collected, t_sales - t_collected, t_capital, t_purchases, t_expense, final_cash, t_stock]
        })
        
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            df_summary.to_excel(writer, sheet_name='Summary (စာရင်းချုပ်)', index=False)
            
            get_df_from_collection("inventory", user_id).to_excel(writer, sheet_name='Inventory', index=False)
            
            df_sales = get_df_from_collection("sales", user_id)
            if not df_sales.empty:
                df_sales.rename(columns={
                    'id': 'ID', 'customer_name': 'ဝယ်သူအမည်', 'phone_number': 'ဖုန်းနံပါတ်',
                    'item_name': 'ပစ္စည်း', 'sale_type': 'အရောင်းအမျိုးအစား', 'total_price': 'စုစုပေါင်းတန်ဖိုး',
                    'paid_amount': 'ပေးသွင်းပြီးငွေ', 'monthly_payment': 'တစ်လပေးသွင်းငွေ',
                    'remaining_months': 'ကျန်သောလ',
                    'status': 'အခြေအနေ', 'date': 'စရောင်းသည့်ရက်', 'gift_item': 'လက်ဆောင်', 'last_payment_date': 'နောက်ဆုံးငွေဆပ်ရက်'
                }, inplace=True)
                df_sales.to_excel(writer, sheet_name='Sales', index=False)
            
            df_bad = get_df_from_collection("sales", user_id)
            if not df_bad.empty:
                df_bad = df_bad[df_bad['status'] == 'BAD_DEBT']
                if not df_bad.empty:
                    df_bad['lost_amount'] = df_bad['total_price'] - df_bad['paid_amount']
                    df_bad.rename(columns={
                        'id': 'ID', 'customer_name': 'ဝယ်သူအမည်', 'phone_number': 'ဖုန်းနံပါတ်',
                        'item_name': 'ပစ္စည်း', 'total_price': 'စုစုပေါင်းတန်ဖိုး', 'paid_amount': 'ပေးသွင်းပြီးငွေ',
                        'lost_amount': 'ဆုံးရှုံးငွေ (အကြွေးဆုံး)', 'date': 'စရောင်းသည့်ရက်'
                    }, inplace=True)
                    df_bad.to_excel(writer, sheet_name='Bad Debts (အကြွေးဆုံး)', index=False)
            
            df_expenses = get_df_from_collection("expenses", user_id)
            if not df_expenses.empty:
                df_expenses.rename(columns={'id': 'ID', 'category': 'အမျိုးအစား', 'title': 'အကြောင်းအရာ', 'amount': 'ပမာဏ', 'date': 'ရက်စွဲ'}, inplace=True)
                df_expenses.to_excel(writer, sheet_name='Expenses', index=False)
            
            get_df_from_collection("capital", user_id).to_excel(writer, sheet_name='Capital', index=False)
            
            df_purchases = get_df_from_collection("purchases", user_id)
            if not df_purchases.empty:
                df_purchases.rename(columns={
                    'id': 'ID', 'item_name': 'ပစ္စည်း', 'quantity': 'အရေအတွက်',
                    'total_cost': 'စုစုပေါင်းကျသင့်ငွေ', 'date': 'ရက်စွဲ', 'gift_item': 'လက်ဆောင်ပစ္စည်း', 'gift_quantity': 'လက်ဆောင်အရေအတွက်'
                }, inplace=True)
                df_purchases.to_excel(writer, sheet_name='Purchases', index=False)
            
        await update.message.reply_document(document=open(file_path, 'rb'), caption="📊 သင့်စာရင်းများနှင့် နောက်ဆုံးငွေလက်ကျန် အချုပ်ပါဝင်သော Excel ဖိုင်ဖြစ်ပါသည်။")
        os.remove(file_path)
    except Exception as e:
        await update.message.reply_text(f"❌ Excel export Error: {str(e)}")

async def handle_excel_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    document = update.message.document
    if not document.file_name.endswith('.xlsx'):
        return await update.message.reply_text("❌ `.xlsx` Excel File ကိုသာ ပို့ပေးပါ။")
    
    status_msg = await update.message.reply_text("🔄 MongoDB သို့ Restore လုပ်နေပါသည်...")
    try:
        temp_path = f"temp_restore_{user_id}.xlsx"
        file = await context.bot.get_file(document.file_id)
        await file.download_to_drive(temp_path)
        xls = pd.ExcelFile(temp_path)

        tables = {'Inventory': 'inventory', 'Sales': 'sales', 'Expenses': 'expenses', 'Capital': 'capital', 'Purchases': 'purchases'}
        
        for sheet_name, coll_name in tables.items():
            if sheet_name in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name=sheet_name)
                if df.empty: continue
                
                if coll_name == 'sales':
                    reverse_rename = {
                        'ID': 'id', 'ဝယ်သူအမည်': 'customer_name', 'ဖုန်းနံပါတ်': 'phone_number',
                        'ပစ္စည်း': 'item_name', 'အရောင်းအမျိုးအစား': 'sale_type', 'စုစုပေါင်းတန်ဖိုး': 'total_price',
                        'ပေးသွင်းပြီးငွေ': 'paid_amount', 'တစ်လပေးသွင်းငွေ': 'monthly_payment',
                        'ကျန်သောလ': 'remaining_months',
                        'အခြေအနေ': 'status', 'စရောင်းသည့်ရက်': 'date', 'လက်ဆောင်': 'gift_item', 'နောက်ဆုံးငွေဆပ်ရက်': 'last_payment_date'
                    }
                    df.rename(columns={k: v for k, v in reverse_rename.items() if k in df.columns}, inplace=True)
                    
                    if 'phone_number' not in df.columns: df['phone_number'] = ""
                    if 'gift_item' not in df.columns: df['gift_item'] = ""
                    if 'last_payment_date' not in df.columns: df['last_payment_date'] = ""
                    if 'remaining_months' not in df.columns: df['remaining_months'] = 0
                    if 'monthly_payment' not in df.columns: df['monthly_payment'] = 0.0

                elif coll_name == 'expenses':
                    reverse_rename_exp = {'ID': 'id', 'အမျိုးအစား': 'category', 'အကြောင်းအရာ': 'title', 'ပမာဏ': 'amount', 'ရက်စွဲ': 'date'}
                    df.rename(columns={k: v for k, v in reverse_rename_exp.items() if k in df.columns}, inplace=True)
                    if 'category' not in df.columns: df['category'] = 'အထွေထွေ'

                elif coll_name == 'purchases':
                    reverse_rename_pur = {'ID': 'id', 'ပစ္စည်း': 'item_name', 'အရေအတွက်': 'quantity', 'စုစုပေါင်းကျသင့်ငွေ': 'total_cost', 'ရက်စွဲ': 'date', 'လက်ဆောင်ပစ္စည်း': 'gift_item', 'လက်ဆောင်အရေအတွက်': 'gift_quantity'}
                    df.rename(columns={k: v for k, v in reverse_rename_pur.items() if k in df.columns}, inplace=True)
                    if 'gift_item' not in df.columns: df['gift_item'] = ""
                    if 'gift_quantity' not in df.columns: df['gift_quantity'] = 0
                
                df['user_id'] = user_id
                db[coll_name].delete_many({"user_id": user_id})
                
                records = df.to_dict(orient='records')
                cleaned_records = [{k: (None if pd.isna(v) else v) for k, v in rec.items()} for rec in records]
                if cleaned_records:
                    db[coll_name].insert_many(cleaned_records)

        os.remove(temp_path)
        await status_msg.edit_text("✅ **Excel File မှ စာရင်းများကို MongoDB သို့ (ဖိုင်ဟောင်းများပါမကျန်) အောင်မြင်စွာ Restore ပြီးပါပြီ!**")
    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {str(e)}")

# ====================================================
# 🔄 Delete Helpers & Callbacks
# ====================================================
async def refresh_del_sale_menu(update, user_id, msg=""):
    query = update.callback_query
    rows = list(db.sales.find({"user_id": user_id}).sort("id", -1).limit(10))
    prefix = f"{msg}\n\n" if msg else ""
    if not rows:
        keyboard = [[InlineKeyboardButton("🔙 နောက်သို့", callback_data="cancel_action")]]
        return await query.edit_message_text(f"{prefix}🎉 ဖျက်စရာ အရောင်းစာရင်း မရှိတော့ပါ။", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    keyboard = [[InlineKeyboardButton(f"ID:{r['id']} | {r['customer_name']} ({r['item_name']})", callback_data=f"do_del_sale_{r['id']}")] for r in rows]
    keyboard.append([InlineKeyboardButton("🔙 နောက်သို့", callback_data="cancel_action")])
    await query.edit_message_text(f"{prefix}🗑️ **ဖျက်လိုသော အရောင်းစာရင်းကို ရွေးပါ:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def refresh_del_pur_menu(update, user_id, msg=""):
    query = update.callback_query
    rows = list(db.purchases.find({"user_id": user_id}).sort("id", -1).limit(10))
    prefix = f"{msg}\n\n" if msg else ""
    if not rows:
        keyboard = [[InlineKeyboardButton("🔙 နောက်သို့", callback_data="cancel_action")]]
        return await query.edit_message_text(f"{prefix}🎉 ဖျက်စရာ အဝယ်စာရင်း မရှိတော့ပါ။", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    keyboard = [[InlineKeyboardButton(f"ID:{r['id']} | {r['item_name']} ({r['quantity']}ခု)", callback_data=f"do_del_pur_{r['id']}")] for r in rows]
    keyboard.append([InlineKeyboardButton("🔙 နောက်သို့", callback_data="cancel_action")])
    await query.edit_message_text(f"{prefix}🗑️ **နောက်ဆုံး အဝယ်စာရင်းများ:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def refresh_del_exp_menu(update, user_id, msg=""):
    query = update.callback_query
    rows = list(db.expenses.find({"user_id": user_id}).sort("id", -1).limit(10))
    prefix = f"{msg}\n\n" if msg else ""
    if not rows:
        keyboard = [[InlineKeyboardButton("🔙 နောက်သို့", callback_data="cancel_action")]]
        return await query.edit_message_text(f"{prefix}🎉 ဖျက်စရာ အသုံးစရိတ်စာရင်း မရှိတော့ပါ။", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    keyboard = [[InlineKeyboardButton(f"ID:{r['id']} | {r['category']} ({r['title']}) - {r['amount']:,.0f}", callback_data=f"do_del_exp_{r['id']}")] for r in rows]
    keyboard.append([InlineKeyboardButton("🔙 နောက်သို့", callback_data="cancel_action")])
    await query.edit_message_text(f"{prefix}🗑️ **နောက်ဆုံး အသုံးစရိတ်စာရင်းများ:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def refresh_del_stock_menu(update, user_id, msg=""):
    query = update.callback_query
    rows = list(db.inventory.find({"user_id": user_id}))
    prefix = f"{msg}\n\n" if msg else ""
    if not rows:
        keyboard = [[InlineKeyboardButton("🔙 နောက်သို့", callback_data="cancel_action")]]
        return await query.edit_message_text(f"{prefix}🎉 ဖျက်စရာ Stock ပစ္စည်း မရှိတော့ပါ။", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    keyboard = [[InlineKeyboardButton(f"📦 {r['item_name']}", callback_data=f"do_del_stock_{r['item_name']}")] for r in rows]
    keyboard.append([InlineKeyboardButton("🔙 နောက်သို့", callback_data="cancel_action")])
    await query.edit_message_text(f"{prefix}🗑️ **ဖျက်လိုသော Stock ပစ္စည်းကို ရွေးပါ:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def main_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    data = query.data

    if data.startswith("stock_page_"):
        await send_stock_page(update, context, user_id, page=int(data.split("_")[2]), is_callback=True)
    elif data.startswith("list_page_"):
        await send_list_page(update, context, user_id, page=int(data.split("_")[2]), is_callback=True)
    elif data.startswith("bad_debt_page_"):
        await send_bad_debt_page(update, context, user_id, page=int(data.split("_")[3]), is_callback=True)

    elif data == "confirm_reset_all":
        for collection in ["inventory", "sales", "expenses", "capital", "purchases"]:
            db[collection].delete_many({"user_id": user_id})
        await query.edit_message_text("💥 **စာရင်း အားလုံးကို ဖျက်ပစ်ပြီးပါပြီ!**", parse_mode="Markdown")
    elif data == "cancel_action":
        await query.edit_message_text("❌ လုပ်ဆောင်ချက်ကို ပယ်ဖျက်လိုက်ပါပြီ။")
    elif data == "guide_edit":
        await query.edit_message_text("✏️ **စာရင်းပြင်ရန်:** မှားယွင်းသော စာရင်းကို ဖျက်ပြီးအသစ်ပြန်သွင်းပါ သို့မဟုတ် Excel ဖြင့် ပြင်ဆင် Restore လုပ်ပါ။", parse_mode="Markdown")
    elif data == "guide_undo_pay":
        await query.edit_message_text("⏪ **ငွေသွင်းမှားတာ ပြန်နှုတ်ရန်:**\n`/undo_pay <ID> | <ပမာဏ>` ဟု ရိုက်ပါ။", parse_mode="Markdown")
    
    elif data == "menu_del_sale": await refresh_del_sale_menu(update, user_id)
    elif data == "menu_del_purchase": await refresh_del_pur_menu(update, user_id)
    elif data == "menu_del_expense": await refresh_del_exp_menu(update, user_id)
    elif data == "menu_del_stock": await refresh_del_stock_menu(update, user_id)

    elif data.startswith("do_del_sale_"):
        sale_id = int(data.split("_")[3])
        sale = db.sales.find_one({"user_id": user_id, "id": sale_id})
        if sale:
            db.sales.delete_one({"user_id": user_id, "id": sale_id})
            restore_sale_stock(user_id, sale.get('item_name'))
            if sale.get('gift_item'): restore_sale_stock(user_id, sale.get('gift_item'))
            await refresh_del_sale_menu(update, user_id, msg=f"✅ ID `{sale_id}` အရောင်းစာရင်း ဖျက်ပြီး Stock ပြန်ပေါင်းပြီးပါပြီ။")
        else:
            await refresh_del_sale_menu(update, user_id, msg="❌ စာရင်းရှာမတွေ့ပါ။")
        
    elif data.startswith("do_del_pur_"):
        pur_id = int(data.split("_")[3])
        pur = db.purchases.find_one({"user_id": user_id, "id": pur_id})
        if pur:
            db.purchases.delete_one({"user_id": user_id, "id": pur_id})
            db.inventory.update_one({"user_id": user_id, "item_name": pur['item_name']}, {"$inc": {"quantity": -pur['quantity']}})
            if pur.get('gift_item') and pur.get('gift_quantity', 0) > 0:
                db.inventory.update_one({"user_id": user_id, "item_name": pur['gift_item']}, {"$inc": {"quantity": -pur['gift_quantity']}})
            await refresh_del_pur_menu(update, user_id, msg=f"✅ ID `{pur_id}` အဝယ်စာရင်း ဖျက်ပြီး Stock မှ ပြန်နှုတ်ပြီးပါပြီ။")
        else:
            await refresh_del_pur_menu(update, user_id, msg="❌ စာရင်းရှာမတွေ့ပါ။")
        
    elif data.startswith("do_del_exp_"):
        exp_id = int(data.split("_")[3])
        db.expenses.delete_one({"user_id": user_id, "id": exp_id})
        await refresh_del_exp_menu(update, user_id, msg="✅ အသုံးစရိတ် ဖျက်ပြီးပါပြီ။")

    elif data.startswith("do_del_stock_"):
        item_name = data.replace("do_del_stock_", "")
        db.inventory.delete_one({"user_id": user_id, "item_name": item_name})
        await refresh_del_stock_menu(update, user_id, msg=f"✅ Stock ပစ္စည်း `{item_name}` ကို ဖျက်လိုက်ပါပြီ။")


# ====================================================
# 🎛️ Message Handling (Button Clicks / Fallbacks)
# ====================================================
async def handle_button_clicks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.message.from_user.id
    
    match = re.search(r'(/[\w_]+)\s*(.*)', text)
    if match and not text.startswith("/"):
        cmd = match.group(1)
        args_text = match.group(2)
        context.args = args_text.split()
        
        if cmd == "/pay": return await pay(update, context)
        elif cmd == "/undo_pay": return await undo_pay(update, context)
        elif cmd == "/buy": return await buy(update, context)
        elif cmd == "/sell_cash": return await sell_cash(update, context)
        elif cmd == "/sell_installment": return await sell_installment(update, context)
        elif cmd == "/expense": return await add_expense(update, context)
        elif cmd == "/add_stock": return await add_stock(update, context)
        elif cmd == "/add_credit": return await add_credit(update, context)
        elif cmd == "/bad_debt": return await mark_bad_debt(update, context)
        elif cmd == "/undo_bad_debt": return await undo_bad_debt(update, context)
        elif cmd == "/search": return await search_customer(update, context)
    
    if text == "📦 ဝယ်ယူမည်":
        await update.message.reply_text("💡 **အောက်ပါအတိုင်း ရိုက်ပါ -**\n\n`/buy ပစ္စည်း : အရေအတွက် : ဝယ်ဈေး | Deliခ | လက်ဆောင် : အရေအတွက်`", parse_mode="Markdown")
    elif text == "💸 အသုံးစရိတ်":
        await update.message.reply_text("💡 **အောက်ပါအတိုင်း ရိုက်ပါ -**\n\n`/expense အမျိုးအစား | အကြောင်းအရာ | ပမာဏ`", parse_mode="Markdown")
    elif text == "💵 လက်ငင်းရောင်း":
        await update.message.reply_text(f"{get_available_stock_info(user_id)}\n\n💡 **အောက်ပါအတိုင်း ရိုက်ပါ -**\n\n`/sell_cash ဝယ်သူ | ပစ္စည်း : အရေအတွက် : ရောင်းဈေး | ဖုန်း | လက်ဆောင်`", parse_mode="Markdown")
    elif text == "⏳ ကြွေးရောင်း":
        await update.message.reply_text(f"{get_available_stock_info(user_id)}\n\n💡 **အောက်ပါအတိုင်း ရိုက်ပါ -**\n\n`/sell_installment ဝယ်သူ | ပစ္စည်း | စပေါ်ငွေ | ကျန်သောလ | ၁လပေး | ဖုန်း | လက်ဆောင်`", parse_mode="Markdown")
    elif text == "🔍 ဝယ်သူရှာရန်":
        await update.message.reply_text("🔍 **ရှာရန် -**\n`/search ဝယ်သူနာမည်`", parse_mode="Markdown")
    elif text == "📈 လချုပ်/နှစ်ချုပ်":
        await update.message.reply_text("📈 **စာရင်းကြည့်ရန် -**\n`/report` သို့မဟုတ် `/report 2026-09`", parse_mode="Markdown")
    elif text == "📊 လက်ကျန် Stock": await stock(update, context)
    elif text == "⏳ ကြွေးကျန်သူများ": await list_pending(update, context)
    elif text == "❌ အကြွေးဆုံး":
        await send_bad_debt_page(update, context, user_id, page=0, is_callback=False)
        await update.message.reply_text("💡 **အကြွေးဆုံးသတ်မှတ်ရန် -**\n`/bad_debt Sale_ID`", parse_mode="Markdown")
    elif text == "📁 Excel Backup": await export_excel(update, context)
    elif text == "📥 Excel Restore":
        await update.message.reply_text("📥 Excel ဖိုင် (ဖိုင်ဟောင်း/ဖိုင်သစ်) ကို ဤ Chat ထဲသို့ တိုက်ရိုက် ပို့ပေးပါ။")
    elif text in ["🗑️ စာရင်းဖျက်", "🗑️/✏️ ဖျက်/ပြင်"]:
        keyboard = [
            [InlineKeyboardButton("📝 အရောင်းစာရင်း ဖျက်မည်", callback_data="menu_del_sale")],
            [InlineKeyboardButton("🛒 အဝယ်စာရင်း ဖျက်မည်", callback_data="menu_del_purchase")],
            [InlineKeyboardButton("💸 အသုံးစရိတ် ဖျက်မည်", callback_data="menu_del_expense")],
            [InlineKeyboardButton("📦 Stock ပစ္စည်း ဖျက်မည်", callback_data="menu_del_stock")],
            [InlineKeyboardButton("⏪ ငွေသွင်းမှားတာ ပြန်နှုတ်မည်", callback_data="guide_undo_pay")],
            [InlineKeyboardButton("💥 စာရင်းအားလုံး ဖျက်မည်", callback_data="confirm_reset_all")]
        ]
        await update.message.reply_text("🗑️/✏️ **ဖျက်လိုသည့် အမျိုးအစားကို ရွေးပါ:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    elif text == "💰 ငွေဆပ်မည်": 
        await update.message.reply_text("💡 **ငွေဆပ်ရန် အောက်ပါအတိုင်း ရိုက်ထည့်ပါ -**\n\n`/pay ID | ပမာဏ`\n(ဥပမာ - `/pay 10 | 50000`)", parse_mode="Markdown")
    elif text == "📜 Command ကြည့်ရန်": await show_commands(update, context)
    elif text == "💵 ငွေလက်ကျန်": await update.message.reply_text("💵 **ထည့်ရန် -**\n`/add_balance ပမာဏ`", parse_mode="Markdown")
    elif text == "⏳ ကြွေးလက်ကျန်": await update.message.reply_text("⏳ **စာရင်းသွင်းရန် -**\n`/add_credit ဝယ်သူ | ပစ္စည်း | အကြွေးစုပေါင်း | တစ်လပေး | ဖုန်း`", parse_mode="Markdown")
    elif text == "📦 Stock အဟောင်း": await update.message.reply_text("📦 **ထည့်ရန် -**\n`/add_stock ပစ္စည်း | အရေအတွက် | ဝယ်ဈေး`", parse_mode="Markdown")


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

    print("Bot is running with MongoDB...")
    app.run_polling()

if __name__ == '__main__':
    main()

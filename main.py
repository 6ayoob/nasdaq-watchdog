import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import requests
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from flask import Flask
import threading
from datetime import datetime

# إعدادات البوت
BOT_TOKEN = "7863509137:AAHBuRbtzMAOM_yBbVZASfx-oORubvQYxY8"
ALLOWED_IDS = [7863509137, 658712542]
API_KEY = "7f1629d677224c75b640f687c1e41561"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_symbols():
    try:
        with open("nasdaq_symbols.txt", "r") as f:
            return [line.strip().upper() for line in f if line.strip()]
    except FileNotFoundError:
        return []

def get_indicator(symbol, indicator, interval="1day"):
    url = f"https://api.twelvedata.com/{indicator}"
    params = {"symbol": symbol, "interval": interval, "outputsize": 100, "apikey": API_KEY}
    resp = requests.get(url, params=params).json()
    return resp.get("values", [])

def fetch_stock_data(symbol):
    try:
        price = float(requests.get("https://api.twelvedata.com/price", params={"symbol": symbol, "apikey": API_KEY}).json().get("price", 0))
        if price == 0 or price > 7:
            return None

        sma50 = get_indicator(symbol, "sma&time_period=50")
        sma200 = get_indicator(symbol, "sma&time_period=200")
        rsi = get_indicator(symbol, "rsi")

        if len(sma50) < 2 or len(sma200) < 2 or not rsi:
            return None

        s50 = float(sma50[0]["sma"]); s50_prev = float(sma50[1]["sma"])
        s200 = float(sma200[0]["sma"]); s200_prev = float(sma200[1]["sma"])
        rsi_val = float(rsi[0]["rsi"])
        if not (s50_prev < s200_prev and s50 > s200 and rsi_val >= 50):
            return None

        return (symbol, price, rsi_val)
    except Exception as e:
        logger.warning(f"خطأ في {symbol}: {e}")
        return None

def scan_stocks():
    syms = load_symbols()
    results = [fetch_stock_data(s) for s in syms[:300]]
    results = [r for r in results if r]
    if not results:
        return ["❌ لا توجد نتائج."]
    results.sort(key=lambda x: x[2], reverse=True)
    return [f"{s} - ${p:.2f} - RSI: {r:.1f}" for s,p,r in results[:10]]

async def scan_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_IDS:
        await update.message.reply_text("🚫 غير مصرح لك.")
        return
    await update.message.reply_text("🔍 جارٍ الفحص...")
    await update.message.reply_text("\n".join(scan_stocks()))

async def send_daily_report(ctx: ContextTypes.DEFAULT_TYPE):
    report = scan_stocks()
    for user_id in ALLOWED_IDS:
        try:
            await ctx.application.bot.send_message(chat_id=user_id, text="📊 التقرير اليومي:\n" + "\n".join(report))
        except Exception as e:
            logger.error(f"فشل الإرسال إلى {user_id}: {e}")

async def setup_scheduler(app):
    scheduler = AsyncIOScheduler(timezone=pytz.timezone("Asia/Riyadh"))
    scheduler.add_job(lambda: asyncio.create_task(send_daily_report(ContextTypes.DEFAULT_TYPE())), trigger="cron", hour=15, minute=0)
    scheduler.start()

app = ApplicationBuilder().token(BOT_TOKEN).post_init(setup_scheduler).build()
app.add_handler(CommandHandler("scan", scan_command))

# Flask وهمي للاحتفاظ بالخدمة حية
flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "✅ Bot is running!"

def run_bot():
    import asyncio
    asyncio.run(app.run_polling())

if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    flask_app.run(host="0.0.0.0", port=10000)

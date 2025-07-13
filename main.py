import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import requests
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime

# إعدادات البوت
BOT_TOKEN = "7863509137:AAHBuRbtzMAOM_yBbVZASfx-oORubvQYxY8"
ALLOWED_IDS = [7863509137, 658712542]
API_KEY = "7f1629d677224c75b640f687c1e41561"

# اللوق
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
    params = {
        "symbol": symbol,
        "interval": interval,
        "outputsize": 100,
        "apikey": API_KEY
    }
    response = requests.get(url, params=params)
    data = response.json()
    if "values" in data:
        return data["values"]
    else:
        raise Exception(data.get("message", f"خطأ في {indicator} لـ {symbol}"))

def fetch_stock_data(symbol):
    try:
        # السعر الحالي
        price_url = f"https://api.twelvedata.com/price?symbol={symbol}&apikey={API_KEY}"
        price_response = requests.get(price_url).json()
        price = float(price_response.get("price", 0))
        if price == 0 or price > 7:
            return None

        # المتوسطات المتحركة
        sma_50 = get_indicator(symbol, "sma")
        sma_200 = get_indicator(symbol, "sma&time_period=200")

        sma_50_latest = float(sma_50[0]["sma"])
        sma_50_prev = float(sma_50[1]["sma"])

        sma_200_latest = float(sma_200[0]["sma"])
        sma_200_prev = float(sma_200[1]["sma"])

        # تحقق من Golden Cross
        if sma_50_prev < sma_200_prev and sma_50_latest > sma_200_latest:
            pass
        else:
            return None

        # RSI
        rsi_data = get_indicator(symbol, "rsi")
        rsi_latest = float(rsi_data[0]["rsi"])
        if rsi_latest < 50:
            return None

        return (symbol, price, rsi_latest)

    except Exception as e:
        logger.warning(f"تخطي {symbol}: {e}")
        return None

def scan_stocks():
    symbols = load_symbols()
    results = []

    for symbol in symbols[:300]:  # لتقليل عدد الطلبات
        result = fetch_stock_data(symbol)
        if result:
            results.append(result)

    if not results:
        return ["❌ لا توجد نتائج."]

    results.sort(key=lambda x: x[2], reverse=True)  # ترتيب حسب RSI
    return [f"{s} - ${p:.2f} - RSI: {r:.1f}" for s, p, r in results[:10]]

# أمر /scan
async def scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_IDS:
        await update.message.reply_text("🚫 غير مصرح لك.")
        return
    await update.message.reply_text("🔍 جاري فحص السوق...")
    report = scan_stocks()
    await update.message.reply_text("\n".join(report))

# تقرير يومي تلقائي
async def send_daily_report(context: ContextTypes.DEFAULT_TYPE):
    report = scan_stocks()
    for user_id in ALLOWED_IDS:
        try:
            await context.bot.send_message(chat_id=user_id, text="📊 التقرير اليومي:\n" + "\n".join(report))
        except Exception as e:
            logger.error(f"فشل إرسال التقرير إلى {user_id}: {e}")

# تشغيل الجدولة
async def setup_scheduler(app):
    scheduler = AsyncIOScheduler(timezone=pytz.timezone("Asia/Riyadh"))

    async def job_wrapper():
        context = ContextTypes.DEFAULT_TYPE()
        context.application = app
        context.bot = app.bot
        await send_daily_report(context)

    scheduler.add_job(job_wrapper, trigger="cron", hour=15, minute=0)
    scheduler.start()

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(setup_scheduler).build()
    app.add_handler(CommandHandler("scan", scan_command))
    app.run_polling()

import logging
import requests
import pandas as pd
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime

# إعدادات البوت
BOT_TOKEN = "7863509137:AAHBuRbtzMAOM_yBbVZASfx-oORubvQYxY8"
ALLOWED_IDS = [7863509137, 658712542]
TWELVE_DATA_API_KEY = "7f1629d677224c75b640f687c1e41561"

# إعداد اللوق
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# تحميل رموز الأسهم
def load_symbols():
    try:
        with open("nasdaq_symbols.txt", "r") as f:
            return [line.strip().upper() for line in f if line.strip()]
    except FileNotFoundError:
        return []

# جلب بيانات السهم
def fetch_stock_data(symbol):
    url = f"https://api.twelvedata.com/time_series"
    params = {
        "symbol": symbol,
        "interval": "1day",
        "outputsize": 200,
        "apikey": TWELVE_DATA_API_KEY
    }
    response = requests.get(url, params=params)
    data = response.json()
    if "values" not in data:
        return None

    df = pd.DataFrame(data["values"])
    df["close"] = df["close"].astype(float)
    df["volume"] = df["volume"].astype(float)
    df = df.iloc[::-1]  # ترتيب تصاعدي

    df["50ma"] = df["close"].rolling(50).mean()
    df["200ma"] = df["close"].rolling(200).mean()
    df["rsi"] = compute_rsi(df["close"])

    latest = df.iloc[-1]

    # شروط التصفية:
    if (
        latest["close"] < 7 and
        latest["50ma"] > latest["200ma"] and
        latest["rsi"] > 50
    ):
        return (symbol, latest["close"], latest["volume"])
    return None

# حساب مؤشر RSI
def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# فحص السوق
def scan_stocks():
    symbols = load_symbols()
    results = []

    for symbol in symbols[:1000]:
        try:
            result = fetch_stock_data(symbol)
            if result:
                results.append(result)
        except Exception as e:
            logger.warning(f"تخطي {symbol} بسبب خطأ: {e}")
            continue

    if not results:
        return ["❌ لا توجد نتائج."]

    results.sort(key=lambda x: x[2], reverse=True)
    return [f"{s} - ${c:.2f} - الحجم: {int(v):,}" for s, c, v in results[:10]]

# أمر /scan
async def scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_IDS:
        await update.message.reply_text("🚫 غير مصرح لك.")
        return
    await update.message.reply_text("🔍 جاري فحص السوق...")
    report = scan_stocks()
    await update.message.reply_text("\n".join(report))

# التقرير اليومي التلقائي
async def send_daily_report(context: ContextTypes.DEFAULT_TYPE):
    report = scan_stocks()
    for user_id in ALLOWED_IDS:
        try:
            await context.bot.send_message(chat_id=user_id, text="📊 التقرير اليومي:\n" + "\n".join(report))
        except Exception as e:
            logger.error(f"فشل إرسال التقرير إلى {user_id}: {e}")

# جدولة التقارير
async def setup_scheduler(app):
    scheduler = AsyncIOScheduler(timezone=pytz.timezone("Asia/Riyadh"))
    scheduler.add_job(send_daily_report, trigger="cron", hour=15, minute=0, args=[app.bot])
    scheduler.start()

# تشغيل البوت
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(setup_scheduler).build()
    app.add_handler(CommandHandler("scan", scan_command))
    app.run_polling()

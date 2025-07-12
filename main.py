import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import yfinance as yf
import pandas as pd
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime

# التوكن والمعرفات
BOT_TOKEN = "7863509137:AAHBuRbtzMAOM_yBbVZASfx-oORubvQYxY8"
ALLOWED_IDS = [7863509137, 658712542]

# إعداد اللوق
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# دالة تحميل الأسهم من الملف
def load_symbols():
    try:
        with open("nasdaq_symbols.txt", "r") as f:
            return [line.strip().upper() for line in f if line.strip()]
    except FileNotFoundError:
        return []

# دالة فحص الأسهم
def scan_stocks():
    symbols = load_symbols()
    results = []

    for symbol in symbols[:1000]:
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period="3mo")
            if df.empty or len(df) < 50:
                continue

            df["50ma"] = df["Close"].rolling(50).mean()
            df["50vol"] = df["Volume"].rolling(50).mean()
            latest = df.iloc[-1]

            if latest["Close"] < 20 and latest["Close"] > df["50ma"].iloc[-1] and latest["Volume"] > df["50vol"].iloc[-1]:
                results.append((symbol, latest["Close"], latest["Volume"]))
        except Exception as e:
            continue

    if not results:
        return ["❌ لا توجد نتائج حالياً."]
    
    results.sort(key=lambda x: x[2], reverse=True)
    return [f"{s} - ${c:.2f} - حجم: {int(v):,}" for s, c, v in results[:10]]

# أمر /scan
async def scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_IDS:
        await update.message.reply_text("🚫 غير مصرح لك.")
        return
    await update.message.reply_text("🔍 يتم الآن فحص الأسهم...")
    report = scan_stocks()
    await update.message.reply_text("\n".join(report))

# التقرير اليومي التلقائي
async def send_daily_report(app):
    report = scan_stocks()
    for user_id in ALLOWED_IDS:
        try:
            await app.bot.send_message(chat_id=user_id, text="📊 التقرير اليومي:\n" + "\n".join(report))
        except Exception as e:
            logger.error(f"فشل إرسال التقرير إلى {user_id}: {e}")

# الدالة الرئيسية
async def run_bot():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("scan", scan_command))

    # جدولة التقرير اليومي الساعة 3 مساءً بتوقيت السعودية
    scheduler = AsyncIOScheduler(timezone=pytz.timezone("Asia/Riyadh"))
    scheduler.add_job(send_daily_report, trigger="cron", hour=15, minute=0, args=[app])
    scheduler.start()

    await app.run_polling()

# تشغيل البوت
if __name__ == "__main__":
    import asyncio
    asyncio.run(run_bot())

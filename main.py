import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import yfinance as yf
import datetime
import pytz
import pandas as pd
import asyncio

TELEGRAM_BOT_TOKEN = "7863509137:AAHBuRbtzMAOM_yBbVZASfx-oORubvQYxY8"
ALLOWED_USERS = [7863509137]
REPORT_TIME_HOUR = 15  # الساعة 3 مساءً بتوقيت السعودية

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_symbols():
    with open("nasdaq_symbols.txt", "r") as f:
        return [line.strip().upper() for line in f.readlines() if line.strip()]

def is_allowed(user_id):
    return user_id in ALLOWED_USERS

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        await update.message.reply_text("🚫 غير مصرح لك باستخدام هذا البوت.")
        return
    await update.message.reply_text("✅ أهلاً بك! أرسل /scan للحصول على أفضل الأسهم.")

def scan_stocks():
    symbols = load_symbols()
    good_stocks = []

    for symbol in symbols:
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period="3mo")
            if df.empty or len(df) < 50:
                continue

            df["50ma"] = df["Close"].rolling(window=50).mean()
            df["50vol"] = df["Volume"].rolling(window=50).mean()
            latest = df.iloc[-1]

            if (
                latest["Close"] < 20 and
                latest["Close"] > latest["50ma"] and
                latest["Volume"] > latest["50vol"]
            ):
                name = ticker.info.get("shortName", symbol)
                good_stocks.append(f"📈 {name} ({symbol})\nالسعر: ${latest['Close']:.2f}")

        except Exception:
            continue

    if not good_stocks:
        return "❌ لم يتم العثور على أسهم مطابقة للشروط."
    return "\n\n".join(good_stocks[:10])

async def scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        return
    await update.message.reply_text("⏳ جاري فحص السوق...")
    result = scan_stocks()
    await update.message.reply_text(result)

# جدولة الإرسال التلقائي
async def daily_report(context: ContextTypes.DEFAULT_TYPE):
    message = scan_stocks()
    for user_id in ALLOWED_USERS:
        try:
            await context.bot.send_message(chat_id=user_id, text=message)
        except Exception as e:
            logger.error(f"Failed to send daily report to {user_id}: {e}")

async def setup_daily_job(application):
    sa_tz = pytz.timezone("Asia/Riyadh")
    now = datetime.datetime.now(sa_tz)
    next_run = now.replace(hour=REPORT_TIME_HOUR, minute=0, second=0, microsecond=0)
    if now >= next_run:
        next_run += datetime.timedelta(days=1)
    delay = (next_run - now).total_seconds()

    async def job_loop():
        while True:
            await asyncio.sleep(delay)
            await daily_report(application)
            await asyncio.sleep(24 * 60 * 60)

    asyncio.create_task(job_loop())

# التشغيل
async def main():
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("scan", scan_command))

    await setup_daily_job(application)
    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())

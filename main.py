import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import yfinance as yf
import datetime
import pytz
import pandas as pd
from apscheduler.schedulers.asyncio import AsyncIOScheduler

TELEGRAM_BOT_TOKEN = "7863509137:AAHBuRbtzMAOM_yBbVZASfx-oORubvQYxY8"
ALLOWED_USERS = [658712542]
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
        await update.message.reply_text("🚫 غير مصرح لك باستخدام هذا البوت.")
        return

    await update.message.reply_text("🔎 يتم فحص السوق الآن، يرجى الانتظار...")
    result = scan_stocks()
    await update.message.reply_text(result)

async def scheduled_report(app):
    now = datetime.datetime.now(pytz.timezone("Asia/Riyadh"))
    if now.hour == REPORT_TIME_HOUR:
        result = scan_stocks()
        for user_id in ALLOWED_USERS:
            try:
                await app.bot.send_message(chat_id=user_id, text=result)
            except Exception as e:
                logger.error(f"❌ فشل إرسال التقرير إلى المستخدم {user_id}: {e}")

def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # أوامر البوت
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("scan", scan_command))

    # مجدول التقارير اليومية
    scheduler = AsyncIOScheduler(timezone="Asia/Riyadh")
    scheduler.add_job(scheduled_report, "cron", hour=REPORT_TIME_HOUR, args=[app])
    scheduler.start()

    # تشغيل البوت
    app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.get_event_loop().run_until_complete(main())

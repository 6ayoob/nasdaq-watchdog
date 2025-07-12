import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import yfinance as yf
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
import pytz

# ✅ توكن البوت الخاص بك
BOT_TOKEN = "7863509137:AAHBuRbtzMAOM_yBbVZASfx-oORubvQYxY8"

# ✅ المعرفات المصرح لها
ALLOWED_IDS = [7863509137, 658712542]

# إعداد التسجيل
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def scan_stocks():
    try:
        with open("nasdaq_symbols.txt", "r") as f:
            symbols = f.read().splitlines()
    except FileNotFoundError:
        return ["❌ لم يتم العثور على ملف الأسهم nasdaq_symbols.txt"]

    top_stocks = []
    for symbol in symbols[:1000]:
        try:
            stock = yf.Ticker(symbol)
            hist = stock.history(period="3mo")
            if hist.empty or len(hist) < 50:
                continue

            latest = hist.iloc[-1]
            ma50 = hist["Close"].rolling(window=50).mean().iloc[-1]
            vol50 = hist["Volume"].rolling(window=50).mean().iloc[-1]

            if latest["Close"] < 20 and latest["Close"] > ma50 and latest["Volume"] > vol50:
                top_stocks.append((symbol, latest["Close"], latest["Volume"]))
        except Exception as e:
            logger.warning(f"خطأ في {symbol}: {e}")
            continue

    if not top_stocks:
        return ["ℹ️ لا توجد أسهم تنطبق عليها الشروط حاليًا"]

    top_stocks.sort(key=lambda x: x[2], reverse=True)
    report = [f"{sym} - ${price:.2f} - حجم: {vol:,}" for sym, price, vol in top_stocks[:10]]
    return report

async def scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_IDS:
        await update.message.reply_text("🚫 غير مصرح لك باستخدام هذا البوت.")
        return

    await update.message.reply_text("🔍 جارٍ فحص السوق، انتظر قليلًا...")
    report = scan_stocks()
    await update.message.reply_text("\n".join(report))

async def scheduled_report(application: Application):
    report = scan_stocks()
    for user_id in ALLOWED_IDS:
        try:
            await application.bot.send_message(chat_id=user_id, text="📊 التقرير اليومي:\n" + "\n".join(report))
        except Exception as e:
            logger.error(f"فشل إرسال التقرير إلى {user_id}: {e}")

async def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("scan", scan_command))

    # جدولة التقرير التلقائي الساعة 3 مساءً بتوقيت السعودية
    scheduler = AsyncIOScheduler(timezone=pytz.timezone("Asia/Riyadh"))
    scheduler.add_job(scheduled_report, "cron", hour=15, minute=0, args=[application])
    scheduler.start()

    logger.info("✅ البوت يعمل الآن...")
    await application.run_polling()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError as e:
        if "cannot be called from a running event loop" in str(e).lower():
            loop = asyncio.get_event_loop()
            loop.create_task(main())
            loop.run_forever()
        else:
            raise

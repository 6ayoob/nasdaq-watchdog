
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import yfinance as yf
import datetime
import pytz
import asyncio
import pandas as pd

TELEGRAM_BOT_TOKEN = "7863509137:AAHBuRbtzMAOM_yBbVZASfx-oORubvQYxY8"
ALLOWED_USERS = [7863509137]
REPORT_TIME_HOUR = 15  # 3 مساءً بتوقيت السعودية

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
    if not symbols:
        return "⚠️ لم يتم العثور على رموز أسهم."

    try:
        df = yf.download(
            tickers=" ".join(symbols),
            period="3mo",
            interval="1d",
            group_by="ticker",
            threads=True,
            auto_adjust=True,
            progress=False
        )
    except Exception as e:
        return f"❌ حدث خطأ أثناء تحميل البيانات: {e}"

    good_stocks = []
    for symbol in symbols:
        try:
            data = df[symbol]
            if data.empty or len(data) < 50:
                continue

            data["50ma"] = data["Close"].rolling(window=50).mean()
            data["50vol"] = data["Volume"].rolling(window=50).mean()
            latest = data.iloc[-1]

            if (
                latest["Close"] < 20 and
                latest["Close"] > latest["50ma"] and
                latest["Volume"] > latest["50vol"]
            ):
                good_stocks.append(f"📈 {symbol}
السعر: ${latest['Close']:.2f}")
        except Exception:
            continue

    if not good_stocks:
        return "❌ لم يتم العثور على أسهم مطابقة للشروط."
    return "\n\n".join(good_stocks[:20])

async def scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        await update.message.reply_text("🚫 غير مصرح لك باستخدام هذا البوت.")
        return

    await update.message.reply_text("🔍 جاري فحص السوق...")
    result = await asyncio.to_thread(scan_stocks)
    await update.message.reply_text(result)

async def daily_report(app):
    while True:
        now = datetime.datetime.now(pytz.timezone("Asia/Riyadh"))
        if now.hour == REPORT_TIME_HOUR and now.minute == 0:
            result = await asyncio.to_thread(scan_stocks)
            for user_id in ALLOWED_USERS:
                try:
                    await app.bot.send_message(chat_id=user_id, text="📊 تقرير السوق اليومي:\n\n" + result)
                except Exception as e:
                    logger.error(f"فشل في إرسال التقرير إلى {user_id}: {e}")
            await asyncio.sleep(60)
        await asyncio.sleep(30)

async def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("scan", scan_command))

    app.create_task(daily_report(app))
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())


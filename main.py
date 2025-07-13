
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import yfinance as yf
from datetime import datetime
import pytz

BOT_TOKEN = "7863509137:AAHBuRbtzMAOM_yBbVZASfx-oORubvQYxY8"
ALLOWED_IDS = [7863509137]

# إعداد المنطقة الزمنية
ksa_tz = pytz.timezone("Asia/Riyadh")

# تحميل الرموز من ملف خارجي
def load_symbols():
    try:
        with open("nasdaq_symbols.txt", "r") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return []

# شروط الفلترة للأسهم
def passes_conditions(stock):
    try:
        info = stock.info
        price = info.get("regularMarketPrice")
        fifty_ma = info.get("fiftyDayAverage")
        volume = info.get("volume")
        avg_volume = info.get("averageVolume")
        return (
            price is not None and price < 20 and
            fifty_ma is not None and price > fifty_ma and
            avg_volume is not None and volume is not None and volume > avg_volume
        )
    except Exception:
        return False

# إنشاء تقرير بالأسهم المطابقة
def generate_report():
    symbols = load_symbols()
    matched = []
    for symbol in symbols:
        stock = yf.Ticker(symbol)
        if passes_conditions(stock):
            matched.append(symbol)
    if matched:
        return "الأسهم المطابقة للشروط:\n" + "\n".join(matched[:10])
    else:
        return "لا توجد أسهم مطابقة للشروط حالياً."

# أمر /scan من المستخدم
async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_IDS:
        return
    await update.message.reply_text("جاري فحص الأسهم...")
    report = generate_report()
    await update.message.reply_text(report)

# مهمة مجدولة للتقرير اليومي
async def daily_job(app):
    r = generate_report()
    for user_id in ALLOWED_IDS:
        try:
            await app.bot.send_message(chat_id=user_id, text=f"📈 التقرير اليومي:\n{r}")
        except Exception as e:
            logging.error(f"فشل الإرسال إلى {user_id}: {e}")

# جدولة المهام اليومية
def setup_scheduler(app):
    scheduler = AsyncIOScheduler(timezone=ksa_tz)
    scheduler.add_job(lambda: daily_job(app), CronTrigger(hour=15, minute=0))
    scheduler.start()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(setup_scheduler).build()
    app.add_handler(CommandHandler("scan", scan))
    app.run_polling()

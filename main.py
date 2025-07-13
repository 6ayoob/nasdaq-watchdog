import logging
import yfinance as yf
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import datetime
import pytz

# ✅ التوكن والمعرفات
BOT_TOKEN = "7863509137:AAHBuRbtzMAOM_yBbVZASfx-oORubvQYxY8"
ALLOWED_IDS = [7863509137]

# ✅ إعداد السجلات
logging.basicConfig(level=logging.INFO)

# ✅ دالة فحص الأسهم
def scan_stocks():
    try:
        with open("nasdaq_symbols.txt") as f:
            symbols = f.read().splitlines()
    except FileNotFoundError:
        return ["⚠️ ملف الأسهم غير موجود"]

    results = []
    for symbol in symbols[:200]:  # يمكنك زيادة العدد حسب الحاجة
        try:
            stock = yf.Ticker(symbol)
            hist = stock.history(period="60d")

            if len(hist) < 50:
                continue

            price = hist['Close'][-1]
            avg_volume = hist['Volume'][-50:].mean()
            volume = hist['Volume'][-1]
            ma50 = hist['Close'][-50:].mean()

            if price < 20 and price > ma50 and volume > avg_volume:
                results.append(f"{symbol}: ${price:.2f}")
        except Exception:
            continue

    return results or ["❌ لا توجد أسهم مطابقة"]

# ✅ أمر /scan
async def scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_IDS:
        return
    await update.message.reply_text("🔍 يتم الفحص الآن...")
    results = scan_stocks()
    await update.message.reply_text("\n".join(results))

# ✅ التقرير اليومي التلقائي
async def daily_report(context: ContextTypes.DEFAULT_TYPE):
    results = scan_stocks()
    await context.bot.send_message(chat_id=ALLOWED_IDS[0], text="📊 تقرير يومي:\n" + "\n".join(results))

# ✅ تشغيل التطبيق
app = ApplicationBuilder().token(BOT_TOKEN).build()

# ✅ أوامر البوت
app.add_handler(CommandHandler("scan", scan_command))

# ✅ جدولة التقرير التلقائي الساعة 3 مساءً بتوقيت السعودية
scheduler = AsyncIOScheduler(timezone=pytz.timezone("Asia/Riyadh"))
scheduler.add_job(daily_report, "cron", hour=15, minute=0)
scheduler.start()

# ✅ تشغيل البوت
print("✅ Bot is running...")
app.run_polling()

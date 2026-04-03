import os
import re
import yt_dlp
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

TOKEN = os.environ.get("TOKEN")
MAX_SIZE_MB = 50

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 أهلاً! أنا بوت تنزيل Pinterest\n\n"
        "📌 أرسل لي رابط أي بوست من Pinterest\n"
        "🎬 وسأرسل لك الفيديو أو الصورة مباشرة!\n\n"
        "✅ يدعم روابط pinterest.com و pin.it"
    )

def check_size(filename):
    size_mb = os.path.getsize(filename) / (1024 * 1024)
    return size_mb <= MAX_SIZE_MB, size_mb

async def download_pinterest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    urls = re.findall(r'https?://[^\s]+', text)
    if not urls:
        await update.message.reply_text("❌ ما لقيت رابط في رسالتك")
        return

    url = urls[0]

    if "pinterest.com" not in url and "pin.it" not in url:
        await update.message.reply_text("❌ أرسل رابط Pinterest فقط")
        return

    msg = await update.message.reply_text("⏳ جاري التنزيل...")

    try:
        ydl_opts = {
            "outtmpl": "/tmp/%(id)s.%(ext)s",
            "quiet": True,
            "no_check_formats": True,
            "format": "best",
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://www.pinterest.com/",
            },
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        if not os.path.exists(filename):
            for f in os.listdir("/tmp"):
                if info.get("id", "") in f:
                    filename = f"/tmp/{f}"
                    break

        is_video = info.get("vcodec") not in [None, "none"]
        ok, size = check_size(filename)

        if size < 0.01:
            os.remove(filename)
            await msg.edit_text("❌ الملف فارغ، جرب رابط ثاني")
            return

        if not ok:
            os.remove(filename)
            await msg.edit_text(f"❌ الملف كبير جداً ({size:.1f}MB)")
            return

        await msg.edit_text(f"📤 جاري الإرسال... ({size:.1f}MB)")

        if is_video:
            with open(filename, "rb") as video:
                await update.message.reply_video(video=video)
        else:
            with open(filename, "rb") as img:
                await update.message.reply_photo(photo=img)

        os.remove(filename)
        await msg.delete()

    except Exception as e:
        await msg.edit_text(f"❌ فشل التنزيل:\n{str(e)}")

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_pinterest))

print("✅ البوت شغال...")
app.run_polling()

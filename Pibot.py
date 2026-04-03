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

    msg = await update.message.reply_text("⏳ جاري التحليل...")

    try:
        ydl_opts_check = {
            "quiet": True,
            "skip_download": True,
            "no_check_formats": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts_check) as ydl:
            info = ydl.extract_info(url, download=False)

        is_video = info.get("vcodec") not in [None, "none"]

        if is_video:
            await msg.edit_text("⏳ جاري تنزيل الفيديو...")

            formats = info.get("formats", [])
            best_url = None
            best_size = 0

            for f in formats:
                if (f.get("vcodec") not in [None, "none"]
                        and f.get("url")
                        and f.get("filesize", 0) and f.get("filesize", 0) > best_size):
                    best_url = f["url"]
                    best_size = f.get("filesize", 0)

            if not best_url:
                for f in reversed(formats):
                    if f.get("vcodec") not in [None, "none"] and f.get("url"):
                        best_url = f["url"]
                        break

            if not best_url:
                best_url = info.get("url")

            headers = {
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://www.pinterest.com/",
            }

            filename = "/tmp/video.mp4"
            r = requests.get(best_url, headers=headers, stream=True, timeout=60)
            with open(filename, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

            ok, size = check_size(filename)
            if not ok:
                os.remove(filename)
                await msg.edit_text(f"❌ الفيديو كبير جداً ({size:.1f}MB)")
                return

            if size < 0.01:
                os.remove(filename)
                await msg.edit_text("❌ الفيديو فارغ، جرب رابط ثاني")
                return

            await msg.edit_text(f"📤 جاري الإرسال... ({size:.1f}MB)")
            with open(filename, "rb") as video:
                await update.message.reply_video(video=video)
            os.remove(filename)

        else:
            thumb = info.get("thumbnail") or info.get("url")
            if not thumb:
                await msg.edit_text("❌ ما قدرت أجيب الصورة")
                return

            await msg.edit_text("🖼️ جاري تنزيل الصورة...")
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(thumb, headers=headers, timeout=15)
            filename = "/tmp/image.jpg"
            with open(filename, "wb") as f:
                f.write(response.content)

            ok, size = check_size(filename)
            if not ok:
                os.remove(filename)
                await msg.edit_text(f"❌ الصورة كبيرة جداً ({size:.1f}MB)")
                return

            await msg.edit_text("📤 جاري إرسال الصورة...")
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

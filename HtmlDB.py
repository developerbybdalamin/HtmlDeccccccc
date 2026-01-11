# main.py
import os
import asyncio
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from playwright.async_api import async_playwright

# Bot token from environment or hardcoded
TOKEN = "8458139520:AAFJHdnDlhJQN9lNSNYRIfyOxgEZ0YdRlXY"

CHANNELS = ["@bdalminofficial0099", "@wingo_server24"]  # চ্যানেলের ইউজারনেম সঠিক করা হয়েছে
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024

# ---------- UTIL ----------
async def is_joined(bot, user_id):
    for ch in CHANNELS:
        try:
            member = await bot.get_chat_member(ch, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
    return True

async def render_html(path):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(f"file://{os.path.abspath(path)}")
        
        # Wait until the network is idle or max 30 seconds
        try:
            await page.wait_for_load_state("networkidle", timeout=30000)
        except:
            pass 
        
        # Smart extraction: Remove heavy encryption logic while keeping the actual page scripts
        await page.evaluate("""() => {
            const scripts = document.querySelectorAll('script');
            scripts.forEach(s => {
                const content = s.innerText || '';
                // Encryption scripts are usually very long (>8000 chars) 
                // and contain huge encoded strings or obfuscated logic.
                // We remove these to prevent duplication and bloat.
                if (content.length > 8000 && (content.includes('eval(') || content.includes('atob(') || /^[a-zA-Z0-9+/=]{1000,}/m.test(content))) {
                    s.remove();
                }
            });
            
            // Also remove common encryption containers if they exist as massive hidden data
            const allElements = document.querySelectorAll('div, span, pre');
            allElements.forEach(el => {
                if (el.style.display === 'none' && el.innerText.length > 10000) {
                    el.remove();
                }
            });
        }""")
        
        # Get the rendered content which now has the original functional scripts
        # but is free of the heavy encryption source
        content = await page.content()
        await browser.close()
        return content

def beautify_html(html):
    # Just return the raw HTML to ensure nothing is stripped or modified
    return html

# ---------- START ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Channel 1", url="https://t.me/bdalminofficial0099")],
        [InlineKeyboardButton("📢 Channel 2", url="https://t.me/wingo_server24")],
        [InlineKeyboardButton("✅ Check Join", callback_data="check")]
    ])
    await update.message.reply_text(
        "🔐 To use this bot, you must join both channels first.\n\n\nDeveloped by @BDALAMINHACKER & @FAHIM_TRADER1",
        reply_markup=kb
    )

# ---------- CALLBACK ----------
async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if await is_joined(context.bot, query.from_user.id):
        await query.edit_message_text(
            "✅ Thanks for joining!\n\nNow send me your `.html` file to render.\n\nDeveloped by @BDALAMINHACKER & @FAHIM_TRADER1"
        )
    else:
        # Use query.message.reply_text to ensure a visible message even if answer() doesn't show alert
        await query.answer("❌ You must join all channels", show_alert=True)
        try:
            await query.message.reply_text("❌ You must join all channels first to use this bot!")
        except:
            pass

# ---------- FILE ----------
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_joined(context.bot, update.effective_user.id):
        await update.message.reply_text("❌ Must join channels first")
        return

    doc = update.message.document

    if not doc.file_name.endswith(".html"):
        await update.message.reply_text("❌ Only HTML files allowed")
        return

    if doc.file_size > MAX_FILE_SIZE:
        await update.message.reply_text("❌ File too large (max 100MB)")
        return

    msg = await update.message.reply_text("📥 Processing: 0%")

    async def update_progress():
        for i in range(1, 101):
            await asyncio.sleep(0.05) # Faster sleep to make 1-100% feel smooth
            try:
                await msg.edit_text(f"📥 Processing: {i}%")
            except:
                pass

    # Start progress update in background
    progress_task = asyncio.create_task(update_progress())

    path = f"temp_{doc.file_name}"
    await (await doc.get_file()).download_to_drive(path)

    try:
        # Render HTML using Playwright
        rendered = await render_html(path)
        clean = beautify_html(rendered)

        # Wait for progress to finish if it's not yet at 100%
        await progress_task

        out = f"clean_{doc.file_name}"
        with open(out, "w", encoding="utf-8") as f:
            f.write(clean)

        await msg.delete()
        caption = "✅ HTML Successfully Decrypted\n\nDeveloped by @BDALAMINHACKER & @FAHIM_TRADER1"
        await update.message.reply_document(open(out, "rb"), caption=caption)

        os.remove(path)
        os.remove(out)

    except Exception as e:
        await msg.edit_text(f"❌ Error: {e}")

# ---------- MAIN ----------
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    app.add_handler(CallbackQueryHandler(callback))

    print("🤖 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
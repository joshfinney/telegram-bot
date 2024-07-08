import os
import logging
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import requests
from telegram.error import NetworkError, Conflict

if 'RENDER' not in os.environ:
    load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Get the bot token and webhook URL from environment variables
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
PORT = int(os.environ.get('PORT', 8080))
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

async def everyone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for the /everyone command"""
    if update.effective_chat.type in ['group', 'supergroup']:
        try:
            chat_id = update.effective_chat.id
            
            # Get administrators
            admins = await context.bot.get_chat_administrators(chat_id)
            admin_ids = set(admin.user.id for admin in admins)
            
            # Get total member count
            member_count = await context.bot.get_chat_member_count(chat_id)
            
            all_members = []
            offset = 0
            limit = 200  # Telegram API limit
            
            # Fetch all members using pagination
            while len(all_members) < member_count:
                members = await context.bot.get_chat_members(chat_id, offset=offset, limit=limit)
                all_members.extend(members)
                offset += limit
                if len(members) < limit:
                    break
            
            # Sort members: admins first, then alphabetically
            sorted_members = sorted(all_members, key=lambda m: (m.user.id not in admin_ids, m.user.full_name.lower()))
            
            # Create a list of all member mentions
            mentions = [member.user.mention_html() for member in sorted_members if not member.user.is_bot]
            
            # Split mentions into chunks of 100 (Telegram message length limit)
            mention_chunks = [mentions[i:i+100] for i in range(0, len(mentions), 100)]
            
            # Send messages
            for chunk in mention_chunks:
                message = """
                🔔 <b>Attention, everyone!</b> 🔔
                
                <code>{}</code>
                """.format(" | ".join(chunk))
                await update.effective_message.reply_html(message)
            
        except Exception as e:
            logger.error(f"Error in everyone command: {e}")
            await update.effective_message.reply_text("An error occurred while mentioning everyone.")
    else:
        await update.effective_message.reply_text("This command can only be used in group chats.")

def setup_webhook():
    url = f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={WEBHOOK_URL}"
    response = requests.get(url)
    logger.info(f"Webhook setup response: {response.json()}")


def remove_webhook():
    url = f"https://api.telegram.org/bot{TOKEN}/deleteWebhook?drop_pending_updates=True"
    response = requests.get(url)
    logger.info(f"Webhook removal response: {response.json()}")

async def main() -> None:
    try:
        logger.info("Starting bot...")
        logger.info(f"TELEGRAM_BOT_TOKEN: {TOKEN}")
        logger.info(f"WEBHOOK_URL: {WEBHOOK_URL}")

        remove_webhook()
        await asyncio.sleep(5)  # Add a 5-second delay after webhook removal
        application = Application.builder().token(TOKEN).build()
        application.add_handler(CommandHandler("everyone", everyone))

        if 'RENDER' in os.environ:
            logger.info("Starting bot on Render")
            await application.initialize()
            await application.start()
            await application.updater.start_webhook(
                listen="0.0.0.0",
                port=PORT,
                webhook_url=WEBHOOK_URL
            )
            # Keep the application running
            await asyncio.Event().wait()
        else:
            logger.info("Starting bot locally")
            await application.initialize()
            await application.start()
            retry_count = 0
            max_retries = 3
            while retry_count < max_retries:
                try:
                    await application.updater.start_polling(drop_pending_updates=True)
                    # Keep the application running
                    while True:
                        await asyncio.sleep(1)
                except Conflict as e:
                    logger.error(f"Conflict error: {e}")
                    retry_count += 1
                    if retry_count < max_retries:
                        logger.info(f"Retrying in 5 seconds (attempt {retry_count}/{max_retries})")
                        await asyncio.sleep(5)
                    else:
                        logger.error("Maximum number of retries reached. Exiting.")
                        break
                except Exception as e:
                    logger.error(f"Unexpected error: {e}")
                    retry_count += 1
                    if retry_count < max_retries:
                        logger.info(f"Retrying in 5 seconds (attempt {retry_count}/{max_retries})")
                        await asyncio.sleep(5)
                    else:
                        logger.error("Maximum number of retries reached. Exiting.")
                        break
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
    finally:
        await application.stop()
        logger.info("Bot stopped")

if __name__ == "__main__":
    asyncio.run(main())
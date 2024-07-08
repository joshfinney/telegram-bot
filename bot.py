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
            # Get all chat members
            chat_members = await context.bot.get_chat_members(update.effective_chat.id)
            
            # Create a list of all member mentions
            mentions = sorted([member.user.mention_html() for member in chat_members if not member.user.is_bot])
            
            # Craft the message
            message = """
            🔔 <b>Attention, everyone!</b> 🔔
            
            <code>{}</code>
            """.format(" | ".join(mentions))
            
            # Send the message
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
        remove_webhook()  # Remove webhook before starting

        application = Application.builder().token(TOKEN).build()
        application.add_handler(CommandHandler("everyone", everyone))

        if 'RENDER' in os.environ:
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
            await application.initialize()
            await application.start()
            await application.updater.start_polling(drop_pending_updates=True)

            # Keep the application running
            while True:
                await asyncio.sleep(1)

    except NetworkError as e:
        logger.error(f"Network error: {e}")
    except Conflict as e:
        logger.error(f"Conflict error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        await application.stop()

if __name__ == "__main__":
    asyncio.run(main())
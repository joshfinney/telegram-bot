import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Get the bot token from an environment variable
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

async def everyone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for the /everyone command"""
    if update.effective_chat.type in ['group', 'supergroup']:
        # Get all chat members
        chat_members = await context.bot.get_chat_administrators(update.effective_chat.id)
        
        # Create a list of all member mentions
        mentions = [member.user.mention_html() for member in chat_members if not member.user.is_bot]
        
        # Join the mentions with newlines
        message = "Attention everyone!\n" + "\n".join(mentions)
        
        # Send the message
        await update.effective_message.reply_html(message)
    else:
        await update.effective_message.reply_text("This command can only be used in group chats.")

def main() -> None:
    """Run the bot"""
    # Create the Application and pass it your bot's token
    application = Application.builder().token(TOKEN).build()

    # Add the command handler
    application.add_handler(CommandHandler("everyone", everyone))

    # Run the bot until the user presses Ctrl-C
    application.run_polling()

if __name__ == "__main__":
    main()
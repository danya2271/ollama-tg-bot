import asyncio
import ollama
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# --- Import Configuration ---
from config import TELEGRAM_BOT_TOKEN, OLLAMA_MODEL, ALLOWED_TELEGRAM_USER_IDS

# --- Bot Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message when the /start command is issued."""
    await update.message.reply_text(f"Hello! I am a bot powered by the {OLLAMA_MODEL} model. How can I help you today?")

async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clears the conversation history and restarts the LLM for the user."""
    user_id = update.effective_user.id
    if user_id not in ALLOWED_TELEGRAM_USER_IDS:
        await update.message.reply_text("Sorry, you are not authorized to use this bot.")
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    await update.message.reply_text("Restarting the language model...")

    # In this stateless implementation, each message is a new chat.
    # Therefore, a "restart" is essentially just a confirmation to the user
    # that the bot is ready for a new, context-free conversation.
    # If you were to implement conversation history, you would clear it here.

    await update.message.reply_text("The language model has been restarted. I'm ready for a new conversation!")


async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles incoming chat messages and gets a response from the Ollama model."""
    user_id = update.effective_user.id
    if user_id not in ALLOWED_TELEGRAM_USER_IDS:
        await update.message.reply_text("Sorry, you are not authorized to use this bot.")
        return

    user_message = update.message.text

    # Show a "typing..." notification to the user
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')

    try:
        # Get the response from the Ollama model
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[
                {
                    'role': 'user',
                    'content': user_message,
                },
            ]
        )
        bot_response = response['message']['content']
        await update.message.reply_text(bot_response)

    except Exception as e:
        print(f"An error occurred: {e}")
        await update.message.reply_text("Sorry, I encountered an error while processing your request.")

def main() -> None:
    """Starts the Telegram bot."""
    print("Starting bot...")

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # --- Register Handlers ---
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("restart", restart)) # <-- Added this line
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

    # --- Start the Bot ---
    print("Bot is running. Press Ctrl+C to stop.")
    app.run_polling()

if __name__ == "__main__":
    main()

import asyncio
import ollama
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# --- Import Configuration ---
from config import TELEGRAM_BOT_TOKEN, OLLAMA_MODEL, ALLOWED_TELEGRAM_USER_IDS

# --- Bot Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_name = update.effective_user.first_name
    """Sends a welcome message when the /start command is issued."""
    await update.message.reply_text(f"Hello, {user_name}! I am a bot powered by the {OLLAMA_MODEL} model. How can I help you today?")

async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a '/clear' command to Ollama to reset the conversation context."""
    user_id = update.effective_user.id
    if user_id not in ALLOWED_TELEGRAM_USER_IDS:
        await update.message.reply_text("Sorry, you are not authorized to use this bot.")
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    await update.message.reply_text("Resetting the model session...")

    try:
        # Send the /clear command to the model to formally end the conversation.
        # We don't need to do anything with the response.
        ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{'role': 'user', 'content': '/clear'}]
        )
        await update.message.reply_text("Model session has been successfully reset. I'm ready for a new conversation!")

    except Exception as e:
        print(f"An error occurred during restart: {e}")
        await update.message.reply_text("Sorry, I encountered an error while trying to reset the model.")


async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles incoming chat messages and gets a response from the Ollama model."""
    user_id = update.effective_user.id

    user_message = update.message.text
    # Print user's message to console
    print(f"User ({update.effective_user.first_name}): {user_message}")

    if user_id not in ALLOWED_TELEGRAM_USER_IDS:
        await update.message.reply_text("Sorry, you are not authorized to use this bot.")
        return

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
        # Print LLM's message to console
        print(f"Bot: {bot_response}")
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
    app.add_handler(CommandHandler("restart", restart))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

    # --- Start the Bot ---
    print("Bot is running. Press Ctrl+C to stop.")
    app.run_polling()

if __name__ == "__main__":
    main()

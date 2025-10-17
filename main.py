import asyncio
import ollama
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from ddgs import DDGS

# --- Import Configuration ---
from config import TELEGRAM_BOT_TOKEN, OLLAMA_MODEL, ALLOWED_TELEGRAM_USER_IDS
from guest_config import OLLAMA_GUEST_MODEL

# --- Bot Handlers ---

TELEGRAM_MAX_MESSAGE_LENGTH = 4096

# --- Текст с описанием команд для переиспользования ---
COMMANDS_INFO = """
Вот список доступных команд:

/ask [ваш вопрос] - Найти информацию в интернете и ответить на основе найденных данных.
Пример: `/ask последние новости о космосе`

/restart - Сбросить контекст текущего диалога.

/help - Показать это сообщение с описанием команд.

Вы также можете просто общаться со мной, отправляя сообщения без команд, или отправить мне фотографию (с подписью или без).
"""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message when the /start command is issued."""
    user_name = update.effective_user.first_name
    user_id = update.effective_user.id

    model_in_use = OLLAMA_MODEL if user_id in ALLOWED_TELEGRAM_USER_IDS else OLLAMA_GUEST_MODEL

    welcome_message = (
        f"Здравствуйте, {user_name}! Я бот, работающий на модели {model_in_use}.\n\n"
        f"{COMMANDS_INFO}"
    )
    await update.message.reply_text(welcome_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a message with information about all available commands."""
    await update.message.reply_text(COMMANDS_INFO)

async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a '/clear' command to Ollama to reset the conversation context."""
    user_id = update.effective_user.id
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')

    model_to_reset = OLLAMA_MODEL if user_id in ALLOWED_TELEGRAM_USER_IDS else OLLAMA_GUEST_MODEL

    await update.message.reply_text("Сбрасываю сессию модели...")

    try:
        ollama.chat(
            model=model_to_reset,
            messages=[{'role': 'user', 'content': '/clear'}]
        )
        await update.message.reply_text("Сессия модели была успешно сброшена. Я готов к новой беседе!")

    except Exception as e:
        print(f"An error occurred during restart: {e}")
        await update.message.reply_text("Извините, при попытке сбросить модель произошла ошибка.")

async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    query = ' '.join(context.args)

    if not query:
        await update.message.reply_text("Пожалуйста, укажите вопрос после команды /ask.\nПример: /ask последние новости о миссии Artemis")
        return

    target_model = OLLAMA_MODEL if user_id in ALLOWED_TELEGRAM_USER_IDS else OLLAMA_GUEST_MODEL

    try:
        await update.message.reply_text(f"Ищу информацию по запросу: \"{query}\"...")
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')

        search_results = DDGS().text(query, max_results=5, region='ru-ru')

        search_context = ""
        if search_results:
            for result in search_results:
                search_context += f"Источник: {result['title']}\nСодержание: {result['body']}\n\n"
        else:
            await update.message.reply_text("К сожалению, мне не удалось найти информацию по вашему запросу. Попробуйте переформулировать его.")
            return

        await update.message.reply_text("Информация найдена. Генерирую ответ...")
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')

        system_prompt = (
            "Ты — ассистент, который отвечает на вопросы пользователя, основываясь ИСКЛЮЧИТЕЛЬНО на предоставленной ниже информации из интернета. "
            "Не используй свои внутренние знания. Сформируй связный и исчерпывающий ответ. "
            "Если предоставленная информация не позволяет ответить на вопрос, сообщи об этом."
        )

        user_prompt = f"Контекст из поиска в интернете:\n---\n{search_context}\n---\nВопрос пользователя: {query}"

        response = ollama.chat(
            model=target_model,
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt}
            ]
        )
        bot_response = response['message']['content']

        await update.message.reply_text(bot_response)

    except Exception as e:
        print(f"An error occurred in the ask function: {e}")
        await update.message.reply_text("Извините, во время обработки вашего запроса произошла ошибка.")

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles incoming chat messages and gets a response from the Ollama model."""
    user_id = update.effective_user.id
    user_message = update.message.text
    # Print user's message to console
    print(f"User ({update.effective_user.first_name}): {user_message}")

    target_model = OLLAMA_MODEL if user_id in ALLOWED_TELEGRAM_USER_IDS else OLLAMA_GUEST_MODEL

    # Show a "typing..." notification to the user
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')

    try:
        # Get the response from the Ollama model
        response = ollama.chat(
            model=target_model,
            messages=[{'role': 'user', 'content': user_message}]
        )
        bot_response = response['message']['content']
        print(f"Bot ({target_model}): {bot_response}")

        if len(bot_response) > TELEGRAM_MAX_MESSAGE_LENGTH:
            print("Response is too long, splitting into multiple messages.")
            for i in range(0, len(bot_response), TELEGRAM_MAX_MESSAGE_LENGTH):
                chunk = bot_response[i:i + TELEGRAM_MAX_MESSAGE_LENGTH]
                await update.message.reply_text(chunk)
        else:
            await update.message.reply_text(bot_response)

    except Exception as e:
        print(f"An error occurred: {e}")
        await update.message.reply_text("Извините, во время обработки вашего запроса произошла ошибка.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    target_model = OLLAMA_MODEL if user_id in ALLOWED_TELEGRAM_USER_IDS else OLLAMA_GUEST_MODEL

    await update.message.reply_text("Получил фото, обрабатываю...")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')

    try:
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()

        prompt = update.message.caption
        if not prompt:
            prompt = "Подробно опиши это изображение."

        response = ollama.chat(
            model=target_model,
            messages=[
                {
                    'role': 'user',
                    'content': prompt,
                    'images': [photo_bytes]
                }
            ]
        )
        bot_response = response['message']['content']

        if len(bot_response) > TELEGRAM_MAX_MESSAGE_LENGTH:
            for i in range(0, len(bot_response), TELEGRAM_MAX_MESSAGE_LENGTH):
                chunk = bot_response[i:i+TELEGRAM_MAX_MESSAGE_LENGTH]
                await update.message.reply_text(chunk)
        else:
            await update.message.reply_text(bot_response)

    except Exception as e:
        print(f"An error occurred while handling photo: {e}")
        await update.message.reply_text("Извините, произошла ошибка при обработке фото. Убедитесь, что для OLLAMA_MODEL установлена мультимодальная модель (например, llava).")


def main() -> None:
    """Starts the Telegram bot."""
    print("Starting bot...")
    print(f"Authorized users will use: {OLLAMA_MODEL}")
    print(f"Guest users will use: {OLLAMA_GUEST_MODEL}")

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # --- Register Handlers ---
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("restart", restart))
    app.add_handler(CommandHandler("ask", ask))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # --- Start the Bot ---
    print("Bot is running. Press Ctrl+C to stop.")
    app.run_polling()

if __name__ == "__main__":
    main()

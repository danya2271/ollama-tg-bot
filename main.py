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
MAX_HISTORY_LENGTH = 20

# --- Текст с описанием команд ---
COMMANDS_INFO = """
Вот список доступных команд:

/ask [ваш вопрос] - Единоразовый поиск информации в интернете (не влияет на текущий диалог).
Пример: `/ask последние новости о космосе`

/restart - Сбросить контекст текущего диалога (начать беседу заново).

/help - Показать это сообщение с описанием команд.

---
**Режим поиска в Google для диалога:**
Вы можете включить поиск в интернете для каждого вашего сообщения в диалоге.

/google_on - Включить автоматический поиск в Google для ответов.
/google_off - Отключить автоматический поиск (режим по умолчанию).
/google_status - Проверить текущий статус режима поиска.
"""

# --- Функции для управления режимом поиска ---

async def set_google_search_on(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Enables Google search for the user."""
    context.user_data['use_google'] = True
    await update.message.reply_text("✅ Режим поиска в Google включен. Теперь я буду использовать интернет для более точных ответов в нашем диалоге.")

async def set_google_search_off(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Disables Google search for the user."""
    context.user_data['use_google'] = False
    await update.message.reply_text("❌ Режим поиска в Google отключен. Я буду отвечать, основываясь только на своих внутренних знаниях.")

async def get_google_search_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Checks the current status of the Google search mode."""
    status = context.user_data.get('use_google', False)
    message = "включен" if status else "выключен"
    await update.message.reply_text(f"Текущий статус режима поиска в Google: **{message}**.", parse_mode='Markdown')


# --- Основные хендлеры ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_name = update.effective_user.first_name
    user_id = update.effective_user.id
    model_in_use = OLLAMA_MODEL if user_id in ALLOWED_TELEGRAM_USER_IDS else OLLAMA_GUEST_MODEL
    welcome_message = (
        f"Здравствуйте, {user_name}! Я бот, работающий на модели {model_in_use}.\n\n"
        f"{COMMANDS_INFO}"
    )
    if 'history' in context.chat_data:
        del context.chat_data['history']
    context.user_data.setdefault('use_google', False)
    await update.message.reply_text(welcome_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(COMMANDS_INFO)

async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if 'history' in context.chat_data:
        del context.chat_data['history']
        await update.message.reply_text("Контекст диалога сброшен. Я готов к новой беседе!")
    else:
        await update.message.reply_text("История уже пуста. Просто напишите мне что-нибудь.")

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
        
        search_results = DDGS().text(query, max_results=18, region='ru-ru')

        search_context = ""
        if search_results:
            for result in search_results:
                search_context += f"Источник: {result['title']}\nСодержание: {result['body']}\n\n"
        else:
            await update.message.reply_text("К сожалению, мне не удалось найти информацию по вашему запросу. Попробуйте переформулировать его.")
            return

        await update.message.reply_text("Информация найдена. Генерирую ответ...")
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
        system_prompt = "Ты — ассистент, который отвечает на вопросы пользователя, основываясь ИСКЛЮЧИТЕЛЬНО на предоставленной ниже информации из интернета. Не используй свои внутренние знания. Сформируй связный и исчерпывающий ответ. Если предоставленная информация не позволяет ответить на вопрос, сообщи об этом."
        user_prompt = f"Контекст из поиска в интернете:\n---\n{search_context}\n---\nВопрос пользователя: {query}"
        response = ollama.chat(model=target_model, messages=[{'role': 'system', 'content': system_prompt}, {'role': 'user', 'content': user_prompt}])
        bot_response = response['message']['content']
        await update.message.reply_text(bot_response)

    except Exception as e:
        print(f"An error occurred in the ask function: {e}")
        await update.message.reply_text("Извините, во время обработки вашего запроса произошла ошибка.")


async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_message = update.message.text
    print(f"User ({update.effective_user.first_name}): {user_message}")

    target_model = OLLAMA_MODEL if user_id in ALLOWED_TELEGRAM_USER_IDS else OLLAMA_GUEST_MODEL
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')

    history = context.chat_data.get('history', [])
    use_google_search = context.user_data.get('use_google', False)
    messages_to_send = list(history)

    try:
        if use_google_search:
            await update.message.reply_text("Ищу актуальную информацию...")
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
            
            search_results = DDGS().text(user_message, max_results=18, region='ru-ru')

            search_context = ""
            if search_results:
                for result in search_results:
                    search_context += f"Источник: {result['title']}\nСодержание: {result['body']}\n\n"
                
                prompt_with_context = (
                    f"Используй предоставленную ниже информацию из поиска, чтобы ответить на последний вопрос пользователя. "
                    f"Также учитывай предыдущий контекст диалога.\n\n"
                    f"--- Контекст из поиска ---\n{search_context}\n"
                    f"--- Конец контекста ---\n\n"
                    f"Последний вопрос пользователя: {user_message}"
                )
                messages_to_send.append({'role': 'user', 'content': prompt_with_context})
            else:
                messages_to_send.append({'role': 'user', 'content': user_message})
        else:
            messages_to_send.append({'role': 'user', 'content': user_message})

        response = ollama.chat(model=target_model, messages=messages_to_send)
        bot_response_content = response['message']['content']
        print(f"Bot ({target_model}): {bot_response_content}")

        history.append({'role': 'user', 'content': user_message})
        history.append({'role': 'assistant', 'content': bot_response_content})

        if len(history) > MAX_HISTORY_LENGTH:
            history = history[-MAX_HISTORY_LENGTH:]
        
        context.chat_data['history'] = history

        if len(bot_response_content) > TELEGRAM_MAX_MESSAGE_LENGTH:
            for i in range(0, len(bot_response_content), TELEGRAM_MAX_MESSAGE_LENGTH):
                chunk = bot_response_content[i:i + TELEGRAM_MAX_MESSAGE_LENGTH]
                await update.message.reply_text(chunk)
        else:
            await update.message.reply_text(bot_response_content)

    except Exception as e:
        print(f"An error occurred in chat: {e}")
        await update.message.reply_text("Извините, во время обработки вашего запроса произошла ошибка.")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    target_model = OLLAMA_MODEL if user_id in ALLOWED_TELEGRAM_USER_IDS else OLLAMA_GUEST_MODEL

    if "llava" not in target_model:
        await update.message.reply_text("Извините, текущая модель не поддерживает обработку изображений.")
        return

    await update.message.reply_text("Получил фото, обрабатываю...")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')

    try:
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()

        prompt = update.message.caption or "Подробно опиши это изображение."
        
        history = context.chat_data.get('history', [])
        
        current_user_message = {
            'role': 'user',
            'content': prompt,
            'images': [photo_bytes]
        }

        response = ollama.chat(
            model=target_model,
            messages=history + [current_user_message]
        )
        bot_response_content = response['message']['content']

        history.append({'role': 'user', 'content': prompt})
        history.append({'role': 'assistant', 'content': bot_response_content})

        if len(history) > MAX_HISTORY_LENGTH:
            history = history[-MAX_HISTORY_LENGTH:]
            
        context.chat_data['history'] = history

        if len(bot_response_content) > TELEGRAM_MAX_MESSAGE_LENGTH:
            for i in range(0, len(bot_response_content), TELEGRAM_MAX_MESSAGE_LENGTH):
                chunk = bot_response_content[i:i+TELEGRAM_MAX_MESSAGE_LENGTH]
                await update.message.reply_text(chunk)
        else:
            await update.message.reply_text(bot_response_content)

    except Exception as e:
        print(f"An error occurred while handling photo: {e}")
        await update.message.reply_text("Извините, произошла ошибка при обработке фото.")


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
    
    app.add_handler(CommandHandler("google_on", set_google_search_on))
    app.add_handler(CommandHandler("google_off", set_google_search_off))
    app.add_handler(CommandHandler("google_status", get_google_search_status))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("Bot is running. Press Ctrl+C to stop.")
    app.run_polling()

if __name__ == "__main__":
    main()

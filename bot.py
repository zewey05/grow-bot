import os
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from groq import Groq

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GROQ_KEY = os.environ.get("GROQ_KEY")
SUPPORT_USERNAME = "zewey05"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = Groq(api_key=GROQ_KEY)

user_modes = {}
user_history = {}

MODES = {
    "code": """Ты Senior Python разработчик с 10 летним опытом.
Когда пишешь код:
- Всегда пиши рабочий, чистый код
- Добавляй комментарии на русском
- Объясняй что делает каждая часть
- Предлагай лучшие практики
- Если есть ошибка — объясни почему и исправь
- Используй современный Python 3.10+
- Пиши обработку ошибок try/except
Отвечай на русском.""",
    "study": """Ты умный репетитор для школьников.
- Объясняй темы простым языком
- Приводи понятные примеры из жизни
- Разбивай сложное на простые шаги
- Проверяй понимание
- Поддерживай и мотивируй
Отвечай на русском.""",
    "chat": """Ты дружелюбный AI ассистент.
- Отвечай коротко и по делу
- Будь дружелюбным и позитивным
- Помогай с любыми вопросами
Отвечай на русском."""
}

def get_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💻 Код", callback_data="mode_code"),
            InlineKeyboardButton(text="📚 Учёба", callback_data="mode_study"),
            InlineKeyboardButton(text="💬 Чат", callback_data="mode_chat"),
        ],
        [
            InlineKeyboardButton(text="🗑 Очистить историю", callback_data="clear")
        ]
    ])

async def set_commands():
    commands = [
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="menu", description="Показать меню"),
        BotCommand(command="support", description="Написать в поддержку"),
        BotCommand(command="clear", description="Очистить историю"),
    ]
    await bot.set_my_commands(commands)

@dp.message(Command("start"))
async def start(message: types.Message):
    user_modes[message.from_user.id] = "chat"
    user_history[message.from_user.id] = []
    await message.answer(
        "Привет! Я мощный AI ассистент 🤖\n\nВыбери режим:",
        reply_markup=get_keyboard()
    )

@dp.message(Command("menu"))
async def menu(message: types.Message):
    await message.answer("Выбери режим:", reply_markup=get_keyboard())

@dp.message(Command("clear"))
async def clear(message: types.Message):
    user_history[message.from_user.id] = []
    await message.answer("История очищена! 🗑")

@dp.message(Command("support"))
async def support(message: types.Message):
    await message.answer(
        f"📩 Связаться с поддержкой:\n@{SUPPORT_USERNAME}\n\nОпишите вашу проблему и мы поможем!"
    )

@dp.callback_query()
async def handle_callback(call: types.CallbackQuery):
    uid = call.from_user.id
    if call.data == "clear":
        user_history[uid] = []
        await call.answer("История очищена!")
    elif call.data.startswith("mode_"):
        mode = call.data.replace("mode_", "")
        user_modes[uid] = mode
        names = {"code": "💻 Код", "study": "📚 Учёба", "chat": "💬 Чат"}
        await call.answer(f"Режим: {names[mode]}")
    await call.message.edit_reply_markup(reply_markup=get_keyboard())

@dp.message()
async def handle(message: types.Message):
    uid = message.from_user.id
    if uid not in user_modes:
        user_modes[uid] = "chat"
    if uid not in user_history:
        user_history[uid] = []

    user_history[uid].append({"role": "user", "content": message.text})

    if len(user_history[uid]) > 20:
        user_history[uid] = user_history[uid][-20:]

    await bot.send_chat_action(message.chat.id, "typing")

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=1000,
        messages=[{"role": "system", "content": MODES[user_modes[uid]]}] + user_history[uid]
    )

    reply = response.choices[0].message.content
    user_history[uid].append({"role": "assistant", "content": reply})

    await message.answer(reply, parse_mode="Markdown")

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, *args):
        pass

def run_server():
    port = int(os.environ.get("PORT", 8080))
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()

async def main():
    await set_commands()
    threading.Thread(target=run_server, daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

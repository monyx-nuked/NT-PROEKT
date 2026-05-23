import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import psycopg
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def get_db_connection():
    return psycopg.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT")
    )

@dp.message(Command("start"))
async def start_command(message: types.Message):
    telegram_id = message.from_user.id
    full_name = message.from_user.full_name

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            try:
                cursor.execute("SELECT telegram_id FROM bot_users WHERE telegram_id = %s;", (telegram_id,))
                user = cursor.fetchone()

                if user:
                    await message.answer(f"Xush kelibsiz, {full_name}! Siz allaqachon ro'yxatdan o'tgansiz.\n"
                                         f"Buyruqlar: /books, /search [kitob nomi]")
                else:
                    cursor.execute(
                        "INSERT INTO bot_users (telegram_id, full_name) VALUES (%s, %s);",
                        (telegram_id, full_name)
                    )
                    conn.commit()
                    await message.answer(f"Salom, {full_name}! Siz muvaffaqiyatli ro'yxatdan o'tdingiz.\n"
                                         f"Buyruqlar: /books, /search [kitob nomi]")
            except Exception as e:
                print(e)

@dp.message(Command("books"))
async def list_books(message: types.Message):
    query = """
    SELECT b.title, a.name, b.available_copies
    FROM books b
    JOIN authors a ON b.author_id = a.id;
    """
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query)
            books = cursor.fetchall()

    if not books:
        await message.answer("Kutubxonada hozircha kitoblar mavjud emas.")
        return

    response_text = "> Kutubxonamizdagi kitoblar ro'yxati:\n\n"
    for title, author, copies in books:
        response_text += f"- {title} (Muallif: {author}) — Soni: {copies} ta\n"

    await message.answer(response_text)

@dp.message(Command("search"))
async def search_book(message: types.Message):
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        await message.answer("Iltimos, qidirayotgan kitob nomini ham yozing.\nMasalan: `/search Xamsa`", parse_mode="Markdown")
        return

    search_query = args[1]
    
    query = "SELECT title, available_copies FROM books WHERE title ILIKE %s;"
    
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, (f"%{search_query}%",))
            books = cursor.fetchall()

    if not books:
        await message.answer("Kutubxonamizda bunday kitob topilmadi.")
    else:
        for title, copies in books:
            if copies > 0:
                await message.answer(f"> Topildi:\n> {title}\n> Kutubxonada: {copies} ta nusxa bor.")
            else:
                await message.answer(f"> {title} — Bu kitob ayni damda qolmagan.")

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
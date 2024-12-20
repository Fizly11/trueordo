import random
import asyncio
import sqlite3
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from keyboards import add_togame

router = Router()

active_games = {}  # {group_id: {"players": list_of_players, "skip_event": asyncio.Event()}}


# Функция для регистрации пользователя
async def register_user(user_id: int, user_name: str, group_id: int, group_name: str):
    try:
        with sqlite3.connect('example.db') as conn:
            cursor = conn.cursor()

            # Создаём таблицы, если их ещё нет
            cursor.execute('''CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                group_id INTEGER NOT NULL
            )''')

            cursor.execute('''CREATE TABLE IF NOT EXISTS groups (
                group_id INTEGER PRIMARY KEY,
                group_name TEXT,
                game_status TEXT DEFAULT 'inactive'
            )''')

            # Регистрируем группу и пользователя
            cursor.execute('''INSERT OR IGNORE INTO groups (group_id, group_name)
                              VALUES (?, ?)''', (group_id, group_name))
            cursor.execute('''INSERT OR REPLACE INTO players (id, name, group_id)
                              VALUES (?, ?, ?)''', (user_id, user_name, group_id))
            conn.commit()
    except Exception as e:
        print(f"Ошибка при регистрации пользователя: {e}")
        raise


# Обработчик команды /start
@router.message(CommandStart())
async def start(message: Message):
    if message.chat.type not in ['group', 'supergroup']:
        await message.answer("Команда /start доступна только в группах.")
        return

    user_id = message.from_user.id
    user_name = message.from_user.first_name
    group_id = message.chat.id
    group_name = message.chat.title or "Без имени"

    try:
        await register_user(user_id, user_name, group_id, group_name)
        await message.answer(f"Ваши данные сохранены! Вы зарегистрированы в группе '{group_name}'.")
        print(f"New Player! ID: {user_id}, Group ID: {group_id}")
    except Exception as e:
        await message.answer("Произошла ошибка при регистрации.")
        print(e)


# Обработчик callback-запроса для кнопки "join"
@router.callback_query(F.data == 'join')
async def handle_add_to_game(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_name = callback.from_user.first_name
    group_id = callback.message.chat.id
    group_name = callback.message.chat.title or "Без имени"

    try:
        await register_user(user_id, user_name, group_id, group_name)
        await callback.message.answer(f"{user_name} присоединился к игре!")
        await callback.answer()
    except Exception as e:
        await callback.answer("Ошибка при добавлении в игру.", show_alert=True)
        print(e)

# Команда /start_game для запуска игры
@router.message(Command('start_game'))
async def start_game(message: Message):
    if message.chat.type not in ['group', 'supergroup']:
        await message.answer("Команда /start_game доступна только в группах.")
        return

    group_id = message.chat.id

    try:
        with sqlite3.connect('example.db') as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT game_status FROM groups WHERE group_id = ?', (group_id,))
            result = cursor.fetchone()

            if result and result[0] == "active":
                await message.answer("Игра уже идёт!")
                return

            cursor.execute('UPDATE groups SET game_status = "active" WHERE group_id = ?', (group_id,))
            cursor.execute('SELECT id, name FROM players WHERE group_id = ?', (group_id,))
            players = cursor.fetchall()

            if len(players) < 2:
                await message.answer("Недостаточно игроков для начала игры.")
                return

            active_games[group_id] = {"players": [{"id": p[0], "name": p[1]} for p in players],
                                      "skip_event": asyncio.Event()}
            await message.answer("Игра началась!")
            asyncio.create_task(game_loop(group_id, message.bot))

    except Exception as e:
        print(e)
        await message.answer("Произошла ошибка при запуске игры.")


# Команда /stop_game для остановки игры
@router.message(Command('stop_game'))
async def stop_game(message: Message):
    group_id = message.chat.id

    try:
        if group_id in active_games:
            del active_games[group_id]

        with sqlite3.connect('example.db') as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE groups SET game_status = "inactive" WHERE group_id = ?', (group_id,))
            conn.commit()

        await message.answer("Игра остановлена.")

    except Exception as e:
        print(e)
        await message.answer("Произошла ошибка при остановке игры.")


# Игровой цикл
async def game_loop(group_id, bot):
    while group_id in active_games:
        game_data = active_games[group_id]
        players = game_data["players"]
        skip_event = game_data["skip_event"]

        if len(players) < 2:
            await bot.send_message(group_id, "Недостаточно игроков для продолжения игры.")
            break

        asker, answerer = random.sample(players, 2)
        await bot.send_message(
            group_id,
            f"🎲 Игрок {asker['name']} задаёт вопрос 'Правда или действие' игроку {answerer['name']}!"
        )

        try:
            skip_event.clear()
            await asyncio.wait_for(skip_event.wait(), timeout=90)
        except asyncio.TimeoutError:
            pass

    if group_id in active_games:
        del active_games[group_id]


# Команда для прерывания задержки
@router.message(Command('skip'))
async def skip_delay(message: Message):
    group_id = message.chat.id

    if group_id in active_games:
        active_games[group_id]["skip_event"].set()
        await message.answer("Задержка пропущена. Следующий раунд начался!")


# Команда /new_game с инлайн-кнопкой
# Команда /new_game с инлайн-кнопкой
@router.message(Command('new_game'))
async def new_game(message: Message):
    await message.answer("Добавь себя в игру, нажав на кнопку ниже:", reply_markup=add_togame)

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData

# Создаём CallbackData для кнопки


# Создаём клавиатуру с инлайн-кнопкой
add_togame = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Учавствовать', callback_data='join')]])
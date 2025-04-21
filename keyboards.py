from telebot import types

def category_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        types.InlineKeyboardButton(text="Обувь", callback_data="обувь"),
        types.InlineKeyboardButton(text="Футболка/кофта/штаны", callback_data="футболка\\кофта\\штаны"),
        types.InlineKeyboardButton(text="Другое", callback_data="другое"),
    ]
    keyboard.add(*buttons)
    return keyboard

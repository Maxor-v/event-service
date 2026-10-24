from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

def main_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("📅 Расписание", "🎫 Мои брони")
    kb.row("⭐ Оставить отзыв", "ℹ️ Помощь")
    return kb

def categories_kb():
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("🎵 Концерты", callback_data="cat:concert"),
        InlineKeyboardButton("🎬 Фильмы",   callback_data="cat:movie"),
    )
    kb.row(
        InlineKeyboardButton("🎭 Спектакли", callback_data="cat:theater"),
        InlineKeyboardButton("🍷 Дегустации", callback_data="cat:tasting"),
    )
    kb.row(InlineKeyboardButton("📋 Все", callback_data="cat:all"))
    return kb

def events_kb(events):
    kb = InlineKeyboardMarkup()
    for ev in events:
        free = ev["total_seats"] - ev["booked_seats"]
        kb.add(InlineKeyboardButton(
            f"{ev['title']} · {ev['date'][:10]} · {free} мест",
            callback_data=f"ev:{ev['id']}"
        ))
    return kb

def event_actions_kb(event_id):
    kb = InlineKeyboardMarkup()
    kb.row(InlineKeyboardButton("🎫 Забронировать", callback_data=f"book:{event_id}"))
    kb.row(InlineKeyboardButton("⭐ Отзывы",        callback_data=f"revs:{event_id}"))
    kb.row(InlineKeyboardButton("⬅️ К списку",     callback_data="back:events"))
    return kb


def confirm_kb():
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("✅ Подтвердить", callback_data="bk:yes"),
        InlineKeyboardButton("❌ Отмена",      callback_data="bk:no"),
    )
    return kb

def payment_kb():
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("💳 Онлайн",     callback_data="pay:online"),
        InlineKeyboardButton("💵 Наличными",  callback_data="pay:cash"),
    )
    return kb

def booking_actions_kb(booking_id):
    kb = InlineKeyboardMarkup()
    kb.row(InlineKeyboardButton("❌ Отменить бронь", callback_data=f"cancel:{booking_id}"))
    return kb

def rating_kb(event_id):
    kb = InlineKeyboardMarkup()
    kb.row(*[InlineKeyboardButton("⭐" * i, callback_data=f"rate:{event_id}:{i}")
             for i in range(1, 6)])
    return kb

def admin_booking_kb(booking_id):
    kb = InlineKeyboardMarkup()
    kb.row(InlineKeyboardButton("✅ Подтвердить", callback_data=f"adm_ok:{booking_id}"))
    return kb
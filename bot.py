import telebot
from telebot import apihelper
from telebot.types import CallbackQuery, Message
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import (
    BOT_TOKEN, CATEGORIES, STATUS_EMOJI, PAYMENT_LABEL, ADMIN_IDS,
    get_proxy_config,
)
from database import (
    init_db, upsert_user, get_user,
    get_events, get_event, free_seats,
    create_booking, get_user_bookings, get_booking, cancel_booking,
    confirm_booking, get_pending_bookings, add_review, get_event_reviews,  user_attended_event,
)
import keyboards as kb

# ---------- Прокси  ----------
_proxy = get_proxy_config()
if _proxy:
    apihelper.proxy = _proxy
    print(f"[proxy] Включён: {_proxy['https']}")
else:
    print("[proxy] Отключён — прямое соединение")

bot = telebot.TeleBot(BOT_TOKEN)

# состояние пользователей для FSM
user_state = {}
# пример: user_state[user_id] = {"step": "guests", "event_id": 3, "guests": 2, "notes": ""}

# ---------------- /start ----------------
@bot.message_handler(commands=["start"])
def cmd_start(message: Message):
    user_state.pop(message.from_user.id, None)
    user = get_user(message.from_user.id)
    if user and user["phone"]:
        bot.send_message(message.chat.id,
                         f"С возвращением, {user['full_name']}! 👋",
                         reply_markup=kb.main_menu())
    else:
        bot.send_message(message.chat.id, "Добро пожаловать! Как вас зовут?")
        user_state[message.from_user.id] = {"step": "reg_name"}

@bot.message_handler(commands=["admin"])
def cmd_admin(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "Нет доступа.")
        return
    pending = get_pending_bookings()
    if not pending:
        bot.send_message(message.chat.id, "Нет новых броней.")
        return
    for b in pending:
        text = (f"🆕 Бронь №{b['id']}\n"
                f"Мероприятие: {b['title']} ({b['date']})\n"
                f"Гостей: {b['guests']}\n"
                f"Пожелания: {b['notes'] or '—'}\n"
                f"Клиент: {b['full_name']}, {b['phone']}\n"
                f"Сумма: {b['total_price']} ₽")
        bot.send_message(message.chat.id, text,
                         reply_markup=kb.admin_booking_kb(b["id"]))

# ---------------- Текстовые кнопки ----------------
@bot.message_handler(func=lambda m: m.text == "📅 Расписание")
def show_categories(message: Message):
    bot.send_message(message.chat.id, "Выберите категорию:",
                     reply_markup=kb.categories_kb())

@bot.message_handler(func=lambda m: m.text == "🎫 Мои брони")
def my_bookings(message: Message):
    bookings = get_user_bookings(message.from_user.id)
    if not bookings:
        bot.send_message(message.chat.id, "У вас пока нет броней.")
        return
    for b in bookings:
        text = (f"Бронь №{b['id']}\n"
                f"🎭 {b['title']} ({b['date']})\n"
                f"Гостей: {b['guests']}\n"
                f"Сумма: {b['total_price']} ₽\n"
                f"Оплата: {PAYMENT_LABEL.get(b['payment_method'], '—')}\n"
                f"Статус: {STATUS_EMOJI.get(b['status'], b['status'])}")
        markup = kb.booking_actions_kb(b["id"]) if b["status"] != "cancelled" else None
        bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "⭐ Оставить отзыв")
def start_review(message: Message):
    # берём подтверждённые брони пользователя
    bookings = [b for b in get_user_bookings(message.from_user.id)
                if b["status"] == "confirmed"]
    if not bookings:
        bot.send_message(message.chat.id,
                         "Отзыв можно оставить только по подтверждённым броням.")
        return
    from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
    k = InlineKeyboardMarkup()
    for b in bookings:
        k.add(InlineKeyboardButton(f"{b['title']} ({b['date'][:10]})",
                                   callback_data=f"rev:{b['event_id']}"))
    bot.send_message(message.chat.id, "Выберите мероприятие:", reply_markup=k)

@bot.message_handler(func=lambda m: m.text == "ℹ️ Помощь")
def help_msg(message: Message):
    bot.send_message(message.chat.id,
        "Я помогу забронировать билеты на мероприятия.\n"
        "• 📅 Расписание — посмотреть события\n"
        "• 🎫 Мои брони — статус заявок\n"
        "• ⭐ Оставить отзыв — оценить событие\n\n"
        "Оплата: онлайн или наличными на месте.")

# ---------------- Регистрация (FSM) ----------------
@bot.message_handler(func=lambda m: user_state.get(m.from_user.id, {}).get("step") == "reg_name")
def reg_name(message: Message):
    user_state[message.from_user.id] = {"step": "reg_phone", "full_name": message.text}
    bot.send_message(message.chat.id, "Отлично! Теперь укажите телефон (например +79990001122):")

@bot.message_handler(func=lambda m: user_state.get(m.from_user.id, {}).get("step") == "reg_phone")
def reg_phone(message: Message):
    st = user_state[message.from_user.id]
    upsert_user(message.from_user.id, message.from_user.username,
                st["full_name"], message.text)
    user_state.pop(message.from_user.id, None)
    bot.send_message(message.chat.id, "Регистрация завершена! 🎉",
                     reply_markup=kb.main_menu())

# ---------------- Callback: категории, мероприятия ----------------
@bot.callback_query_handler(func=lambda c: c.data.startswith("cat:"))
def on_category(call: CallbackQuery):
    cat = call.data.split(":", 1)[1]
    events = get_events(cat)
    if not events:
        bot.answer_callback_query(call.id, "Нет мероприятий в этой категории.")
        return
    label = "📋 Все мероприятия" if cat == "all" else CATEGORIES.get(cat, cat)
    bot.edit_message_text(f"{label}\nВыберите мероприятие:",
                          call.message.chat.id, call.message.message_id,
                          reply_markup=kb.events_kb(events))

@bot.callback_query_handler(func=lambda c: c.data == "back:events")
def back_events(call: CallbackQuery):
    bot.edit_message_text("Выберите категорию:",
                          call.message.chat.id, call.message.message_id,
                          reply_markup=kb.categories_kb())

@bot.callback_query_handler(func=lambda c: c.data.startswith("ev:"))
def on_event(call: CallbackQuery):
    event_id = int(call.data.split(":")[1])
    ev = get_event(event_id)
    if not ev:
        bot.answer_callback_query(call.id, "Мероприятие не найдено.")
        return
    free = ev["total_seats"] - ev["booked_seats"]
    text = (f"🎭 {ev['title']}\n"
            f"Категория: {CATEGORIES.get(ev['category'], ev['category'])}\n"
            f"Дата: {ev['date']}\n"
            f"Цена: {ev['price']} ₽ за билет\n"
            f"Свободно мест: {free}\n\n"
            f"{ev['description'] or ''}")
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                          reply_markup=kb.event_actions_kb(event_id))


@bot.callback_query_handler(func=lambda c: c.data.startswith("revs:"))
def on_show_reviews(call: CallbackQuery):
    event_id = int(call.data.split(":")[1])
    ev = get_event(event_id)
    if not ev:
        bot.answer_callback_query(call.id, "Мероприятие не найдено.")
        return

    reviews = get_event_reviews(event_id)

    if not reviews:
        text = (f"⭐ Отзывы на «{ev['title']}»\n\n"
                f"Пока отзывов нет. Станьте первым!")
    else:
        avg = sum(r["rating"] for r in reviews) / len(reviews)
        header = (f"⭐ Отзывы на «{ev['title']}»\n"
                  f"Средняя оценка: {avg:.1f}/5 · всего {len(reviews)}\n\n")
        lines = []
        for r in reviews[:10]:                    # не больше 10 последних
            name = r["full_name"] or "Пользователь"
            stars = "⭐" * r["rating"]
            body = (r["text"] or "—")
            if len(body) > 200:
                body = body[:200] + "…"
            lines.append(f"{stars} — {name}\n{body}")
        text = header + "\n\n".join(lines)
        if len(reviews) > 10:
            text += f"\n\n… и ещё {len(reviews) - 10} отзыв(ов)."

    # Telegram лимит — 4096 символов
    if len(text) > 4000:
        text = text[:4000] + "…"

    back = InlineKeyboardMarkup()
    back.row(InlineKeyboardButton("⬅️ К мероприятию", callback_data=f"ev:{event_id}"))
    bot.edit_message_text(text, call.message.chat.id,
                          call.message.message_id, reply_markup=back)

# ---------------- Бронирование (FSM) ----------------
@bot.callback_query_handler(func=lambda c: c.data.startswith("book:"))
def start_booking(call: CallbackQuery):
    event_id = int(call.data.split(":")[1])
    free = free_seats(event_id)
    if free <= 0:
        bot.answer_callback_query(call.id, "Мест не осталось 😔")
        return
    user_state[call.from_user.id] = {"step": "guests", "event_id": event_id}
    bot.send_message(call.message.chat.id,
                     f"Сколько билетов нужно? (свободно: {free})")



@bot.message_handler(func=lambda m: user_state.get(m.from_user.id, {}).get("step") == "guests")
def booking_guests(message: Message):
    st = user_state[message.from_user.id]
    free = free_seats(st["event_id"])

    # мест уже нет — завершаем сессию
    if free <= 0:
        user_state.pop(message.from_user.id, None)
        bot.send_message(message.chat.id, "Свободных мест больше нет 😔")
        return

    # 1) не число / пустая строка / не целое
    try:
        guests = int(message.text.strip())
    except (ValueError, TypeError):
        bot.send_message(
            message.chat.id,
            f"Нужно ввести целое число от 1 до {free}.\nПопробуйте ещё раз:"
        )
        return

    # 2) число, но вне допустимого диапазона
    if guests < 1 or guests > free:
        bot.send_message(
            message.chat.id,
            f"Число должно быть от 1 до {free}.\nПопробуйте ещё раз:"
        )
        return

    st["guests"] = guests
    st["step"] = "notes"
    bot.send_message(message.chat.id, "Есть пожелания? (или отправьте «-»)")

@bot.message_handler(func=lambda m: user_state.get(m.from_user.id, {}).get("step") == "notes")
def booking_notes(message: Message):
    st = user_state[message.from_user.id]
    st["notes"] = "" if message.text.strip() == "-" else message.text
    st["step"] = "confirm"
    ev = get_event(st["event_id"])
    total = ev["price"] * st["guests"]
    st["total"] = total
    bot.send_message(message.chat.id,
        f"Проверьте бронь:\n"
        f"🎭 {ev['title']} ({ev['date']})\n"
        f"Билетов: {st['guests']}\n"
        f"Пожелания: {st['notes'] or '—'}\n"
        f"Итого: {total} ₽",
        reply_markup=kb.confirm_kb())

@bot.callback_query_handler(func=lambda c: c.data == "bk:no")
def booking_cancel(call: CallbackQuery):
    user_state.pop(call.from_user.id, None)
    bot.edit_message_text("Бронирование отменено.",
                          call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda c: c.data == "bk:yes")
def booking_confirm(call: CallbackQuery):
    st = user_state.get(call.from_user.id)
    if not st or st.get("step") != "confirm":
        bot.answer_callback_query(call.id, "Сессия устарела, начните заново.")
        return
    st["step"] = "payment"
    bot.edit_message_text("Выберите способ оплаты:",
                          call.message.chat.id, call.message.message_id,
                          reply_markup=kb.payment_kb())

@bot.callback_query_handler(func=lambda c: c.data.startswith("pay:"))
def booking_payment(call: CallbackQuery):
    method = call.data.split(":")[1]
    st = user_state.get(call.from_user.id)
    if not st or st.get("step") != "payment":
        bot.answer_callback_query(call.id, "Сессия устарела.")
        return
    booking_id = create_booking(
        call.from_user.id, st["event_id"], st["guests"],
        st["notes"], st["total"], method
    )
    user_state.pop(call.from_user.id, None)
    bot.edit_message_text(
        f"✅ Бронь №{booking_id} создана!\n"
        f"Оплата: {PAYMENT_LABEL[method]}\n"
        f"Статус: {STATUS_EMOJI['pending']}\n\n"
        f"Ожидайте подтверждения организатора.",
        call.message.chat.id, call.message.message_id
    )
    # уведомляем админов
    for admin_id in ADMIN_IDS:
        try:
            bot.send_message(admin_id, f"🆕 Новая бронь №{booking_id}")
        except Exception:
            pass

# ---------------- Отмена брони ----------------
@bot.callback_query_handler(func=lambda c: c.data.startswith("cancel:"))
def on_cancel(call: CallbackQuery):
    booking_id = int(call.data.split(":")[1])
    b = get_booking(booking_id)
    if not b or b["user_id"] != call.from_user.id:
        bot.answer_callback_query(call.id, "Недоступно.")
        return
    cancel_booking(booking_id)
    bot.edit_message_text(f"❌ Бронь №{booking_id} отменена.",
                          call.message.chat.id, call.message.message_id)

# ---------------- Админ: подтверждение ----------------
@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_ok:"))
def on_admin_confirm(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "Нет доступа.")
        return
    booking_id = int(call.data.split(":")[1])
    confirm_booking(booking_id)
    bot.edit_message_text(f"✅ Бронь №{booking_id} подтверждена.",
                          call.message.chat.id, call.message.message_id)
    # уведомляем клиента
    b = get_booking(booking_id)
    try:
        bot.send_message(b["user_id"], f"🎉 Ваша бронь №{booking_id} подтверждена!")
    except Exception:
        pass

# ---------------- Отзывы ----------------
@bot.callback_query_handler(func=lambda c: c.data.startswith("rev:"))
def on_review_start(call: CallbackQuery):
    event_id = int(call.data.split(":")[1])
    bot.edit_message_text("Поставьте оценку:",
                          call.message.chat.id, call.message.message_id,
                          reply_markup=kb.rating_kb(event_id))

@bot.callback_query_handler(func=lambda c: c.data.startswith("rate:"))
def on_review_rate(call: CallbackQuery):
    _, event_id, rating = call.data.split(":")
    user_state[call.from_user.id] = {
        "step": "review_text", "event_id": int(event_id), "rating": int(rating)
    }
    bot.send_message(call.message.chat.id, "Напишите текст отзыва:")

@bot.message_handler(func=lambda m: user_state.get(m.from_user.id, {}).get("step") == "review_text")
def on_review_text(message: Message):
    st = user_state.pop(message.from_user.id)
    add_review(message.from_user.id, st["event_id"], st["rating"], message.text)
    bot.send_message(message.chat.id, "Спасибо за отзыв! ⭐")

# ---------------- Запуск ----------------
if __name__ == "__main__":
    init_db()
    print("Бот запущен...")
    bot.infinity_polling(skip_pending=True)
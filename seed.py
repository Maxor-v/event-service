from database import init_db, get_connection

EVENTS = [
    ("Французская классика: Бордо и Бургундия", "tasting", "2024-08-12 19:00",
     3500, 20, "Дегустация сухих вин Франции. 6 образцов."),
    ("Вино и сыр: идеальные пары", "tasting", "2024-08-19 19:00",
     4200, 15, "Подборка из 5 вин и 5 сыров."),
    ("Новый Свет: вина Чили и Аргентины", "tasting", "2024-08-26 19:00",
     3800, 25, "Знакомство с винами Нового Света."),
    ("Симфонический концерт: Чайковский", "concert", "2024-09-05 20:00",
     2500, 100, "Большой зал филармонии."),
    ("Фильм «Дюна: Часть вторая»", "movie", "2024-09-10 18:30",
     700, 60, "Показ в формате IMAX."),
    ("Спектакль «Вишнёвый сад»", "theater", "2024-09-15 19:00",
     1800, 80, "Постановка МХТ."),
]

def seed():
    init_db()
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) AS c FROM events").fetchone()["c"]
    if count == 0:
        conn.executemany("""
            INSERT INTO events (title, category, date, price, total_seats, description)
            VALUES (?, ?, ?, ?, ?, ?)
        """, EVENTS)
        conn.commit()
        print(f"Добавлено мероприятий: {len(EVENTS)}")
    else:
        print("Мероприятия уже есть, пропускаем.")
    conn.close()

if __name__ == "__main__":
    seed()
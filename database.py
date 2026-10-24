import sqlite3
from config import DB_PATH

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_connection()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        user_id    INTEGER PRIMARY KEY,
        username   TEXT,
        full_name  TEXT,
        phone      TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS events (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        title        TEXT NOT NULL,
        category     TEXT NOT NULL,
        date         TEXT NOT NULL,
        price        REAL NOT NULL DEFAULT 0,
        total_seats  INTEGER NOT NULL DEFAULT 0,
        booked_seats INTEGER NOT NULL DEFAULT 0,
        description  TEXT
    );

    CREATE TABLE IF NOT EXISTS bookings (
        id                      INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id                 INTEGER NOT NULL,
        event_id                INTEGER NOT NULL,
        guests                  INTEGER NOT NULL,
        notes                   TEXT,
        total_price             REAL NOT NULL,
        payment_method          TEXT,
        status                  TEXT NOT NULL DEFAULT 'pending',
        confirmed_by_organizer  INTEGER NOT NULL DEFAULT 0,
        created_at              TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id)  REFERENCES users(user_id),
        FOREIGN KEY (event_id) REFERENCES events(id)
    );

    CREATE TABLE IF NOT EXISTS reviews (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id    INTEGER NOT NULL,
        event_id   INTEGER NOT NULL,
        rating     INTEGER NOT NULL,
        text       TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id)  REFERENCES users(user_id),
        FOREIGN KEY (event_id) REFERENCES events(id)
    );
    """)
    conn.commit()
    conn.close()

# ---------- ПОЛЬЗОВАТЕЛИ ----------
def upsert_user(user_id, username, full_name, phone):
    conn = get_connection()
    conn.execute("""
        INSERT INTO users (user_id, username, full_name, phone)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            username  = excluded.username,
            full_name = excluded.full_name,
            phone     = excluded.phone
    """, (user_id, username, full_name, phone))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return row

# ---------- МЕРОПРИЯТИЯ ----------
def get_events(category=None):
    conn = get_connection()
    if category and category != "all":
        rows = conn.execute(
            "SELECT * FROM events WHERE category = ? ORDER BY date", (category,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM events ORDER BY date").fetchall()
    conn.close()
    return rows

def get_event(event_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    conn.close()
    return row

def free_seats(event_id):
    ev = get_event(event_id)
    return ev["total_seats"] - ev["booked_seats"] if ev else 0

# ---------- БРОНИ ----------
def create_booking(user_id, event_id, guests, notes, total_price, payment_method):
    conn = get_connection()
    cur = conn.execute("""
        INSERT INTO bookings (user_id, event_id, guests, notes, total_price, payment_method)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, event_id, guests, notes, total_price, payment_method))
    booking_id = cur.lastrowid
    conn.execute(
        "UPDATE events SET booked_seats = booked_seats + ? WHERE id = ?",
        (guests, event_id)
    )
    conn.commit()
    conn.close()
    return booking_id

def get_user_bookings(user_id):
    conn = get_connection()
    rows = conn.execute("""
        SELECT b.*, e.title, e.date, e.category
        FROM bookings b
        JOIN events e ON e.id = b.event_id
        WHERE b.user_id = ?
        ORDER BY b.created_at DESC
    """, (user_id,)).fetchall()
    conn.close()
    return rows

def get_booking(booking_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()
    conn.close()
    return row

def cancel_booking(booking_id):
    conn = get_connection()
    b = conn.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()
    if b and b["status"] != "cancelled":
        conn.execute("UPDATE bookings SET status='cancelled' WHERE id = ?", (booking_id,))
        conn.execute(
            "UPDATE events SET booked_seats = MAX(booked_seats - ?, 0) WHERE id = ?",
            (b["guests"], b["event_id"])
        )
        conn.commit()
    conn.close()

def confirm_booking(booking_id):
    conn = get_connection()
    conn.execute("""
        UPDATE bookings
        SET status='confirmed', confirmed_by_organizer=1
        WHERE id = ?
    """, (booking_id,))
    conn.commit()
    conn.close()

def get_pending_bookings():
    conn = get_connection()
    rows = conn.execute("""
        SELECT b.*, u.full_name, u.phone, e.title, e.date
        FROM bookings b
        JOIN users u  ON u.user_id = b.user_id
        JOIN events e ON e.id = b.event_id
        WHERE b.status = 'pending'
        ORDER BY b.created_at
    """).fetchall()
    conn.close()
    return rows

# ---------- ОТЗЫВЫ ----------
def add_review(user_id, event_id, rating, text):
    conn = get_connection()
    conn.execute("""
        INSERT INTO reviews (user_id, event_id, rating, text)
        VALUES (?, ?, ?, ?)
    """, (user_id, event_id, rating, text))
    conn.commit()
    conn.close()

def get_event_reviews(event_id):
    conn = get_connection()
    rows = conn.execute("""
        SELECT r.*, u.full_name FROM reviews r
        JOIN users u ON u.user_id = r.user_id
        WHERE r.event_id = ?
        ORDER BY r.created_at DESC
    """, (event_id,)).fetchall()
    conn.close()
    return rows

def user_attended_event(user_id, event_id):
    """Проверяем, что у пользователя была подтверждённая бронь на мероприятие."""
    conn = get_connection()
    row = conn.execute("""
        SELECT 1 FROM bookings
        WHERE user_id = ? AND event_id = ? AND status = 'confirmed'
        LIMIT 1
    """, (user_id, event_id)).fetchone()
    conn.close()
    return row is not None
import json
import sqlite3
from datetime import datetime

conn = sqlite3.connect("shop.db")
conn.row_factory = sqlite3.Row 

conn.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        date     TEXT,
        status   TEXT,
        items    TEXT,     -- список товаров в виде JSON
        total    INTEGER,
        name     TEXT,
        phone    TEXT,
        address  TEXT,
        comment  TEXT,
        user_id  INTEGER
    )
""")

# Дополнить базу, сохранви существующие закзы
if "user_username" not in {row[1] for row in conn.execute("PRAGMA table_info(orders)")}:
    conn.execute("ALTER TABLE orders ADD COLUMN user_username TEXT")
    conn.commit()


def to_dict(row):
    order = dict(row)
    order["items"] = json.loads(order["items"])
    return order


def add_order(items, total, name, phone, address, comment, user_id, user_username=None):
    cursor = conn.execute(
        "INSERT INTO orders (date, status, items, total, name, phone, address, comment, user_id, user_username) "
        "VALUES (?, 'new', ?, ?, ?, ?, ?, ?, ?, ?)",
        (datetime.now().strftime("%d.%m.%Y %H:%M"), json.dumps(items, ensure_ascii=False),
         total, name, phone, address, comment, user_id, user_username),
    )
    conn.commit()
    return get_order(cursor.lastrowid)


def get_order(order_id):
    row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    return to_dict(row)


def set_status(order_id, status):
    conn.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
    conn.commit()
    return get_order(order_id)


def active_orders():
    rows = conn.execute("SELECT * FROM orders WHERE status IN ('new', 'accepted')").fetchall()
    return [to_dict(row) for row in rows]


def today_orders():
    today = datetime.now().strftime("%d.%m.%Y")
    rows = conn.execute("SELECT * FROM orders WHERE date LIKE ? AND status != 'canceled'", (today + "%",)).fetchall()
    return [to_dict(row) for row in rows]

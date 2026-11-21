"""Sample SQLite database (customers, products, orders, order_items) and connection helpers."""
import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

DB_PATH = Path(__file__).with_name("shop.db")

DDL = """
CREATE TABLE customers (
    id        INTEGER PRIMARY KEY,
    name      TEXT NOT NULL,
    city      TEXT NOT NULL,
    joined_on DATE NOT NULL
);
CREATE TABLE products (
    id       INTEGER PRIMARY KEY,
    name     TEXT NOT NULL,
    category TEXT NOT NULL,
    price    REAL NOT NULL
);
CREATE TABLE orders (
    id          INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    order_date  DATE NOT NULL,
    status      TEXT NOT NULL CHECK (status IN ('delivered', 'shipped', 'cancelled'))
);
CREATE TABLE order_items (
    id         INTEGER PRIMARY KEY,
    order_id   INTEGER NOT NULL REFERENCES orders(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity   INTEGER NOT NULL,
    unit_price REAL NOT NULL
);
"""

FIRST = ["Aarav", "Diya", "Vihaan", "Anaya", "Aditya", "Isha", "Kabir", "Meera", "Rohan", "Saanvi",
         "Arjun", "Riya", "Dev", "Kiara", "Yash", "Tara", "Neel", "Pooja", "Karan", "Nisha"]
LAST = ["Shah", "Patel", "Mehta", "Desai", "Joshi", "Trivedi", "Parmar", "Modi"]
CITIES = ["Vadodara", "Ahmedabad", "Surat", "Rajkot", "Mumbai", "Pune"]
PRODUCTS = [
    ("Wireless Mouse", "Electronics", 799), ("Mechanical Keyboard", "Electronics", 3499),
    ("USB-C Hub", "Electronics", 1299), ("Laptop Stand", "Accessories", 999),
    ("Notebook (Pack of 5)", "Stationery", 350), ("Gel Pens (Box of 10)", "Stationery", 180),
    ("Backpack", "Accessories", 1899), ("Water Bottle", "Accessories", 450),
    ("Desk Lamp", "Home", 1100), ("Office Chair Cushion", "Home", 1550),
    ("Bluetooth Speaker", "Electronics", 2299), ("Phone Stand", "Accessories", 399),
]


def create_database(path: Path = DB_PATH, force: bool = False) -> Path:
    """Create and seed the sample database (deterministic) if it does not exist."""
    path = Path(path)
    if path.exists() and not force:
        return path
    if path.exists():
        path.unlink()
    rng = random.Random(42)
    conn = sqlite3.connect(path)
    conn.executescript(DDL)
    for i in range(1, 41):
        joined = date(2024, 1, 1) + timedelta(days=rng.randint(0, 600))
        conn.execute("INSERT INTO customers VALUES (?,?,?,?)",
                     (i, f"{rng.choice(FIRST)} {rng.choice(LAST)}", rng.choice(CITIES), joined.isoformat()))
    for i, (name, cat, price) in enumerate(PRODUCTS, start=1):
        conn.execute("INSERT INTO products VALUES (?,?,?,?)", (i, name, cat, price))
    item_id = 1
    for oid in range(1, 201):
        odate = date(2025, 1, 1) + timedelta(days=rng.randint(0, 680))
        status = rng.choices(["delivered", "shipped", "cancelled"], weights=[70, 20, 10])[0]
        conn.execute("INSERT INTO orders VALUES (?,?,?,?)", (oid, rng.randint(1, 40), odate.isoformat(), status))
        for pid in rng.sample(range(1, len(PRODUCTS) + 1), rng.randint(1, 4)):
            conn.execute("INSERT INTO order_items VALUES (?,?,?,?,?)",
                         (item_id, oid, pid, rng.randint(1, 3), PRODUCTS[pid - 1][2]))
            item_id += 1
    conn.commit()
    conn.close()
    return path


# SQLite authorizer action codes that a read-only SELECT needs.
_SELECT, _READ, _FUNCTION, _RECURSIVE = 21, 20, 31, 33
_ALLOWED_ACTIONS = {_SELECT, _READ, _FUNCTION, _RECURSIVE}


def _authorizer(action, arg1, arg2, db_name, source):
    return sqlite3.SQLITE_OK if action in _ALLOWED_ACTIONS else sqlite3.SQLITE_DENY


def get_readonly_connection(path: Path = DB_PATH) -> sqlite3.Connection:
    """Read-only connection: opened with mode=ro AND an authorizer that denies everything but SELECT/READ."""
    conn = sqlite3.connect(f"file:{Path(path).as_posix()}?mode=ro", uri=True, check_same_thread=False)
    conn.set_authorizer(_authorizer)
    return conn


def get_schema_text(conn: sqlite3.Connection) -> str:
    """CREATE TABLE statements, used as schema context for the LLM."""
    rows = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return "\n\n".join(r[0].strip() + ";" for r in rows)

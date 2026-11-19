
import sqlite3

DB_NAME = "trip_planner.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def initialize_database():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            destination TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            budget REAL NOT NULL,
            description TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS itinerary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trip_id INTEGER NOT NULL,
            visit_date TEXT NOT NULL,
            place TEXT NOT NULL,
            activity TEXT,
            notes TEXT,
            FOREIGN KEY (trip_id) REFERENCES trips(id)
            ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trip_id INTEGER NOT NULL,
            expense_date TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            description TEXT,
            FOREIGN KEY (trip_id) REFERENCES trips(id)
            ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()

# ---------------- TRIP OPERATIONS ----------------

def add_trip(name, destination, start_date, end_date, budget, description):
    conn = get_connection()

    conn.execute("""
        INSERT INTO trips
        (name, destination, start_date, end_date, budget, description)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (name, destination, start_date, end_date, budget, description))

    conn.commit()
    conn.close()

def get_all_trips():
    conn = get_connection()
    trips = conn.execute(
        "SELECT * FROM trips ORDER BY start_date DESC"
    ).fetchall()
    conn.close()
    return trips

def get_trip(trip_id):
    conn = get_connection()
    trip = conn.execute(
        "SELECT * FROM trips WHERE id = ?", (trip_id,)
    ).fetchone()
    conn.close()
    return trip

def update_trip(trip_id, name, destination, start_date,
                end_date, budget, description):
    conn = get_connection()

    conn.execute("""
        UPDATE trips
        SET name=?, destination=?, start_date=?,
            end_date=?, budget=?, description=?
        WHERE id=?
    """, (name, destination, start_date, end_date,
          budget, description, trip_id))

    conn.commit()
    conn.close()

def delete_trip(trip_id):
    conn = get_connection()
    conn.execute("DELETE FROM trips WHERE id=?", (trip_id,))
    conn.commit()
    conn.close()

# ---------------- ITINERARY OPERATIONS ----------------

def add_itinerary(trip_id, visit_date, place, activity, notes):
    conn = get_connection()

    conn.execute("""
        INSERT INTO itinerary
        (trip_id, visit_date, place, activity, notes)
        VALUES (?, ?, ?, ?, ?)
    """, (trip_id, visit_date, place, activity, notes))

    conn.commit()
    conn.close()

def get_itinerary(trip_id):
    conn = get_connection()

    records = conn.execute("""
        SELECT * FROM itinerary
        WHERE trip_id=?
        ORDER BY visit_date, id
    """, (trip_id,)).fetchall()

    conn.close()
    return records

def delete_itinerary(item_id):
    conn = get_connection()
    conn.execute("DELETE FROM itinerary WHERE id=?", (item_id,))
    conn.commit()
    conn.close()

# ---------------- EXPENSE OPERATIONS ----------------

def add_expense(trip_id, expense_date, category, amount, description):
    conn = get_connection()

    conn.execute("""
        INSERT INTO expenses
        (trip_id, expense_date, category, amount, description)
        VALUES (?, ?, ?, ?, ?)
    """, (trip_id, expense_date, category, amount, description))

    conn.commit()
    conn.close()

def get_expenses(trip_id):
    conn = get_connection()

    records = conn.execute("""
        SELECT * FROM expenses
        WHERE trip_id=?
        ORDER BY expense_date DESC, id DESC
    """, (trip_id,)).fetchall()

    conn.close()
    return records

def delete_expense(expense_id):
    conn = get_connection()
    conn.execute("DELETE FROM expenses WHERE id=?", (expense_id,))
    conn.commit()
    conn.close()

# Initialize tables whenever the application starts
initialize_database()
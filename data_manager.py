import sqlite3
class DataManager:
    def __init__(self, db_name='gym_bot.db'):
        self.db_name = db_name
        self._initialize_database()

    def _initialize_database(self):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                                user_id INTEGER PRIMARY KEY,
                                name TEXT NOT NULL,
                                surname TEXT NOT NULL,
                                ci TEXT NOT NULL UNIQUE,
                                payment_date TEXT,
                                weight REAL,
                                height REAL,
                                modality TEXT,
                                role TEXT
                              )''')
            conn.commit()

    def upsert_user_profile(self, user_id, name, surname, ci, payment_date, weight, height, modality, role):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('''INSERT INTO users (user_id, name, surname, ci, payment_date, weight, height, modality,role)
                              VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                              ON CONFLICT(user_id) DO UPDATE SET
                                name=excluded.name,
                                surname=excluded.surname,
                                ci=excluded.ci,
                                payment_date=excluded.payment_date,
                                weight=excluded.weight,
                                height=excluded.height,
                                modality=excluded.modality''',
                           (user_id, name, surname, ci, payment_date, weight, height, modality, role))
            conn.commit()

    def get_user_profile(self, user_id):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            return row

    def get_all_clients(self):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE role = 'cliente'")
            rows = cursor.fetchall()
            print(rows)
            return rows

    def update_user_role(self, user_id, role):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET role = ? WHERE user_id = ?", (role, user_id))
            conn.commit()

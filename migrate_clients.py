import sqlite3
def migrate():
    conn = sqlite3.connect('gym_tracker.db')
    cursor = conn.cursor()
    try:
        cursor.execute('''
            CREATE TABLE clients_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trainer_id INTEGER NOT NULL,
                name VARCHAR(100) NOT NULL,
                contact_number VARCHAR(20),
                status VARCHAR(20) DEFAULT 'ongoing',
                pt_tier VARCHAR(20) DEFAULT 'Silver',
                renewal_date DATE,
                notes TEXT,
                created_at DATETIME,
                FOREIGN KEY(trainer_id) REFERENCES trainers(id)
            )
        ''')
        cursor.execute('''
            INSERT INTO clients_new (id, trainer_id, name, contact_number, status, pt_tier, renewal_date, notes, created_at)
            SELECT id, trainer_id, name, contact_number, status, pt_tier, renewal_date, notes, created_at FROM clients
        ''')
        cursor.execute('DROP TABLE clients')
        cursor.execute('ALTER TABLE clients_new RENAME TO clients')
        conn.commit()
        print("Migration successful")
    except Exception as e:
        conn.rollback()
        print(f"Error during migration: {e}")
    finally:
        conn.close()
if __name__ == '__main__':
    migrate()
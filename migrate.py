import sqlite3
import psycopg2

print("🔄 Reading data from SQLite...")
sqlite_conn = sqlite3.connect('database.db')
sqlite_cur = sqlite_conn.cursor()
sqlite_cur.execute('SELECT name, email, password, role FROM users')
users_data = sqlite_cur.fetchall()
sqlite_conn.close()

print(f"✅ Found {len(users_data)} users in SQLite.")
print("🔄 Connecting to PostgreSQL...")

try:
    # ⚠️ खालील password मध्ये तुझा PostgreSQL चा खरा पासवर्ड टाक
    pg_conn = psycopg2.connect(
        dbname="env_education",
        user="postgres",
        password="YOUR_POSTGRES_PASSWORD", 
        host="localhost"
    )
    pg_cur = pg_conn.cursor()

    # PostgreSQL मध्ये users टेबल बनवणे
    pg_cur.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT,
        role TEXT
    )
    ''')
    pg_conn.commit()

    # SQLite चा डेटा PostgreSQL मध्ये टाकणे
    for user in users_data:
        try:
            pg_cur.execute(
                "INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)",
                (user[0], user[1], user[2], user[3])
            )
            pg_conn.commit()
            print(f"✅ Migrated: {user[0]} ({user[3]})")
        except psycopg2.IntegrityError:
            pg_conn.rollback()
            print(f"⚠️ Already exists in PostgreSQL: {user[0]}")

    pg_cur.close()
    pg_conn.close()
    print("🎉 All data successfully migrated to PostgreSQL!")

except Exception as e:
    print("❌ Error connecting to PostgreSQL:", e)

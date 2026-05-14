import bcrypt
import sqlite3

conn = sqlite3.connect('orcanos_performance.db')
password = bcrypt.hashpw(b'Orcanos@2026!1234', bcrypt.gensalt()).decode()

conn.execute('DELETE FROM users')
conn.execute('INSERT INTO users (username, hashed_password, role) VALUES (?, ?, ?)',
             ('admin', password, 'admin'))
conn.execute('INSERT INTO users (username, hashed_password, role) VALUES (?, ?, ?)',
             ('user', password, 'user'))

conn.commit()
conn.close()
print("Users reset. Login with: admin/Orcanos@2026!1234 or user/Orcanos@2026!1234")

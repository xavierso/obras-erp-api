import sqlite3
conn = sqlite3.connect('obras.db')
conn.execute("UPDATE usuarios SET email = 'deleted_' || id || '_' || email WHERE is_active = 0;")
conn.commit()
conn.close()

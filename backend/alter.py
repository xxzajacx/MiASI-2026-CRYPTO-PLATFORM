import sqlite3

try:
    conn = sqlite3.connect('d:/Giełda/backend/gielda.db')
    conn.execute('ALTER TABLE wallets ADD COLUMN wallet_type VARCHAR DEFAULT "SPOT"')
    conn.commit()
    conn.close()
    print("Database altered successfully")
except Exception as e:
    print("Error:", e)

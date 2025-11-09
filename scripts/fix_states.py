import sqlite3
con = sqlite3.connect('queue.db')
with con:
    con.execute("UPDATE jobs SET state='pending' WHERE state='queued'")
print("State normalized to 'pending' where needed.")

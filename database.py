import sqlite3
from sqlite3 import Error

DB_FILE = "osint_data.db"

def create_connection():
    """ יצירת חיבור למסד הנתונים """
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        return conn
    except Error as e:
        print(f"Error connecting to database: {e}")
    return conn

def setup_database():
    """ יצירת הטבלה אם היא לא קיימת """
    conn = create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            # יצירת טבלה עם השדות שנדרשו במשימה
            # שים לב ש post_link מוגדר כ-UNIQUE כדי למנוע כפילויות
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    platform TEXT NOT NULL,
                    username TEXT NOT NULL,
                    post_text TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    post_link TEXT UNIQUE NOT NULL
                );
            """)
            conn.commit()
            print("Database setup complete. Table 'posts' is ready.")
        except Error as e:
            print(f"Error creating table: {e}")
        finally:
            conn.close()
    else:
        print("Cannot create the database connection.")

def insert_post(platform, username, post_text, timestamp, post_link):
    """ הכנסת פוסט חדש למסד הנתונים """
    conn = create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO posts (platform, username, post_text, timestamp, post_link)
                VALUES (?, ?, ?, ?, ?)
            """, (platform, username, post_text, timestamp, post_link))
            conn.commit()
            print(f"[+] Saved new post from {username} on {platform}")
            return True
        except sqlite3.IntegrityError:
            # שגיאה זו קופצת אוטומטית אם אנחנו מנסים להכניס לינק שכבר קיים
            # כך אנחנו עומדים בדרישה של מניעת כפילויות בקלות!
            print(f"[-] Duplicate post ignored: {post_link}")
            return False
        except Error as e:
            print(f"Error inserting post: {e}")
            return False
        finally:
            conn.close()

# בלוק בדיקה - ירוץ רק אם נפעיל את הקובץ הזה ישירות
if __name__ == '__main__':
    setup_database()
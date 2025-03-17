import os
import mysql.connector

# ✅ ตั้งค่าการเชื่อมต่อ MySQL (XAMPP)
def connect_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="ai_orchestration_local"
    )

class ConfigManager:
    def __init__(self):
        self._create_table()

    def _create_table(self):
        """✅ สร้างตารางเก็บ LINE OA Config ถ้ายังไม่มี"""
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS line_oa_config (
                id INT AUTO_INCREMENT PRIMARY KEY,
                agency_name VARCHAR(255) UNIQUE,
                channel_secret TEXT,
                access_token TEXT
            )
        """)
        conn.commit()
        conn.close()

    def add_oa(self, agency_name, channel_secret, access_token):
        """✅ เพิ่ม LINE OA ใหม่เข้าไปในระบบ"""
        conn = connect_db()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO line_oa_config (agency_name, channel_secret, access_token)
                VALUES (%s, %s, %s)
            """, (agency_name, channel_secret, access_token))
            conn.commit()
            print(f"✅ Added OA for {agency_name}")
        except mysql.connector.Error as e:
            print(f"❌ Database Error: {e}")
        finally:
            conn.close()

    def get_oa_config(self, agency_name):
        """✅ ดึงค่าของ LINE OA ตามชื่อหน่วยงาน"""
        print(f"🔍 Checking database for agency: {agency_name}")
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT channel_secret, access_token FROM line_oa_config WHERE agency_name = %s", (agency_name,))
        row = cursor.fetchone()
        conn.close()

        if row:
            print(f"✅ Found config for {agency_name}: {row}")
            return row
        else:
            print(f"⚠️ Agency '{agency_name}' not found in database!")
            return None

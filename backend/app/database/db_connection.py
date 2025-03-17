import mysql.connector
import logging

def get_db_connection():
    """สร้างการเชื่อมต่อกับฐานข้อมูล MySQL"""
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="ai_orchestration_local"
        )
        return connection
    except mysql.connector.Error as err:
        logging.error(f"ไม่สามารถเชื่อมต่อกับฐานข้อมูลได้: {err}")
        raise

def init_database():
    """สร้างฐานข้อมูลและตารางที่จำเป็น"""
    try:
        # สร้างการเชื่อมต่อโดยไม่ระบุฐานข้อมูล
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password=""
        )
        cursor = connection.cursor()

        # สร้างฐานข้อมูล
        cursor.execute("CREATE DATABASE IF NOT EXISTS ai_orchestration_local")
        cursor.execute("USE ai_orchestration_local")

        # สร้างตาราง agents
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agents (
                id INT AUTO_INCREMENT PRIMARY KEY,
                agent_name VARCHAR(255) UNIQUE,
                agent_type VARCHAR(50),
                prompt_template TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # สร้างตาราง webhooks
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS webhooks (
                id INT AUTO_INCREMENT PRIMARY KEY,
                agency_name VARCHAR(255) NOT NULL,
                webhook_url VARCHAR(255) NOT NULL,
                line_access_token TEXT NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # สร้างตาราง webhook_agents
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS webhook_agents (
                id INT AUTO_INCREMENT PRIMARY KEY,
                webhook_id INT NOT NULL,
                agent_id INT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (webhook_id) REFERENCES webhooks(id) ON DELETE CASCADE,
                FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE,
                UNIQUE KEY unique_webhook_agent (webhook_id, agent_id)
            )
        """)

        # สร้างตาราง webhook_logs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS webhook_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                webhook_id INT,
                request_data TEXT,
                response_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (webhook_id) REFERENCES webhooks(id) ON DELETE CASCADE
            )
        """)

        # สร้างตาราง agent_performance
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_performance (
                id INT AUTO_INCREMENT PRIMARY KEY,
                agent_name VARCHAR(255),
                request_text TEXT,
                response_text TEXT,
                response_time FLOAT,
                status VARCHAR(50),
                error TEXT NULL,
                usage_data JSON NULL,
                model VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (agent_name) REFERENCES agents(agent_name) ON DELETE CASCADE
            )
        """)

        connection.commit()
        cursor.close()
        connection.close()

        logging.info("สร้างฐานข้อมูลและตารางสำเร็จ")
    except mysql.connector.Error as err:
        logging.error(f"เกิดข้อผิดพลาดในการสร้างฐานข้อมูล: {err}")
        raise

# ทดสอบ Connection
try:
    conn = get_db_connection()
    conn.close()
    logging.info("เชื่อมต่อฐานข้อมูลสำเร็จ")
except Exception as e:
    logging.error(f"ไม่สามารถเชื่อมต่อฐานข้อมูล: {e}")
    raise

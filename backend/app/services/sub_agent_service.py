import mysql.connector
import logging
import json
import openai
from datetime import datetime

# ตั้งค่า OpenAI API Key
openai.api_key = "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"

def connect_db():
    """เชื่อมต่อฐานข้อมูล MySQL"""
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="ai_orchestration_local"
    )

class SubAgentService:
    def __init__(self):
        self._create_tables()
        self.chat_model = openai.ChatCompletion()

    def _create_tables(self):
        """สร้างตารางที่จำเป็นถ้ายังไม่มี"""
        conn = connect_db()
        cursor = conn.cursor()

        # สร้างตาราง agents
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agents (
                id INT AUTO_INCREMENT PRIMARY KEY,
                agent_name VARCHAR(255) UNIQUE,
                description TEXT,
                prompt_template TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # สร้างตาราง training_data
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS training_data (
                id INT AUTO_INCREMENT PRIMARY KEY,
                agent_id INT,
                input_text TEXT,
                expected_output TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (agent_id) REFERENCES agents(id)
            )
        """)

        conn.commit()
        cursor.close()
        conn.close()

    def list_agents(self):
        """ดึงข้อมูล agents ทั้งหมด"""
        try:
            conn = connect_db()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM agents")
            agents = cursor.fetchall()
            cursor.close()
            conn.close()
            return agents
        except mysql.connector.Error as err:
            logging.error(f"Error listing agents: {err}")
            return []

    def create_agent(self, agent_name: str, description: str, prompt_template: str):
        """สร้าง agent ใหม่"""
        try:
            conn = connect_db()
            cursor = conn.cursor()

            cursor.execute(
                "INSERT INTO agents (agent_name, description, prompt_template) VALUES (%s, %s, %s)",
                (agent_name, description, prompt_template)
            )

            conn.commit()
            agent_id = cursor.lastrowid

            cursor.close()
            conn.close()

            return {
                "id": agent_id,
                "agent_name": agent_name,
                "description": description,
                "prompt_template": prompt_template
            }
        except mysql.connector.Error as err:
            logging.error(f"Error creating agent: {err}")
            raise Exception("ไม่สามารถสร้าง agent ได้")

    def get_agent(self, agent_id: int):
        """ดึงข้อมูล agent ตาม ID"""
        try:
            conn = connect_db()
            cursor = conn.cursor(dictionary=True)

            cursor.execute("SELECT * FROM agents WHERE id = %s", (agent_id,))
            agent = cursor.fetchone()

            cursor.close()
            conn.close()

            return agent
        except mysql.connector.Error as err:
            logging.error(f"Error getting agent: {err}")
            return None

    def update_agent(self, agent_id: int, description: str, prompt_template: str):
        """อัพเดทข้อมูล agent"""
        try:
            conn = connect_db()
            cursor = conn.cursor()

            cursor.execute(
                "UPDATE agents SET description = %s, prompt_template = %s WHERE id = %s",
                (description, prompt_template, agent_id)
            )

            conn.commit()
            success = cursor.rowcount > 0

            cursor.close()
            conn.close()

            return success
        except mysql.connector.Error as err:
            logging.error(f"Error updating agent: {err}")
            return False

    def add_training_data(self, agent_id: int, input_text: str, expected_output: str):
        """เพิ่มข้อมูลสำหรับฝึก agent"""
        try:
            conn = connect_db()
            cursor = conn.cursor()

            cursor.execute(
                "INSERT INTO training_data (agent_id, input_text, expected_output) VALUES (%s, %s, %s)",
                (agent_id, input_text, expected_output)
            )

            conn.commit()
            success = cursor.rowcount > 0

            cursor.close()
            conn.close()

            return success
        except mysql.connector.Error as err:
            logging.error(f"Error adding training data: {err}")
            return False

    def get_training_data(self, agent_id: int):
        """ดึงข้อมูลที่ใช้ฝึก agent"""
        try:
            conn = connect_db()
            cursor = conn.cursor(dictionary=True)

            cursor.execute(
                "SELECT * FROM training_data WHERE agent_id = %s ORDER BY created_at DESC",
                (agent_id,)
            )
            training_data = cursor.fetchall()

            cursor.close()
            conn.close()

            return training_data
        except mysql.connector.Error as err:
            logging.error(f"Error getting training data: {err}")
            return []

    def process_message(self, agent_name: str, message: str):
        """ประมวลผลข้อความด้วย agent ที่เลือก

        Args:
            agent_name (str): ชื่อของ agent
            message (str): ข้อความที่ต้องการประมวลผล

        Returns:
            str: ข้อความตอบกลับจาก AI
        """
        try:
            # ดึงข้อมูล agent จาก database
            conn = connect_db()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM agents WHERE agent_name = %s", (agent_name,))
            agent = cursor.fetchone()
            cursor.close()
            conn.close()

            if not agent:
                return f"❌ ไม่พบ agent ชื่อ {agent_name}"

            # สร้างโครงสร้างข้อความสำหรับ OpenAI
            messages = [
                {"role": "system", "content": agent["prompt_template"]},
                {"role": "user", "content": message}
            ]

            print(f"📝 กำลังส่งข้อความไป OpenAI: {json.dumps(messages, indent=2, ensure_ascii=False)}")

            # เรียกใช้ OpenAI API
            start_time = datetime.now()
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=2048,
                temperature=0.3
            )
            response_time = (datetime.now() - start_time).total_seconds()

            # แปลง response เป็น dict
            if isinstance(response, str):
                response_dict = json.loads(response)
            else:
                response_dict = response if isinstance(response, dict) else response.to_dict()

            print(f"📌 Response จาก OpenAI: {json.dumps(response_dict, indent=2, ensure_ascii=False)}")

            try:
                # ดึงข้อความจาก choices[0].message.content
                choices = response_dict["choices"]
                if not choices:
                    return "❌ OpenAI API ไม่ได้ส่ง choices"

                first_choice = choices[0]
                if isinstance(first_choice, str):
                    first_choice = json.loads(first_choice)

                message_obj = first_choice["message"]
                if isinstance(message_obj, str):
                    message_obj = json.loads(message_obj)

                ai_message = message_obj["content"].strip()
                if not ai_message:
                    return "❌ OpenAI API ไม่ได้ส่งข้อความที่ถูกต้อง"

                # บันทึก log การสนทนา
                usage_data = {}
                if "usage" in response_dict:
                    usage_data = response_dict["usage"]
                    if isinstance(usage_data, str):
                        usage_data = json.loads(usage_data)

                save_conversation_log(
                    agent_name=agent_name,
                    message=message,
                    response=ai_message,
                    response_time=response_time,
                    status='success',
                    usage_data=usage_data,
                    model=response_dict.get("model", "unknown")
                )

                return ai_message

            except (KeyError, IndexError) as e:
                error_message = f"❌ รูปแบบข้อมูลจาก OpenAI API ไม่ถูกต้อง: {str(e)}"
                save_conversation_log(
                    agent_name=agent_name,
                    message=message,
                    response=None,
                    response_time=0,
                    status='error',
                    error=error_message
                )
                return error_message

        except Exception as e:
            error_message = f"❌ เกิดข้อผิดพลาด: {str(e)}"
            print(error_message)
            
            save_conversation_log(
                agent_name=agent_name,
                message=message,
                response=None,
                response_time=0,
                status='error',
                error=str(e)
            )
            
            return error_message
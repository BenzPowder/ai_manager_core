import mysql.connector
import os
import openai
import json
from datetime import datetime
from app.agents.sub_agent_manager import SubAgentManager
from app.services.sub_agent_service import SubAgentService

# ตั้งค่าการเชื่อมต่อ MySQL (XAMPP)
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="ai_orchestration_local"
    )

# ตั้งค่า OpenAI API Key
openai.api_key = os.getenv("OPENAI_API_KEY")

def save_conversation_log(agent_name, message, response, response_time, status='success', usage_data=None, model=None, error=None, test=False):
    """บันทึก log การสนทนากับ OpenAI

    Args:
        agent_name (str): ชื่อของ agent
        message (str): ข้อความที่ส่งไป
        response (str): ข้อความตอบกลับ
        response_time (float): เวลาที่ใช้ในการตอบกลับ
        status (str, optional): สถานะการตอบกลับ. Defaults to 'success'.
        usage_data (dict, optional): ข้อมูลการใช้งาน token. Defaults to None.
        model (str, optional): โมเดลที่ใช้. Defaults to None.
        error (str, optional): ข้อความ error ถ้ามี. Defaults to None.
        test (bool, optional): เป็นการทดสอบหรือไม่. Defaults to False.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # สร้างตารางถ้ายังไม่มี
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                agent_name VARCHAR(255),
                message TEXT,
                response TEXT,
                response_time FLOAT,
                status VARCHAR(50),
                usage_data JSON,
                model VARCHAR(50),
                error TEXT,
                test BOOLEAN,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

        # แปลง usage_data เป็น JSON string ถ้ามี
        usage_json = json.dumps(usage_data) if usage_data else None

        # บันทึก log
        cursor.execute("""
            INSERT INTO conversation_logs 
            (agent_name, message, response, response_time, status, usage_data, model, error, test)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            agent_name,
            message,
            response,
            response_time,
            status,
            usage_json,
            model,
            error,
            test
        ))
        conn.commit()

    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดในการบันทึก log: {str(e)}")
    finally:
        cursor.close()
        conn.close()

import openai
import json

def process_with_openai(messages):
    """ส่งข้อความไปประมวลผลที่ OpenAI API"""
    try:
        print(f"📝 กำลังส่งข้อความไป OpenAI: {json.dumps(messages, ensure_ascii=False, indent=2)}")

        start_time = datetime.now()
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.2,
            max_tokens=300
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
                raise ValueError("❌ OpenAI API ไม่ได้ส่ง choices")

            first_choice = choices[0]
            if isinstance(first_choice, str):
                first_choice = json.loads(first_choice)

            message_obj = first_choice["message"]
            if isinstance(message_obj, str):
                message_obj = json.loads(message_obj)

            message_content = message_obj["content"].strip()
            if not message_content:
                raise ValueError("❌ OpenAI API ไม่ได้ส่งข้อความที่ถูกต้อง")

            # จัดการ usage_data
            usage_data = {}
            if "usage" in response_dict:
                usage_data = response_dict["usage"]
                if isinstance(usage_data, str):
                    usage_data = json.loads(usage_data)

            result = {
                'message': message_content,
                'usage': usage_data,
                'model': response_dict.get("model", "unknown"),
                'response_time': response_time
            }

            print(f"✅ Debug: process_with_openai() return: {json.dumps(result, ensure_ascii=False, indent=2)}")
            return result

        except (KeyError, IndexError) as e:
            raise ValueError(f"❌ รูปแบบข้อมูลจาก OpenAI API ไม่ถูกต้อง: {str(e)}")

    except Exception as e:
        error_message = f"❌ เกิดข้อผิดพลาด: {str(e)}"
        print(error_message)
        return {
            'message': "ขออภัย ระบบไม่สามารถประมวลผลข้อความได้ในขณะนี้ กรุณาลองใหม่อีกครั้งในภายหลัง",
            'error': error_message
        }

class AgentService:
    """บริการจัดการ AI Agent"""

    def __init__(self):
        """สร้าง instance ของ AgentService"""
        self._create_table()
        self.sub_agent_manager = SubAgentManager()  # ใช้ SubAgentManager
        self.agents = {}  # เก็บ agent ทั้งหมด

    def test_agent(self, agent_id, message):
        """ทดสอบ agent ด้วยข้อความทดสอบ

        Args:
            agent_id (str): ID ของ agent ที่ต้องการทดสอบ
            message (str): ข้อความทดสอบ

        Returns:
            str: ข้อความตอบกลับจาก AI
        """
        try:
            # ดึงข้อมูล agent จากฐานข้อมูล
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name, prompt_template, agent_type
                FROM agents
                WHERE id = %s
            """, (agent_id,))
            agent_data = cursor.fetchone()
            cursor.close()
            conn.close()

            if not agent_data:
                return "ไม่พบ Agent ที่ระบุ"

            name, prompt_template, agent_type = agent_data

            # สร้าง messages array
            messages = [{
                "role": "system",
                "content": prompt_template or """คุณเป็น AI ผู้ช่วยที่ตอบคำถามสั้น กระชับ และตรงประเด็น
                - ตอบให้สั้นที่สุดเท่าที่จะเป็นไปได้
                - ใช้ภาษาที่เข้าใจง่าย
                - ถ้าต้องแนะนำขั้นตอน ให้ระบุเป็นข้อๆ สั้นๆ
                - ไม่ต้องมีคำนำหรือคำลงท้าย"""
            }, {
                "role": "user",
                "content": message
            }]

            # เรียกใช้ OpenAI API
            start_time = datetime.now()
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.3,
                max_tokens=500
            )
            response_time = (datetime.now() - start_time).total_seconds()

            # ดึงข้อความตอบกลับและจัดรูปแบบ
            ai_message = response.choices[0].message.content.strip()
            ai_message = self._format_response(ai_message)

            # บันทึก log การทดสอบ
            save_conversation_log(
                agent_name=name,
                message=message,
                response=ai_message,
                response_time=response_time,
                status='success',
                usage_data=dict(response.usage) if hasattr(response, 'usage') else None,
                model=response.model
            )

            return ai_message

        except Exception as e:
            print(f"❌ เกิดข้อผิดพลาดในการทดสอบ agent: {str(e)}")
            error_message = "ขออภัย ระบบไม่สามารถทดสอบ agent ได้ในขณะนี้ กรุณาลองใหม่อีกครั้งในภายหลัง"
            
            # บันทึก error log
            save_conversation_log(
                agent_name=name if 'name' in locals() else 'unknown',
                message=message,
                response=None,
                response_time=0,
                status='error',
                error=str(e),
                test=True
            )
            
            return error_message

    def _format_response(self, message):
        """จัดรูปแบบข้อความตอบกลับให้สวยงาม"""
        # ลบ markdown format และจัดรูปแบบข้อความ
        message = message.replace('*', '')  # ลบ markdown
        message = message.replace('\\n', '\n')  # แก้ไข escaped newlines
        message = message.replace('\n\n', '\n')  # ลดช่องว่างระหว่างบรรทัด

        # แทนที่หมายเลขข้อด้วยข้อความที่อ่านง่ายกว่า
        import re
        lines = message.split('\n')
        formatted_lines = []
        
        for line in lines:
            # แทนที่หมายเลขข้อ
            line = re.sub(r'(\d+)\. ', r'📍 ข้อ \1: ', line)
            # เพิ่ม emoji ที่เกี่ยวข้อง
            if "ตรวจสอบ" in line:
                line = "🔍 " + line
            elif "ติดต่อ" in line:
                line = "📞 " + line
            elif "แจ้ง" in line:
                line = "📢 " + line
            elif "รอ" in line:
                line = "⏳ " + line
            formatted_lines.append(line)

        message = '\n'.join(formatted_lines)
        message = ' '.join(message.split())  # แก้ไขการจัดรูปแบบช่องว่าง
        
        return message

    def _create_table(self):
        """สร้างตารางสำหรับเก็บข้อมูล AI Sub-Agent ถ้ายังไม่มี"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_sub_agents (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) UNIQUE,
                sub_agents JSON
            )
        """)
        conn.commit()
        conn.close()

    def create_agent(self, name, sub_agent):
        """เพิ่ม AI Sub-Agent ใหม่"""
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO ai_sub_agents (name, sub_agents) VALUES (%s, %s)", (name, sub_agent))
            conn.commit()
            print(f" Created AI Sub-Agent: {name} with Sub-Agent: {sub_agent}")
            return {"id": cursor.lastrowid, "name": name, "sub_agent": sub_agent}
        except mysql.connector.Error as e:
            print(f" Database Error: {e}")
        finally:
            conn.close()

    def list_agents(self):
        """ดึงรายชื่อ AI Sub-Agent ทั้งหมด"""
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, name, sub_agents FROM ai_sub_agents")
        agents = cursor.fetchall()
        conn.close()
        return agents

    def get_sub_agent(self, agency_name):
        """ค้นหา AI Sub-Agent ที่เกี่ยวข้องกับ agency_name"""
        print(f" Searching for AI Sub-Agent linked to {agency_name}")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT sub_agents FROM ai_sub_agents WHERE name = %s", (agency_name,))
            row = cursor.fetchone()
        except Exception as e:
            print(f" Database Error: {e}")
            row = None
        finally:
            conn.close()

        if row:
            sub_agent_name = row[0]
            print(f" Found Sub-Agent: {sub_agent_name}")
            return self.sub_agent_manager.get_agent(sub_agent_name)  # คืนค่าเป็น Object
        else:
            print(f" No AI Sub-Agent found for {agency_name}")
            return None  # ไม่มี AI Sub-Agent

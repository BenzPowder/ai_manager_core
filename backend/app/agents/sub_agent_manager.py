import mysql.connector
import os
import openai
import json
from datetime import datetime

# ตั้งค่า OpenAI API Key
openai.api_key = os.getenv("OPENAI_API_KEY")

def connect_db():
    """เชื่อมต่อกับฐานข้อมูล MySQL"""
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="ai_orchestration_local"
    )

def save_conversation_log(agent_name, request_text, response_text, response_time, status='success', error=None, usage_data=None, model=None):
    """บันทึก log การสนทนากับ AI Agent"""
    conn = connect_db()
    cursor = conn.cursor()
    try:
        # สร้างตารางถ้ายังไม่มี
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
        
        # บันทึกข้อมูล
        cursor.execute("""
            INSERT INTO agent_performance 
            (agent_name, request_text, response_text, response_time, status, error, usage_data, model)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            agent_name,
            request_text,
            response_text,
            response_time,
            status,
            error,
            json.dumps(usage_data) if usage_data else None,
            model
        ))
        conn.commit()
        
    except Exception as e:
        print(f"❌ ไม่สามารถบันทึก log ได้: {str(e)}")
    finally:
        cursor.close()
        conn.close()

class SubAgent:
    def __init__(self, name, agent_type=None, prompt_template=None, model="gpt-4o-mini"):
        """สร้าง instance ของ SubAgent"""
        self.name = name
        self.agent_type = agent_type
        self.prompt_template = prompt_template
        self.model = model
        self.conversation_history = []  # เพิ่มการเก็บประวัติการสนทนา
        
    def process_message(self, message):
        """ประมวลผลข้อความและส่งคำตอบกลับ"""
        try:
            messages = []

            # ✅ ตรวจสอบว่ามี prompt_template หรือไม่
            if self.prompt_template:
                messages.append({"role": "system", "content": self.prompt_template})
            else:
                messages.append({
                    "role": "system", 
                    "content": """คุณเป็น AI ผู้ช่วยที่ตอบคำถามสั้น กระชับ และตรงประเด็น
                    - ตอบให้สั้นที่สุดเท่าที่จะเป็นไปได้
                    - ใช้ภาษาที่เข้าใจง่าย
                    - ถ้าต้องแนะนำขั้นตอน ให้ระบุเป็นข้อๆ สั้นๆ
                    - ไม่ต้องมีคำนำหรือคำลงท้าย"""
                })

            # ✅ เพิ่มประวัติการสนทนา (ล่าสุด 5 ข้อความ)
            for msg in self.conversation_history[-5:]:
                messages.append(msg)

            # ✅ เพิ่มข้อความปัจจุบันของผู้ใช้
            messages.append({"role": "user", "content": message})

            print(f"📝 กำลังส่งข้อความไป OpenAI: {json.dumps(messages, indent=2, ensure_ascii=False)}")

            start_time = datetime.now()
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                max_tokens=500
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

                ai_message = message_obj["content"].strip()
                if not ai_message:
                    raise ValueError("❌ OpenAI API ไม่ได้ส่งข้อความที่ถูกต้อง")

                # เพิ่มข้อความลงในประวัติการสนทนา
                self.conversation_history.append({"role": "assistant", "content": ai_message})

                # บันทึก log การสนทนา
                usage_data = {}
                if "usage" in response_dict:
                    usage_data = response_dict["usage"]
                    if isinstance(usage_data, str):
                        usage_data = json.loads(usage_data)

                save_conversation_log(
                    agent_name=self.name,
                    request_text=message,
                    response_text=ai_message,
                    response_time=response_time,
                    status='success',
                    usage_data=usage_data,
                    model=response_dict.get("model", "unknown")
                )

                return ai_message

            except (KeyError, IndexError) as e:
                error_message = f"❌ รูปแบบข้อมูลจาก OpenAI API ไม่ถูกต้อง: {str(e)}"
                save_conversation_log(
                    agent_name=self.name,
                    request_text=message,
                    response_text=None,
                    response_time=0,
                    status='error',
                    error=error_message
                )
                return error_message

        except Exception as e:
            error_message = f"❌ เกิดข้อผิดพลาด: {str(e)}"
            print(error_message)
            
            save_conversation_log(
                agent_name=self.name,
                request_text=message,
                response_text=None,
                response_time=0,
                status='error',
                error=str(e)
            )
            
            return error_message

    def _format_response(self, message):
        """จัดรูปแบบข้อความตอบกลับจาก AI"""
        try:
            # ลบ markdown format
            message = message.replace('*', '')
            message = message.replace('\\n', '\n')
            message = message.replace('\n\n', '\n')

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
            return ' '.join(message.split())  # แก้ไขการจัดรูปแบบช่องว่าง

        except Exception as e:
            print(f"❌ เกิดข้อผิดพลาดในการจัดรูปแบบข้อความ: {str(e)}")
            return message  # ถ้าเกิดข้อผิดพลาด ส่งคืนข้อความเดิม

    def _log_prompt_change(self, old_prompt, new_prompt):
        """บันทึกการเปลี่ยนแปลง prompt template"""
        print(f"🔄 Prompt template เปลี่ยนจาก: {old_prompt} เป็น: {new_prompt}")

    def update_prompt(self, new_prompt):
        """อัปเดต prompt template"""
        if new_prompt != self.prompt_template:
            self._log_prompt_change(self.prompt_template, new_prompt)
            self.prompt_template = new_prompt

    @staticmethod
    def get_agent_performance(agent_name):
        """ดึงข้อมูลประสิทธิภาพของ agent"""
        conn = connect_db()
        cursor = conn.cursor()
        try:
            # ดึงข้อมูลจำนวนคำขอทั้งหมด
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_requests,
                    AVG(response_time) as avg_response_time,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as capable_requests,
                    SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as non_capable_requests
                FROM agent_performance
                WHERE agent_name = %s
            """, (agent_name,))
            
            result = cursor.fetchone()
            if result:
                return {
                    'total_requests': result[0],
                    'avg_response_time': float(result[1]) if result[1] else 0,
                    'capable_requests': result[2],
                    'non_capable_requests': result[3]
                }
            return {
                'total_requests': 0,
                'avg_response_time': 0,
                'capable_requests': 0,
                'non_capable_requests': 0
            }
            
        except Exception as e:
            print(f"❌ ไม่สามารถดึงข้อมูลประสิทธิภาพได้: {str(e)}")
            return None
        finally:
            cursor.close()
            conn.close()

class SubAgentManager:
    def __init__(self):
        """สร้าง instance ของ SubAgentManager"""
        self.agents = {}
    
    def create_agent(self, name, agent_type=None, prompt_template=None):
        """สร้าง SubAgent ใหม่"""
        self.agents[name] = SubAgent(name, agent_type, prompt_template)
        return self.agents[name]
    
    def get_agent(self, name):
        """ดึง SubAgent ตามชื่อ"""
        return self.agents.get(name)
    
    def list_agents(self):
        """แสดงรายชื่อ SubAgent ทั้งหมด"""
        return list(self.agents.keys())

# สร้าง instance ของ SubAgentManager
ai_manager = SubAgentManager()

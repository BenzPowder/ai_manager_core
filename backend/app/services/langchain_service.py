import os
import openai
import logging
from datetime import datetime

# ตั้งค่า OpenAI API Key
openai.api_key = "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"

# โหลด environment variables
# load_dotenv()

class LangChainService:
    def __init__(self):
        """เริ่มต้นการทำงานของ LangChain Service"""
        try:
            self.chat_model = openai.ChatCompletion()
        except Exception as e:
            logging.error(f"ไม่สามารถเริ่มต้น LangChain Service ได้: {e}")
            raise

    def analyze_message(self, message: str, agents: list) -> str:
        """วิเคราะห์ข้อความและเลือก agent ที่เหมาะสมที่สุด"""
        try:
            if not agents:
                return None

            # สร้าง prompt สำหรับวิเคราะห์ข้อความ
            agent_descriptions = "\n".join([
                f"- {agent['name']}: {agent['description']}"
                for agent in agents
            ])

            prompt_template = """วิเคราะห์ข้อความต่อไปนี้และเลือก agent ที่เหมาะสมที่สุดในการตอบกลับ:

ข้อความ: {message}

รายชื่อ agents ที่มี:
{agent_descriptions}

เลือก agent ที่เหมาะสมที่สุดโดยพิจารณาจากคำอธิบายของแต่ละ agent
ตอบกลับเฉพาะชื่อ agent เท่านั้น"""

            prompt = prompt_template.format(
                message=message,
                agent_descriptions=agent_descriptions
            )

            # ส่งข้อความไปยัง OpenAI
            response = self.chat_model.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "คุณเป็น AI Assistant ที่ช่วยตอบคำถามและให้คำแนะนำ"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )

            selected_agent = response.choices[0].message.content.strip()

            # ตรวจสอบว่า agent ที่เลือกมีอยู่จริง
            agent_names = [agent['name'] for agent in agents]
            if selected_agent in agent_names:
                return selected_agent
            else:
                # ถ้าไม่พบ agent ที่เลือก ให้ใช้ agent แรกในรายการ
                logging.warning(f"ไม่พบ agent '{selected_agent}' ใช้ agent แรกแทน")
                return agents[0]['name']

        except Exception as e:
            logging.error(f"เกิดข้อผิดพลาดในการวิเคราะห์ข้อความ: {e}")
            # ในกรณีที่มีข้อผิดพลาด ให้ใช้ agent แรกในรายการ
            return agents[0]['name'] if agents else None

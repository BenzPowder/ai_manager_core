import logging
import json
from datetime import datetime
from .sub_agent_service import SubAgentService
import mysql.connector
from .langchain_service import LangChainService

# ฟังก์ชันเชื่อมต่อฐานข้อมูล
def connect_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="ai_orchestration_local"
    )

class WebhookService:
    def __init__(self):
        self.agent_service = SubAgentService()
        self.langchain_service = LangChainService()

    def list_webhooks(self):
        """ดึงข้อมูล webhooks ทั้งหมดจาก database"""
        try:
            conn = connect_db()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT id, agency_name, webhook_url, sub_agent, is_active FROM webhooks")
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            return rows
        except mysql.connector.Error as err:
            logging.error(f"Database error: {err}")
            return []

    def create_webhook(self, agency_name: str, sub_agent: str):
        """สร้าง webhook ใหม่"""
        try:
            conn = connect_db()
            cursor = conn.cursor()
            
            # สร้าง webhook URL แบบ unique
            webhook_url = f"/webhook/{agency_name.lower().replace(' ', '_')}"
            
            cursor.execute(
                "INSERT INTO webhooks (agency_name, webhook_url, sub_agent, is_active) VALUES (%s, %s, %s, %s)",
                (agency_name, webhook_url, sub_agent, True)
            )
            
            conn.commit()
            webhook_id = cursor.lastrowid
            
            cursor.close()
            conn.close()
            
            return {
                "id": webhook_id,
                "agency_name": agency_name,
                "webhook_url": webhook_url,
                "sub_agent": sub_agent,
                "is_active": True
            }
            
        except mysql.connector.Error as err:
            logging.error(f"Error creating webhook: {err}")
            raise Exception("ไม่สามารถสร้าง webhook ได้")

    def toggle_webhook(self, webhook_id: int, is_active: bool):
        """เปิด/ปิดการทำงานของ webhook"""
        try:
            conn = connect_db()
            cursor = conn.cursor()
            
            cursor.execute(
                "UPDATE webhooks SET is_active = %s WHERE id = %s",
                (is_active, webhook_id)
            )
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return True
            
        except mysql.connector.Error as err:
            logging.error(f"Error toggling webhook: {err}")
            return False

    def log_webhook_call(self, webhook_id: int, request_data: dict, response_data: dict):
        """บันทึก log การเรียกใช้ webhook"""
        try:
            conn = connect_db()
            cursor = conn.cursor()
            
            cursor.execute(
                "INSERT INTO webhook_logs (webhook_id, request_data, response_data, created_at) VALUES (%s, %s, %s, %s)",
                (webhook_id, json.dumps(request_data), json.dumps(response_data), datetime.now())
            )
            
            conn.commit()
            cursor.close()
            conn.close()
            
        except mysql.connector.Error as err:
            logging.error(f"Error logging webhook call: {err}")

    def get_webhook_logs(self, webhook_id: int, limit: int = 100):
        """ดึงประวัติการเรียกใช้ webhook"""
        try:
            conn = connect_db()
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute(
                "SELECT * FROM webhook_logs WHERE webhook_id = %s ORDER BY created_at DESC LIMIT %s",
                (webhook_id, limit)
            )
            
            logs = cursor.fetchall()
            cursor.close()
            conn.close()
            
            return logs
            
        except mysql.connector.Error as err:
            logging.error(f"Error getting webhook logs: {err}")
            return []

    def handle_webhook(self, agency_name: str, data: dict):
        """จัดการข้อมูลที่ได้รับจาก webhook"""
        try:
            logging.info(f"Processing webhook for agency: {agency_name}")
            
            # ตรวจสอบว่า webhook นี้เปิดใช้งานอยู่หรือไม่
            conn = connect_db()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM webhooks WHERE agency_name = %s AND is_active = TRUE", (agency_name,))
            webhook = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if not webhook:
                return {"error": "Webhook is not active or not found"}
            
            # ดึงข้อมูล agents ทั้งหมด
            agents = self.agent_service.list_agents()
            
            # วิเคราะห์ข้อความด้วย LangChain
            message = data.get("message", "")
            target_agent = self.langchain_service.analyze_message(message, agents)
            
            # ส่งข้อความไปยัง sub-agent ที่เหมาะสม
            response = self.agent_service.process_message(target_agent, message)
            
            # บันทึก log
            self.log_webhook_call(webhook["id"], data, response)
            
            return response
            
        except Exception as e:
            logging.error(f"Error processing webhook: {e}")
            return {"error": str(e)}

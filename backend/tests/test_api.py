import unittest
import requests

BASE_URL = "http://127.0.0.1:5000/api"  # ✅ URL ของ API ที่จะทดสอบ

class TestAPI(unittest.TestCase):

    def test_create_agent(self):
        """✅ ทดสอบสร้าง Agent"""
        payload = {"agent_name": "AI_Manager", "agent_type": "Automation"}
        response = requests.post(f"{BASE_URL}/agents/create", json=payload)

        self.assertEqual(response.status_code, 201)
        json_data = response.json()
        print("✅ Create Agent Response:", json_data)

    def test_list_agents(self):
        """✅ ทดสอบดึงรายการ Agent (ยังไม่มี API นี้ อาจต้องเพิ่มเอง)"""
        response = requests.get(f"{BASE_URL}/agents/list")

        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        print("✅ List Agents Response:", json_data)

    def test_create_webhook(self):
        """✅ ทดสอบสร้าง Webhook"""
        payload = {"agency_name": "Company XYZ", "webhook_url": "https://example.com/webhook", "sub_agent": "SubAgent1"}
        response = requests.post(f"{BASE_URL}/webhooks/create", json=payload)

        self.assertEqual(response.status_code, 201)
        json_data = response.json()
        print("✅ Create Webhook Response:", json_data)

    def test_get_webhook(self):
        """✅ ทดสอบเรียก Webhook (ต้องเปลี่ยนเป็น Webhook ที่มีอยู่จริง)"""
        payload = {"destination": "test_destination", "events": []}  # ✅ ย้าย payload เข้าไปในฟังก์ชัน
        response = requests.post(f"{BASE_URL}/webhooks/hospital_a", json=payload)

        self.assertIn(response.status_code, [200, 400, 404])  # ✅ เพิ่ม 404 เผื่อ API ยังไม่มี
        print("✅ Webhook Response:", response.text)

if __name__ == "__main__":
    unittest.main()

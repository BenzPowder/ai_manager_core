# AI Manager Core

ระบบจัดการ AI Agent และ Webhook สำหรับการทำงานร่วมกับ AI

## คุณสมบัติหลัก
- จัดการ AI Agents และ Sub-agents
- ระบบ Webhook สำหรับการเชื่อมต่อภายนอก
- หน้า Dashboard สำหรับการจัดการระบบ
- รองรับการทำงานร่วมกับ OpenAI API
- ระบบทดสอบ Webhook ผ่าน NGROK

## การติดตั้ง

1. Clone repository:
```bash
git clone [repository-url]
cd ai_manager_core
```

2. สร้าง Virtual Environment:
```bash
python -m venv venv
source venv/bin/activate  # สำหรับ Linux/Mac
venv\Scripts\activate     # สำหรับ Windows
```

3. ติดตั้ง Dependencies:
```bash
pip install -r requirements.txt
```

4. ตั้งค่า Environment Variables:
สร้างไฟล์ `.env` ใน folder backend:
```
OPENAI_API_KEY=your_openai_api_key
NGROK_AUTH_TOKEN=your_ngrok_token
```

5. รันระบบ:
```bash
cd backend
python main.py
```

## โครงสร้างโปรเจค
```
ai_manager_core/
├── backend/
│   ├── app/
│   │   ├── agents/      # จัดการ AI Agents
│   │   ├── api/         # API Endpoints
│   │   ├── database/    # การจัดการฐานข้อมูล
│   │   ├── routes/      # Flask Routes
│   │   ├── services/    # Business Logic
│   │   ├── templates/   # UI Templates
│   │   └── webhook/     # Webhook Management
│   └── main.py          # Entry point
├── static/              # Static files
└── config.yaml          # Configuration file
```

## การใช้งาน
1. เข้าถึง Dashboard ที่ `http://localhost:5000`
2. สร้างและจัดการ Agent ผ่านหน้า Dashboard
3. ตั้งค่า Webhook สำหรับการเชื่อมต่อภายนอก
4. ทดสอบการทำงานของ Agent ผ่านหน้าทดสอบ

## หมายเหตุ
- ต้องมี API Key ของ OpenAI
- ต้องมี NGROK Auth Token สำหรับการทดสอบ Webhook
- รองรับ Python 3.8+
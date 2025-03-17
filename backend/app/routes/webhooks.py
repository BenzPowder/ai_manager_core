from flask import Blueprint, request, jsonify, render_template
import uuid
import logging
import json
import os
import requests
from datetime import datetime
from linebot import LineBotApi
from linebot.models import TextSendMessage
from ..database.db_connection import get_db_connection
from ..agents.agent_service import process_with_openai, save_conversation_log
from app.agents.sub_agent_manager import ai_manager, SubAgent
from app.services.webhook_service import WebhookService
import openai

webhooks_bp = Blueprint('webhooks', __name__)

webhook_service = WebhookService()

# สร้างตาราง webhooks ถ้ายังไม่มี
def create_webhooks_table():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # สร้างตาราง webhooks ใหม่รองรับหลาย agents
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS webhooks (
                id INT AUTO_INCREMENT PRIMARY KEY,
                agency_name VARCHAR(255) NOT NULL,
                webhook_url VARCHAR(255) NOT NULL,
                line_access_token TEXT NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # สร้างตาราง webhook_agents สำหรับเก็บความสัมพันธ์ระหว่าง webhook และ agent
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS webhook_agents (
                id INT AUTO_INCREMENT PRIMARY KEY,
                webhook_id INT NOT NULL,
                agent_id INT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
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
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (webhook_id) REFERENCES webhooks(id) ON DELETE CASCADE
            )
        """)

        conn.commit()
        cursor.close()
        conn.close()

    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดในการสร้างตาราง: {str(e)}")

# เรียกฟังก์ชันสร้างตารางเมื่อโหลดไฟล์
create_webhooks_table()

@webhooks_bp.route('/create_webhook', methods=['GET', 'POST'])
def create_webhook_page():
    return render_template('create_webhook.html')

@webhooks_bp.route('/api/webhooks/create', methods=['POST'])
def create_webhook_api():
    """✅ API สำหรับสร้างหรืออัปเดต Webhook พร้อมรองรับ NGROK และหลาย Agent"""
    try:
        data = request.get_json()
        logging.info(f"📌 ข้อมูลที่ได้รับ: {data}")

        # ตรวจสอบข้อมูลที่จำเป็น
        required_fields = ['agency_name', 'sub_agents', 'line_access_token']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'❌ กรุณากรอก {field}'}), 400

        agency_name = data['agency_name'].strip()
        sub_agents = data['sub_agents']
        line_access_token = data['line_access_token'].strip()

        # ตรวจสอบว่า sub_agents เป็น list และต้องมีค่าขั้นต่ำ 1 ตัว
        if not isinstance(sub_agents, list) or len(sub_agents) == 0:
            return jsonify({'error': '❌ กรุณาเลือก agent อย่างน้อย 1 ตัว'}), 400

        # ตรวจสอบ NGROK URL
        ngrok_url = os.getenv("NGROK_URL", "http://127.0.0.1:5000")  # ใช้ localhost หากไม่มีค่า

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # ✅ ตรวจสอบว่า Webhook สำหรับหน่วยงานนี้มีอยู่หรือไม่
        cursor.execute("SELECT id, webhook_url FROM webhooks WHERE agency_name = %s", (agency_name,))
        existing_webhook = cursor.fetchone()

        webhook_uuid = str(uuid.uuid4())
        webhook_url = f"{ngrok_url}/webhook/{webhook_uuid}"
        sub_agents_json = json.dumps(sub_agents)  # ✅ ใช้ JSON ใน `webhooks`

        if existing_webhook:
            # ✅ **อัปเดต Webhook หากมีอยู่แล้ว**
            cursor.execute("""
                UPDATE webhooks
                SET sub_agents = %s, line_access_token = %s, updated_at = NOW()
                WHERE agency_name = %s
            """, (sub_agents_json, line_access_token, agency_name))
            webhook_id = existing_webhook['id']  # ใช้ ID เดิม
            webhook_url = existing_webhook['webhook_url']  # ใช้ URL เดิม
            action = "อัปเดต Webhook สำเร็จ"
        else:
            # ✅ **สร้าง Webhook ใหม่**
            cursor.execute("""
                INSERT INTO webhooks (agency_name, webhook_url, sub_agents, line_access_token, created_at)
                VALUES (%s, %s, %s, %s, NOW())
            """, (agency_name, webhook_url, sub_agents_json, line_access_token))
            webhook_id = cursor.lastrowid  # ดึง ID ที่เพิ่งสร้าง
            action = "สร้าง Webhook สำเร็จ"

        # ✅ 1. ตรวจสอบว่า agent_id ที่ได้มามีอยู่จริงใน `agents`
        valid_agent_ids = []
        for agent_id in sub_agents:
            cursor.execute("SELECT id FROM agents WHERE id = %s", (agent_id,))
            agent = cursor.fetchone()
            if agent:
                valid_agent_ids.append(agent['id'])

        print(f"✅ Debug: agent_id ที่มีอยู่จริง = {valid_agent_ids}")  # เช็คค่า agent_id ที่จะบันทึก

        # ✅ 2. ลบข้อมูลเก่า แล้ว INSERT เฉพาะ agent_id ที่มีอยู่จริง
        cursor.execute("DELETE FROM webhook_agents WHERE webhook_id = %s", (webhook_id,))
        for agent_id in valid_agent_ids:
            cursor.execute("INSERT INTO webhook_agents (webhook_id, agent_id) VALUES (%s, %s)", (webhook_id, agent_id))

        conn.commit()
        cursor.close()
        conn.close()

        logging.info(f"✅ {action}: {webhook_url}")
        return jsonify({
            'message': action,
            'webhook_url': webhook_url,
            'sub_agents': valid_agent_ids  # ✅ ส่งค่า agent_id ที่ถูกต้องกลับไป
        }), 201

    except Exception as e:
        logging.error(f"❌ เกิดข้อผิดพลาด: {str(e)}")
        return jsonify({'error': f'❌ เกิดข้อผิดพลาด: {str(e)}'}), 500

@webhooks_bp.route('/api/webhooks/toggle/<int:webhook_id>', methods=['POST'])
def toggle_webhook_status(webhook_id):
    """✅ API สำหรับเปิด/ปิดสถานะ Webhook"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # ตรวจสอบว่า Webhook มีอยู่จริงหรือไม่
        cursor.execute("SELECT id, is_active FROM webhooks WHERE id = %s", (webhook_id,))
        webhook = cursor.fetchone()

        if not webhook:
            cursor.close()
            conn.close()
            return jsonify({'error': '❌ ไม่พบ Webhook'}), 404

        print(f"🔍 ก่อนอัปเดต: Webhook ID {webhook_id} | is_active = {webhook['is_active']}")  # ✅ Debug

        # สลับสถานะ
        new_status = not webhook['is_active']
        cursor.execute("UPDATE webhooks SET is_active = %s WHERE id = %s", (new_status, webhook_id))

        conn.commit()

        # ตรวจสอบค่าใหม่หลังอัปเดต
        cursor.execute("SELECT is_active FROM webhooks WHERE id = %s", (webhook_id,))
        updated_webhook = cursor.fetchone()
        print(f"✅ หลังอัปเดต: Webhook ID {webhook_id} | is_active = {updated_webhook['is_active']}")  # ✅ Debug

        cursor.close()
        conn.close()

        return jsonify({
            'message': f'✅ {"เปิด" if new_status else "ปิด"} การใช้งาน Webhook สำเร็จ',
            'is_active': new_status
        }), 200

    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาด: {str(e)}")
        return jsonify({'error': f'❌ เกิดข้อผิดพลาด: {str(e)}'}), 500

@webhooks_bp.route('/api/webhooks/logs/<int:webhook_id>', methods=['GET'])
def get_webhook_logs(webhook_id):
    """ดู Log การเรียกใช้ Webhook"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT * FROM webhook_logs 
            WHERE webhook_id = %s 
            ORDER BY created_at DESC 
            LIMIT 100
        """, (webhook_id,))
        
        logs = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify(logs), 200

    except Exception as e:
        print(f"เกิดข้อผิดพลาด: {str(e)}")
        return jsonify({'error': f'เกิดข้อผิดพลาด: {str(e)}'}), 500

@webhooks_bp.route('/api/webhooks', methods=['GET'])
def get_webhooks():
    """ดึงรายการ Webhooks ทั้งหมด"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # ดึงข้อมูล webhook พร้อมชื่อ agent
        cursor.execute("""
            SELECT w.*, GROUP_CONCAT(a.agent_name) as agent_names
            FROM webhooks w
            LEFT JOIN webhook_agents wa ON w.id = wa.webhook_id
            LEFT JOIN agents a ON wa.agent_id = a.id
            GROUP BY w.id
        """)
        webhooks = cursor.fetchall()
        
        # แปลงข้อมูลให้อยู่ในรูปแบบที่ต้องการ
        for webhook in webhooks:
            if webhook['created_at']:
                webhook['created_at'] = webhook['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            
            # ถ้าไม่มี agent ให้แสดงว่า "ไม่ได้เลือก Agent"
            if webhook['agent_names'] is None:
                webhook['agent_name'] = "ไม่ได้เลือก Agent"
            else:
                webhook['agent_name'] = webhook['agent_names']
            
            del webhook['agent_names']  # ลบฟิลด์ที่ไม่ต้องการ
        
        cursor.close()
        conn.close()
        
        return jsonify(webhooks), 200
        
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาด: {str(e)}")
        return jsonify({'error': f'❌ เกิดข้อผิดพลาด: {str(e)}'}), 500

@webhooks_bp.route('/api/agents', methods=['GET'])
def get_agents_list():
    """ดึงรายการ AI Agents ทั้งหมด"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id, agent_name FROM agents ORDER BY agent_name")
        agents = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify(agents), 200

    except Exception as e:
        print(f"เกิดข้อผิดพลาด: {str(e)}")
        return jsonify({'error': f'เกิดข้อผิดพลาด: {str(e)}'}), 500

@webhooks_bp.route('/webhook/<webhook_id>', methods=['POST'])
def handle_webhook(webhook_id):
    """✅ ปฏิเสธ Webhook ที่ปิดอยู่ และให้ LINE OA ได้รับ 404 หรือ 400"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 🔍 ตรวจสอบว่ามี Webhook หรือไม่
        cursor.execute("SELECT * FROM webhooks WHERE webhook_url LIKE %s", (f"%{webhook_id}%",))
        webhook = cursor.fetchone()

        if not webhook:
            logging.error("❌ ไม่พบ Webhook")
            return jsonify({"error": "❌ ไม่พบ Webhook"}), 404  # ❌ ส่ง 404 กลับไป

        # ✅ ตรวจสอบว่า Webhook ถูกปิดใช้งานหรือไม่
        if not webhook['is_active']:
            logging.error("❌ Webhook ถูกปิดใช้งาน")
            return jsonify({"error": "❌ Webhook ถูกปิดใช้งาน"}), 400  # ❌ LINE OA ต้องการ 400 Bad Request

        # 📌 ดึงข้อมูลที่ได้รับจาก LINE
        request_data = request.get_json()
        if not request_data or 'events' not in request_data or not request_data['events']:
            return '', 200  # ถ้าไม่มี event ก็จบเลย

        event = request_data['events'][0]
        if event['type'] != 'message' or event.get('message', {}).get('type') != 'text':
            return '', 200  # ถ้าไม่ใช่ข้อความก็ไม่ต้องทำอะไร

        # 🔍 ดึงรายการ AI Agent ที่ผูกกับ Webhook
        sub_agents = json.loads(webhook.get('sub_agents', '[]'))
        if not sub_agents:
            logging.error("❌ ไม่มี Agent ที่ผูกไว้กับ Webhook นี้")
            return '', 200

        # 📌 ข้อความที่รับจาก LINE OA
        user_text = event['message']['text']

        responses = []
        for agent_name in sub_agents:
            cursor.execute("SELECT * FROM agents WHERE agent_name = %s", (agent_name,))
            agent = cursor.fetchone()
            if agent:
                try:
                    messages = [
                        {"role": "system", "content": agent['prompt_template']},
                        {"role": "user", "content": user_text}
                    ]
                    agent_response = process_with_openai(messages)

                    # ✅ Debug ตรวจสอบค่า response
                    print(f"✅ Debug: agent_response = {agent_response}")

                    # ✅ ตรวจสอบ response เป็น dictionary หรือไม่
                    if not isinstance(agent_response, dict):
                        raise ValueError(f"❌ OpenAI API ตอบกลับผิดพลาด: {type(agent_response)} = {agent_response}")

                    ai_message = agent_response.get("message", "ขออภัย ระบบไม่สามารถให้คำตอบได้")
                    responses.append(f"{agent_name}: {ai_message}")
                except Exception as e:
                    logging.error(f"❌ OpenAI Error: {str(e)}")

        if not responses:
            return '', 200

        # ✅ ส่งข้อความกลับไปยัง LINE OA
        reply_token = event['replyToken']
        line_reply_url = "https://api.line.me/v2/bot/message/reply"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {webhook['line_access_token']}"
        }
        body = {
            "replyToken": reply_token,
            "messages": [{"type": "text", "text": "\n".join(responses)}]
        }
        requests.post(line_reply_url, headers=headers, json=body)

        return '', 200

    except Exception as e:
        logging.error(f"❌ Webhook Error: {str(e)}")
        return jsonify({'error': f'❌ เกิดข้อผิดพลาด: {str(e)}'}), 500  # ❌ ถ้ามีข้อผิดพลาด ให้คืน 500 Internal Server Error

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@webhooks_bp.route('/api/webhooks/update/<int:webhook_id>', methods=['POST'])
def update_webhook_api(webhook_id):
    """✅ API สำหรับอัปเดต Webhook"""
    try:
        data = request.get_json()
        
        # ตรวจสอบข้อมูลที่จำเป็น
        required_fields = ['agency_name', 'sub_agents', 'line_access_token']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'❌ กรุณากรอก {field}'}), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # ตรวจสอบว่า webhook มีอยู่จริง
        cursor.execute("SELECT id FROM webhooks WHERE id = %s", (webhook_id,))
        webhook = cursor.fetchone()
        if not webhook:
            cursor.close()
            conn.close()
            return jsonify({'error': '❌ ไม่พบ webhook ที่ต้องการแก้ไข'}), 404

        # อัปเดตข้อมูล webhook
        cursor.execute("""
            UPDATE webhooks 
            SET agency_name = %s,
                line_access_token = %s
            WHERE id = %s
        """, (data['agency_name'], data['line_access_token'], webhook_id))

        # ลบข้อมูล webhook_agents เก่า
        cursor.execute("DELETE FROM webhook_agents WHERE webhook_id = %s", (webhook_id,))

        # เพิ่มข้อมูล webhook_agents ใหม่
        for agent_id in data['sub_agents']:
            cursor.execute("""
                INSERT INTO webhook_agents (webhook_id, agent_id)
                VALUES (%s, %s)
            """, (webhook_id, agent_id))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'message': '✅ อัปเดต webhook สำเร็จ'}), 200

    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาด: {str(e)}")
        return jsonify({'error': f'❌ เกิดข้อผิดพลาด: {str(e)}'}), 500

@webhooks_bp.route('/dashboard')
def dashboard():
    """หน้า Dashboard"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # ดึงข้อมูล webhooks พร้อมชื่อ agents ที่เกี่ยวข้อง
        cursor.execute("""
            SELECT w.*, GROUP_CONCAT(a.agent_name) as agent_names
            FROM webhooks w
            LEFT JOIN webhook_agents wa ON w.id = wa.webhook_id
            LEFT JOIN agents a ON wa.agent_id = a.id
            GROUP BY w.id
        """)
        webhooks = cursor.fetchall()

        # ดึงข้อมูล agents
        cursor.execute("SELECT * FROM agents")
        agents = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template('dashboard.html', webhooks=webhooks, agents=agents)

    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาด: {str(e)}")
        return jsonify({'error': f'❌ เกิดข้อผิดพลาด: {str(e)}'}), 500

@webhooks_bp.route('/webhook/<webhook_name>', methods=['POST'])
def webhook_handler(webhook_name):
    data = request.json
    user_input = data.get("message", "")
    
    # ตรวจสอบว่า webhook นี้ตรงกับ agent หรือไม่
    assigned_agent = webhook_service.get_assigned_agent(webhook_name)
    
    if assigned_agent:
        response = ai_manager.process_request(assigned_agent, user_input)
    else:
        response = "ขออภัย Webhook นี้ไม่ได้เชื่อมกับ Agent ที่สามารถตอบคำถามนี้ได้"
    
    return jsonify({"response": response})

@webhooks_bp.route('/webhook/<uuid>', methods=['POST'])
def webhook(uuid):
    """รับข้อความจาก LINE OA และส่งไปให้ AI Agent ตอบ"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 🔍 ดึงข้อมูล webhook และ agent
        cursor.execute("""
            SELECT w.*, GROUP_CONCAT(a.id) as agent_ids, GROUP_CONCAT(a.name) as agent_names,
            GROUP_CONCAT(a.prompt_template) as prompt_templates, w.line_access_token
            FROM webhooks w
            LEFT JOIN webhook_agents wa ON w.id = wa.webhook_id
            LEFT JOIN agents a ON wa.agent_id = a.id
            WHERE w.webhook_url LIKE %s
            GROUP BY w.id
        """, (f'%{uuid}%',))

        webhook_data = cursor.fetchone()

        if not webhook_data:
            print("❌ ไม่พบ webhook")
            return 'Webhook not found', 404

        if not webhook_data['is_active']:
            print("❌ Webhook ถูกปิดใช้งาน")
            return 'Webhook is inactive', 400

        # รับข้อมูลจาก LINE
        data = request.get_json()
        print(f"📝 ข้อมูลที่ได้รับจาก LINE: {json.dumps(data, ensure_ascii=False, indent=2)}")

        events = data.get('events', [])
        if not events:
            print("❌ ไม่พบ events")
            return 'No events', 200

        for event in events:
            if event['type'] != 'message' or event['message']['type'] != 'text':
                continue

            user_message = event['message']['text']
            reply_token = event['replyToken']

            print(f"👤 ข้อความจากผู้ใช้: {user_message}")
            print(f"🔑 Reply Token: {reply_token}")

            # 🔹 สร้าง messages array สำหรับ OpenAI
            messages = [
                {"role": "system", "content": webhook_data['prompt_templates'].split(',')[0]},
                {"role": "user", "content": user_message}
            ]

            try:
                # ✅ เรียกใช้ OpenAI API
                if not isinstance(messages, list):
                    raise ValueError(f"❌ messages ต้องเป็น list แต่ได้ค่า: {type(messages)}")

                start_time = datetime.now()
                openai_response = process_with_openai(messages)
                response_time = (datetime.now() - start_time).total_seconds()

                if not isinstance(openai_response, dict):
                    raise ValueError(f"❌ OpenAI API ตอบกลับรูปแบบผิดพลาด: {openai_response}")

                ai_message = openai_response['message'].strip()
                print(f"🤖 ข้อความตอบกลับจาก AI: {ai_message}")

                # ✅ บันทึก log การสนทนา
                save_conversation_log(
                    agent_name=webhook_data['agent_names'].split(',')[0],
                    message=user_message,
                    response=ai_message,
                    response_time=response_time,
                    status='success',
                    usage_data=openai_response.get('usage', {}),
                    model=openai_response.get('model', 'unknown')
                )

                # ✅ ส่งข้อความตอบกลับไปยัง LINE OA
                line_bot_api = LineBotApi(webhook_data['line_access_token'])
                line_bot_api.reply_message(
                    reply_token,
                    TextSendMessage(text=ai_message)
                )

                print(f"✅ ส่งข้อความตอบกลับไปยัง LINE สำเร็จ")

                # ✅ บันทึก webhook log
                cursor.execute("""
                    INSERT INTO webhook_logs (webhook_id, request_data, response_data)
                    VALUES (%s, %s, %s)
                """, (
                    webhook_data['id'],
                    json.dumps({"message": user_message}, ensure_ascii=False),
                    json.dumps({"response": ai_message}, ensure_ascii=False)
                ))
                conn.commit()

            except Exception as e:
                print(f"❌ เกิดข้อผิดพลาดในการประมวลผลข้อความ: {str(e)}")

                # ✅ ส่งข้อความแจ้ง error กลับไปยัง LINE
                try:
                    line_bot_api.reply_message(
                        reply_token,
                        TextSendMessage(text="ขออภัย ระบบไม่สามารถประมวลผลข้อความได้ในขณะนี้ กรุณาลองใหม่อีกครั้งในภายหลัง")
                    )
                except Exception as line_error:
                    print(f"❌ ไม่สามารถส่งข้อความ error กลับไปยัง LINE: {str(line_error)}")

        cursor.close()
        conn.close()
        return 'OK', 200

    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดใน webhook: {str(e)}")
        return 'Error', 500

@webhooks_bp.route('/api/webhooks/delete/<int:webhook_id>', methods=['DELETE'])
def delete_webhook(webhook_id):
    """✅ API สำหรับลบ Webhook"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # ตรวจสอบว่า Webhook มีอยู่จริงหรือไม่
        cursor.execute("SELECT id FROM webhooks WHERE id = %s", (webhook_id,))
        webhook = cursor.fetchone()

        if not webhook:
            cursor.close()
            conn.close()
            return jsonify({'error': '❌ ไม่พบ Webhook'}), 404

        # ลบ webhook_agents ก่อน (จะถูกลบอัตโนมัติด้วย ON DELETE CASCADE)
        cursor.execute("DELETE FROM webhooks WHERE id = %s", (webhook_id,))
        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({'message': '✅ ลบ Webhook สำเร็จ'}), 200

    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาด: {str(e)}")
        return jsonify({'error': f'❌ เกิดข้อผิดพลาด: {str(e)}'}), 500

@webhooks_bp.route('/edit_webhook/<int:webhook_id>', methods=['GET'])
def edit_webhook_page(webhook_id):
    """หน้าแก้ไข Webhook"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # ดึงข้อมูล webhook
        cursor.execute("""
            SELECT w.*, GROUP_CONCAT(wa.agent_id) as agent_ids
            FROM webhooks w
            LEFT JOIN webhook_agents wa ON w.id = wa.webhook_id
            WHERE w.id = %s
            GROUP BY w.id
        """, (webhook_id,))
        webhook = cursor.fetchone()

        if not webhook:
            cursor.close()
            conn.close()
            return "ไม่พบ webhook", 404

        # แปลง agent_ids เป็น list
        if webhook['agent_ids']:
            webhook['agent_ids'] = [int(id) for id in webhook['agent_ids'].split(',')]
        else:
            webhook['agent_ids'] = []

        # ดึงรายการ agents ทั้งหมด
        cursor.execute("SELECT * FROM agents")
        agents = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template('edit_webhook.html', webhook=webhook, agents=agents)

    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาด: {str(e)}")
        return str(e), 500
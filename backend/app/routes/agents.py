from flask import Blueprint, request, jsonify, render_template
from app.services.sub_agent_service import SubAgentService
from app.agents.sub_agent_manager import ai_manager
import logging
from app.database.db_connection import get_db_connection

agents_bp = Blueprint('agents', __name__)
agent_service = SubAgentService()

# API สำหรับทดสอบ AI Response
@agents_bp.route('/api/agents/test', methods=['POST'])
def test_ai():
    """ทดสอบการตอบกลับของ AI Agent"""
    try:
        data = request.json
        if not data or 'prompt' not in data:
            return jsonify({'error': '❌ กรุณาระบุข้อความที่ต้องการทดสอบ'}), 400

        user_input = data['prompt']
        
        # ดึง agent แรกจากฐานข้อมูล
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT agent_name FROM agents LIMIT 1")
        agent = cursor.fetchone()
        cursor.close()
        conn.close()

        if not agent:
            return jsonify({'error': '❌ ไม่พบ AI Agent ในระบบ กรุณาสร้าง Agent ก่อนทดสอบ'}), 404

        # เรียกใช้ agent_service
        result = agent_service.process_message(agent['agent_name'], user_input)
        
        # Debug: ตรวจสอบค่า result
        print(f"✅ Debug test_ai() result: {result}")
        
        # ตรวจสอบว่า result เป็น dict หรือไม่
        if isinstance(result, str):
            return jsonify({'response': result}), 200
            
        if isinstance(result, dict):
            if 'error' in result:
                return jsonify({'error': result['error']}), 500
            if 'response' in result:
                return jsonify({'response': result['response']}), 200
                
        # กรณีที่ไม่ตรงกับรูปแบบใดๆ
        return jsonify({'error': '❌ รูปแบบข้อมูลไม่ถูกต้อง'}), 500

    except Exception as e:
        error_message = f"❌ เกิดข้อผิดพลาด: {str(e)}"
        print(error_message)
        return jsonify({'error': error_message}), 500

# Route สำหรับหน้า UI ทดสอบ AI
@agents_bp.route('/test')
def test_ai_page():
    """แสดงหน้าทดสอบ AI Agent"""
    return render_template('test_ai.html')

# Route สำหรับหน้าสร้าง Agent
@agents_bp.route('/create_agent')
def create_agent_page():
    return render_template('create_agent.html')

# Route สำหรับหน้าแก้ไข Agent
@agents_bp.route('/agents/edit/<int:agent_id>')
def edit_agent_page(agent_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM agents WHERE id = %s", (agent_id,))
    agent = cursor.fetchone()

    cursor.close()
    conn.close()

    if not agent:
        return "Agent not found", 404

    return render_template('edit_agent.html', agent=agent)

@agents_bp.route('/api/agents/create', methods=['POST'])
def create_agent():
    """สร้าง AI Agent ใหม่"""
    try:
        data = request.get_json()
        print("🔹 Received Data:", data)  # ✅ Debug ค่าที่ได้รับจาก Frontend
        
        if not data:
            return jsonify({'error': '❌ ไม่ได้รับข้อมูลจาก Client'}), 400

        # ตรวจสอบข้อมูลที่จำเป็น
        required_fields = ['agent_name', 'agent_type', 'prompt_template']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'❌ กรุณากรอก {field}'}), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # ตรวจสอบว่ามี agent ชื่อนี้อยู่แล้วหรือไม่
        cursor.execute("SELECT id FROM agents WHERE agent_name = %s", (data['agent_name'],))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'error': '❌ มี Agent ชื่อนี้อยู่แล้ว'}), 400

        # เพิ่มข้อมูล agent ใหม่
        cursor.execute("""
            INSERT INTO agents (agent_name, agent_type, prompt_template)
            VALUES (%s, %s, %s)
        """, (data['agent_name'], data['agent_type'], data['prompt_template']))
        
        conn.commit()
        cursor.close()
        conn.close()

        print("✅ Agent Created Successfully:", data['agent_name'])
        return jsonify({'message': '✅ สร้าง Agent สำเร็จ'}), 201

    except Exception as e:
        print("❌ Error:", str(e))
        return jsonify({'error': f'❌ เกิดข้อผิดพลาดในการสร้าง Agent: {str(e)}'}), 500


@agents_bp.route('/api/agents', methods=['GET'])
def get_agents():
    """ดึงรายการ AI Agents ทั้งหมด"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT * FROM agents")
        agents = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        # แปลงวันที่เป็น string
        for agent in agents:
            if 'created_at' in agent:
                agent['created_at'] = agent['created_at'].strftime('%Y-%m-%d %H:%M:%S')
        
        return jsonify(agents), 200
    except Exception as e:
        logging.error(f"เกิดข้อผิดพลาดในการดึงรายการ Agents: {e}")
        return jsonify({'error': 'เกิดข้อผิดพลาดในการดึงรายการ Agents'}), 500

@agents_bp.route('/api/agents/<agent_name>', methods=['GET'])
def get_agent(agent_name):
    """ดึงข้อมูล AI Agent ตามชื่อ"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT * FROM agents WHERE agent_name = %s", (agent_name,))
        agent = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if agent:
            # แปลงวันที่เป็น string
            if 'created_at' in agent:
                agent['created_at'] = agent['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            return jsonify(agent), 200
        else:
            return jsonify({'error': 'ไม่พบ Agent'}), 404
    except Exception as e:
        logging.error(f"เกิดข้อผิดพลาดในการดึงข้อมูล Agent: {e}")
        return jsonify({'error': 'เกิดข้อผิดพลาดในการดึงข้อมูล Agent'}), 500

@agents_bp.route('/api/agents/update/<int:agent_id>', methods=['PUT'])
def update_agent(agent_id):
    try:
        data = request.get_json()

        if not data.get("agent_name") or not data.get("agent_type") or not data.get("prompt_template"):
            return jsonify({'error': 'ข้อมูลไม่ครบถ้วน'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE agents SET agent_name = %s, agent_type = %s, prompt_template = %s
            WHERE id = %s
        """, (data["agent_name"], data["agent_type"], data["prompt_template"], agent_id))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'message': 'แก้ไข Agent สำเร็จ'}), 200

    except Exception as e:
        return jsonify({'error': f'เกิดข้อผิดพลาด: {str(e)}'}), 500

@agents_bp.route('/agents/delete/<int:agent_id>', methods=['DELETE'])
def delete_agent(agent_id):
    """ลบ AI Agent ตาม ID"""
    try:
        print(f"🔹 กำลังลบ Agent ID: {agent_id}")  # Debug log
        
        conn = get_db_connection()
        cursor = conn.cursor()

        # ตรวจสอบว่ามี agent นี้อยู่หรือไม่
        cursor.execute("SELECT id FROM agents WHERE id = %s", (agent_id,))
        agent = cursor.fetchone()
        
        if not agent:
            cursor.close()
            conn.close()
            return jsonify({'error': '❌ ไม่พบ Agent ที่ต้องการลบ'}), 404

        # ลบข้อมูลที่เกี่ยวข้องใน webhook_agents ก่อน
        cursor.execute("DELETE FROM webhook_agents WHERE agent_id = %s", (agent_id,))
        
        # ลบ agent
        cursor.execute("DELETE FROM agents WHERE id = %s", (agent_id,))
        conn.commit()
        
        cursor.close()
        conn.close()
        
        print(f"✅ ลบ Agent ID: {agent_id} สำเร็จ")  # Debug log
        return jsonify({'message': '✅ ลบ Agent สำเร็จ'}), 200

    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดในการลบ Agent: {str(e)}")  # Debug log
        return jsonify({'error': f'❌ เกิดข้อผิดพลาด: {str(e)}'}), 500

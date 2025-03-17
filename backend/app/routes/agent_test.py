from flask import Blueprint, request, jsonify, render_template
from ..database.db_connection import get_db_connection
from ..agents.agent_service import AgentService
from ..agents.sub_agent_manager import SubAgent, save_conversation_log
import time
import json

agent_test_bp = Blueprint('agent_test', __name__)

@agent_test_bp.route('/test')
def test_page():
    """หน้า UI สำหรับทดสอบ AI"""
    return render_template('agent_test.html')

@agent_test_bp.route('/api/agents')
def get_agents():
    """ดึงรายการ agents ทั้งหมด"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT id, agent_name, agent_type FROM agents")
        agents = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify(agents)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@agent_test_bp.route('/api/agents/<int:agent_id>')
def get_agent(agent_id):
    """ดึงข้อมูล agent ตาม ID"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT id, agent_name, agent_type FROM agents WHERE id = %s", (agent_id,))
        agent = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if agent:
            return jsonify(agent)
        return jsonify({'error': 'ไม่พบ agent'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@agent_test_bp.route('/api/agents/test', methods=['POST'])
def test_agent():
    """ทดสอบ AI agent"""
    try:
        data = request.get_json()
        agent_id = data.get('agent_id')
        message = data.get('message')
        
        if not agent_id or not message:
            return jsonify({
                'status': 'error',
                'error': 'กรุณาระบุ agent_id และ message'
            }), 400
            
        # ดึงข้อมูล agent จากฐานข้อมูล
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT a.id, a.agent_name, a.agent_type, a.prompt_template 
            FROM agents a 
            WHERE a.id = %s
        """, (agent_id,))
        agent_data = cursor.fetchone()
        
        if not agent_data:
            cursor.close()
            conn.close()
            return jsonify({"error": "ไม่พบ Agent ที่ระบุ"}), 404

        # สร้าง SubAgent instance
        agent = SubAgent(
            name=agent_data['agent_name'],
            agent_type=agent_data['agent_type'],
            prompt_template=agent_data['prompt_template']
        )

        # เริ่มจับเวลา
        start_time = time.time()
        
        # ประมวลผลข้อความ
        try:
            response = agent.process_message(message)
            response_time = time.time() - start_time
            
            # ตรวจสอบว่า response เป็น string หรือ dict
            if isinstance(response, str):
                # กรณีเป็น string (error message หรือ AI message)
                if "❌" in response:  # เป็น error message
                    save_conversation_log(
                        agent_name=agent_data['agent_name'],
                        request_text=message,
                        response_text=None,
                        response_time=response_time,
                        status='error',
                        error=response
                    )
                    return jsonify({
                        'status': 'error',
                        'error': response
                    }), 500
                else:  # เป็น AI message
                    save_conversation_log(
                        agent_name=agent_data['agent_name'],
                        request_text=message,
                        response_text=response,
                        response_time=response_time,
                        status='success'
                    )
                    return jsonify({
                        'status': 'success',
                        'response': response
                    })

            # กรณีเป็น dict (legacy format)
            if isinstance(response, dict):
                save_conversation_log(
                    agent_name=agent_data['agent_name'],
                    request_text=message,
                    response_text=response.get('response', ''),
                    response_time=response_time,
                    status=response.get('status', 'error'),
                    error=response.get('error'),
                    usage_data=response.get('usage'),
                    model=response.get('model')
                )
                return jsonify(response)

            # กรณีไม่ตรงกับรูปแบบใดๆ
            error_message = "❌ รูปแบบข้อมูลไม่ถูกต้อง"
            save_conversation_log(
                agent_name=agent_data['agent_name'],
                request_text=message,
                response_text=None,
                response_time=response_time,
                status='error',
                error=error_message
            )
            return jsonify({
                'status': 'error',
                'error': error_message
            }), 500

        except Exception as e:
            error_message = f"❌ เกิดข้อผิดพลาด: {str(e)}"
            save_conversation_log(
                agent_name=agent_data['agent_name'],
                request_text=message,
                response_text=None,
                response_time=time.time() - start_time,
                status='error',
                error=error_message
            )
            return jsonify({
                'status': 'error',
                'error': error_message
            }), 500

    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@agent_test_bp.route('/api/agents/<agent_name>/performance')
def get_agent_performance(agent_name):
    """ดึงข้อมูล performance ของ agent"""
    try:
        performance = SubAgent.get_agent_performance(agent_name)
        return jsonify(performance)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

from flask import Blueprint, request, jsonify
from agents.agent_service import AgentService

agent_bp = Blueprint("agent", __name__)

agent_service = AgentService()

@agent_bp.route("/create", methods=["POST"])
def create_agent():
    """✅ API สำหรับสร้าง AI Sub-Agent"""
    data = request.get_json()
    print("🔹 Received Data in Controller:", data)  # Debug ข้อมูลที่มาถึง Controller

    if not data:
        return jsonify({"error": "❌ ไม่ได้รับข้อมูลจาก Client"}), 400

    name = data.get("agent_name")  # เปลี่ยนจาก "name" เป็น "agent_name"
    sub_agent = data.get("agent_type", "default_agent")  # แก้เป็น agent_type

    if not name:
        return jsonify({"error": "❌ Missing agent name"}), 400

    agent = agent_service.create_agent(name, sub_agent)
    return jsonify(agent), 201


@agent_bp.route("/list", methods=["GET"])
def list_agents():
    """✅ API สำหรับดึงรายการ AI Sub-Agent"""
    agents = agent_service.list_agents()
    return jsonify(agents), 200
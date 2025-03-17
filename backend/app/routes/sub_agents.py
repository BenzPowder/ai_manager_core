from flask import Blueprint, request, jsonify
from app.services.sub_agent_service import SubAgentService

agent_bp = Blueprint('agent_bp', __name__)
sub_agent_service = SubAgentService()

@agent_bp.route("/create", methods=["POST"])
def create_agent():
    data = request.json
    name = data.get("name")
    sub_agent = data.get("sub_agent", "default")
    result = sub_agent_service.create_agent(name, sub_agent)
    return jsonify(result), 201

@agent_bp.route("/list", methods=["GET"])
def list_agents():
    agents = sub_agent_service.list_agents()
    return jsonify(agents), 200

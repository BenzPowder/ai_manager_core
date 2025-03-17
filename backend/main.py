import os
import sys
import openai
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_cors import CORS
from app.services.webhook_service import WebhookService
from app.services.sub_agent_service import SubAgentService
from app.routes.webhooks import webhooks_bp
from app.routes.agent_test import agent_test_bp
from app.routes.agents import agents_bp
from app.database.db_connection import get_db_connection
from pyngrok import ngrok, conf
from dotenv import load_dotenv
import time

openai.api_key ="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"

def get_chat_response(message):
    response = openai.ChatCompletion.create(
        model="gpt-4",  
        messages=[
            {"role": "system", "content": "คุณเป็น AI Assistant ที่ช่วยตอบคำถามเกี่ยวกับระบบที่รองรับ"},
            {"role": "user", "content": message}
        ]
    )
    return response["choices"][0]["message"]["content"]

# ตั้งค่า NGROK Token
NGROK_AUTH_TOKEN = "2sKxERBFEv42OQ6SecdYQWsPXJJ_41AXM2uA78vS33KwLMZ17"  
conf.get_default().auth_token = NGROK_AUTH_TOKEN

app = Flask(__name__, template_folder='app/templates', static_folder='app/static')
CORS(app)

# Register API Blueprints
app.register_blueprint(webhooks_bp)
app.register_blueprint(agent_test_bp)
app.register_blueprint(agents_bp)

webhook_service = WebhookService()
agent_service = SubAgentService()

# Dashboard Route
@app.route('/')
def index():
    return redirect(url_for('webhooks.dashboard'))

@app.route("/sub_agents")
def sub_agents():
    return render_template("sub_agents.html")

# AI Chat API
@app.route('/api/ai', methods=['POST'])
def ai_response():
    data = request.json
    prompt = data.get("prompt", "")

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        return jsonify({"response": response["choices"][0]["message"]["content"]})
    except Exception as e:
        return jsonify({"error": str(e)})

def start_ngrok():
    try:
        if "NGROK_URL" not in os.environ:
            public_url = ngrok.connect(5000).public_url
            os.environ["NGROK_URL"] = public_url
            print(f" NGROK Tunnel เปิดที่: {public_url}")
    except Exception as e:
        print(f" เกิดข้อผิดพลาดในการเปิด NGROK: {str(e)}")

# เรียกใช้ฟังก์ชัน NGROK
start_ngrok()

if __name__ == '__main__':
    print(get_chat_response("Hello!"))
    app.run(debug=True)

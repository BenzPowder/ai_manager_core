import os
from flask import Blueprint, request, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from linebot.exceptions import InvalidSignatureError
from app.config.config_manager import ConfigManager
import openai
from agents.agent_service import AgentService

webhooks_bp = Blueprint("webhook", __name__)
config_manager = ConfigManager()
sub_agent_manager = AgentService()

# ฟังก์ชันสำหรับดึง LINE OA Config
def get_line_bot(agency_name):
    config = config_manager.get_oa_config(agency_name)
    if not config:
        return None, None
    channel_secret, access_token = config
    return LineBotApi(access_token), WebhookHandler(channel_secret)

# @webhooks_bp.route('/webhook/<agency_name>', methods=['POST'])
@webhooks_bp.route('/<agency_name>', methods=['POST'])
def webhook(agency_name):
    """Webhook สำหรับแต่ละหน่วยงาน"""
    print(f"🔍 Webhook called for agency: {agency_name}")

    config = config_manager.get_oa_config(agency_name)
    if not config:
        print(f"⚠️ Agency '{agency_name}' not found in database!")
        return jsonify({"error": "Agency not found"}), 404

    channel_secret, access_token = config
    print(f"✅ Channel Secret: {channel_secret}")

    line_bot_api = LineBotApi(access_token)
    handler = WebhookHandler(channel_secret)

    signature = request.headers.get("X-Line-Signature")
    if signature is None:
        print(f"❌ Missing X-Line-Signature in request headers!")
        # return jsonify({"error": "Missing X-Line-Signature"}), 400

    body = request.get_data(as_text=True)
    print(f"📌 Request Body: {body}")

    import json
    body_data = json.loads(body)
    events = body_data.get("events", [])

    if not events:
        print(f"⚠️ No events found in request body.")
        return "OK", 200

    try:
        print(f"✅ Processing event: {events[0]}")

        # ✅ เลือก AI Sub-Agent ที่เกี่ยวข้อง
        sub_agent = sub_agent_manager.get_sub_agent(agency_name)
        if not sub_agent:
            print(f"⚠️ No AI Sub-Agent assigned for {agency_name}.")
            return "OK", 200

        print(f"✅ Assigned AI Sub-Agent: {sub_agent}")

        handler.handle(body, signature)

        # ✅ ส่งข้อความไปให้ AI Sub-Agent ตอบ
        event = events[0]
        if event["type"] == "message" and event["message"]["type"] == "text":
            reply_token = event["replyToken"]
            user_message = event["message"]["text"]
            
            # AI Sub-Agent ตอบกลับ
            bot_reply = sub_agent.process_message(user_message)

            line_bot_api.reply_message(reply_token, TextSendMessage(text=bot_reply))

    except InvalidSignatureError:
        print(f"❌ Invalid Signature Error!")
        return jsonify({"error": "Invalid signature"}), 400
    except Exception as e:
        print(f"❌ Error occurred: {str(e)}")
        return jsonify({"error": str(e)}), 500

    return "OK", 200

# ✅ แก้ปัญหาการใช้งาน `handler` ที่ยังไม่ถูกกำหนด
@webhooks_bp.route('/webhook/message/<agency_name>', methods=['POST'])
def handle_message_api(agency_name):
    """API สำหรับทดสอบการส่งข้อความ"""
    data = request.json
    user_message = data.get("message", "")

    line_bot_api, handler = get_line_bot(agency_name)
    if not line_bot_api or not handler:
        return jsonify({"error": "Agency not found"}), 404

    # ส่งข้อความไปให้ AI (OpenAI API)
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": user_message}]
    )

    reply_text = response["choices"][0]["message"]["content"]
    return jsonify({"response": reply_text})
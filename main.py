import json
import requests
import os
from fastapi import FastAPI, Request
from dotenv import load_dotenv
load_dotenv()

app = FastAPI()

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
API_KEY = os.getenv("API_KEY")

# Webhook verification route
@app.get("/webhook")
async def verify(request: Request):
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return str(challenge)
    return {"status": "verification failed"}

# Webhook POST route to receive WhatsApp messages
@app.post("/webhook")
async def receive_message(request: Request):
    body = await request.json()
    print("Incoming message:", json.dumps(body, indent=2))

    try:
        change = body["entry"][0]["changes"][0]["value"]
        if "messages" not in change:
            print("No message to respond to. Probably a status update.")
            return {"status": "ignored - not a message"}
        messages = change["messages"]
        message = messages[0]
        sender_id = message["from"]
        user_text = message.get("text", {}).get("body", "")

        if not user_text:
            return {"status": "no text content"}

        # Step 1: Call your friend's public legal assistant API
        query_payload = {
            "query": user_text,
            "top_k": 3,
            "rerank": False,
            "include_scores": False,
            "filters": {}
        }

        api_response = requests.post(API_KEY, json=query_payload)
        results = api_response.json().get("results", [])

        # Step 2: Format the response to send back to user
        if results:
            reply = "Here's what I found:\n\n"
            for idx, result in enumerate(results, 1):
                content = result.get("content", "No content available.")
                reply += f"{idx}. {content.strip()}\n\n"
        else:
            reply = "Sorry, I couldn't find anything related to your question."

        # Step 3: Send the reply via WhatsApp API
        wa_url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        data = {
            "messaging_product": "whatsapp",
            "to": sender_id,
            "text": {"body": reply.strip()}
        }

        wa_response = requests.post(wa_url, headers=headers, json=data)
        print("Message sent. Status:", wa_response.status_code)

    except Exception as e:
        print("Error:", str(e))

    return {"status": "ok"}

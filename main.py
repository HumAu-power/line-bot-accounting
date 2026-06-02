"""
LINE Bot + Claude Vision + Google Sheets
รับรูปสลิป → อ่านข้อมูล → บันทึก Sheets
"""

import os
import json
import base64
import httpx
from fastapi import FastAPI, Request, HTTPException
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi,
    ReplyMessageRequest, TextMessage
)
from linebot.v3.webhooks import MessageEvent, ImageMessageContent
from linebot.v3.exceptions import InvalidSignatureError
import anthropic
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

app = FastAPI()

# ───── Config from env ─────
LINE_CHANNEL_SECRET = os.environ["LINE_CHANNEL_SECRET"]
LINE_CHANNEL_ACCESS_TOKEN = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
GOOGLE_SHEETS_ID = os.environ["GOOGLE_SHEETS_ID"]
GOOGLE_CREDENTIALS_JSON = os.environ["GOOGLE_CREDENTIALS_JSON"]  # JSON string

handler = WebhookHandler(LINE_CHANNEL_SECRET)
line_config = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


# ───── Google Sheets setup ─────
def get_sheet():
    creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(GOOGLE_SHEETS_ID)
    worksheet = sh.sheet1

    # สร้าง header ถ้ายังไม่มี
    if worksheet.row_count == 0 or worksheet.cell(1, 1).value != "วันที่/เวลา":
        worksheet.insert_row(["วันที่/เวลา", "จำนวนเงิน (บาท)", "Memo", "บันทึกเมื่อ"], 1)
    return worksheet


def append_to_sheet(date_time: str, amount: str, memo: str):
    sheet = get_sheet()
    recorded_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet.append_row([date_time, amount, memo, recorded_at])


# ───── Claude Vision ─────
def extract_slip_data(image_bytes: bytes) -> dict:
    """ส่งรูปสลิปให้ Claude อ่าน คืนค่า dict {date_time, amount, memo}"""
    image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

    message = anthropic_client.messages.create(
        model="claude-opus-4-6",
        max_tokens=512,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            "นี่คือสลิปโอนเงิน กรุณาอ่านข้อมูลต่อไปนี้และตอบเป็น JSON เท่านั้น ห้ามมีข้อความอื่น:\n"
                            '{"date_time": "YYYY-MM-DD HH:MM", "amount": "ตัวเลขเท่านั้น ไม่มีหน่วย", "memo": "ข้อความ memo หรือ NaN ถ้าไม่มี"}\n'
                            "ถ้าอ่านข้อมูลใดไม่ได้ให้ใส่ NaN"
                        ),
                    },
                ],
            }
        ],
    )

    raw = message.content[0].text.strip()
    # ตัด markdown code block ถ้ามี
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw)


# ───── LINE Webhook ─────
@app.post("/webhook")
async def webhook(request: Request):
    signature = request.headers.get("X-Line-Signature", "")
    body = await request.body()
    try:
        handler.handle(body.decode(), signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    return "OK"


@handler.add(MessageEvent, message=ImageMessageContent)
def handle_image(event: MessageEvent):
    """รับรูปจาก LINE → อ่านสลิป → บันทึก Sheets → ตอบกลับ"""
    with ApiClient(line_config) as api_client:
        line_bot_api = MessagingApi(api_client)

        # ดาวน์โหลดรูปจาก LINE
        url = f"https://api-data.line.me/v2/bot/message/{event.message.id}/content"
        headers = {"Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}
        resp = httpx.get(url, headers=headers)
        image_bytes = resp.content

        try:
            data = extract_slip_data(image_bytes)
            date_time = data.get("date_time", "NaN")
            amount = data.get("amount", "NaN")
            memo = data.get("memo", "NaN")

            append_to_sheet(date_time, amount, memo)

            reply_text = (
                f"✅ บันทึกแล้ว!\n"
                f"📅 วันที่/เวลา: {date_time}\n"
                f"💰 จำนวน: {amount} บาท\n"
                f"📝 Memo: {memo}"
            )
        except Exception as e:
            reply_text = f"❌ อ่านสลิปไม่สำเร็จ: {str(e)}"

        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)]
            )
        )


@app.get("/")
def health():
    return {"status": "ok"}

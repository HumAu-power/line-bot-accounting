# คู่มือ Deploy LINE Bot บัญชี

## สิ่งที่ต้องมีก่อน

| สิ่ง | ลิงก์สมัคร | ค่าใช้จ่าย |
|------|-----------|-----------|
| LINE Developers account | https://developers.line.biz | ฟรี |
| Anthropic API key | https://console.anthropic.com | จ่ายตามใช้งาน |
| Google Cloud (Service Account) | https://console.cloud.google.com | ฟรี |
| Render account | https://render.com | ฟรี (tier ฟรี) |

---

## ขั้นตอนที่ 1 — สร้าง LINE Messaging API Channel

1. ไปที่ https://developers.line.biz → **Create a new provider**
2. สร้าง **Messaging API** channel
3. ไปที่ tab **Messaging API** → เปิด **Allow bot to join group chats** (ถ้าต้องการ)
4. เก็บค่า 2 อย่าง:
   - `Channel secret` (Basic settings tab)
   - `Channel access token` (Messaging API tab → Issue)

---

## ขั้นตอนที่ 2 — สร้าง Google Sheets และ Service Account

1. สร้าง Google Sheets ใหม่ → copy **Spreadsheet ID** จาก URL  
   ตัวอย่าง: `https://docs.google.com/spreadsheets/d/**1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms**/edit`

2. ไปที่ https://console.cloud.google.com → สร้าง project ใหม่

3. เปิด **Google Sheets API**: APIs & Services → Enable APIs → ค้นหา "Google Sheets API" → Enable

4. สร้าง **Service Account**: APIs & Services → Credentials → Create Credentials → Service Account

5. หลังสร้างแล้ว ไปที่ Service Account → **Keys** tab → Add Key → JSON → Download

6. เปิดไฟล์ JSON ที่ดาวน์โหลด → copy ทั้งหมด (ใช้เป็น `GOOGLE_CREDENTIALS_JSON`)

7. **แชร์ Google Sheet** ให้กับ email ของ Service Account  
   (อยู่ในไฟล์ JSON ที่ field `client_email`)  
   สิทธิ์: **Editor**

---

## ขั้นตอนที่ 3 — Deploy บน Render

1. Push โค้ดขึ้น GitHub (ไม่ต้อง push ไฟล์ `.env`)

2. ไปที่ https://render.com → New → **Web Service**

3. เชื่อม GitHub repo

4. ตั้งค่า:
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

5. ใส่ **Environment Variables** (ใส่ทีละตัว):

   | Key | Value |
   |-----|-------|
   | `LINE_CHANNEL_SECRET` | จาก LINE Developers |
   | `LINE_CHANNEL_ACCESS_TOKEN` | จาก LINE Developers |
   | `ANTHROPIC_API_KEY` | จาก Anthropic Console |
   | `GOOGLE_SHEETS_ID` | ID จาก URL ของ Sheet |
   | `GOOGLE_CREDENTIALS_JSON` | วาง JSON ทั้งก้อน (ต้องอยู่บรรทัดเดียว) |

6. กด **Deploy** → รอ 2-3 นาที

7. Copy URL ของ service เช่น `https://your-bot.onrender.com`

---

## ขั้นตอนที่ 4 — ตั้งค่า Webhook ใน LINE

1. ไปที่ LINE Developers → Messaging API channel
2. **Webhook URL**: `https://your-bot.onrender.com/webhook`
3. กด **Verify** → ต้องขึ้น Success
4. เปิด **Use webhook**: ON
5. ปิด **Auto-reply messages**: OFF (ไม่งั้นจะตอบซ้ำ)

---

## ทดสอบ

ส่งรูปสลิปไปใน LINE Chat กับ Bot  
ควรได้รับข้อความตอบกลับภายใน 5-10 วินาที เช่น:

```
✅ บันทึกแล้ว!
📅 วันที่/เวลา: 2026-06-02 14:35
💰 จำนวน: 1500 บาท
📝 Memo: ค่าอาหาร
```

และใน Google Sheets จะมี row ใหม่ปรากฏ

---

## หมายเหตุ Render Free Tier

Render free tier จะ **sleep หลังไม่มีการใช้งาน 15 นาที** ทำให้ครั้งแรกช้า ~30 วินาที  
ถ้าต้องการให้ตอบเร็วตลอด ให้ upgrade เป็น Starter ($7/เดือน) หรือย้ายไป Railway

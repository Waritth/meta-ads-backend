from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import requests

# อ่าน ENV จาก Railway / .env
META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
META_API_VERSION = os.getenv("META_API_VERSION", "v20.0")
BASE_URL = f"https://graph.facebook.com/{META_API_VERSION}"

app = FastAPI(
    title="Meta Ads Backend for Agent",
    description="Backend ตัวกลางดึง Meta Ads Insights ให้ Agent วิเคราะห์",
)

# ถ้าอยากให้ frontend ที่โดเมนอื่นเรียก API ได้
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # ใน production ควรจำกัดโดเมน
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "ok", "message": "Meta Ads Backend running on Railway"}

@app.get("/meta/insights")
def get_meta_insights(
    account_id: str,
    since: str,
    until: str,
):
    """
    ดึงข้อมูล performance จาก Meta Ads Insights แบบรายวัน

    - account_id: ใส่เลขบัญชีโฆษณา เช่น 920686982928728 (ไม่ต้องใส่ 'act_')
    - since / until: รูปแบบ YYYY-MM-DD
    """

    if not META_ACCESS_TOKEN:
        raise HTTPException(
            status_code=500,
            detail="META_ACCESS_TOKEN is not configured in environment variables",
        )

    # เติม act_ ให้เอง
    endpoint = f"{BASE_URL}/act_{account_id}/insights"

    fields = [
        "campaign_id",
        "campaign_name",
        "adset_id",
        "adset_name",
        "ad_id",
        "ad_name",
        "impressions",
        "clicks",
        "ctr",
        "spend",
        "cpc",
        "cpm",
        "reach",
        "frequency",
        "objective",
        "actions",
        "action_values",
    ]

    params = {
        "fields": ",".join(fields),
        "time_range[since]": since,
        "time_range[until]": until,
        "time_increment": 1,  # รายวัน
        "access_token": META_ACCESS_TOKEN,
    }

    r = requests.get(endpoint, params=params, timeout=30)
    if r.status_code != 200:
        # ส่ง error จาก Meta กลับไปดูด้วย
        raise HTTPException(
            status_code=r.status_code,
            detail=f"Meta API error: {r.text}",
        )

    data = r.json().get("data", [])

    return {
        "account_id": account_id,
        "since": since,
        "until": until,
        "rows": data,
    }

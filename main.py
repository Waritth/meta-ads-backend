from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import requests

# อ่านค่า ENV จากระบบ (Railway จะใส่ให้)
META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
META_API_VERSION = os.getenv("META_API_VERSION", "v20.0")  # เผื่อเปลี่ยนเวอร์ชันในอนาคต
BASE_URL = f"https://graph.facebook.com/{META_API_VERSION}"

app = FastAPI(
    title="Meta Ads Backend for Agent",
    description="Backend ตัวกลางดึง Meta Ads Insights ให้ Agent วิเคราะห์",
)

# ถ้าคุณจะให้ frontend/domain อื่นเรียก API โดยตรง ใส่ CORS ตามนี้ได้
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # โปรดปรับให้แคบลงใน production
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
    - account_id: ไม่ต้องใส่ 'act_' ข้างหน้า ใส่แค่เลข เช่น 123456789012345
    - since / until: รูปแบบ YYYY-MM-DD
    """

    if not META_ACCESS_TOKEN:
        raise HTTPException(
            status_code=500,
            detail="META_ACCESS_TOKEN is not configured in environment variables"
        )

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
        "action_values"
    ]

    params = {
        "fields": ",".join(fields),
        "time_range[since]": since,
        "time_range[until]": until,
        "time_increment": 1,  # รายวัน
        "access_token": META_ACCESS_TOKEN,
    }

    r = requests.get(endpoint, params=params)
    if r.status_code != 200:
        raise HTTPException(
            status_code=r.status_code,
            detail=f"Meta API error: {r.text}"
        )

    data = r.json().get("data", [])

    # คุณจะ normalize ข้อมูลตรงนี้ก่อนก็ได้ เช่น ทำ mapping action เป็น conversions ฯลฯ
    return {
        "account_id": account_id,
        "since": since,
        "until": until,
        "rows": data
    }

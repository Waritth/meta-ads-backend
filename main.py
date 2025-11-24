from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import os
import requests
from typing import Literal

# ===== Config จาก ENV =====
META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
META_API_VERSION = os.getenv("META_API_VERSION", "v20.0")
BASE_URL = f"https://graph.facebook.com/{META_API_VERSION}"

# ===== สร้างแอป =====
app = FastAPI(
    title="Meta Ads Backend for Agent",
    description="Backend ตัวกลางดึง Meta Ads Insights ให้ Agent วิเคราะห์ (Agency-grade)",
    version="0.2.0",
)

# CORS เผื่อมี frontend/Web dashboard มาเรียก
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # ใน production แนะนำให้ล็อก domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===== Healthcheck =====
@app.get("/")
def root():
    return {"status": "ok", "message": "Meta Ads Backend running on Railway"}


# ===== Insights Endpoint (All-in-one) =====
@app.get("/meta/insights")
def get_meta_insights(
    account_id: str = Query(..., description="เลขบัญชีโฆษณา เช่น 920686982928728 (ไม่ต้องมี act_)"),
    since: str = Query(..., description="วันที่เริ่มต้น YYYY-MM-DD"),
    until: str = Query(..., description="วันที่สิ้นสุด YYYY-MM-DD"),
    level: Literal["account", "campaign", "adset", "ad"] = Query(
        "campaign",
        description="ระดับข้อมูลที่ต้องการ: account / campaign / adset / ad",
    ),
    granularity: Literal["total", "day"] = Query(
        "total",
        description="รูปแบบเวลา: total=ยอดรวมทั้งช่วง, day=รายวัน",
    ),
):
    """
    ดึง Meta Ads Insights แบบ Agency-grade

    - รองรับ level: campaign (default), adset, ad, account
    - รองรับ pagination (ดึงครบทุกหน้า)
    - เลือก granularity:
        - total: รวมยอดทั้งช่วงวันที่
        - day: แยกรายวัน (time_increment=1)
    """

    if not META_ACCESS_TOKEN:
        raise HTTPException(
            status_code=500,
            detail="META_ACCESS_TOKEN is not configured in environment variables",
        )

    # จุดเริ่มต้นของ request แรก
    url = f"{BASE_URL}/act_{account_id}/insights"

    # fields สำหรับวิเคราะห์จริงจัง
    # เพิ่ม/ลดได้ตามต้องการ
    fields = [
        "date_start",
        "date_stop",
        "account_id",
        "account_name",
        "campaign_id",
        "campaign_name",
        "adset_id",
        "adset_name",
        "ad_id",
        "ad_name",
        "objective",
        "impressions",
        "reach",
        "frequency",
        "clicks",
        "unique_clicks",
        "spend",
        "cpm",
        "cpc",
        "cpp",
        "ctr",
        "unique_ctr",
        "actions",
        "action_values",
        "conversion_values",
        "purchase_roas",
        "website_purchase_roas",
    ]

    params = {
        "level": level,
        "fields": ",".join(fields),
        "time_range[since]": since,
        "time_range[until]": until,
        "access_token": META_ACCESS_TOKEN,
    }

    # ถ้าอยากได้รายวัน → ใส่ time_increment=1
    if granularity == "day":
        params["time_increment"] = 1

    all_rows = []
    current_url = url
    current_params = params

    # ===== pagination loop =====
    while True:
        resp = requests.get(current_url, params=current_params, timeout=60)

        if resp.status_code != 200:
            # ส่ง error จาก Meta กลับไปให้ดูด้วย
            raise HTTPException(
                status_code=resp.status_code,
                detail=f"Meta API error: {resp.text}",
            )

        body = resp.json()
        data = body.get("data", [])
        all_rows.extend(data)

        paging = body.get("paging", {})
        next_url = paging.get("next")

        if not next_url:
            break

        # next URL มี query ครบแล้ว → ไม่ต้องส่ง params ซ้ำ
        current_url = next_url
        current_params = {}

    return {
        "account_id": account_id,
        "since": since,
        "until": until,
        "level": level,
        "granularity": granularity,
        "row_count": len(all_rows),
        "rows": all_rows,
    }

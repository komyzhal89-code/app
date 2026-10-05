import os
import math
from datetime import datetime, timedelta
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import requests
import xml.etree.ElementTree as ET

app = FastAPI(title="Korail Realtime Location API")

# 앱 및 웹에서의 접근 허용 (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 공공데이터포털 API Key (환경변수 또는 직접 입력)
SERVICE_KEY = os.getenv("DATA_GO_KEY", "YOUR_DECODED_SERVICE_KEY_HERE")

# 대표 주요 역 좌표 DB (위도, 경도)
STATION_COORDS = {
    "서울": (37.5547, 126.9707),
    "영등포": (37.5155, 126.9078),
    "수원": (37.2656, 127.0000),
    "대전": (36.3323, 127.4342),
    "김천구미": (36.1248, 128.1812),
    "동대구": (35.8797, 128.6285),
    "신경주": (35.7981, 129.1397),
    "울산": (35.5517, 129.1386),
    "부산": (35.1152, 129.0422),
    "익산": (35.9404, 126.9542),
    "광주송정": (35.1378, 126.7916),
    "목포": (34.7912, 126.3868),
}

def interpolate_location(start_coords: tuple, end_coords: tuple, progress: float):
    """두 역의 위도/경도 사이를 progress(0.0~1.0) 비율로 선형 보간"""
    lat = start_coords[0] + (end_coords[0] - start_coords[0]) * progress
    lng = start_coords[1] + (end_coords[1] - start_coords[1]) * progress
    return round(lat, 6), round(lng, 6)

@app.get("/")
def root():
    return {"status": "ok", "message": "Korail Location Server Running"}

@app.get("/api/train/location")
def get_train_location(
    dep_station: str = Query(..., description="출발역 이름 (예: 대전)"),
    arr_station: str = Query(..., description="도착역 이름 (예: 동대구)"),
    dep_time: str = Query(..., description="출발예정시각 HH:MM (예: 12:00)"),
    arr_time: str = Query(..., description="도착예정시각 HH:MM (예: 12:30)"),
    delay_minutes: int = Query(0, description="지연 시간(분)"),
    train_no: Optional[str] = Query("KTX 123", description="열차 번호")
):
    """
    현재 시각 기준으로 열차의 두 역 사이 진행률과 위도/경도 좌표를 계산합니다.
    """
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")

    try:
        dep_dt = datetime.strptime(f"{today_str} {dep_time}", "%Y-%m-%d %H:%M") + timedelta(minutes=delay_minutes)
        arr_dt = datetime.strptime(f"{today_str} {arr_time}", "%Y-%m-%d %H:%M") + timedelta(minutes=delay_minutes)
    except ValueError:
        raise HTTPException(status_code=400, detail="시간 형식이 올바르지 않습니다. HH:MM 형식으로 입력하세요.")

    total_seconds = (arr_dt - dep_dt).total_seconds()
    if total_seconds <= 0:
        raise HTTPException(status_code=400, detail="도착 시간이 출발 시간보다 빠를 수 없습니다.")

    elapsed_seconds = (now - dep_dt).total_seconds()

    # 진행률 및 상태 판단
    if elapsed_seconds <= 0:
        progress = 0.0
        status = "출발 전 정차"
    elif elapsed_seconds >= total_seconds:
        progress = 1.0
        status = "도착 완료"
    else:
        progress = elapsed_seconds / total_seconds
        status = "운행 중"

    # 좌표 계산
    start_coord = STATION_COORDS.get(dep_station, (36.3323, 127.4342))
    end_coord = STATION_COORDS.get(arr_station, (35.8797, 128.6285))
    current_lat, current_lng = interpolate_location(start_coord, end_coord, progress)

    return {
        "train_no": train_no,
        "status": status,
        "departure_station": dep_station,
        "arrival_station": arr_station,
        "delay_minutes": delay_minutes,
        "progress_percentage": round(progress * 100, 1),
        "current_position": {
            "latitude": current_lat,
            "longitude": current_lng
        },
        "updated_at": now.strftime("%Y-%m-%d %H:%M:%S")
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
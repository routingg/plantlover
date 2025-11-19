import cv2
from django.http import StreamingHttpResponse
from django.shortcuts import render

def home(request):
    return render(request, "home.html")

def current_plant(request):
    return render(request, "current_plant.html")



def tips(request):
    return render(request, "tips.html", {"title": "식물관리팁", "desc": "식물관리 꿀팁"})

# ---------- 실시간 카메라 스트림 ----------
def generate_camera_stream():
    cap = cv2.VideoCapture(0)  # 0번 카메라 사용 (노트북 카메라 or USB 웹캠)
    if not cap.isOpened():
        print("카메라를 찾을 수 없습니다!")

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        # JPEG로 인코딩
        ret, jpeg = cv2.imencode('.jpg', frame)
        if not ret:
            continue

        # MJPEG 스트림 형식으로 yield
        yield (b"--frame\r\n"
               b"Content-Type: image/jpeg\r\n\r\n" +
               jpeg.tobytes() +
               b"\r\n\r\n")


def video_feed(request):
    return StreamingHttpResponse(
        generate_camera_stream(),
        content_type="multipart/x-mixed-replace; boundary=frame"
    )


# ---------- 물주기 / 식물등 제어 ----------
def control(request, cmd):
    print("식물 명령:", cmd)
    return HttpResponse(f"{cmd} OK")


import csv
import os
from django.shortcuts import render

CSV_FILENAME = "ndvi_log.csv"   # ndvi.py와 같은 위치에 있다고 가정

def plant_report(request):
    ndvi_time = None
    ndvi_avg = None
    ndvi_mid = None

    if os.path.exists(CSV_FILENAME):
        with open(CSV_FILENAME, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader, None)  # ['Time', 'Average', 'Median']
            rows = [row for row in reader if row]

        if rows:
            last = rows[-1]
            ndvi_time = last[0]
            ndvi_avg = float(last[1])
            ndvi_mid = float(last[2])

    context = {
        "soil_moisture": "45%",
        "light_lux": "320",
        "temperature": "23.5°C",
        "humidity": "58%",
        "last_watering_time": "2025-11-17 10:30",
        "watering_count_week": "3회",
        "growth_log_1": "2025-11-01: 새 잎 1개 성장",
        "growth_log_2": "2025-10-27: 잎 색 개선됨",
        "growth_log_3": "2025-10-21: 토양 건조도 감소",

        # NDVI 값
        "ndvi_time": ndvi_time,
        "ndvi_avg": f"{ndvi_avg:.3f}" if ndvi_avg is not None else None,
        "ndvi_mid": f"{ndvi_mid:.3f}" if ndvi_mid is not None else None,
    }

    return render(request, "plant_report.html", context)

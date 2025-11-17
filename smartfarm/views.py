import cv2
from django.http import StreamingHttpResponse
from django.shortcuts import render

def home(request):
    return render(request, "home.html")

def current_plant(request):
    return render(request, "current_plant.html")

def plant_report(request):
    return render(request, "plant_report.html", {"title": "식물리포트", "desc": "우리 식물 리포트"})

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

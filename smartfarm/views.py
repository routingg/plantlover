import cv2
from django.http import StreamingHttpResponse
from django.shortcuts import render
from openai import OpenAI
import os

client = OpenAI()  # OPENAI_API_KEY는 환경변수에서 자동 사용


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


from django.shortcuts import render, redirect
from django.utils import timezone

def plant_counseling(request):
    # 세션에 대화 내역 저장
    if "chat_messages" not in request.session:
        request.session["chat_messages"] = []

    messages = request.session["chat_messages"]
    plant_type = request.session.get("plant_type", "")

    if request.method == "POST":
        plant_type_input = request.POST.get("plant_type", "").strip()
        user_message = request.POST.get("user_message", "").strip()

        if plant_type_input:
            plant_type = plant_type_input
            request.session["plant_type"] = plant_type

        if user_message:
            now = timezone.now().strftime("%H:%M")

            # 사용자 메시지 저장
            messages.append({
                "sender": "user",
                "text": user_message,
                "time": now,
            })

            # GPT에게 질문
            bot_reply = generate_bot_reply(plant_type, user_message, history=messages)

            # 봇 답변 저장
            messages.append({
                "sender": "bot",
                "text": bot_reply,
                "time": now,
            })

            request.session["chat_messages"] = messages
            request.session.modified = True

        return redirect("plant_counseling")

    return render(request, "plant_counseling.html", {
        "messages": messages,
        "plant_type": plant_type,
    })



from openai import OpenAI

client = OpenAI()  # OPENAI_API_KEY는 환경변수로 설정되어 있다고 가정

def generate_bot_reply(plant_type, user_message, history=None):
    """
    GPT API를 이용해 식물 상담 답변 생성.
    history: 이전 대화 목록 (옵션, 지금은 안 써도 됨)
    """
    # 1) 역할 + 스타일 정의 (마크다운 금지)
    system_prompt = (
        "너는 한국어로 답변하는 식물 상담사야. "
        "사용자가 키우는 실내식물, 허브, 관엽식물 등의 상태를 설명하면 "
        "가능한 원인(물주기, 광량, 온도, 통풍, 병해충 등)을 추론하고, "
        "집에서 따라 할 수 있는 구체적인 관리 방법을 알려줘.\n\n"
        "답변 스타일 규칙:\n"
        "- 마크다운을 쓰지 말 것. 별표(**), #, -, 번호 목록(1. 2. 3.)을 사용하지 말 것.\n"
        "- 보고서 말투 대신, 상담하듯이 자연스러운 한국어 문장으로 답하기.\n"
        "- 문단은 최대 2~3개 정도, 각 문단은 2~3문장 정도로 간결하게.\n"
        "- 핵심만 말하고, 너무 장황하게 설명하지 말 것.\n"
        "- 가능하면 오늘 당장 해볼 수 있는 행동 위주로 조언하기."
    )

    plant_info = f"키우는 식물: {plant_type}" if plant_type else "키우는 식물 종류는 아직 모름"

    # 필요하면 history도 한 번에 요약해서 넣을 수 있지만,
    # 처음엔 단순하게 최근 발화 기준으로만 보낼게.
    user_content = (
        f"{plant_info}\n\n"
        f"사용자 고민:\n{user_message}\n\n"
        "위 고민을 바탕으로, 원인 추측과 오늘 당장 해볼 수 있는 관리 방법, "
        "앞으로의 관리 방향을 차분하게 설명해줘."
    )

    resp = client.responses.create(
        model="gpt-4.1-mini",  # 가벼운 모델
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        max_output_tokens=400,  # 너무 길게 안 나오게 제한
    )

    try:
        reply_text = resp.output_text
    except AttributeError:
        reply_text = resp.output[0].content[0].text

    return reply_text.strip()


from django.shortcuts import render

def home(request):
    return render(request, "home.html")

def temperature(request):
    return render(request, "placeholder.html", {"title": "온도", "desc": "현재 온도 확인하기"})

def humidity(request):
    return render(request, "placeholder.html", {"title": "습도", "desc": "습도 수치 보기"})

def growth(request):
    return render(request, "placeholder.html", {"title": "생장", "desc": "식물 성장 기록"})

def watering(request):
    return render(request, "placeholder.html", {"title": "물주기", "desc": "물주기 관리"})

def current_plant(request):
    return render(request, "placeholder.html", {"title": "현재식물보기", "desc": "우리 식물 상태"})

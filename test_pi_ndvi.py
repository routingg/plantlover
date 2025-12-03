import cv2
import numpy as np
import matplotlib.pyplot as plt
from fastiecm import fastiecm 
import time
import os
import csv
from picamera2 import Picamera2 # Picamera2 임포트

# --- 설정 구간 ---
CAPTURE_INTERVAL = 30  
CSV_FILENAME = "ndvi_log.csv"
SAVE_FOLDER = "ndvi_graph" 

ICON_SIZE = (500, 500)

IMG_PATHS = {
    "dead": "plant_death.png",
    "bad": "plant_nothealth.png",
    "mid": "plant_midhealth.png",
    "good": "plant_veryhealth.png"
}

# 이미지 로드 함수
def load_images(paths):
    images = {}
    for key, path in paths.items():
        if os.path.exists(path):
            img = cv2.imread(path)
            if img is not None:
                images[key] = img
            else:
                print(f"Warning: 이미지를 읽을 수 없습니다 ({path})")
                images[key] = None
        else:
            print(f"Warning: 파일이 존재하지 않습니다 ({path})")
            images[key] = None
    return images

status_images = load_images(IMG_PATHS)

if not os.path.exists(CSV_FILENAME):
    with open(CSV_FILENAME, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Time', 'Average', 'Median'])

if not os.path.exists(SAVE_FOLDER):
    os.makedirs(SAVE_FOLDER) 

# [수정] cv2.VideoCapture 대신 Picamera2 설정
picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"size": (640, 480), "format": "RGB888"})
picam2.configure(config)
picam2.start()

# NDVI 계산 함수들
def contrast_stretch(im):
    in_min = np.percentile(im, 5)
    in_max = np.percentile(im, 95)
    out_min = 0.0
    out_max = 255.0
    out = im - in_min
    out *= ((out_min - out_max) / (in_min - in_max))
    out += in_min
    return out

def calc_ndvi(image):
    b, g, r = cv2.split(image)
    bottom = (r.astype(float) + b.astype(float))
    bottom[bottom==0] = 0.01
    ndvi = (b.astype(float) - r) / bottom
    return ndvi

def save_summary_graph_from_csv(csv_path, graph_path, current_timestamp):
    times = []
    avgs = []
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)
            for row in reader:
                if not row: continue
                times.append(row[0])
                avgs.append(float(row[1]))

        if len(times) > 0:
            plt.figure(figsize=(10, 6)) 
            plt.plot(times, avgs, marker='o', color='red', label='Average', linewidth=2)
            plt.title(f"NDVI Trend - {current_timestamp}")
            plt.tight_layout()
            plt.savefig(graph_path)
            plt.close() 
            return True
        else:
            return False
    except Exception as e:
        print(f"Error creating graph: {e}")
        plt.close()
        return False

last_capture_time = time.time()
print("시스템 시작. [창 1: NDVI Camera] [창 2: Plant Status]")

try:
    while True:
        # [수정] Picamera2에서 캡처한 배열을 변환 없이 그대로 original에 저장
        original = picam2.capture_array()
        
        # 1. 카메라 영상 처리 (NDVI)
        shape = original.shape
        height = int(shape[0] / 2)
        width = int(shape[1] / 2)
        original = cv2.resize(original, (width, height))

        contrasted = contrast_stretch(original)
        ndvi = calc_ndvi(contrasted)
        ndvi_contrasted = contrast_stretch(ndvi)
        
        color_mapped_prep = ndvi_contrasted.astype(np.uint8)
        color_mapped_image = cv2.applyColorMap(color_mapped_prep, fastiecm)

        # 평균값 계산
        normalized_data = color_mapped_prep / 255.0
        curr_avg = np.mean(normalized_data)
        curr_mid = np.median(normalized_data)

        img_key = ""
        if curr_avg < 0.1: 
             img_key = "dead"
        elif curr_avg < 0.33:
            img_key = "bad"
        elif curr_avg < 0.66:
            img_key = "mid"
        else:
            img_key = "good"

        status_display = None
        if status_images[img_key] is not None:
            status_display = cv2.resize(status_images[img_key], ICON_SIZE)
        else:
            status_display = np.zeros((ICON_SIZE[1], ICON_SIZE[0], 3), dtype=np.uint8)
            cv2.putText(status_display, "No Image", (50, 250), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)


        text_str = f"Avg: {curr_avg:.3f}"
        cv2.putText(status_display, text_str, (20, ICON_SIZE[1] - 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 5) 
        cv2.putText(status_display, text_str, (20, ICON_SIZE[1] - 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2) 

        current_time = time.time()
        if current_time - last_capture_time >= CAPTURE_INTERVAL:
            time_str = time.strftime("%H:%M:%S")
            file_timestamp = time.strftime("%Y%m%d_%H%M%S")
            
            with open(CSV_FILENAME, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([time_str, curr_avg, curr_mid])
            
            graph_output_path = os.path.join(SAVE_FOLDER, f"trend_{file_timestamp}.png")
            save_summary_graph_from_csv(CSV_FILENAME, graph_output_path, time_str)
            print(f"[Saved] {time_str}")
            last_capture_time = current_time

        cv2.imshow('NDVI Camera', color_mapped_image)  # 카메라 영상
        cv2.imshow('Plant Status', status_display)     # 상태 이미지 

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    # [수정] 자원 해제
    picam2.stop()
    picam2.close()
    cv2.destroyAllWindows()

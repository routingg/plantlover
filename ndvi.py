import cv2
import numpy as np
import matplotlib.pyplot as plt
from fastiecm import fastiecm 
import time
import os
import csv
from picamera2 import Picamera2

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

def contrast_stretch(im):
    img_float = im.astype(float)
    in_min = np.percentile(img_float, 5)
    in_max = np.percentile(img_float, 95)

    out_min = 0.0
    out_max = 255.0

    if in_max - in_min == 0:
        return im

    out = img_float - in_min
    out *= ((out_min - out_max) / (in_min - in_max))
    out += out_min
    
    out = np.clip(out, 0, 255)
    return out.astype(np.uint8)

def calc_ndvi(image):
    b, g, r = cv2.split(image)

    bottom = (r.astype(float) + b.astype(float))
    bottom[bottom == 0] = 0.01
    ndvi = (b.astype(float) - r.astype(float)) / bottom
  
    return ndvi

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
            images[key] = None
    return images

status_images = load_images(IMG_PATHS)

# CSV 및 폴더 초기화
if not os.path.exists(CSV_FILENAME):
    with open(CSV_FILENAME, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Time', 'Average', 'Median'])

if not os.path.exists(SAVE_FOLDER):
    os.makedirs(SAVE_FOLDER) 

picam2 = Picamera2()
config = picam2.create_video_configuration(
    main={"size": (640, 480), "format": "BGR888"}
)
picam2.configure(config)
picam2.start()

# 그래프 저장 
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
print("시스템 시작. [창 1: NDVI Camera] [창 3: Plant Status]")

try:
    while True:
        original = picam2.capture_array()
        
        if original is None:
            continue

        stretched_frame = contrast_stretch(original)
        ndvi_val = calc_ndvi(stretched_frame)
        ndvi_scaled = (ndvi_val + 1) / 2 * 255
        ndvi_uint8 = ndvi_scaled.astype(np.uint8)
        
        color_mapped_image = cv2.applyColorMap(ndvi_uint8, fastiecm)

        # 평균값 계산
        normalized_data = ndvi_uint8 / 255.0
        curr_avg = np.mean(normalized_data)
        curr_mid = np.median(normalized_data)

        img_key = ""
        if curr_avg < 0.35:     
             img_key = "dead"
        elif curr_avg < 0.45:
            img_key = "bad"
        elif curr_avg < 0.55:
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

        # 로깅 및 그래프 저장
        current_time = time.time()
        if current_time - last_capture_time >= CAPTURE_INTERVAL:
            time_str = time.strftime("%H:%M:%S")
            file_timestamp = time.strftime("%Y%m%d_%H%M%S")
            
            with open(CSV_FILENAME, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([time_str, curr_avg, curr_mid])
            
            graph_output_path = os.path.join(SAVE_FOLDER, f"trend_{file_timestamp}.png")
            save_summary_graph_from_csv(CSV_FILENAME, graph_output_path, time_str)
            print(f"[Saved] {time_str} - Avg: {curr_avg:.3f}")
            last_capture_time = current_time

        # 화면 출력
        cv2.imshow('NDVI Camera', color_mapped_image)  
        cv2.imshow('Plant Status', status_display)      

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

except Exception as e:
    print(f"에러 발생: {e}")

finally:
    picam2.stop()
    picam2.close()
    cv2.destroyAllWindows()

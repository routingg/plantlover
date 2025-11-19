import cv2
import numpy as np
import matplotlib.pyplot as plt
from collections import deque
from fastiecm import fastiecm 
import time
import os
import csv

CAPTURE_INTERVAL = 30  # 데이터 기록 간격 (초 단위)
CSV_FILENAME = "ndvi_log.csv"
SAVE_FOLDER = "ndvi_graph" 

if not os.path.exists(CSV_FILENAME):
    with open(CSV_FILENAME, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Time', 'Average', 'Median'])

if not os.path.exists(SAVE_FOLDER):
    os.makedirs(SAVE_FOLDER) 

cap = cv2.VideoCapture(0)

#실시간 화면
plt.ion()
fig, ax = plt.subplots()
max_len = 100
x_data = np.arange(max_len)
y_avg = deque([0.0] * max_len, maxlen=max_len)
y_mid = deque([0.0] * max_len, maxlen=max_len)

line_avg, = ax.plot(x_data, y_avg, color='red', label='Average', linewidth=2)
line_mid, = ax.plot(x_data, y_mid, color='blue', label='Median', linewidth=2)

ax.set_ylim(0, 1.05)
ax.set_xlim(0, max_len - 1)
ax.set_ylabel("NDVI Value")
ax.set_title("Live Monitor")
ax.legend(loc='upper left')
ax.grid(True, linestyle='--', alpha=0.5)

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
    #ndvi = (r.astype(float) - b) / bottom Noir 카메라 사용시

    return ndvi

def save_summary_graph_from_csv(csv_path, graph_path, current_timestamp):
    times = []
    avgs = []
    mids = []

    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)
            
            for row in reader:
                if not row: continue
                times.append(row[0])
                avgs.append(float(row[1]))
                mids.append(float(row[2]))

        if len(times) > 0:
            # 저장을 위한 새로운 figure 생성
            plt.figure(figsize=(10, 6)) 
            plt.plot(times, avgs, marker='o', color='red', label='Average (Mean)', linewidth=2)
            plt.plot(times, mids, marker='s', color='blue', label='Median', linestyle='--', linewidth=2)

            plt.title(f"NDVI Analysis Log - Snapshot {current_timestamp}", fontsize=16)
            plt.xlabel("Time", fontsize=12)
            plt.ylabel("NDVI Value (0.0 ~ 1.0)", fontsize=12)
            plt.ylim(0, 1.1)
            plt.legend()
            plt.grid(True, alpha=0.5)
            
            if len(times) > 20:
                step = len(times) // 20
                plt.xticks(range(0, len(times), step), times[::step], rotation=45)
            else:
                plt.xticks(rotation=45)

            plt.tight_layout()
            plt.savefig(graph_path)
            plt.close() 
            return True
        else:
            return False

    except Exception as e:
        print(f"Error creating periodic graph: {e}")
        return False

last_capture_time = time.time()
print(f"시스템 시작. 데이터 로깅 및 그래프 저장 {CAPTURE_INTERVAL}초 간격.")

try:
    while True:
        ret, original = cap.read()
        if not ret:
            break

        shape = original.shape
        height = int(shape[0] / 2)
        width = int(shape[1] / 2)
        original = cv2.resize(original, (width, height))

        contrasted = contrast_stretch(original)
        ndvi = calc_ndvi(contrasted)
        ndvi_contrasted = contrast_stretch(ndvi)
        
        color_mapped_prep = ndvi_contrasted.astype(np.uint8)
        color_mapped_image = cv2.applyColorMap(color_mapped_prep, fastiecm)

        normalized_data = color_mapped_prep / 255.0
        curr_avg = np.mean(normalized_data)
        curr_mid = np.median(normalized_data)

        y_avg.append(curr_avg)
        y_mid.append(curr_mid)
        line_avg.set_ydata(y_avg)
        line_mid.set_ydata(y_mid)
        fig.canvas.draw()
        fig.canvas.flush_events()

        current_time = time.time()
        
        # Check Logging/Saving Interval
        if current_time - last_capture_time >= CAPTURE_INTERVAL:
            time_str = time.strftime("%H:%M:%S")
            file_timestamp = time.strftime("%Y%m%d_%H%M%S")
            
            #CSV에 데이터 기록
            with open(CSV_FILENAME, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([time_str, curr_avg, curr_mid])
            
            #CSV 데이터를 읽어와 누적 그래프 저장
            graph_output_path = os.path.join(SAVE_FOLDER, f"trend_{file_timestamp}.png")
            if save_summary_graph_from_csv(CSV_FILENAME, graph_output_path, time_str):
                 print(f"[LOG & GRAPH SAVED] {time_str}. File: {graph_output_path}")
            
            last_capture_time = current_time

        cv2.imshow('NDVI', color_mapped_image)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    cap.release()
    cv2.destroyAllWindows()
    plt.close('all')

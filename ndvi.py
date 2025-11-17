import cv2
import numpy as np
import matplotlib.pyplot as plt
from collections import deque
from fastiecm import fastiecm

cap = cv2.VideoCapture(0)

# --- 그래프 설정 ---
plt.ion()
fig, ax = plt.subplots()

max_len = 100
x_data = np.arange(max_len)

# 데이터 저장용 큐
y_avg = deque([0.0] * max_len, maxlen=max_len)
y_mid = deque([0.0] * max_len, maxlen=max_len)

line_avg, = ax.plot(x_data, y_avg, color='red', label='Average', linewidth=2)
line_mid, = ax.plot(x_data, y_mid, color='blue', label='Median', linewidth=2)

ax.set_ylim(0, 1.05)
ax.set_xlim(0, max_len - 1)
ax.set_ylabel("NDVI Value (All Pixels)")
ax.set_xlabel("Time (Frames)")
ax.set_title("Real-time NDVI Trend")
ax.legend(loc='upper left')
ax.grid(True, linestyle='--', alpha=0.5)

def contrast_stretch(im):
    im = im.astype(float)
    in_min = np.percentile(im, 5)
    in_max = np.percentile(im, 95)
    out_min = 0.0
    out_max = 255.0
    out = im - in_min
    if in_max - in_min != 0:
        out *= ((out_min - out_max) / (in_min - in_max))
    out += out_min
    out = np.clip(out, 0, 255)
    return out

def calc_ndvi(image):
    b, g, r = cv2.split(image)
    bottom = (r.astype(float) + b.astype(float))
    bottom[bottom==0] = 0.01
    ndvi = (b.astype(float) - r) / bottom
    #ndvi = (r.astype(float) - b) / bottom #noir 카메라 사용시 이것으로 바꿀것

    return ndvi

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

    # 전체 픽셀 데이터 정규화 (0.0 ~ 1.0)
    normalized_data = color_mapped_prep / 255.0
    
    curr_avg = np.mean(normalized_data)
    curr_mid = np.median(normalized_data)

    y_avg.append(curr_avg)
    y_mid.append(curr_mid)

    line_avg.set_ydata(y_avg)
    line_mid.set_ydata(y_mid)

    fig.canvas.draw()
    fig.canvas.flush_events()

    cv2.imshow('Real-time NDVI', color_mapped_image)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
plt.close()

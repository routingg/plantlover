import cv2
from ultralytics import YOLO

#모델 불러오기
model = YOLO('best.pt')

class_names = ['Disease', 'Healthy']

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("웹캠을 열 수 없습니다.")
    exit()

print("종료하려면 화면을 클릭하고 'q' 키를 누르세요.")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # conf=0.5: 50% 이상인 것만 잡음 (조절 가능)
    results = model(frame, conf=0.5)

    annotated_frame = results[0].plot()

    for result in results:
        boxes = result.boxes
        for box in boxes:
            cls_id = int(box.cls[0])
            cls_name = class_names[cls_id]
            confidence = float(box.conf[0])
            
            if cls_name == 'Disease':
                print(f"병충해 식물 (확률: {confidence:.2f})")
            else:
                print(f"건강한 식물 (확률: {confidence:.2f})")

    cv2.imshow("Plant Health Check", annotated_frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
      
cap.release()
cv2.destroyAllWindows()

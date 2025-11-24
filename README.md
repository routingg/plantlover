# plantlover

### Requirements
matplotlib==3.10.7

numpy==2.3.5

opencv_python==4.12.0.88

ultralytics==8.3.230

### Features
#### AI 실시간 병해 진단 (Disease Detection)

YOLO 모델 기반 탐지: 학습된 가중치 파일(best.pt)을 사용하여 웹캠 영상 속 식물을 실시간으로 분석합니다.

상태 분류: 식물의 상태를 Healthy(건강함) 또는 Disease(병해) 두 가지 클래스로 즉시 판별하고 바운딩 박스로 표시합니다.

관련 파일: detect.py

#### NDVI 식물 생육 분석 (Vegetation Analysis)

생육 상태 시각화: 식물 잎의 이미지를 분석하여 NDVI(정규 식생 지수) 알고리즘을 적용합니다.

컬러맵 적용: 육안으로 구분하기 힘든 식물의 활력도를 fastiecm 컬러맵을 통해 시각적으로 보여줍니다.

관련 파일: ndvi.py, fastiecm.py

### best.pt

Class (클래스)	Images (이미지 수)	Instances (객체 수)	Precision (정확도)	Recall (재현율)	mAP50	mAP50-95
all (전체 평균)	514	1753	0.753	0.692	0.771	0.527
Disease (병해)	331	798	0.741	0.664	0.741	0.508
Healthy (건강)	182	955	0.764	0.72	0.8	0.546

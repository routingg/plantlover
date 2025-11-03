import cv2
import numpy as np
from fastiecm import fastiecm
from ultralytics import YOLO

def calculate_exgr(image):
  blue = image[:, :, 0].astype(np.float32)
  green = image[:, :, 1].astype(np.float32)
  red = image[:, :, 2].astype(np.float32)

  exgr = 3 * green - 2.4 * red - blue

  return exgr

def calculate_ngrdi(image):
  green = image[:, :, 1].astype(np.float32)
  red = image[:, :, 2].astype(np.float32)

  ngrdi = (green - red) / (green + red)

  return ngrdi

def detect_trees(model_path, image):
    model = YOLO(model_path)
    output = model(image)
    plots = output[0].plot()
    boxes = output[0].boxes

    mask = np.zeros_like(image[:, :, 0], dtype=np.uint8)

    for box in boxes:
        box_cord = box.xyxy.cpu().detach().numpy().tolist()

        for cord in box_cord:
            if len(cord) == 4:
                x1, y1, x2, y2 = cord
                cv2.rectangle(mask, (int(x1), int(y1)), (int(x2), int(y2)), (255, 255, 255), -1)
            elif len(cord) == 5:
                x1, y1, x2, y2, _ = cord
                cv2.rectangle(mask, (int(x1), int(y1)), (int(x2), int(y2)), (255, 255, 255), -1)

    return mask

def main():
    image = cv2.imread('IMG_2409.png')

    if image is None:
        print("이미지를 로드할 수 없습니다.")
        return

    mask = detect_trees('best.pt', image)
    exgr_image = calculate_exgr(image)
    ngrdi_image = calculate_ngrdi(image)

    exgr_image_with_mask = cv2.bitwise_and(exgr_image, exgr_image, mask=mask)
    ngrdi_image_with_mask = cv2.bitwise_and(ngrdi_image, ngrdi_image, mask=mask)

    normalized_exgr = cv2.normalize(exgr_image, None, 0, 255, cv2.NORM_MINMAX)
    normalized_ngrdi = cv2.normalize(ngrdi_image, None, 0, 255, cv2.NORM_MINMAX)

    result_image_exgr = cv2.applyColorMap(normalized_exgr.astype(np.uint8), fastiecm)
    result_image_ngrdi = cv2.applyColorMap(normalized_ngrdi.astype(np.uint8), fastiecm)

#    cv2.imshow('Original Image', image)
#    cv2.imshow('ExGR Image with Bounding Boxes', result_image_exgr)
#    cv2.imshow('NGRDI Image with Bounding Boxes', result_image_ngrdi)

    cv2.imwrite('result_exgr.png', result_image_exgr)
    cv2.imwrite('result_ngrdi.png', result_image_ngrdi)

    cv2.waitKey(0)
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()

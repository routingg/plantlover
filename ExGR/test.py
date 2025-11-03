import cv2
import numpy as np
from fastiecm import fastiecm
from ultralytics import YOLO


def calculate_ngrdi(image):
    green = image[:, :, 1].astype(np.float32)
    red = image[:, :, 2].astype(np.float32)

    ngrdi = (green - red) / (green + red)
    return ngrdi


def calculate_exgr(image):
    blue = image[:, :, 0].astype(np.float32)
    green = image[:, :, 1].astype(np.float32)
    red = image[:, :, 2].astype(np.float32)

    exgr = 3 * green - 2.4 * red - blue
    return exgr


def detect_trees(model_path, image):
    model = YOLO(model_path)
    output = model(image)
    plots = output[0].plot()
    boxes = output[0].boxes

    # Create a mask to store bounding box regions
    mask = np.zeros_like(image[:, :, 0], dtype=np.uint8)

    for box in boxes:
        box_cord = box.xyxy.cpu().detach().numpy().tolist()
        print(box_cord)

        # Draw bounding box on the mask
        for cord in box_cord:
            if len(cord) == 4:
                x1, y1, x2, y2 = cord
                cv2.rectangle(mask, (int(x1), int(y1)), (int(x2), int(y2)), (255, 255, 255), -1)
            elif len(cord) == 5:
                x1, y1, x2, y2, _ = cord
                cv2.rectangle(mask, (int(x1), int(y1)), (int(x2), int(y2)), (255, 255, 255), -1)

    # Apply the mask to the ExGR and NGRDI images
    exgr_image = calculate_exgr(image)
    ngrdi_image = calculate_ngrdi(image)

    exgr_image_with_mask = cv2.bitwise_and(exgr_image, exgr_image, mask=mask)
    ngrdi_image_with_mask = cv2.bitwise_and(ngrdi_image, ngrdi_image, mask=mask)

    return exgr_image_with_mask, ngrdi_image_with_mask


# Load the image
image = cv2.imread('IMG_2409.png')

# Check if the image is loaded successfully
if image is None:
    print("이미지를 로드할 수 없습니다.")
else:
    # Detect trees and calculate ExGR and NGRDI
    exgr_image_with_mask, ngrdi_image_with_mask = detect_trees('best.pt', image)

    # Normalize ExGR and NGRDI values to [0, 255] range
    normalized_exgr = cv2.normalize(exgr_image_with_mask, None, 0, 255, cv2.NORM_MINMAX)
    normalized_ngrdi = cv2.normalize(ngrdi_image_with_mask, None, 0, 255, cv2.NORM_MINMAX)

    # Convert normalized ExGR and NGRDI values to images
    result_image_exgr = cv2.applyColorMap(normalized_exgr.astype(np.uint8), fastiecm)
    result_image_ngrdi = cv2.applyColorMap(normalized_ngrdi.astype(np.uint8), fastiecm)

    # Display the results
    cv2.imshow('Original Image', image)
    cv2.imshow('ExGR Image with Bounding Boxes', result_image_exgr)
    cv2.imshow('NGRDI Image with Bounding Boxes', result_image_ngrdi)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

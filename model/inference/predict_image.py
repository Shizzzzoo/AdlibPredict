from ultralytics import YOLO
import cv2



MODEL_PATH = "train/final/weights/best.pt"   
CONF_THRESHOLD = 0.3
IMG_SIZE = 640
DEVICE = "cuda:0"   


model = YOLO(MODEL_PATH)


def predict_image(image_path: str):
    """
    Runs YOLOv8 inference on a single image.

    Args:
        image_path (str): Path to input image

    Returns:
        results: YOLO prediction results
    """

    # Run inference
    results = model.predict(
        source=image_path,
        imgsz=IMG_SIZE,
        conf=CONF_THRESHOLD,
        device=DEVICE,
        verbose=False
    )

    # Get annotated image
    annotated_img = results[0].plot()

    # Show result
    cv2.imshow("Prediction", annotated_img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    return results



if __name__ == "__main__":
    test_image = "dataset/images/test/sample.png"
    predict_image(test_image)

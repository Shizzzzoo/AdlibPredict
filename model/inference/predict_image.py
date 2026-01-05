import cv2
import json
import os
from ultralytics import YOLO

# Construct the model path relative to this script's location
MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "weights", "best.pt")

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
        str: A JSON string of the prediction results.
    """

    # Run inference
    results = model.predict(
        source=image_path,
        imgsz=IMG_SIZE,
        conf=CONF_THRESHOLD,
        device=DEVICE,
        verbose=False,
    )

    # Process results
    output = []
    for result in results:
        boxes = result.boxes
        for box in boxes:
            x1, y1, x2, y2 = box.xyxy[0]
            conf = box.conf[0]
            cls = box.cls[0]
            output.append(
                {
                    "box": [int(x1), int(y1), int(x2), int(y2)],
                    "confidence": float(conf),
                    "class": int(cls),
                    "class_name": model.names[int(cls)],
                }
            )

    return json.dumps(output)


def show_prediction(image_path: str):
    """
    Runs YOLOv8 inference on a single image and displays it.

    Args:
        image_path (str): Path to input image
    """
    results = model.predict(
        source=image_path,
        imgsz=IMG_SIZE,
        conf=CONF_THRESHOLD,
        device=DEVICE,
        verbose=False,
    )
    # Get annotated image
    annotated_img = results[0].plot()

    # Show result
    cv2.imshow("Prediction", annotated_img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    # This is an example of how to use the functions.
    # You should replace "path/to/your/test/image.jpg" with the actual path to your image.
    # For example, if you have an image in the same directory, you can just use its name.
    test_image = os.path.join(
        os.path.dirname(__file__), "..", "..", "server", "captured_images", "test.png"
    )
    if os.path.exists(test_image):
        predictions_json = predict_image(test_image)
        print(predictions_json)
        show_prediction(test_image)
    else:
        print(f"Test image not found at {test_image}")
        # Create a dummy test image for demonstration if it doesn't exist
        import numpy as np

        dummy_image = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(
            dummy_image,
            "Please replace with a real image",
            (50, 240),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (255, 255, 255),
            2,
        )
        test_image_dir = os.path.dirname(test_image)
        if not os.path.exists(test_image_dir):
            os.makedirs(test_image_dir)
        cv2.imwrite(test_image, dummy_image)
        print(f"Created a dummy test image at {test_image}")
        predictions_json = predict_image(test_image)
        print(predictions_json)
        show_prediction(test_image)


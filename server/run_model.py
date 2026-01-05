import sys
import os
import argparse

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from model.inference.predict_image import predict_image


def main():
    """
    This script takes an image path as input, runs the prediction model on it,
    and prints the prediction results as a JSON string to standard output.
    """
    parser = argparse.ArgumentParser(
        description="Run model inference on an image and get the output."
    )
    parser.add_argument(
        "image_path", type=str, help="The full path to the image to process."
    )
    args = parser.parse_args()

    if not os.path.exists(args.image_path):
        print(f'{{"error": "Image not found at {args.image_path}"}}')
        sys.exit(1)

    try:
        predictions_json = predict_image(args.image_path)
        print(predictions_json)
    except Exception as e:
        print(f'{{"error": "An error occurred during prediction: {str(e)}"}}')
        sys.exit(1)


if __name__ == "__main__":
    main()

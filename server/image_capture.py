import cv2
import os
import time
import subprocess
import sys


def capture_and_predict():
    """
    Captures an image from the webcam, saves it, and runs the model inference
    script as a background process
        """
    
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Error: Could not open webcam.", file=sys.stderr)
        return

    ret, frame = cap.read()
    cap.release()

    if not ret:
        print("Error: Could not read frame from webcam.", file=sys.stderr)
        return

    # --- 2. Save the Image ---
    # Create the directory if it doesn't exist
    save_dir = os.path.join(os.path.dirname(__file__), "captured_images")
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    # Generate a unique filename with a timestamp
    timestamp = int(time.time())
    filename = f"capture_{timestamp}.png"
    image_path = os.path.join(save_dir, filename)

    # Save the captured frame to the file
    cv2.imwrite(image_path, frame)
    print(f"Image captured and saved to {image_path}")

    # --- 3. Run the Model in the Background ---
    # Get the path to the run_model.py script
    run_model_script_path = os.path.join(os.path.dirname(__file__), "run_model.py")
    
    # Get the python interpreter path
    python_executable = sys.executable

    # Command to execute the script
    command = [python_executable, run_model_script_path, image_path]

    try:
        # Execute the script as a background process
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True, # To make it a true background process
        )
        print(
            f"Started model inference in the background (PID: {process.pid})."
        )
        # We can optionally wait for the process and get output for debugging
        # stdout, stderr = process.communicate()
        # print("Model Output:", stdout)
        # if stderr:
        #     print("Model Error:", stderr)

    except FileNotFoundError:
        print(
            f"Error: Could not find the script '{run_model_script_path}'.",
            file=sys.stderr,
        )
    except Exception as e:
        print(f"An error occurred while running the model: {e}", file=sys.stderr)


if __name__ == "__main__":
    capture_and_predict()

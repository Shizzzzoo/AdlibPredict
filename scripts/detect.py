import cv2
import time
import threading
from pymavlink import mavutil

# ==========================================
# CONFIGURATION
# ==========================================
# Drone 1 RTSP URL (Replace with actual URL)
RTSP_URL = "rtsp://192.168.1.100:8554/stream"

# Mission Planner UDP Mirror Port (Setup in Ctrl+F > MAVLink > Local Port)
MAV_CONNECTION_STRING = "udp:127.0.0.1:14550"

# Target Drone System ID (The Scout Drone)
TARGET_SYSID = 1

# AI Check Interval (Seconds)
CHECK_INTERVAL = 0.5 

# ==========================================
# CLASS 1: THE VIDEO JANITOR (Thread A)
# ==========================================
class VideoStream:
    def __init__(self, rtsp_url):
        # GStreamer Pipeline: Low latency, drop frames if late
        self.gst_pipeline = (
            f"rtspsrc location={rtsp_url} latency=0 buffer-mode=0 ! "
            "rtph264depay ! h264parse ! avdec_h264 ! "
            "videoconvert ! appsink drop=true sync=false"
        )

        # Initialize OpenCV with GStreamer backend
        self.cap = cv2.VideoCapture(self.gst_pipeline, cv2.CAP_GSTREAMER)
        self.frame = None
        self.running = True
        self.lock = threading.Lock()

        if not self.cap.isOpened():
            print("Error: Could not open RTSP stream.")
            exit()

        # Start the background thread
        self.thread = threading.Thread(target=self.update, args=())
        self.thread.daemon = True
        self.thread.start()

    def update(self):
        """Constantly grabs frames to keep buffer empty"""
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                with self.lock:
                    self.frame = frame
            else:
                # If stream drops, try to reconnect or just wait
                time.sleep(0.1)

    def read(self):
        """Returns the absolute latest frame"""
        with self.lock:
            return self.frame if self.frame is not None else None

    def stop(self):
        self.running = False
        self.thread.join()
        self.cap.release()

# ==========================================
# CLASS 2: THE GPS LISTENER (Thread B)
# ==========================================
class DroneTelemetry:
    def __init__(self, connection_string, target_sysid):
        self.connection = mavutil.mavlink_connection(connection_string)
        self.target_sysid = target_sysid
        self.latest_lat = 0
        self.latest_lon = 0
        self.latest_alt = 0
        self.running = True

        # Start background thread
        self.thread = threading.Thread(target=self.monitor_messages, args=())
        self.thread.daemon = True
        self.thread.start()

    def monitor_messages(self):
        """Listens for GLOBAL_POSITION_INT from specific drone"""
        print(f"Listening for MAVLink on {MAV_CONNECTION_STRING}...")
        while self.running:
            # Wait for a 'GLOBAL_POSITION_INT' message
            msg = self.connection.recv_match(type='GLOBAL_POSITION_INT', blocking=True)
            
            # Filter: Ensure message comes from Drone 1
            if msg and msg.get_srcSystem() == self.target_sysid:
                self.latest_lat = msg.lat / 1e7  # Convert to degrees
                self.latest_lon = msg.lon / 1e7
                self.latest_alt = msg.relative_alt / 1000  # Convert to meters

    def get_location(self):
        return self.latest_lat, self.latest_lon, self.latest_alt

    def stop(self):
        self.running = False
        self.thread.join()

# ==========================================
# LOGIC: THE AI HANDLER
# ==========================================
def run_detection_model(frame):
    """
    PLACEHOLDER: Replace this with your YOLO/TensorFlow logic.
    Returns True if human detected, else False.
    """
    # For testing: Let's pretend we found a human if the image is mostly bright
    # Replace this entire block with: 
    # results = model(frame)
    # return len(results) > 0
    return False 

# ==========================================
# MAIN LOOP
# ==========================================
if __name__ == "__main__":
    # 1. Start Telemetry Thread
    telemetry = DroneTelemetry(MAV_CONNECTION_STRING, TARGET_SYSID)
    
    # 2. Start Video Thread
    print(f"Connecting to video: {RTSP_URL}...")
    video = VideoStream(RTSP_URL)
    
    # Wait a moment for streams to stabilize
    time.sleep(2)
    print("System Active. Press 'q' to quit.")

    last_check_time = time.time()

    try:
        while True:
            current_time = time.time()
            frame = video.read()

            if frame is None:
                continue

            # Display the video feed
            display_frame = frame.copy()

            # --- THE AI CHECK LOOP (Runs every 0.5 - 1.0s) ---
            if current_time - last_check_time > CHECK_INTERVAL:
                
                # Run AI on the FRESH frame
                human_detected = run_detection_model(frame) 

                if human_detected:
                    # FETCH GPS INSTANTLY
                    lat, lon, alt = telemetry.get_location()
                    
                    print(f"!!! TARGET DETECTED !!!")
                    print(f"Coordinates: {lat}, {lon} | Alt: {alt}m")
                    print(f"ACTION: Enter these into Mission Planner for Drone 2")
                    print("-" * 30)

                    # Draw red box and text on screen for operator
                    cv2.putText(display_frame, f"TARGET: {lat:.6f}, {lon:.6f}", 
                               (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
                    
                    # Optional: Save image to disk
                    # cv2.imwrite(f"detection_{time.time()}.jpg", frame)

                last_check_time = current_time

            # Show the feed
            cv2.imshow("Drone 1 Scout Feed", display_frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except KeyboardInterrupt:
        print("Stopping...")

    finally:
        video.stop()
        telemetry.stop()
        cv2.destroyAllWindows()

import os
import time

import gi
gi.require_version("Gst", "1.0")
gi.require_version("GstRtspServer", "1.0")
from gi.repository import Gst, GLib, GstRtspServer

Gst.init(None)

SHM_STR = "/tmp/rtsp_server_cam_str.sock"
RTSP_PORT = 8554
VIDEO_WIDTH = 1280
VIDEO_HEIGHT = 720
VIDEO_FPS = 30
VIDEO_BITRATE = 2000  # in kbps


class RTSPWorker:
    def __init__(self, shm_socket, rtsp_port, video_width, video_height, video_fps, video_bitrate):
        self.shm_socket = shm_socket
        self.rtsp_port = rtsp_port
        self.video_width = video_width
        self.video_height = video_height
        self.video_fps = video_fps
        self.video_bitrate = video_bitrate
        self.server = None
        self.loop = None

    def _make_factory(self):
        factory = GstRtspServer.RTSPMediaFactory()
        launch_str = f"""
        ( shmsrc socket-path={self.shm_socket} is-live=true do-timestamp=true
          ! video/x-raw,format=I420,width={self.video_width},height={self.video_height},framerate={self.video_fps}/1
          ! x264enc threads=2 bitrate={self.video_bitrate} tune=zerolatency speed-preset=ultrafast key-int-max={self.video_fps} pass=cbr
          ! video/x-h264,profile=baseline
          ! h264parse config-interval=1
          ! rtph264pay name=pay0 pt=96 )
        """
        factory.set_launch(launch_str)
        factory.set_shared(True)
        return factory

    def run(self):
        try:
            print(f"Waiting for shared memory socket: {self.shm_socket}")
            for _ in range(100):
                if os.path.exists(self.shm_socket):
                    break
                time.sleep(0.05)
            else:
                raise RuntimeError(f"SHM socket {self.shm_socket} never appeared")

            print(f"Starting RTSP server on port {self.rtsp_port}")
            self.server = GstRtspServer.RTSPServer()
            self.server.set_service(str(self.rtsp_port))
            mounts = self.server.get_mount_points()
            mounts.add_factory("/live", self._make_factory())
            self.server.attach(None)

            print(f"RTSP server started successfully!")
            print(f"Stream available at: rtsp://<your-ip>:{self.rtsp_port}/live")

            self.loop = GLib.MainLoop()
            self.loop.run()
        except Exception as e:
            print(f"Error starting RTSP server: {e}")

    def stop(self):
        if self.loop:
            self.loop.quit()


def main():
    shm_socket = os.getenv("SHM_SOCKET", SHM_STR)
    rtsp_port = int(os.getenv("RTSP_PORT", RTSP_PORT))
    video_width = int(os.getenv("VIDEO_WIDTH", VIDEO_WIDTH))
    video_height = int(os.getenv("VIDEO_HEIGHT", VIDEO_HEIGHT))
    video_fps = int(os.getenv("VIDEO_FPS", VIDEO_FPS))
    video_bitrate = int(os.getenv("VIDEO_BITRATE", VIDEO_BITRATE))

    worker = RTSPWorker(
        shm_socket=shm_socket,
        rtsp_port=rtsp_port,
        video_width=video_width,
        video_height=video_height,
        video_fps=video_fps,
        video_bitrate=video_bitrate
    )

    try:
        worker.run()
    except KeyboardInterrupt:
        print("\nShutting down RTSP server...")
        worker.stop()


if __name__ == "__main__":
    main()

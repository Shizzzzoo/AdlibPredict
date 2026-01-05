#!/usr/bin/env python3

import os
import sys
import time
import signal
import multiprocessing as mp

import gi
gi.require_version("Gst", "1.0")
gi.require_version("GstRtspServer", "1.0")
from gi.repository import Gst, GLib, GstRtspServer

Gst.init(None)


SHM_SOCKET = "/tmp/rtsp_server_cam_str.sock"
RTSP_PORT = 8554
CAMERA_DEVICE = "/dev/video0"
VIDEO_WIDTH = 1280
VIDEO_HEIGHT = 720
VIDEO_FPS = 30
VIDEO_BITRATE = 2000


class CameraFeeder:
    """Captures video from camera and writes to shared memory"""
    def __init__(self, camera_dev, shm_socket, video_width, video_height, video_fps):
        self.camera_dev = camera_dev
        self.shm_socket = shm_socket
        self.video_width = video_width
        self.video_height = video_height
        self.video_fps = video_fps
        self.pipeline = None
        self.loop = None

    def _make_pipeline(self):
        try:
            if os.path.exists(self.shm_socket):
                os.unlink(self.shm_socket)
        except Exception as e:
            print(f"Warning: Could not remove old socket: {e}")

        pipeline_str = f"""
        v4l2src device={self.camera_dev} io-mode=2
        ! image/jpeg,framerate={self.video_fps}/1
        ! jpegdec
        ! videorate max-rate={self.video_fps} drop-only=true
        ! videoscale
        ! videoconvert
        ! video/x-raw,format=I420,width={self.video_width},height={self.video_height},framerate={self.video_fps}/1,pixel-aspect-ratio=1/1
        ! shmsink socket-path={self.shm_socket} wait-for-connection=false sync=false async=false shm-size=33554432
        """

        pipeline = Gst.parse_launch(pipeline_str)
        bus = pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self._on_bus_message)
        return pipeline

    def _on_bus_message(self, bus, msg):
        if msg.type == Gst.MessageType.ERROR:
            err, debug = msg.parse_error()
            print(f"Camera Feeder Error: {err}, {debug}")
            if self.loop:
                self.loop.quit()
        elif msg.type == Gst.MessageType.EOS:
            print("Camera feeder received EOS")
            if self.loop:
                self.loop.quit()

    def run(self):
        try:
            print(f"Starting camera feeder from {self.camera_dev}")
            self.pipeline = self._make_pipeline()
            self.loop = GLib.MainLoop()

            ret = self.pipeline.set_state(Gst.State.PLAYING)
            if ret == Gst.StateChangeReturn.FAILURE:
                raise RuntimeError("Failed to start camera pipeline")

            print(f"Camera feeder started, writing to {self.shm_socket}")
            self.loop.run()
        except Exception as e:
            print(f"Camera feeder error: {e}")
        finally:
            if self.pipeline:
                self.pipeline.set_state(Gst.State.NULL)

    def stop(self):
        if self.pipeline:
            self.pipeline.send_event(Gst.Event.new_eos())
        time.sleep(0.5)
        if self.loop:
            self.loop.quit()


class RTSPWorker:
    """RTSP server that reads from shared memory"""
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
            for i in range(100):
                if os.path.exists(self.shm_socket):
                    print(f"Socket found after {i * 0.05:.2f}s")
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

            print(f"✓ RTSP server started successfully!")
            print(f"✓ Stream available at: rtsp://localhost:{self.rtsp_port}/live")
            print(f"  Test with: ffplay rtsp://localhost:{self.rtsp_port}/live")

            self.loop = GLib.MainLoop()
            self.loop.run()
        except Exception as e:
            print(f"Error starting RTSP server: {e}")

    def stop(self):
        if self.loop:
            self.loop.quit()


def camera_feeder_process(camera_dev, shm_socket, video_width, video_height, video_fps):
    """Process function for camera feeder"""
    feeder = CameraFeeder(camera_dev, shm_socket, video_width, video_height, video_fps)
    feeder.run()


def rtsp_server_process(shm_socket, rtsp_port, video_width, video_height, video_fps, video_bitrate):
    """Process function for RTSP server"""
    server = RTSPWorker(shm_socket, rtsp_port, video_width, video_height, video_fps, video_bitrate)
    server.run()


def main():
    camera_dev = os.getenv("CAMERA_DEVICE", CAMERA_DEVICE)
    shm_socket = os.getenv("SHM_SOCKET", SHM_SOCKET)
    rtsp_port = int(os.getenv("RTSP_PORT", RTSP_PORT))
    video_width = int(os.getenv("VIDEO_WIDTH", VIDEO_WIDTH))
    video_height = int(os.getenv("VIDEO_HEIGHT", VIDEO_HEIGHT))
    video_fps = int(os.getenv("VIDEO_FPS", VIDEO_FPS))
    video_bitrate = int(os.getenv("VIDEO_BITRATE", VIDEO_BITRATE))

    print("=" * 60)
    print("RTSP Server with Camera Feeder")
    print("=" * 60)
    print(f"Camera: {camera_dev}")
    print(f"Resolution: {video_width}x{video_height} @ {video_fps}fps")
    print(f"Bitrate: {video_bitrate} kbps")
    print(f"RTSP Port: {rtsp_port}")
    print("=" * 60)

    mp.set_start_method("fork", force=True)

    feeder_proc = mp.Process(
        target=camera_feeder_process,
        args=(camera_dev, shm_socket, video_width, video_height, video_fps),
        name="camera_feeder"
    )

    rtsp_proc = mp.Process(
        target=rtsp_server_process,
        args=(shm_socket, rtsp_port, video_width, video_height, video_fps, video_bitrate),
        name="rtsp_server"
    )

    def signal_handler(sig, frame):
        print("\n\nShutting down...")
        feeder_proc.terminate()
        rtsp_proc.terminate()
        time.sleep(1)
        if feeder_proc.is_alive():
            feeder_proc.kill()
        if rtsp_proc.is_alive():
            rtsp_proc.kill()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        feeder_proc.start()
        time.sleep(1)
        rtsp_proc.start()

        feeder_proc.join()
        rtsp_proc.join()

    except KeyboardInterrupt:
        print("\nInterrupted by user")
    finally:
        if feeder_proc.is_alive():
            feeder_proc.terminate()
        if rtsp_proc.is_alive():
            rtsp_proc.terminate()

        feeder_proc.join(timeout=2)
        rtsp_proc.join(timeout=2)


if __name__ == "__main__":
    main()

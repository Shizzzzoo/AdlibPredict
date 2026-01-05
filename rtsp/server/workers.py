#!/usr/bin/env python3
# Two pipelines via SHM: feeder→(recorder, streamer).

from __future__ import annotations
import multiprocessing as _mp
_mp.set_start_method("fork", force=True)


import os
import threading
import time
from datetime import datetime
from multiprocessing import Process, Queue
from pathlib import Path
from queue import Empty
from typing import Self

import gi
import numpy as np
from PIL import Image as PILImage

gi.require_version("Gst", "1.0")
gi.require_version("GstRtspServer", "1.0")
from gi.repository import Gst, GLib, GstRtspServer

from server.core import DroneConfig

Gst.init(None)

# ---- types ----
type MessagePkt = dict[str, object]
type MessageQueue = Queue[MessagePkt]

# SHM sockets
SHM_REC: str = "/tmp/drone_cam_rec.sock"
SHM_STR: str = "/tmp/drone_cam_str.sock"


# FEEDER (single camera)
class CameraFeeder:
    def __init__(self: Self, config: DroneConfig, statq: (MessageQueue | None) = None) -> None:
        self.config = config
        self.statq = statq
        self.pipeline: (Gst.Pipeline | None) = None
        self.loop: (GLib.MainLoop | None) = None

    def _mkpipe(self: Self) -> Gst.Pipeline:
        for s in (SHM_REC, SHM_STR):
            try:
                if os.path.exists(s):
                    os.unlink(s)
            except Exception:
                pass

        elements = f"""
        v4l2src device={self.config.camera_dev} io-mode=2
        ! image/jpeg,framerate={self.config.video_fps}/1
        ! jpegdec
        ! videorate max-rate={self.config.video_fps} drop-only=true
        ! videoscale
        ! videoconvert
        ! video/x-raw,format=I420,width={self.config.video_width},height={self.config.video_height},framerate={self.config.video_fps}/1,pixel-aspect-ratio=1/1
        ! tee name=t allow-not-linked=true

        t. ! queue max-size-buffers=20 max-size-time=2000000000
        ! shmsink socket-path={SHM_REC} wait-for-connection=false sync=false async=false shm-size=33554432

        t. ! queue max-size-buffers=20 max-size-time=2000000000
        ! shmsink socket-path={SHM_STR} wait-for-connection=false sync=false async=false shm-size=33554432
        """


        p = Gst.parse_launch(elements)
        bus = p.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self._busmsg)
        return p

    def _busmsg(self: Self, _bus, msg) -> None:
        if msg.type in (Gst.MessageType.EOS, Gst.MessageType.ERROR):
            if self.loop:
                self.loop.quit()

    def run(self: Self) -> None:
        try:
            self.pipeline = self._mkpipe()
            self.loop = GLib.MainLoop()
            if self.pipeline.set_state(Gst.State.PLAYING) == Gst.StateChangeReturn.FAILURE:
                raise RuntimeError("feeder pipeline failed")
            if self.statq:
                try:
                    self.statq.put_nowait({"worker": "feeder", "status": "camera feeder started"})
                except Exception:
                    pass
            self.loop.run()
        except Exception:
            pass
        finally:
            if self.pipeline:
                self.pipeline.set_state(Gst.State.NULL)

    def stop(self: Self) -> None:
        try:
            if self.pipeline:
                self.pipeline.send_event(Gst.Event.new_eos())
            time.sleep(0.5)
        except Exception:
            pass
        if self.loop:
            self.loop.quit()


#RECORDER (5s chunks + 1 FPS images)
class RecorderWorker:
    def __init__(self: Self, config: DroneConfig, statq: (MessageQueue | None) = None) -> None:
        self.config = config
        self.statq = statq
        self.pipeline: (Gst.Pipeline | None) = None
        self.loop: (GLib.MainLoop | None) = None
        self.vidcount = 0
        self.imgcount = 0
        self.lastframe = 0.0
        self.frameq: Queue[dict[str, object]] = Queue(maxsize=2)
        config.setup_storage()

    def _genfile(self: Self, idx: int, ext: str) -> str:
        now = datetime.now()
        return f"{idx:09d}-[{now.strftime('%d.%m.%Y')}]({now.strftime('%H:%M:%S')}).{ext}"

    def _vidfile(self: Self) -> str:
        self.vidcount += 1
        return self._genfile(self.vidcount, "mp4")

    def _imgfile(self: Self) -> str:
        self.imgcount += 1
        return self._genfile(self.imgcount, "jpg")

    def _mkpipe(self: Self) -> Gst.Pipeline:
        base_pattern = str(self.config.archive_video / "%09d-[chunk].mp4")
        keyframe_interval = 17
        chunk_time_ns = 5_500_000_000

        elements = f"""
        shmsrc socket-path={SHM_REC} is-live=true do-timestamp=true
        ! video/x-raw,format=I420,width=1280,height=720,framerate={self.config.video_fps}/1
        ! tee name=t allow-not-linked=true

        t. ! queue max-size-buffers=100 max-size-time=6000000000
           ! x264enc threads=2 bitrate=4000 tune=zerolatency speed-preset=ultrafast key-int-max={keyframe_interval} pass=cbr
           ! video/x-h264,profile=baseline
           ! h264parse
           ! splitmuxsink name=splitter location={base_pattern} max-size-time={chunk_time_ns} muxer-factory=mp4mux async-finalize=true

        t. ! queue max-size-buffers=20 max-size-time=2000000000
           ! videoscale method=0
           ! videoconvert
           ! video/x-raw,format=RGB
           ! videorate skip-to-first=true
           ! video/x-raw,framerate=1/1
           ! appsink name=imgsink emit-signals=true max-buffers=2 drop=false sync=false
        """
        p = Gst.parse_launch(elements)
        bus = p.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self._busmsg)

        splitter = p.get_by_name("splitter")
        if splitter:
            splitter.connect("format-location", self._saveform)

        appsink = p.get_by_name("imgsink")
        if appsink:
            appsink.connect("new-sample", self._qframe)

        return p

    def _busmsg(self: Self, _bus, msg) -> None:
        if msg.type in (Gst.MessageType.EOS, Gst.MessageType.ERROR):
            if self.loop:
                self.loop.quit()

    def _saveform(self: Self, _splitter, fragment_id) -> str:
        try:
            path = self.config.archive_video / self._vidfile()

            for _ in range(50):  # ~0.5 seconds
                try:
                    if path.exists() and path.stat().st_size > 0:
                        break
                except Exception:
                    pass
                time.sleep(0.01)

            link = self.config.temp_path / "latest_video.mp4"
            try:
                if link.exists() or link.is_symlink():
                    link.unlink()
                link.symlink_to(path)
            except Exception:
                pass

            if self.statq:
                try:
                    self.statq.put_nowait({"worker": "recorder", "video_chunk": path.name})
                except Exception:
                    pass

            return str(path)

        except Exception:
            return str(self.config.archive_video / f"error-{fragment_id}.mp4")


    def _qframe(self: Self, appsink) -> int:
        sample = appsink.emit("pull-sample")
        if not sample:
            return int(Gst.FlowReturn.OK)

        now = time.time()
        if now - self.lastframe < 0.9:
            return int(Gst.FlowReturn.OK)
        self.lastframe = now

        try:
            buf = sample.get_buffer()
            caps = sample.get_caps()
            ok, info = buf.map(Gst.MapFlags.READ)
            if not ok:
                return int(Gst.FlowReturn.OK)

            w = caps.get_structure(0).get_value("width")
            h = caps.get_structure(0).get_value("height")
            data = np.frombuffer(info.data, dtype=np.uint8).reshape((h, w, 3)).copy()
            buf.unmap(info)

            try:
                self.frameq.put_nowait({"data": data, "timestamp": now})
            except Exception:
                pass
        except Exception:
            pass
        return int(Gst.FlowReturn.OK)

    def _compress(self: Self) -> None:
        while True:
            try:
                frame = self.frameq.get(timeout=2.0)
                if frame is None:
                    break
                path = self.config.archive_image / self._imgfile()
                PILImage.fromarray(frame["data"], mode="RGB").save(
                    path, "JPEG", quality=self.config.image_quality, optimize=False
                )
                link = self.config.temp_path / "latest_image.jpg"
                try:
                    if link.exists() or link.is_symlink():
                        link.unlink()
                    link.symlink_to(path)
                except Exception:
                    pass
                if self.statq:
                    try:
                        self.statq.put_nowait({"worker": "recorder", "image_file": path.name})
                    except Exception:
                        pass
            except Empty:
                continue
            except Exception:
                pass

    def run(self: Self) -> None:
        try:
            for _ in range(100):
                if os.path.exists(SHM_REC):
                    break
                time.sleep(0.05)
            else:
                raise RuntimeError(f"SHM socket {SHM_REC} never appeared")

            threading.Thread(target=self._compress, daemon=True).start()
            self.pipeline = self._mkpipe()
            self.loop = GLib.MainLoop()
            if self.pipeline.set_state(Gst.State.PLAYING) == Gst.StateChangeReturn.FAILURE:
                raise RuntimeError("recorder pipeline failed")
            if self.statq:
                try:
                    self.statq.put_nowait({"worker": "recorder", "status": "recorder started"})
                except Exception:
                    pass
            self.loop.run()
        except Exception:
            pass
        finally:
            try:
                self.frameq.put_nowait(None)
            except Exception:
                pass
            if self.pipeline:
                self.pipeline.set_state(Gst.State.NULL)

    def stop(self: Self) -> None:
        try:
            if self.pipeline:
                self.pipeline.send_event(Gst.Event.new_eos())
            time.sleep(0.5)
        except Exception:
            pass
        if self.loop:
            self.loop.quit()


# STREAMER (RTP/UDP)
class StreamWorker:
    def __init__(self: Self, config: DroneConfig, statq: (MessageQueue | None) = None) -> None:
        self.config = config
        self.statq = statq
        self.pipeline: (Gst.Pipeline | None) = None
        self.loop: (GLib.MainLoop | None) = None

    def _mkpipe(self: Self) -> Gst.Pipeline:
        target = self.config.get_stream_target()
        mcast = ""
        if self.config.cast_type == "multicast":
            mcast = f"auto-multicast=true ttl={self.config.ttl}"
        elif self.config.cast_type == "broadcast":
            mcast = "broadcast=true"

        rtp_port = int(self.config.port)
        rtcp_port_tx = rtp_port + 1   # send RTCP to receiver
        rtcp_port_rx = rtp_port + 5   # listen RTCP from receiver

        elements = f"""
        rtpbin name=rtpbin

        shmsrc socket-path={SHM_STR} is-live=true do-timestamp=true
        ! queue leaky=downstream max-size-buffers=0 max-size-time=0 max-size-bytes=0
        ! video/x-raw,format=I420,width={self.config.video_width},height={self.config.video_height},framerate={self.config.video_fps}/1
        ! x264enc threads=1 bitrate={self.config.video_bitrate // 1000} tune=zerolatency speed-preset=ultrafast key-int-max={self.config.video_fps} pass=cbr
        ! video/x-h264,profile=baseline
        ! h264parse config-interval=1
        ! rtph264pay pt=96 mtu=1400
        ! rtpbin.send_rtp_sink_0

        rtpbin.send_rtp_src_0
        ! udpsink host={target} port={rtp_port} sync=false async=false {mcast}

        udpsrc port={rtcp_port_rx}
        ! rtpbin.recv_rtcp_sink_0

        rtpbin.send_rtcp_src_0
        ! udpsink host={target} port={rtcp_port_tx} sync=false async=false {mcast}
        """

        p = Gst.parse_launch(elements)
        bus = p.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self._busmsg)
        return p

    def _busmsg(self: Self, _bus, msg) -> None:
        if msg.type in (Gst.MessageType.EOS, Gst.MessageType.ERROR):
            if self.loop:
                self.loop.quit()

    def run(self: Self) -> None:
        try:
            for _ in range(100):
                if os.path.exists(SHM_STR):
                    break
                time.sleep(0.05)
            else:
                raise RuntimeError(f"SHM socket {SHM_STR} never appeared")

            self.pipeline = self._mkpipe()
            self.loop = GLib.MainLoop()
            if self.pipeline.set_state(Gst.State.PLAYING) == Gst.StateChangeReturn.FAILURE:
                raise RuntimeError("stream pipeline failed")
            if self.statq:
                try:
                    self.statq.put_nowait({"worker": "stream", "status": "stream started"})
                except Exception:
                    pass
            self.loop.run()
        except Exception:
            pass
        finally:
            if self.pipeline:
                self.pipeline.set_state(Gst.State.NULL)

    def stop(self: Self) -> None:
        try:
            if self.pipeline:
                self.pipeline.send_event(Gst.Event.new_eos())
            time.sleep(0.5)
        except Exception:
            pass
        if self.loop:
            self.loop.quit()


# RTSP SERVER
class RTSPWorker:
    def __init__(self: Self, config: DroneConfig, statq: (MessageQueue | None) = None) -> None:
        self.config = config
        self.statq = statq
        self.server: (GstRtspServer.RTSPServer | None) = None
        self.loop: (GLib.MainLoop | None) = None

    def _make_factory(self: Self) -> GstRtspServer.RTSPMediaFactory:
        factory = GstRtspServer.RTSPMediaFactory()
        launch_str = f"""
        ( shmsrc socket-path={SHM_STR} is-live=true do-timestamp=true
          ! video/x-raw,format=I420,width={self.config.video_width},height={self.config.video_height},framerate={self.config.video_fps}/1
          ! x264enc threads=2 bitrate={self.config.video_bitrate // 1000} tune=zerolatency speed-preset=ultrafast key-int-max={self.config.video_fps} pass=cbr
          ! video/x-h264,profile=baseline
          ! h264parse config-interval=1
          ! rtph264pay name=pay0 pt=96 )
        """
        factory.set_launch(launch_str)
        factory.set_shared(True)
        return factory

    def run(self: Self) -> None:
        try:
            for _ in range(100):
                if os.path.exists(SHM_STR):
                    break
                time.sleep(0.05)
            else:
                raise RuntimeError(f"SHM socket {SHM_STR} never appeared")

            self.server = GstRtspServer.RTSPServer()
            self.server.set_service(str(self.config.rtsp_port))
            mounts = self.server.get_mount_points()
            mounts.add_factory("/live", self._make_factory())
            self.server.attach(None)

            if self.statq:
                try:
                    self.statq.put_nowait({"worker": "rtsp", "status": f"RTSP server started on port {self.config.rtsp_port}"})
                except Exception:
                    pass

            self.loop = GLib.MainLoop()
            self.loop.run()
        except Exception:
            pass

    def stop(self: Self) -> None:
        if self.loop:
            self.loop.quit()


# PROCESS LAUNCHER
def _spawn(target, name: str) -> Process:
    p = Process(target=target, name=name, daemon=False)
    p.start()
    return p

def start_camera(config: DroneConfig, statq: (MessageQueue | None) = None) -> list[Process]:
    procs: list[Process] = []

    def feeder_main() -> None:
        w = CameraFeeder(config, statq)
        w.run()

    def recorder_main() -> None:
        w = RecorderWorker(config, statq)
        w.run()

    def stream_main() -> None:
        w = StreamWorker(config, statq)
        w.run()

    def rtsp_main() -> None:
        w = RTSPWorker(config, statq)
        w.run()

    if any([config.video_mode, config.image_mode, config.stream_mode, config.rtsp_mode]):
        procs.append(_spawn(feeder_main, "camera_feeder"))

    if config.video_mode or config.image_mode:
        procs.append(_spawn(recorder_main, "recorder_worker"))

    if config.stream_mode:
        procs.append(_spawn(stream_main, "stream_worker"))

    if config.rtsp_mode:
        procs.append(_spawn(rtsp_main, "rtsp_worker"))

    return procs

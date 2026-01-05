#!/usr/bin/env python3
# env var configuration management for DroneConfig

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal, Self


type Flag = bool
type IP = str
type Port = int
type TTL = int
type CastType = Literal["unicast", "multicast", "broadcast"]


class DroneConfig:

    def __init__(
        self: Self,
        *,
        stream_mode: Flag = True,
        video_mode: Flag = True,
        image_mode: Flag = True,
        rtsp_mode: Flag = True,

        cast_type: CastType = "unicast",
        target_ip: IP = "192.168.1.100",
        multicast_ip: IP = "224.1.1.1",
        port: Port = 5000,
        rtsp_port: Port = 8554,
        ttl: TTL = 16,

        camera_dev: str = "/dev/video0",
        video_bitrate: int = 2_000_000,
        video_fps: int = 30,
        video_width: int = 1280,
        video_height: int = 720,
        image_quality: int = 95,

        storage_path: (str | Path) = "/mnt/ssd",

    ) -> None:

        self.stream_mode: Flag = stream_mode
        self.video_mode: Flag = video_mode
        self.image_mode: Flag = image_mode
        self.rtsp_mode: Flag = rtsp_mode

        self.cast_type: CastType = cast_type
        self.target_ip: IP = target_ip
        self.multicast_ip: IP = multicast_ip
        self.port: Port = port
        self.rtsp_port: Port = rtsp_port
        self.ttl: TTL = ttl

        self.camera_dev: str = camera_dev
        self.video_bitrate: int = video_bitrate
        self.video_fps: int = video_fps
        self.video_width: int = video_width
        self.video_height: int = video_height
        self.image_quality: int = image_quality

        self.storage_path: Path = Path(storage_path)
        self.archive_video: Path = self.storage_path / "drone_archive" / "videos"
        self.archive_image: Path = self.storage_path / "drone_archive" / "images"
        self.temp_path: Path = self.storage_path / "drone_temp"


    @classmethod
    def from_env(cls: type[Self]) -> Self:
        def getb(k: str, d: Flag) -> Flag:
            v = os.getenv(k, "").lower()
            return v in ("1", "true", "yes", "on") if v else d

        def geti(k: str, d: int) -> int:
            try:
                return int(os.getenv(k, str(d)))
            except Exception:
                return d

        v = os.getenv("CAST_TYPE", "unicast").lower()
        ct: CastType = v if v in ("unicast", "multicast", "broadcast") else "unicast"  # type: ignore[assignment]

        return cls(
            stream_mode=getb("ENABLE_STREAM", True),
            video_mode=getb("ENABLE_VIDEO", True),
            image_mode=getb("ENABLE_IMAGES", True),
            rtsp_mode=getb("ENABLE_RTSP", True),

            cast_type=ct,
            target_ip=os.getenv("TARGET_IP", "192.168.1.100"),
            multicast_ip=os.getenv("MULTICAST_IP", "224.1.1.1"),
            port=geti("PORT", 5000),
            rtsp_port=geti("RTSP_PORT", 8554),
            ttl=geti("TTL", 16),

            camera_dev=os.getenv("CAMERA", "/dev/video0"),
            video_bitrate=geti("VIDEO_BITRATE", 2_000_000),
            video_fps=geti("VIDEO_FPS", 30),
            video_width=geti("VIDEO_WIDTH", 1280),
            video_height=geti("VIDEO_HEIGHT", 720),
            image_quality=geti("IMAGE_QUALITY", 95),

            storage_path=os.getenv("SSD_PATH", "/mnt/ssd"),
        )


    def get_stream_target(self: Self) -> IP:
        return {
            "broadcast": "255.255.255.255",
            "multicast": self.multicast_ip,
        }.get(self.cast_type, self.target_ip)


    def setup_storage(self: Self) -> None:
        for p in (self.archive_video, self.archive_image, self.temp_path):
            p.mkdir(parents=True, exist_ok=True)


    def __str__(self: Self) -> str:
        return (
            f"DroneConfig:stream={self.stream_mode}, "
            f"video={self.video_mode}, "
            f"images={self.image_mode}, "
            f"rtsp={self.rtsp_mode}, "
            f"cast={self.cast_type}, "
            f"target={self.get_stream_target()}:{self.port}, "
            f"rtsp_port={self.rtsp_port}, "
            f"storage={self.storage_path}"
        )

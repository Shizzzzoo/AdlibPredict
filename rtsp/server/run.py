#!/usr/bin/env python3
# lifecycle manager for camera workers

from __future__ import annotations

import logging
import signal
import sys
import time
from multiprocessing import Process, Queue
from queue import Empty
from typing import Self

from server.core import DroneConfig
from server.workers import start_camera


type MessagePkt = dict[str, object]
type MessageQueue = Queue[MessagePkt]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class DroneController:
    def __init__(self: Self, config: DroneConfig) -> None:
        self.config = config
        self.procs: list[Process] = []
        self.statq: MessageQueue = Queue(maxsize=50)
        self._stop: bool = False
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    def _handle_signal(self: Self, _signum: int, _frame) -> None:
        self._stop = True

    def start(self: Self) -> None:
        self.config.setup_storage()
        active = sum([self.config.stream_mode, self.config.video_mode, self.config.image_mode, self.config.rtsp_mode])
        if active == 0:
            raise RuntimeError("no workers enabled")
        self.procs = start_camera(self.config, self.statq)

    def run(self: Self) -> None:
        try:
            while not self._stop:
                try:
                    while True:
                        stat = self.statq.get_nowait()
                        if "error" in stat:
                            logger.error(f"{stat.get('worker','')}: {stat['error']}")
                        elif "status" in stat:
                            logger.info(str(stat["status"]))
                        elif "video_chunk" in stat:
                            logger.info(f"chunk: {stat['video_chunk']}")
                        elif "image_file" in stat:
                            logger.info(f"image: {stat['image_file']}")
                except Empty:
                    pass
                time.sleep(0.1)
        except KeyboardInterrupt:
            pass
        finally:
            self._shutdown()

    def _shutdown(self: Self) -> None:
        for p in self.procs:
            try:
                if p.is_alive():
                    p.terminate()
            except Exception:
                pass
        for p in self.procs:
            try:
                p.join(timeout=5)
                if p.is_alive():
                    p.kill()
            except Exception:
                pass


def main() -> int:
    try:
        config = DroneConfig.from_env()
        controller = DroneController(config)
        controller.start()
        controller.run()
    except Exception as e:
        logger.exception(f"Fatal: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

import os
import sys

from pathlib import Path


COCO_DATASET = os.path.abspath(os.path.join(
  os.path.dirname(__file__),
  "./dataset/coco/data.yaml",
))
PRETRAINED_WEIGHTS_DIR = os.path.abspath(os.path.join(
  os.path.dirname(__file__),
  "./weights/pretrained/"
))
YOLO11M = os.path.abspath(os.path.join(
  os.path.dirname(__file__),
  "./weights/pretrained/yolo11m.pt"
))
RUNS_LOG_DIR = os.path.abspath(os.path.join(
  os.path.dirname(__file__),
  "./runs/detect/"
))

Path(PRETRAINED_WEIGHTS_DIR).mkdir(parents=True, exist_ok=True)
Path(RUNS_LOG_DIR).mkdir(parents=True, exist_ok=True)


from ultralytics.utils import SETTINGS
SETTINGS["weights_dir"] = PRETRAINED_WEIGHTS_DIR

from ultralytics import YOLO
model = YOLO(YOLO11M)
model.train(
  data=COCO_DATASET,
  epochs=500,
  batch=16,
  imgsz=640,
  plots=True,
  project=RUNS_LOG_DIR,
  name="train",
)

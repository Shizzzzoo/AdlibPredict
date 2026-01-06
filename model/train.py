import os
import sys

from ultralytics import YOLO

COCO_DATASET = os.path.abspath(os.path.join(
  os.path.dirname(__file__),
  "./dataset/coco/data.yaml",
))
WEIGHTS_PATH = os.path.abspath(os.path.join(
  os.path.dirname(__file__),
  "./weights/"
))
YOLO11M = os.path.abspath(os.path.join(
  WEIGHTS_PATH,
  "pretrained/yolo11m.pt"
))

model = YOLO(YOLO11M)
model.train(
  data=COCO_DATASET,
  epochs=500,
  imgsz=1024,
  plots=True,
  project=WEIGHTS_PATH,
  name="trainOne",
)

import os

from ultralytics import YOLO
from rich import print


root = os.path.dirname(__file__)
model = YOLO(
  os.path.join(
    root,
    "../model/weights/trained/yolov11m.pt",
  )
)
input_dir = os.path.join(
  root, "./images/inputs/"
)
samples = [
  os.path.join(
    input_dir,
    f
  ) for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f))
]
res = model(samples)

out_dir = os.path.join(root, "./images/outputs")
os.makedirs(out_dir, exist_ok=True)

for i, r in enumerate(res):
    if r.boxes is None or len(r.boxes) == 0:
      print("[yellow]No detections for image[/yellow]")
    out_path = os.path.join(out_dir, f"pred_{i}.png")
    r.save(filename=out_path)
    print(f"[green]Saved:[/green] {out_path}")

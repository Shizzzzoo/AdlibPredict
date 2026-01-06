import json
import os

from pathlib import Path
from rich import print

INPUT_JSON_PATH = os.path.abspath(os.path.join(
  os.path.dirname(__file__),
  "./dataset/json/data.json",
))
OUTPUT_COCO_PATH = os.path.abspath(os.path.join(
  os.path.dirname(__file__),
  "./dataset/coco/",
))

def convert_json_to_coco(
  input_json_path,
  output_coco_path,
):
  with open(input_json_path, "r") as f:
    ls_data = json.load(f)
  dataset_path = Path(output_coco_path)
  images_dir = dataset_path / "images" / "train"
  labels_dir = dataset_path / "labels" / "train"
  images_dir.mkdir(parents=True, exist_ok=True)
  labels_dir.mkdir(parents=True, exist_ok=True)
  print(ls_data.keys())
  categories = {
    cat["id"]: cat["name"] for cat in ls_data.get("categories", [])
  }
  annotations_by_image = {}
  for ann in ls_data.get("annotations", []):
    img_id = ann["image_id"]
    if img_id not in annotations_by_image:
      annotations_by_image[img_id] = []
    annotations_by_image[img_id].append(ann)
  for img in ls_data.get("images", []):
    img_id = img["id"]
    width = img["width"]
    height = img["height"]
    original_filename = os.path.basename(img["file_name"])
    base_name = os.path.splitext(original_filename)[0]
    label_file = labels_dir / f"{base_name}.txt"
    img_annotations = annotations_by_image.get(img_id, [])
    with open(label_file, 'w') as f:
      for ann in img_annotations:
        x, y, w, h = ann["bbox"]
        x_center = (x + w / 2) / width
        y_center = (y + h / 2) / height
        norm_width = w / width
        norm_height = h / height
        category_id = ann["category_id"]
        f.write(f"{category_id} {x_center:.6f} {y_center:.6f} {norm_width:.6f} {norm_height:.6f}\n")
    print(f"Created label file: {label_file.name} ({len(img_annotations)} annotations)")
  yaml_content = f"""# Dataset Configuration
path: {dataset_path.absolute()}
train: images/train

# Classes
names:
"""
  for cat_id in sorted(categories.keys()):
    yaml_content += f"  {cat_id}: {categories[cat_id]}\n"
  yaml_path = dataset_path / "data.yaml"
  with open(yaml_path, 'w') as f:
    f.write(yaml_content)


def main():
  convert_json_to_coco(
    INPUT_JSON_PATH,
    OUTPUT_COCO_PATH,
  )


if __name__ == "__main__":
  main()

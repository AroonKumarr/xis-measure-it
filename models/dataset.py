"""
dataset.py — PyTorch Dataset for XIS Measure It Phone Segmentation
===================================================================
Loads undistorted images and COCO format instance segmentation masks
for the phone object (class_id=1, label="phone").
"""

import json
from pathlib import Path
import cv2
import numpy as np
import torch
from torch.utils.data import Dataset


class PhoneCOCODataset(Dataset):
    """
    PyTorch Dataset loading images and COCO instance-segmentation annotations.
    """
    def __init__(self, images_dir: Path, annotations_json: Path, transforms=None):
        self.images_dir = Path(images_dir)
        self.transforms = transforms

        with open(annotations_json, "r", encoding="utf-8") as f:
            self.coco = json.load(f)

        # Index images
        self.images = self.coco["images"]
        self.img_id_to_index = {img["id"]: idx for idx, img in enumerate(self.images)}

        # Group annotations by image_id
        self.img_id_to_anns = {}
        for ann in self.coco["annotations"]:
            img_id = ann["image_id"]
            if img_id not in self.img_id_to_anns:
                self.img_id_to_anns[img_id] = []
            self.img_id_to_anns[img_id].append(ann)

    def __len__(self):
        return len(self.images)

    def __getitem__(self, idx):
        img_info = self.images[idx]
        img_path = self.images_dir / img_info["file_name"]

        # Load image via OpenCV (BGR -> RGB)
        img_bgr = cv2.imread(str(img_path), cv2.IMREAD_COLOR)
        if img_bgr is None:
            raise FileNotFoundError(f"Failed to load image: {img_path}")
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        h, w = img_rgb.shape[:2]

        # Convert to float tensor [3, H, W] in [0, 1]
        img_tensor = torch.from_numpy(img_rgb).permute(2, 0, 1).float() / 255.0

        anns = self.img_id_to_anns.get(img_info["id"], [])

        boxes = []
        labels = []
        masks = []
        areas = []
        iscrowd = []

        for ann in anns:
            # Bounding box in [x, y, w, h] -> convert to [x1, y1, x2, y2]
            bx, by, bw, bh = ann["bbox"]
            x1, y1 = bx, by
            x2, y2 = bx + bw, by + bh

            # Clamp coordinates to image boundaries
            x1 = max(0.0, min(float(x1), float(w)))
            y1 = max(0.0, min(float(y1), float(h)))
            x2 = max(0.0, min(float(x2), float(w)))
            y2 = max(0.0, min(float(y2), float(h)))

            if (x2 - x1) <= 1.0 or (y2 - y1) <= 1.0:
                continue

            # Rasterize polygon into binary mask [H, W]
            mask = np.zeros((h, w), dtype=np.uint8)
            for seg in ann["segmentation"]:
                poly_pts = np.array(seg, dtype=np.float32).reshape(-1, 2)
                cv2.fillPoly(mask, [np.round(poly_pts).astype(np.int32)], 1)

            boxes.append([x1, y1, x2, y2])
            labels.append(1)  # Class 1: phone
            masks.append(mask)
            areas.append(ann["area"])
            iscrowd.append(0)

        target = {}
        if boxes:
            target["boxes"] = torch.as_tensor(boxes, dtype=torch.float32)
            target["labels"] = torch.as_tensor(labels, dtype=torch.int64)
            target["masks"] = torch.as_tensor(np.array(masks), dtype=torch.uint8)
            target["image_id"] = torch.tensor([img_info["id"]])
            target["area"] = torch.as_tensor(areas, dtype=torch.float32)
            target["iscrowd"] = torch.as_tensor(iscrowd, dtype=torch.int64)
        else:
            target["boxes"] = torch.zeros((0, 4), dtype=torch.float32)
            target["labels"] = torch.zeros((0,), dtype=torch.int64)
            target["masks"] = torch.zeros((0, h, w), dtype=torch.uint8)
            target["image_id"] = torch.tensor([img_info["id"]])
            target["area"] = torch.zeros((0,), dtype=torch.float32)
            target["iscrowd"] = torch.zeros((0,), dtype=torch.int64)

        if self.transforms is not None:
            img_tensor, target = self.transforms(img_tensor, target)

        return img_tensor, target

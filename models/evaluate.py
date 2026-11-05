"""
evaluate.py — Evaluate Mask R-CNN Phone Segmentation Model
===========================================================
Computes Mean Mask IoU and Detection Rate on a given COCO dataset split.
"""

import argparse
import json
import sys
from pathlib import Path
import numpy as np
import torch
from torch.utils.data import DataLoader

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from models.dataset import PhoneCOCODataset
from models.model import create_maskrcnn_model
from models.train import collate_fn, evaluate_model


def parse_args():
    p = argparse.ArgumentParser(description="Evaluate Mask R-CNN on phone segmentation")
    p.add_argument(
        "--dataset-dir",
        type=str,
        default=str(Path.home() / "Downloads" / "xis_measure_it_dataset_milestone" / "dataset"),
        help="Path to prepared dataset directory.",
    )
    p.add_argument(
        "--weights",
        type=str,
        default="models/weights/best_maskrcnn_phone.pth",
        help="Path to trained model weights.",
    )
    p.add_argument("--batch-size", type=int, default=1)
    p.add_argument("--device", type=str, default="auto", choices=["auto", "mps", "cpu"])
    return p.parse_args()


def main():
    args = parse_args()
    weights_path = Path(args.weights).resolve()
    if not weights_path.exists():
        print(f"ERROR: Model weights not found at {weights_path}", file=sys.stderr)
        return 1

    if args.device == "auto":
        device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    else:
        device = torch.device(args.device)

    print("=" * 65)
    print("XIS Measure It — Model Evaluation")
    print("=" * 65)
    print(f"Device      : {device}")
    print(f"Weights     : {weights_path}")

    # Load model
    model = create_maskrcnn_model(num_classes=2, pretrained_backbone=False)
    checkpoint = torch.load(str(weights_path), map_location=device)
    if "model_state_dict" in checkpoint:
        model.load_state_dict(checkpoint["model_state_dict"])
    else:
        model.load_state_dict(checkpoint)
    model.to(device)
    model.eval()

    train_images = Path(args.dataset_dir) / "train" / "images"
    train_ann = Path(args.dataset_dir) / "train" / "annotations" / "instances_train.json"
    if not train_ann.exists():
        print(f"ERROR: Annotations not found at {train_ann}", file=sys.stderr)
        return 1

    dataset = PhoneCOCODataset(images_dir=train_images, annotations_json=train_ann)
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=False, collate_fn=collate_fn)

    print(f"Loaded {len(dataset)} images from {train_ann.name}")
    metrics = evaluate_model(model, loader, device)

    print("\n" + "=" * 65)
    print(f"Total Evaluated     : {metrics['total_evaluated']}")
    print(f"Total Detected      : {metrics['total_detected']}")
    print(f"Detection Rate      : {metrics['detection_rate'] * 100:.1f}%")
    print(f"Mean Mask IoU       : {metrics['mean_mask_iou']:.4f}")
    print("=" * 65)
    return 0


if __name__ == "__main__":
    sys.exit(main())

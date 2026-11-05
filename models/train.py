"""
train.py — Train Mask R-CNN on Phone Segmentation Dataset
==========================================================
Trains TorchVision Mask R-CNN ResNet-50-FPN on the 77 annotated images.
Uses Apple Silicon M4 MPS backend with batch size 1.
Preserves session grouping to avoid data leakage during validation.
"""

import argparse
import datetime
import gc
import json
import time
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader, Subset

from models.dataset import PhoneCOCODataset
from models.model import create_maskrcnn_model


def collate_fn(batch):
    return tuple(zip(*batch))


def compute_iou(mask1: np.ndarray, mask2: np.ndarray) -> float:
    inter = np.logical_and(mask1 > 0, mask2 > 0).sum()
    union = np.logical_or(mask1 > 0, mask2 > 0).sum()
    return float(inter / union) if union > 0 else 0.0


def evaluate_model(model, val_loader, device):
    """
    Evaluates model on validation loader, computing mean Mask IoU and detection rate.
    """
    model.eval()
    ious = []
    n_detected = 0
    n_total = 0

    with torch.no_grad():
        for images, targets in val_loader:
            images = [img.to(device) for img in images]
            outputs = model(images)

            for target, output in zip(targets, outputs):
                n_total += 1
                gt_masks = target["masks"].cpu().numpy()
                if len(gt_masks) == 0:
                    continue
                gt_mask = gt_masks[0]

                pred_scores = output["scores"].cpu().numpy()
                pred_masks = output["masks"].cpu().numpy()

                # Filter by confidence threshold >= 0.5 and phone class == 1
                valid_idx = np.where((pred_scores >= 0.5))[0]
                if len(valid_idx) > 0:
                    best_idx = valid_idx[0]
                    pred_mask = (pred_masks[best_idx, 0] >= 0.5).astype(np.uint8)
                    iou = compute_iou(gt_mask, pred_mask)
                    ious.append(iou)
                    n_detected += 1
                else:
                    ious.append(0.0)

    mean_iou = float(np.mean(ious)) if ious else 0.0
    det_rate = float(n_detected / n_total) if n_total > 0 else 0.0
    return {
        "mean_mask_iou": round(mean_iou, 4),
        "detection_rate": round(det_rate, 4),
        "total_evaluated": n_total,
        "total_detected": n_detected,
    }


def parse_args():
    p = argparse.ArgumentParser(description="Train Mask R-CNN for Phone Segmentation")
    p.add_argument(
        "--dataset-dir",
        type=str,
        default=str(Path.home() / "Downloads" / "xis_measure_it_dataset_milestone" / "dataset"),
        help="Path to prepared dataset directory.",
    )
    p.add_argument(
        "--output-dir",
        type=str,
        default="models/weights",
        help="Directory to save model checkpoints and logs.",
    )
    p.add_argument("--epochs", type=int, default=10, help="Number of training epochs.")
    p.add_argument("--batch-size", type=int, default=1, help="Batch size per step.")
    p.add_argument("--grad-accum", type=int, default=2, help="Gradient accumulation steps.")
    p.add_argument("--lr", type=float, default=0.0025, help="Initial learning rate.")
    p.add_argument("--device", type=str, default="auto", choices=["auto", "mps", "cpu"])
    p.add_argument("--val-session", type=str, default="B", help="Session to hold out for validation (B, C, E, F, G).")
    p.add_argument("--smoke-test", action="store_true", default=False, help="Run 1-epoch smoke test on 5 images.")
    return p.parse_args()


def main():
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Determine device
    if args.device == "auto":
        device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    else:
        device = torch.device(args.device)

    print("=" * 70)
    print("XIS Measure It — Phone Segmentation Training Pipeline")
    print("=" * 70)
    print(f"Device               : {device}")
    print(f"Dataset root         : {args.dataset_dir}")
    print(f"Output directory     : {output_dir}")
    print(f"Epochs               : {args.epochs}")
    print(f"Batch size           : {args.batch_size} (accum={args.grad_accum})")
    print(f"Initial learning rate: {args.lr}")
    print(f"Validation Session   : {args.val_session}")
    print(f"Smoke test mode      : {args.smoke_test}")
    print("=" * 70)

    # Load full training dataset
    train_images_dir = Path(args.dataset_dir) / "train" / "images"
    train_ann_json = Path(args.dataset_dir) / "train" / "annotations" / "instances_train.json"

    dataset = PhoneCOCODataset(images_dir=train_images_dir, annotations_json=train_ann_json)
    print(f"Loaded COCO dataset: {len(dataset)} images total.")

    # Partition by capture session for honest internal validation
    session_ranges = {
        "B": (8019, 8029),
        "C": (8030, 8038),
        "E": (8072, 8088),
        "F": (8093, 8116),
        "G": (8118, 8145),
    }

    val_range = session_ranges.get(args.val_session.upper(), (8019, 8029))

    train_indices = []
    val_indices = []

    for idx, img_info in enumerate(dataset.images):
        fname = img_info["file_name"]
        num = int(fname.replace("IMG_", "").replace(".JPG", ""))
        if val_range[0] <= num <= val_range[1]:
            val_indices.append(idx)
        else:
            train_indices.append(idx)

    print(f"Session-Grouped Split (Hold out Session {args.val_session}):")
    print(f"  Training samples  : {len(train_indices)} images")
    print(f"  Validation samples: {len(val_indices)} images")

    if args.smoke_test:
        train_indices = train_indices[:5]
        val_indices = val_indices[:3]
        args.epochs = 1
        print("Smoke-test mode: restricted to 5 train and 3 val samples.")

    train_dataset = Subset(dataset, train_indices)
    val_dataset = Subset(dataset, val_indices)

    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=True,
        collate_fn=collate_fn,
        num_workers=0,
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=1,
        shuffle=False,
        collate_fn=collate_fn,
        num_workers=0,
    )

    # Instantiate model
    print("\nInstantiating Mask R-CNN ResNet-50-FPN model...")
    model = create_maskrcnn_model(num_classes=2, pretrained_backbone=True)
    model.to(device)

    # Optimizer & Scheduler
    params = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.SGD(params, lr=args.lr, momentum=0.9, weight_decay=0.0005)
    lr_scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=args.epochs, eta_min=args.lr * 0.01
    )

    training_log = {
        "timestamp_start": datetime.datetime.now().isoformat(),
        "device": str(device),
        "num_epochs": args.epochs,
        "batch_size": args.batch_size,
        "grad_accum": args.grad_accum,
        "val_session_held_out": args.val_session,
        "n_train_samples": len(train_indices),
        "n_val_samples": len(val_indices),
        "epoch_metrics": [],
    }

    best_val_iou = 0.0
    start_total_time = time.time()

    print("\nStarting training loop...")
    for epoch in range(1, args.epochs + 1):
        epoch_start = time.time()
        model.train()
        epoch_losses = []

        optimizer.zero_grad()
        step = 0

        for images, targets in train_loader:
            images = [img.to(device) for img in images]
            targets = [{k: v.to(device) for k, v in t.items()} for t in targets]

            loss_dict = model(images, targets)
            losses = sum(loss for loss in loss_dict.values())
            loss_scaled = losses / args.grad_accum
            loss_scaled.backward()

            epoch_losses.append(losses.item())
            step += 1

            if step % args.grad_accum == 0 or step == len(train_loader):
                optimizer.step()
                optimizer.zero_grad()

        lr_scheduler.step()
        train_loss = float(np.mean(epoch_losses))
        epoch_time = time.time() - epoch_start

        # Validation evaluation
        val_metrics = evaluate_model(model, val_loader, device)

        print(
            f"Epoch [{epoch:02d}/{args.epochs:02d}] "
            f"Loss: {train_loss:.4f} | "
            f"Val Mask IoU: {val_metrics['mean_mask_iou']:.4f} | "
            f"Val Det Rate: {val_metrics['detection_rate']*100:.1f}% | "
            f"LR: {optimizer.param_groups[0]['lr']:.6f} | "
            f"Time: {epoch_time:.1f}s"
        )

        record = {
            "epoch": epoch,
            "train_loss": round(train_loss, 4),
            "val_mask_iou": val_metrics["mean_mask_iou"],
            "val_detection_rate": val_metrics["detection_rate"],
            "lr": round(optimizer.param_groups[0]["lr"], 6),
            "epoch_duration_s": round(epoch_time, 2),
        }
        training_log["epoch_metrics"].append(record)

        # Checkpoint saving: keep only best and latest
        latest_path = output_dir / "latest_maskrcnn_phone.pth"
        torch.save(
            {
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "val_mask_iou": val_metrics["mean_mask_iou"],
            },
            str(latest_path),
        )

        if val_metrics["mean_mask_iou"] >= best_val_iou:
            best_val_iou = val_metrics["mean_mask_iou"]
            best_path = output_dir / "best_maskrcnn_phone.pth"
            torch.save(
                {
                    "epoch": epoch,
                    "model_state_dict": model.state_dict(),
                    "val_mask_iou": best_val_iou,
                },
                str(best_path),
            )

        # Memory cleanup
        if device.type == "mps":
            torch.mps.empty_cache()
        gc.collect()

    total_training_time = time.time() - start_total_time
    training_log["total_training_time_s"] = round(total_training_time, 2)
    training_log["best_val_iou"] = round(best_val_iou, 4)
    training_log["timestamp_end"] = datetime.datetime.now().isoformat()

    log_path = output_dir / "training_log.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(training_log, f, indent=2)

    print("\n" + "=" * 70)
    print(f"Training completed in {total_training_time:.1f}s.")
    print(f"Best Validation Mask IoU: {best_val_iou:.4f}")
    print(f"Saved best model weights : {output_dir / 'best_maskrcnn_phone.pth'}")
    print(f"Saved training log       : {log_path}")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

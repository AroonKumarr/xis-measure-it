"""
model.py — Mask R-CNN ResNet-50 FPN Model Builder
===================================================
Constructs a TorchVision Mask R-CNN with ResNet-50-FPN backbone,
configured for 2 classes (Background = 0, Phone = 1).
Configures min_size=800 and max_size=1067 to preserve the native 3:4 portrait aspect ratio.
"""

import torchvision
from torchvision.models.detection import maskrcnn_resnet50_fpn, MaskRCNN_ResNet50_FPN_Weights
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
from torchvision.models.detection.mask_rcnn import MaskRCNNPredictor


def create_maskrcnn_model(
    num_classes: int = 2,
    pretrained_backbone: bool = True,
    min_size: int = 800,
    max_size: int = 1067,
):
    """
    Constructs Mask R-CNN with ResNet-50-FPN.
    num_classes: 2 (Background=0, Phone=1).
    min_size=800, max_size=1067: preserves exact 3:4 portrait aspect ratio (800 * 5712 / 4284 = 1067 px).
    """
    if pretrained_backbone:
        weights = MaskRCNN_ResNet50_FPN_Weights.DEFAULT
    else:
        weights = None

    # Instantiate model with aspect-ratio preserving scaling
    model = maskrcnn_resnet50_fpn(
        weights=weights,
        min_size=min_size,
        max_size=max_size,
    )

    # 1. Replace Box Predictor (Classification & Bounding Box)
    in_features_box = model.roi_heads.box_predictor.cls_score.in_features
    model.roi_heads.box_predictor = FastRCNNPredictor(in_features_box, num_classes)

    # 2. Replace Mask Predictor
    in_features_mask = model.roi_heads.mask_predictor.conv5_mask.in_channels
    dim_reduced = 256
    model.roi_heads.mask_predictor = MaskRCNNPredictor(
        in_channels=in_features_mask,
        dim_reduced=dim_reduced,
        num_classes=num_classes,
    )

    return model

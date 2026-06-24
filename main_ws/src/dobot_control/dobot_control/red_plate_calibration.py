"""Red rectangular plate detection and planar pixel-to-base calibration."""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import cv2
import numpy as np


class RedPlateDetectionError(RuntimeError):
    """Raised when the red plate cannot be detected confidently."""


@dataclass(frozen=True)
class RedPlateDetection:
    center: tuple[float, float]
    corners: np.ndarray
    area_px: float
    aspect_ratio: float
    rectangularity: float
    quality: float
    contour_count: int


@dataclass(frozen=True)
class RedPlateHsvThresholds:
    """
    HSV red threshold configuration.

    Red wraps around hue=0 in OpenCV HSV, so two ranges are required.
    Defaults follow the SSAFY RGBD/OpenCV red examples: [0,120,70]-[10,255,255]
    and [170,120,70]-[180,255,255].
    """

    lower_red_1: tuple[int, int, int] = (0, 120, 70)
    upper_red_1: tuple[int, int, int] = (10, 255, 255)
    lower_red_2: tuple[int, int, int] = (170, 120, 70)
    upper_red_2: tuple[int, int, int] = (180, 255, 255)


@dataclass(frozen=True)
class PixelToBaseCalibration:
    model_type: str
    matrix: np.ndarray
    sample_count: int
    inlier_count: int
    residual_mean_m: float
    residual_max_m: float
    residual_rms_m: float
    inlier_mask: np.ndarray


def order_corners_clockwise(corners: np.ndarray) -> np.ndarray:
    """Return corners ordered top-left, top-right, bottom-right, bottom-left."""
    points = np.asarray(corners, dtype=np.float32).reshape(4, 2)
    center = points.mean(axis=0)
    angles = np.arctan2(points[:, 1] - center[1], points[:, 0] - center[0])
    ordered = points[np.argsort(angles)]
    # np angle order starts around left/top depending on quadrant. Normalize via sums.
    sums = ordered[:, 0] + ordered[:, 1]
    top_left_index = int(np.argmin(sums))
    return np.roll(ordered, -top_left_index, axis=0).astype(np.float32)


def _hsv_bound(values: Iterable[int]) -> np.ndarray:
    bound = np.asarray(list(values), dtype=np.int16).reshape(3)
    bound = np.clip(bound, [0, 0, 0], [180, 255, 255])
    return bound.astype(np.uint8)


def red_mask_hsv(
    image_bgr: np.ndarray,
    *,
    thresholds: RedPlateHsvThresholds | None = None,
) -> np.ndarray:
    """Create a red mask using two hue ranges for wrap-around red."""
    thresholds = thresholds or RedPlateHsvThresholds()
    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
    lower_red_1 = _hsv_bound(thresholds.lower_red_1)
    upper_red_1 = _hsv_bound(thresholds.upper_red_1)
    lower_red_2 = _hsv_bound(thresholds.lower_red_2)
    upper_red_2 = _hsv_bound(thresholds.upper_red_2)
    mask = cv2.bitwise_or(
        cv2.inRange(hsv, lower_red_1, upper_red_1),
        cv2.inRange(hsv, lower_red_2, upper_red_2),
    )
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    return mask


def build_red_debug_images(
    image_bgr: np.ndarray,
    *,
    thresholds: RedPlateHsvThresholds | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return red mask, red-only BGR image, and a green-mask overlay image."""
    mask = red_mask_hsv(image_bgr, thresholds=thresholds)
    red_only = cv2.bitwise_and(image_bgr, image_bgr, mask=mask)
    overlay = image_bgr.copy()
    overlay[mask > 0] = (0, 255, 0)
    overlay = cv2.addWeighted(image_bgr, 0.65, overlay, 0.35, 0.0)
    return mask, red_only, overlay


def _candidate_from_contour(
    contour: np.ndarray,
    *,
    expected_aspect_ratio: float,
    min_area_px: float,
) -> RedPlateDetection | None:
    area = float(cv2.contourArea(contour))
    if area < min_area_px:
        return None

    rect = cv2.minAreaRect(contour)
    (width, height) = rect[1]
    if width <= 0.0 or height <= 0.0:
        return None

    long_side = max(float(width), float(height))
    short_side = min(float(width), float(height))
    aspect = long_side / short_side
    rect_area = long_side * short_side
    rectangularity = area / rect_area if rect_area > 0.0 else 0.0
    aspect_error = abs(aspect - expected_aspect_ratio) / expected_aspect_ratio
    if aspect_error > 0.45 or rectangularity < 0.65:
        return None

    aspect_score = max(0.0, 1.0 - aspect_error / 0.45)
    rect_score = min(1.0, rectangularity)
    area_score = min(1.0, area / (min_area_px * 4.0))
    quality = 0.45 * aspect_score + 0.35 * rect_score + 0.20 * area_score
    box = order_corners_clockwise(cv2.boxPoints(rect))
    center = (float(rect[0][0]), float(rect[0][1]))
    return RedPlateDetection(
        center=center,
        corners=box,
        area_px=area,
        aspect_ratio=aspect,
        rectangularity=float(rectangularity),
        quality=float(quality),
        contour_count=0,
    )


def detect_red_plate(
    image_bgr: np.ndarray,
    *,
    thresholds: RedPlateHsvThresholds | None = None,
    expected_aspect_ratio: float = 5.0 / 3.4,
    min_area_px: float = 800.0,
    min_quality: float = 0.55,
    ambiguity_ratio: float = 0.85,
) -> RedPlateDetection:
    """Detect a single confident red rectangular plate in a BGR image."""
    mask = red_mask_hsv(image_bgr, thresholds=thresholds)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidates = []
    for contour in contours:
        candidate = _candidate_from_contour(
            contour,
            expected_aspect_ratio=expected_aspect_ratio,
            min_area_px=min_area_px,
        )
        if candidate is not None and candidate.quality >= min_quality:
            candidates.append(candidate)

    if not candidates:
        raise RedPlateDetectionError(
            "red plate not detected confidently "
            f"(contours={len(contours)}, min_area_px={min_area_px}, min_quality={min_quality})"
        )

    candidates.sort(key=lambda item: item.quality * item.area_px, reverse=True)
    best = candidates[0]
    if len(candidates) > 1:
        second = candidates[1]
        best_score = best.quality * best.area_px
        second_score = second.quality * second.area_px
        if second_score >= best_score * ambiguity_ratio:
            raise RedPlateDetectionError("multiple red plate candidates are ambiguous")

    return RedPlateDetection(
        center=best.center,
        corners=best.corners,
        area_px=best.area_px,
        aspect_ratio=best.aspect_ratio,
        rectangularity=best.rectangularity,
        quality=best.quality,
        contour_count=len(contours),
    )


def _residuals_for_matrix(
    matrix: np.ndarray,
    src_pixels: np.ndarray,
    dst_xy: np.ndarray,
) -> np.ndarray:
    if matrix.shape == (3, 3):
        src_h = cv2.convertPointsToHomogeneous(src_pixels).reshape(-1, 3).T
        pred_h = matrix @ src_h
        pred = (pred_h[:2] / pred_h[2:3]).T
    else:
        src_aug = np.column_stack([src_pixels, np.ones(len(src_pixels))])
        pred = (matrix @ src_aug.T).T
    return np.linalg.norm(pred - dst_xy, axis=1)


def estimate_pixel_to_base_calibration(
    pixel_points: Iterable[Iterable[float]],
    base_xy_points: Iterable[Iterable[float]],
    *,
    ransac_reproj_threshold_m: float = 0.01,
) -> PixelToBaseCalibration:
    """Estimate planar mapping from red plate center pixel to base XY meters."""
    src = np.asarray(list(pixel_points), dtype=np.float32).reshape(-1, 2)
    dst = np.asarray(list(base_xy_points), dtype=np.float32).reshape(-1, 2)
    if len(src) != len(dst):
        raise ValueError("pixel_points and base_xy_points must have same length")
    if len(src) < 3:
        raise ValueError("at least 3 samples are required for affine calibration")

    matrix = None
    mask = None
    model_type = "affine"
    if len(src) >= 4:
        matrix, mask = cv2.findHomography(src, dst, cv2.RANSAC, ransac_reproj_threshold_m)
        if matrix is not None:
            model_type = "homography"

    if matrix is None:
        affine, mask = cv2.estimateAffine2D(
            src,
            dst,
            method=cv2.RANSAC,
            ransacReprojThreshold=ransac_reproj_threshold_m,
        )
        if affine is None:
            raise RuntimeError("pixel-to-base calibration failed")
        matrix = affine
        model_type = "affine"

    if mask is not None:
        inlier_mask = mask.reshape(-1).astype(bool)
    else:
        inlier_mask = np.ones(len(src), dtype=bool)
    residuals = _residuals_for_matrix(matrix, src, dst)
    inlier_residuals = residuals[inlier_mask] if np.any(inlier_mask) else residuals
    return PixelToBaseCalibration(
        model_type=model_type,
        matrix=np.asarray(matrix, dtype=np.float64),
        sample_count=int(len(src)),
        inlier_count=int(np.count_nonzero(inlier_mask)),
        residual_mean_m=float(np.mean(inlier_residuals)),
        residual_max_m=float(np.max(inlier_residuals)),
        residual_rms_m=float(np.sqrt(np.mean(inlier_residuals ** 2))),
        inlier_mask=inlier_mask,
    )


def apply_pixel_to_base_xy(
    calibration: PixelToBaseCalibration,
    pixel: Iterable[float],
) -> tuple[float, float]:
    """Apply an estimated planar mapping to one pixel center."""
    point = np.asarray(list(pixel), dtype=np.float64).reshape(1, 2)
    if calibration.matrix.shape == (3, 3):
        point_h = cv2.convertPointsToHomogeneous(point.astype(np.float32)).reshape(3, 1)
        mapped_h = calibration.matrix @ point_h
        mapped = (mapped_h[:2] / mapped_h[2]).reshape(2)
    else:
        point_aug = np.array([point[0, 0], point[0, 1], 1.0], dtype=np.float64)
        mapped = calibration.matrix @ point_aug
    return float(mapped[0]), float(mapped[1])


def calibration_to_json(calibration: PixelToBaseCalibration) -> str:
    """Serialize calibration to JSON for approval-time persistence."""
    payload = asdict(calibration)
    payload["matrix"] = calibration.matrix.tolist()
    payload["inlier_mask"] = calibration.inlier_mask.astype(bool).tolist()
    return json.dumps(payload, ensure_ascii=False, indent=2)


def save_calibration(path: str | Path, calibration: PixelToBaseCalibration) -> None:
    """Save approved calibration to a JSON file."""
    output = Path(path).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(calibration_to_json(calibration), encoding="utf-8")


def load_calibration(path: str | Path) -> PixelToBaseCalibration:
    """Load a saved planar pixel-to-base calibration JSON file."""
    payload = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    matrix = np.asarray(payload["matrix"], dtype=np.float64)
    inlier_mask = np.asarray(payload.get("inlier_mask", []), dtype=bool)
    if inlier_mask.size == 0:
        inlier_mask = np.ones(int(payload.get("sample_count", 0)), dtype=bool)
    return PixelToBaseCalibration(
        model_type=str(payload["model_type"]),
        matrix=matrix,
        sample_count=int(payload.get("sample_count", len(inlier_mask))),
        inlier_count=int(payload.get("inlier_count", np.count_nonzero(inlier_mask))),
        residual_mean_m=float(payload.get("residual_mean_m", 0.0)),
        residual_max_m=float(payload.get("residual_max_m", 0.0)),
        residual_rms_m=float(payload.get("residual_rms_m", 0.0)),
        inlier_mask=inlier_mask,
    )


def pose_xy_to_action_target(
    *,
    x_m: float,
    y_m: float,
    z_m: float,
    yaw_deg: float,
) -> list[float]:
    """Convert base meters into Dobot PointToPoint action target units."""
    if not all(math.isfinite(value) for value in [x_m, y_m, z_m, yaw_deg]):
        raise ValueError("target pose contains non-finite values")
    return [x_m * 1000.0, y_m * 1000.0, z_m * 1000.0, yaw_deg]

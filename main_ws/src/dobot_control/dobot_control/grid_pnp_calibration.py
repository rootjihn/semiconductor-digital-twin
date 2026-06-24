"""
Grid-board PnP helpers for Dobot/RealSense extrinsic calibration.

The object points are expressed directly in the robot base frame.  OpenCV's
solvePnP therefore estimates T_camera_object, which is T_camera_base when the
object coordinate system is the base/grid coordinate system.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

import cv2
import numpy as np


@dataclass(frozen=True)
class PnPQuality:
    mean_error_px: float
    max_error_px: float
    rms_error_px: float
    inlier_ratio: float
    inlier_count: int
    point_count: int


@dataclass(frozen=True)
class PnPResult:
    rvec_object_to_camera: np.ndarray
    tvec_object_to_camera: np.ndarray
    rotation_base_to_camera: np.ndarray
    translation_base_to_camera: np.ndarray
    rotation_camera_to_base: np.ndarray
    translation_camera_to_base: np.ndarray
    quality: PnPQuality
    image_points: np.ndarray
    object_points: np.ndarray
    inliers: np.ndarray | None


def make_grid_object_points(
    *,
    columns: int,
    rows: int,
    square_size: float,
    origin_xyz: Iterable[float] = (0.0, 0.0, 0.0),
    axes: str = "xy",
) -> np.ndarray:
    """
    Create planar grid object points in base-frame meters.

    columns/rows follow OpenCV checkerboard convention: the number of inner
    corners along x/y.  axes selects the plane used in the robot base frame:
    - "xy": floor/table plane z=origin_z
    - "xz": y=origin_y
    - "yz": x=origin_x
    """
    if columns < 2 or rows < 2:
        raise ValueError("grid columns and rows must both be >= 2")
    if square_size <= 0.0:
        raise ValueError("square_size must be positive meters")

    origin = np.asarray(list(origin_xyz), dtype=np.float64)
    if origin.shape != (3,):
        raise ValueError("origin_xyz must contain exactly 3 values")

    points = []
    for row in range(rows):
        for col in range(columns):
            a = col * square_size
            b = row * square_size
            if axes == "xy":
                point = origin + np.array([a, b, 0.0], dtype=np.float64)
            elif axes == "xz":
                point = origin + np.array([a, 0.0, b], dtype=np.float64)
            elif axes == "yz":
                point = origin + np.array([0.0, a, b], dtype=np.float64)
            else:
                raise ValueError("axes must be one of: xy, xz, yz")
            points.append(point)
    return np.asarray(points, dtype=np.float32)


def camera_matrix_from_k(k: Iterable[float]) -> np.ndarray:
    values = np.asarray(list(k), dtype=np.float64)
    if values.size != 9:
        raise ValueError("CameraInfo.k must contain 9 values")
    matrix = values.reshape(3, 3)
    if matrix[0, 0] == 0.0 or matrix[1, 1] == 0.0:
        raise ValueError("CameraInfo.k has invalid fx/fy")
    return matrix


def distortion_from_d(d: Iterable[float]) -> np.ndarray:
    values = np.asarray(list(d), dtype=np.float64)
    if values.size == 0:
        return np.zeros((5, 1), dtype=np.float64)
    return values.reshape(-1, 1)


def find_checkerboard_corners(
    image_bgr_or_gray: np.ndarray,
    *,
    columns: int,
    rows: int,
    refine_subpixel: bool = True,
) -> np.ndarray | None:
    """Detect checkerboard inner corners and optionally refine to subpixels."""
    if image_bgr_or_gray.ndim == 3:
        gray = cv2.cvtColor(image_bgr_or_gray, cv2.COLOR_BGR2GRAY)
    else:
        gray = image_bgr_or_gray

    pattern_size = (columns, rows)
    flags = cv2.CALIB_CB_ADAPTIVE_THRESH | cv2.CALIB_CB_NORMALIZE_IMAGE
    found, corners = cv2.findChessboardCorners(gray, pattern_size, flags)
    if not found:
        # SB is more robust on perspective/lighting but can be slower.
        found, corners = cv2.findChessboardCornersSB(gray, pattern_size, None)
    if not found or corners is None:
        return None

    if refine_subpixel:
        criteria = (
            cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER,
            30,
            0.001,
        )
        corners = cv2.cornerSubPix(gray, corners.astype(np.float32), (11, 11), (-1, -1), criteria)
    return corners.reshape(-1, 2).astype(np.float32)


def compute_reprojection_quality(
    *,
    object_points: np.ndarray,
    image_points: np.ndarray,
    rvec: np.ndarray,
    tvec: np.ndarray,
    camera_matrix: np.ndarray,
    dist_coeffs: np.ndarray,
    inliers: np.ndarray | None,
) -> PnPQuality:
    projected, _ = cv2.projectPoints(object_points, rvec, tvec, camera_matrix, dist_coeffs)
    projected = projected.reshape(-1, 2)
    image_points = image_points.reshape(-1, 2)
    errors = np.linalg.norm(projected - image_points, axis=1)
    point_count = int(len(errors))
    inlier_count = int(len(inliers.reshape(-1))) if inliers is not None else point_count
    inlier_ratio = float(inlier_count / point_count) if point_count else 0.0
    return PnPQuality(
        mean_error_px=float(np.mean(errors)) if point_count else math.inf,
        max_error_px=float(np.max(errors)) if point_count else math.inf,
        rms_error_px=float(np.sqrt(np.mean(errors ** 2))) if point_count else math.inf,
        inlier_ratio=inlier_ratio,
        inlier_count=inlier_count,
        point_count=point_count,
    )


def estimate_grid_pose_pnp(
    *,
    object_points: np.ndarray,
    image_points: np.ndarray,
    camera_matrix: np.ndarray,
    dist_coeffs: np.ndarray,
    ransac_reprojection_error_px: float = 4.0,
    ransac_confidence: float = 0.99,
    ransac_iterations: int = 100,
    refine_lm: bool = True,
) -> PnPResult:
    """Estimate camera/base pose from matched grid object and image points."""
    object_points = np.asarray(object_points, dtype=np.float32).reshape(-1, 3)
    image_points = np.asarray(image_points, dtype=np.float32).reshape(-1, 2)
    if len(object_points) != len(image_points):
        raise ValueError("object_points and image_points must have the same length")
    if len(object_points) < 4:
        raise ValueError("at least 4 point correspondences are required for PnP")

    ok, rvec, tvec, inliers = cv2.solvePnPRansac(
        object_points,
        image_points,
        camera_matrix,
        dist_coeffs,
        iterationsCount=int(ransac_iterations),
        reprojectionError=float(ransac_reprojection_error_px),
        confidence=float(ransac_confidence),
        flags=cv2.SOLVEPNP_ITERATIVE,
    )
    if not ok:
        raise RuntimeError("solvePnPRansac failed")

    if refine_lm and inliers is not None and len(inliers) >= 4:
        idx = inliers.reshape(-1)
        rvec, tvec = cv2.solvePnPRefineLM(
            object_points[idx],
            image_points[idx],
            camera_matrix,
            dist_coeffs,
            rvec,
            tvec,
        )

    rotation_base_to_camera, _ = cv2.Rodrigues(rvec)
    translation_base_to_camera = tvec.reshape(3)
    rotation_camera_to_base = rotation_base_to_camera.T
    translation_camera_to_base = -rotation_camera_to_base @ translation_base_to_camera
    quality = compute_reprojection_quality(
        object_points=object_points,
        image_points=image_points,
        rvec=rvec,
        tvec=tvec,
        camera_matrix=camera_matrix,
        dist_coeffs=dist_coeffs,
        inliers=inliers,
    )
    return PnPResult(
        rvec_object_to_camera=rvec.reshape(3),
        tvec_object_to_camera=tvec.reshape(3),
        rotation_base_to_camera=rotation_base_to_camera,
        translation_base_to_camera=translation_base_to_camera,
        rotation_camera_to_base=rotation_camera_to_base,
        translation_camera_to_base=translation_camera_to_base,
        quality=quality,
        image_points=image_points,
        object_points=object_points,
        inliers=inliers,
    )


def rpy_from_rotation_matrix(rotation: np.ndarray) -> tuple[float, float, float]:
    """Return ROS-style fixed-axis roll/pitch/yaw from a rotation matrix."""
    sy = math.sqrt(rotation[0, 0] * rotation[0, 0] + rotation[1, 0] * rotation[1, 0])
    singular = sy < 1e-6
    if not singular:
        roll = math.atan2(rotation[2, 1], rotation[2, 2])
        pitch = math.atan2(-rotation[2, 0], sy)
        yaw = math.atan2(rotation[1, 0], rotation[0, 0])
    else:
        roll = math.atan2(-rotation[1, 2], rotation[1, 1])
        pitch = math.atan2(-rotation[2, 0], sy)
        yaw = 0.0
    return float(roll), float(pitch), float(yaw)


def quaternion_from_rotation_matrix(rotation: np.ndarray) -> tuple[float, float, float, float]:
    """Return x,y,z,w quaternion from a 3x3 rotation matrix."""
    m = np.asarray(rotation, dtype=np.float64)
    trace = float(np.trace(m))
    if trace > 0.0:
        s = math.sqrt(trace + 1.0) * 2.0
        qw = 0.25 * s
        qx = (m[2, 1] - m[1, 2]) / s
        qy = (m[0, 2] - m[2, 0]) / s
        qz = (m[1, 0] - m[0, 1]) / s
    elif m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
        s = math.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2]) * 2.0
        qw = (m[2, 1] - m[1, 2]) / s
        qx = 0.25 * s
        qy = (m[0, 1] + m[1, 0]) / s
        qz = (m[0, 2] + m[2, 0]) / s
    elif m[1, 1] > m[2, 2]:
        s = math.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2]) * 2.0
        qw = (m[0, 2] - m[2, 0]) / s
        qx = (m[0, 1] + m[1, 0]) / s
        qy = 0.25 * s
        qz = (m[1, 2] + m[2, 1]) / s
    else:
        s = math.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1]) * 2.0
        qw = (m[1, 0] - m[0, 1]) / s
        qx = (m[0, 2] + m[2, 0]) / s
        qy = (m[1, 2] + m[2, 1]) / s
        qz = 0.25 * s
    return float(qx), float(qy), float(qz), float(qw)

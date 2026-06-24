import cv2
import numpy as np
import pytest

from dobot_control.grid_pnp_calibration import (
    estimate_grid_pose_pnp,
    make_grid_object_points,
    rpy_from_rotation_matrix,
)


def test_make_grid_object_points_on_xy_plane_in_base_frame():
    points = make_grid_object_points(
        columns=3,
        rows=2,
        square_size=0.05,
        origin_xyz=(0.1, -0.2, 0.0),
        axes="xy",
    )

    assert points.shape == (6, 3)
    assert points[0] == pytest.approx((0.1, -0.2, 0.0))
    assert points[1] == pytest.approx((0.15, -0.2, 0.0))
    assert points[3] == pytest.approx((0.1, -0.15, 0.0))


def test_estimate_grid_pose_pnp_recovers_synthetic_pose_with_low_reprojection_error():
    object_points = make_grid_object_points(
        columns=7,
        rows=5,
        square_size=0.025,
        origin_xyz=(0.0, 0.0, 0.0),
        axes="xy",
    )
    camera_matrix = np.array(
        [[620.0, 0.0, 320.0], [0.0, 620.0, 240.0], [0.0, 0.0, 1.0]],
        dtype=np.float64,
    )
    dist_coeffs = np.zeros((5, 1), dtype=np.float64)

    true_rvec = np.array([[0.25], [-0.15], [0.05]], dtype=np.float64)
    true_tvec = np.array([[0.02], [-0.04], [0.65]], dtype=np.float64)
    image_points, _ = cv2.projectPoints(
        object_points, true_rvec, true_tvec, camera_matrix, dist_coeffs
    )
    image_points = image_points.reshape(-1, 2).astype(np.float32)

    result = estimate_grid_pose_pnp(
        object_points=object_points,
        image_points=image_points,
        camera_matrix=camera_matrix,
        dist_coeffs=dist_coeffs,
        ransac_reprojection_error_px=1.0,
        refine_lm=True,
    )

    assert result.translation_base_to_camera == pytest.approx(true_tvec.reshape(3), abs=1e-4)
    assert result.quality.mean_error_px < 1e-3
    assert result.quality.max_error_px < 1e-2
    assert result.quality.inlier_ratio == pytest.approx(1.0)


def test_rpy_from_rotation_matrix_identity():
    assert rpy_from_rotation_matrix(np.eye(3)) == pytest.approx((0.0, 0.0, 0.0))

from pathlib import Path

import cv2
import numpy as np

from dobot_control.image_crop_viewer import (
    CropSetting,
    apply_crop_setting,
    build_crop_setting,
    load_crop_setting,
    order_crop_points,
    save_crop_setting,
)


def test_order_crop_points_accepts_clicks_in_any_order():
    points = [(160, 20), (20, 30), (150, 120), (30, 110)]

    ordered = order_crop_points(points)

    np.testing.assert_allclose(
        ordered,
        np.array([[20, 30], [160, 20], [150, 120], [30, 110]], dtype=np.float32),
        atol=1e-6,
    )


def test_apply_crop_setting_warps_selected_quadrilateral():
    image = np.zeros((160, 220, 3), dtype=np.uint8)
    src = np.array([[20, 30], [160, 20], [150, 120], [30, 110]], dtype=np.float32)
    dst = np.array([[0, 0], [139, 0], [139, 89], [0, 89]], dtype=np.float32)
    matrix = cv2.getPerspectiveTransform(dst, src)
    pattern = np.zeros((90, 140, 3), dtype=np.uint8)
    pattern[:, :] = (10, 20, 30)
    pattern[20:70, 30:100] = (0, 0, 255)
    warped_into_source = cv2.warpPerspective(pattern, matrix, (220, 160))
    mask = cv2.warpPerspective(np.full((90, 140), 255, dtype=np.uint8), matrix, (220, 160))
    image[mask > 0] = warped_into_source[mask > 0]
    setting = build_crop_setting(points=src[[2, 0, 3, 1]], image_shape=image.shape)

    crop = apply_crop_setting(image, setting)

    assert crop.shape[:2] == (setting.output_height, setting.output_width)
    assert crop[45, 70, 2] > 200
    assert crop[45, 70, 0] < 50


def test_crop_setting_round_trips_to_json(tmp_path: Path):
    setting = CropSetting(
        points=[[10.0, 20.0], [110.0, 20.0], [110.0, 90.0], [10.0, 90.0]],
        output_width=100,
        output_height=70,
        image_width=320,
        image_height=240,
    )
    path = tmp_path / "crop.json"

    save_crop_setting(path, setting)
    loaded = load_crop_setting(path)

    assert loaded == setting

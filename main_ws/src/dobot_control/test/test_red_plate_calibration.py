import cv2
import numpy as np
import pytest

from dobot_control.red_plate_calibration import (
    RedPlateDetection,
    RedPlateDetectionError,
    apply_pixel_to_base_xy,
    build_red_debug_images,
    detect_red_plate,
    estimate_pixel_to_base_calibration,
)
from dobot_control.red_plate_interactive_calibrator import (
    command_helper_command,
    compact_choice_hint,
    make_calibration_sample,
)


def _synthetic_red_plate_image() -> np.ndarray:
    image = np.zeros((480, 640, 3), dtype=np.uint8)
    image[:] = (45, 45, 45)
    rect = ((320.0, 240.0), (100.0, 68.0), 18.0)
    box = cv2.boxPoints(rect).astype(np.int32)
    cv2.drawContours(image, [box], 0, (0, 0, 255), -1)
    # Obstacles/noise that should not win over the red rectangular plate.
    cv2.circle(image, (120, 100), 15, (0, 0, 180), -1)
    cv2.rectangle(image, (500, 350), (530, 380), (0, 0, 200), -1)
    return image


def test_detect_red_plate_returns_center_corners_and_quality():
    detection = detect_red_plate(
        _synthetic_red_plate_image(),
        expected_aspect_ratio=5.0 / 3.4,
        min_area_px=1000,
    )

    assert detection.center == pytest.approx((320.0, 240.0), abs=1.0)
    assert detection.corners.shape == (4, 2)
    assert detection.area_px > 6000
    assert detection.quality >= 0.75


def test_build_red_debug_images_shows_mask_and_red_only_pixels():
    image = _synthetic_red_plate_image()

    mask, red_only, overlay = build_red_debug_images(image)

    assert mask.shape == image.shape[:2]
    assert red_only.shape == image.shape
    assert overlay.shape == image.shape
    assert mask[240, 320] == 255
    assert np.count_nonzero(mask) > 5000
    assert red_only[240, 320, 2] > 200
    assert np.count_nonzero(red_only[0, 0]) == 0


def test_detect_red_plate_rejects_ambiguous_multiple_good_candidates():
    image = np.zeros((480, 640, 3), dtype=np.uint8)
    image[:] = (40, 40, 40)
    for center in [(220, 240), (420, 240)]:
        rect = (center, (100.0, 68.0), 0.0)
        cv2.drawContours(image, [cv2.boxPoints(rect).astype(np.int32)], 0, (0, 0, 255), -1)

    with pytest.raises(RedPlateDetectionError):
        detect_red_plate(image, min_area_px=1000)


def test_two_step_sample_pairs_visible_plate_detection_with_later_tcp_pose():
    detection = RedPlateDetection(
        center=(320.0, 240.0),
        corners=np.array(
            [[270.0, 206.0], [370.0, 206.0], [370.0, 274.0], [270.0, 274.0]],
            dtype=np.float32,
        ),
        area_px=6800.0,
        aspect_ratio=5.0 / 3.4,
        rectangularity=0.96,
        quality=0.91,
        contour_count=1,
    )

    sample = make_calibration_sample(
        detection=detection,
        tcp_pose_m=[0.37, 0.02, 0.018, 0.0],
        timestamp="2026-06-23T00:00:00+00:00",
    )

    assert sample.pixel_center == (320.0, 240.0)
    assert sample.tcp_pose_m[:3] == pytest.approx([0.37, 0.02, 0.018])
    assert sample.quality == pytest.approx(0.91)
    assert sample.corners[0] == pytest.approx([270.0, 206.0])


def test_command_prompt_hints_are_concise_and_stage_aware():
    assert command_helper_command("1").endswith("red_plate_command.launch.py command:=1")
    assert compact_choice_hint({"", "1"}) == (
        "명령: ros2 launch dobot_control red_plate_command.launch.py command:=1"
    )
    assert compact_choice_hint({"1", "2"}) == (
        "명령: ros2 launch dobot_control red_plate_command.launch.py command:=<번호>  (1/2)"
    )


def test_estimate_pixel_to_base_calibration_homography_predicts_xy():
    pixel_points = np.array(
        [[100.0, 100.0], [500.0, 100.0], [500.0, 380.0], [100.0, 380.0], [320.0, 240.0]],
        dtype=np.float32,
    )
    base_xy = np.array(
        [[0.20, -0.10], [0.50, -0.10], [0.50, 0.12], [0.20, 0.12], [0.365, 0.01]],
        dtype=np.float32,
    )

    result = estimate_pixel_to_base_calibration(pixel_points, base_xy)
    predicted = apply_pixel_to_base_xy(result, (320.0, 240.0))

    assert result.model_type == "homography"
    assert result.sample_count == 5
    assert result.inlier_count == 5
    assert result.residual_rms_m < 1e-6
    assert predicted == pytest.approx((0.365, 0.01), abs=1e-6)

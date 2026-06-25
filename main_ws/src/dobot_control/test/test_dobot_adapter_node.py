import json

import numpy as np
import pytest

from dobot_control.dobot_adapter_node import (
    DetectionResult,
    build_detection_pick_place_plan,
    parse_detection_results,
    plan_to_status_steps,
    select_detection,
)
from dobot_control.red_plate_calibration import PixelToBaseCalibration


def _linear_calibration() -> PixelToBaseCalibration:
    # base_x = 0.001 * image_x + 0.100, base_y = 0.002 * image_y - 0.050
    return PixelToBaseCalibration(
        model_type="affine",
        matrix=np.array([[0.001, 0.0, 0.100], [0.0, 0.002, -0.050]], dtype=np.float64),
        sample_count=3,
        inlier_count=3,
        residual_mean_m=0.0,
        residual_max_m=0.0,
        residual_rms_m=0.0,
        inlier_mask=np.array([True, True, True]),
    )


def test_parse_detection_results_accepts_contract_and_sorts_by_confidence():
    payload = json.dumps([
        {
            "label": "target_object",
            "class_id": 0,
            "confidence": 0.42,
            "bbox": [10, 20, 30, 40],
            "center": [20, 30],
            "image_size": [640, 480],
            "stamp": {"sec": 1, "nanosec": 2},
            "frame_id": "camera_color_optical_frame",
        },
        {
            "label": "target_object",
            "class_id": 0,
            "confidence": 0.91,
            "bbox": [100, 120, 180, 220],
            "center": [140, 170],
        },
    ])

    detections = parse_detection_results(payload)

    assert [d.confidence for d in detections] == [0.91, 0.42]
    assert detections[0].center == pytest.approx((140, 170))
    assert detections[1].image_size == (640, 480)
    assert detections[1].frame_id == "camera_color_optical_frame"


def test_parse_detection_results_rejects_non_array_and_missing_center():
    with pytest.raises(ValueError, match="JSON array"):
        parse_detection_results(json.dumps({"center": [1, 2]}))
    with pytest.raises(ValueError, match="center"):
        parse_detection_results(json.dumps([{
            "label": "x",
            "class_id": 0,
            "confidence": 0.9,
            "bbox": [1, 2, 3, 4],
        }]))


def test_select_detection_filters_label_and_confidence():
    detections = [
        DetectionResult("a", 0, 0.95, (0, 0, 1, 1), (1, 1)),
        DetectionResult("b", 1, 0.75, (0, 0, 1, 1), (2, 2)),
        DetectionResult("b", 1, 0.20, (0, 0, 1, 1), (3, 3)),
    ]

    selected = select_detection(detections, target_label="b", min_confidence=0.5)

    assert selected is not None
    assert selected.label == "b"
    assert selected.center == pytest.approx((2, 2))
    assert select_detection(detections, target_label="b", min_confidence=0.8) is None


def test_build_detection_pick_place_plan_uses_detection_center_as_image_pixel():
    detection = DetectionResult(
        label="target_object",
        class_id=0,
        confidence=0.9,
        bbox=(100, 120, 180, 220),
        center=(140, 170),
        image_size=(640, 480),
    )

    plan = build_detection_pick_place_plan(
        mode="attach",
        detection=detection,
        calibration=_linear_calibration(),
        hover_z_m=0.060,
        descend_distance_m=0.040,
        r_deg=12.0,
        return_to_hover=True,
        movej_motion_type=1,
        movel_motion_type=2,
    )

    assert plan.image_xy == pytest.approx((140, 170))
    assert plan.base_xy == pytest.approx((0.240, 0.290))
    assert plan.steps[0].target_pose == pytest.approx([240.0, 290.0, 60.0, 12.0])
    assert plan.steps[1].target_pose == pytest.approx([240.0, 290.0, 20.0, 12.0])
    assert plan.steps[2].suction_enabled is True
    assert plan_to_status_steps(plan)[0]["motion_type"] == 1

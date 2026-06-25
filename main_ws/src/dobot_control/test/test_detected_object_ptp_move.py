import numpy as np
import pytest

from dobot_control.detected_object_ptp_move import (
    build_detected_object_ptp_plan,
    plan_to_status,
)
from dobot_control.dobot_adapter_node import DetectionResult
from dobot_control.red_plate_calibration import PixelToBaseCalibration


def _linear_calibration() -> PixelToBaseCalibration:
    # base_x = 0.001 * image_x + 0.100, base_y = 0.002 * image_y - 0.050
    return PixelToBaseCalibration(
        model_type='affine',
        matrix=np.array([[0.001, 0.0, 0.100], [0.0, 0.002, -0.050]], dtype=np.float64),
        sample_count=3,
        inlier_count=3,
        residual_mean_m=0.0,
        residual_max_m=0.0,
        residual_rms_m=0.0,
        inlier_mask=np.array([True, True, True]),
    )


def test_build_detected_object_ptp_plan_pick_detected_xy_then_fixed_place():
    detection = DetectionResult(
        label='target_object',
        class_id=0,
        confidence=0.9,
        bbox=(100, 120, 180, 220),
        center=(140, 170),
        image_size=(640, 480),
    )

    plan = build_detected_object_ptp_plan(
        detection=detection,
        calibration=_linear_calibration(),
        pick_hover_z_m=0.08,
        pick_descend_distance_m=0.05,
        min_pick_z_m=0.02,
        place_x_m=0.20,
        place_y_m=-0.01,
        place_z_m=0.04,
        place_hover_offset_m=0.06,
        yaw_deg=12.0,
        movej_motion_type=1,
        return_to_place_hover=True,
    )

    assert plan.image_xy == pytest.approx((140, 170))
    assert plan.base_xy == pytest.approx((0.240, 0.290))
    assert plan.pick_z_m == pytest.approx(0.03)
    assert [step.label for step in plan.steps] == [
        'MoveJ detected pick hover',
        'MoveJ detected pick descend',
        'suction ON',
        'MoveJ detected pick hover return',
        'MoveJ place hover',
        'MoveJ place descend',
        'suction OFF',
        'MoveJ place hover return',
    ]
    assert plan.steps[0].target_pose == pytest.approx([240.0, 290.0, 80.0, 12.0])
    assert plan.steps[1].target_pose == pytest.approx([240.0, 290.0, 30.0, 12.0])
    assert plan.steps[2].suction_enabled is True
    assert plan.steps[4].target_pose == pytest.approx([200.0, -10.0, 100.0, 12.0])
    assert plan.steps[5].target_pose == pytest.approx([200.0, -10.0, 40.0, 12.0])
    assert plan.steps[6].suction_enabled is False
    assert plan_to_status(plan)['steps'][0]['motion_type'] == 1


def test_pick_descend_is_clamped_to_min_pick_z():
    detection = DetectionResult('target_object', 0, 0.9, (0, 0, 1, 1), (10, 20))

    plan = build_detected_object_ptp_plan(
        detection=detection,
        calibration=_linear_calibration(),
        pick_hover_z_m=0.06,
        pick_descend_distance_m=0.20,
        min_pick_z_m=0.02,
        place_x_m=0.20,
        place_y_m=-0.01,
        place_z_m=0.04,
        place_hover_offset_m=0.06,
        yaw_deg=0.0,
        return_to_place_hover=False,
    )

    assert plan.pick_z_m == pytest.approx(0.02)
    assert plan.steps[1].target_pose[2] == pytest.approx(20.0)
    assert [step.label for step in plan.steps][-1] == 'suction OFF'


def test_invalid_place_hover_offset_rejected():
    detection = DetectionResult('target_object', 0, 0.9, (0, 0, 1, 1), (10, 20))

    with pytest.raises(ValueError, match='place_hover_offset_m'):
        build_detected_object_ptp_plan(
            detection=detection,
            calibration=_linear_calibration(),
            pick_hover_z_m=0.06,
            pick_descend_distance_m=0.04,
            min_pick_z_m=0.02,
            place_x_m=0.20,
            place_y_m=-0.01,
            place_z_m=0.04,
            place_hover_offset_m=-0.01,
            yaw_deg=0.0,
        )

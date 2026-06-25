import numpy as np
import pytest

from dobot_control.click_pick_place import (
    DisplayTransform,
    build_click_pick_place_plan,
    build_perspective_display_transform,
    compute_descend_z_m,
    crop_and_resize_preview,
    effective_descend_distance_m,
    execute_plan_steps,
    marker_kind_for_mode,
    normalize_descend_distance_m,
    parse_bool,
)
from dobot_control.image_crop_viewer import CropSetting
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


def test_display_transform_no_crop_no_resize_maps_identity():
    transform = DisplayTransform(
        crop_x=0,
        crop_y=0,
        crop_w=640,
        crop_h=480,
        display_w=640,
        display_h=480,
    )

    assert transform.display_to_image(123, 45) == pytest.approx((123, 45))
    assert transform.image_to_display(123, 45) == pytest.approx((123, 45))


def test_display_transform_crop_without_resize_adds_crop_offset():
    transform = DisplayTransform(
        crop_x=100,
        crop_y=50,
        crop_w=320,
        crop_h=240,
        display_w=320,
        display_h=240,
    )

    assert transform.display_to_image(20, 30) == pytest.approx((120, 80))
    assert transform.image_to_display(120, 80) == pytest.approx((20, 30))


def test_display_transform_crop_with_resize_scales_to_original_image():
    transform = DisplayTransform(
        crop_x=80,
        crop_y=40,
        crop_w=320,
        crop_h=240,
        display_w=160,
        display_h=120,
    )

    assert transform.display_to_image(40, 30) == pytest.approx((160, 100))
    assert transform.image_to_display(160, 100) == pytest.approx((40, 30))


def test_display_transform_round_trips_image_display_image():
    transform = DisplayTransform(
        crop_x=77,
        crop_y=31,
        crop_w=503,
        crop_h=317,
        display_w=251,
        display_h=159,
    )
    image_point = (333.25, 201.75)

    display_point = transform.image_to_display(*image_point)
    round_trip = transform.display_to_image(*display_point)

    assert round_trip == pytest.approx(image_point, abs=1e-9)


def test_perspective_crop_transform_round_trips_original_image_coordinates():
    setting = CropSetting(
        points=[[20, 10], [180, 20], [170, 120], [30, 110]],
        output_width=160,
        output_height=100,
        image_width=200,
        image_height=140,
    )
    transform = build_perspective_display_transform(setting, display_w=320, display_h=200)
    image_point = (92.5, 64.25)

    display_point = transform.image_to_display(*image_point)
    round_trip = transform.display_to_image(*display_point)

    assert round_trip == pytest.approx(image_point, abs=1e-6)


def test_perspective_crop_preview_resizes_to_display_dimensions():
    image = np.zeros((140, 200, 3), dtype=np.uint8)
    setting = CropSetting(
        points=[[20, 10], [180, 20], [170, 120], [30, 110]],
        output_width=160,
        output_height=100,
        image_width=200,
        image_height=140,
    )
    transform = build_perspective_display_transform(setting, display_w=80, display_h=50)

    preview = crop_and_resize_preview(image, transform)

    assert preview.shape == (50, 80, 3)


def test_marker_kind_follows_attach_and_detach_modes():
    assert marker_kind_for_mode("attach") == "+"
    assert marker_kind_for_mode("detach") == "x"
    with pytest.raises(ValueError):
        marker_kind_for_mode(None)


def test_parse_bool_accepts_launch_string_values():
    assert parse_bool(True) is True
    assert parse_bool(False) is False
    assert parse_bool("true") is True
    assert parse_bool("False") is False
    assert parse_bool("1") is True
    assert parse_bool("0") is False
    with pytest.raises(ValueError):
        parse_bool("sometimes")


def test_negative_descend_distance_is_treated_as_downward_magnitude():
    assert normalize_descend_distance_m(-0.01) == pytest.approx(0.01)
    assert compute_descend_z_m(0.08, -0.01) == pytest.approx(0.07)


def test_descend_target_is_clamped_to_min_z():
    assert compute_descend_z_m(0.02, 0.03) == pytest.approx(0.02)
    assert compute_descend_z_m(0.02, 0.03, min_z_m=0.0) == pytest.approx(0.0)
    assert effective_descend_distance_m(0.08, 0.15) == pytest.approx(0.06)


def test_click_plan_uses_pixel_to_base_then_movej_movel_suction_return_sequence():
    transform = DisplayTransform(
        crop_x=100,
        crop_y=50,
        crop_w=320,
        crop_h=240,
        display_w=160,
        display_h=120,
    )

    plan = build_click_pick_place_plan(
        mode="attach",
        display_xy=(40, 30),
        transform=transform,
        calibration=_linear_calibration(),
        hover_z_m=0.060,
        descend_distance_m=0.040,
        r_deg=12.0,
        return_to_hover=True,
        movej_motion_type=1,
        movel_motion_type=2,
    )

    assert plan.image_xy == pytest.approx((180.0, 110.0))
    assert plan.base_xy == pytest.approx((0.280, 0.170))
    assert [step.kind for step in plan.steps] == ["move", "move", "suction", "move"]
    assert [step.label for step in plan.steps] == [
        "MoveJ XY hover",
        "MoveL descend",
        "suction ON",
        "MoveL return hover",
    ]
    assert plan.steps[0].motion_type == 1
    assert plan.steps[0].target_pose == pytest.approx([280.0, 170.0, 60.0, 12.0])
    assert plan.steps[1].motion_type == 2
    assert plan.steps[1].target_pose == pytest.approx([280.0, 170.0, 20.0, 12.0])
    assert plan.steps[2].suction_enabled is True
    assert plan.steps[3].target_pose == pytest.approx([280.0, 170.0, 60.0, 12.0])


def test_detach_plan_uses_x_marker_and_suction_off_without_return_when_disabled():
    transform = DisplayTransform(0, 0, 640, 480, 640, 480)

    plan = build_click_pick_place_plan(
        mode="detach",
        display_xy=(10, 20),
        transform=transform,
        calibration=_linear_calibration(),
        hover_z_m=0.070,
        descend_distance_m=0.010,
        r_deg=0.0,
        return_to_hover=False,
        movej_motion_type=1,
        movel_motion_type=2,
    )

    assert marker_kind_for_mode(plan.mode) == "x"
    assert [step.kind for step in plan.steps] == ["move", "move", "suction"]
    assert plan.steps[2].label == "suction OFF"
    assert plan.steps[2].suction_enabled is False
    assert plan.steps[1].target_pose[2] == pytest.approx(60.0)


def test_click_plan_accepts_negative_descend_distance_as_positive_distance():
    transform = DisplayTransform(0, 0, 640, 480, 640, 480)

    plan = build_click_pick_place_plan(
        mode="attach",
        display_xy=(10, 20),
        transform=transform,
        calibration=_linear_calibration(),
        hover_z_m=0.080,
        descend_distance_m=-0.010,
        r_deg=0.0,
        return_to_hover=False,
        movej_motion_type=1,
        movel_motion_type=2,
    )

    assert plan.steps[0].target_pose[2] == pytest.approx(80.0)
    assert plan.steps[1].target_pose[2] == pytest.approx(70.0)


def test_click_plan_clamps_descend_target_to_default_min_z():
    transform = DisplayTransform(0, 0, 640, 480, 640, 480)

    plan = build_click_pick_place_plan(
        mode="attach",
        display_xy=(10, 20),
        transform=transform,
        calibration=_linear_calibration(),
        hover_z_m=0.020,
        descend_distance_m=0.030,
        r_deg=0.0,
        return_to_hover=False,
        movej_motion_type=1,
        movel_motion_type=2,
    )

    assert plan.steps[0].target_pose[2] == pytest.approx(20.0)
    assert plan.steps[1].target_pose[2] == pytest.approx(20.0)


def test_dry_run_execution_does_not_call_motion_or_suction_clients():
    transform = DisplayTransform(0, 0, 640, 480, 640, 480)
    plan = build_click_pick_place_plan(
        mode="attach",
        display_xy=(20, 30),
        transform=transform,
        calibration=_linear_calibration(),
        hover_z_m=0.060,
        descend_distance_m=0.040,
        r_deg=0.0,
        return_to_hover=True,
        movej_motion_type=1,
        movel_motion_type=2,
    )
    calls = []

    execution = execute_plan_steps(
        plan,
        dry_run=True,
        motion_sender=lambda *args: calls.append(("move", args)),
        suction_sender=lambda *args: calls.append(("suction", args)),
    )

    assert calls == []
    assert execution.succeeded is True
    assert "[dry-run] MoveJ XY hover" in execution.logs[0]
    assert "[dry-run] suction ON" in "\n".join(execution.logs)


def test_real_execution_reports_incomplete_when_motion_sender_fails():
    transform = DisplayTransform(0, 0, 640, 480, 640, 480)
    plan = build_click_pick_place_plan(
        mode="attach",
        display_xy=(20, 30),
        transform=transform,
        calibration=_linear_calibration(),
        hover_z_m=0.060,
        descend_distance_m=0.040,
        r_deg=0.0,
        return_to_hover=True,
        movej_motion_type=1,
        movel_motion_type=2,
    )
    suction_calls = []

    execution = execute_plan_steps(
        plan,
        dry_run=False,
        motion_sender=lambda *_args: False,
        suction_sender=lambda *args: suction_calls.append(args),
    )

    assert execution.succeeded is False
    assert execution.failed_step_label == "MoveJ XY hover"
    assert "sequence stopped after MoveJ XY hover" in "\n".join(execution.logs)
    assert suction_calls == []


def test_click_plan_accepts_depth_descend_z_override():
    transform = DisplayTransform(0, 0, 640, 480, 640, 480)

    plan = build_click_pick_place_plan(
        mode="attach",
        display_xy=(10, 20),
        transform=transform,
        calibration=_linear_calibration(),
        hover_z_m=0.020,
        descend_distance_m=0.030,
        r_deg=0.0,
        return_to_hover=False,
        movej_motion_type=1,
        movel_motion_type=2,
        descend_z_m_override=0.015,
    )

    assert plan.descend_z_m == pytest.approx(0.02)
    assert plan.steps[1].target_pose[2] == pytest.approx(20.0)


def test_attach_plan_uses_absolute_mode_target_z_without_min_clamp_or_home_return():
    transform = DisplayTransform(0, 0, 640, 480, 640, 480)

    plan = build_click_pick_place_plan(
        mode="attach",
        display_xy=(10, 20),
        transform=transform,
        calibration=_linear_calibration(),
        hover_z_m=0.080,
        descend_distance_m=None,
        target_z_m=-0.070,
        r_deg=5.0,
        return_to_hover=False,
        movej_motion_type=1,
        movel_motion_type=2,
        return_home_pose_m=None,
    )

    assert [step.label for step in plan.steps] == [
        "MoveJ XY hover",
        "MoveL descend",
        "suction ON",
    ]
    assert plan.descend_z_m == pytest.approx(-0.070)
    assert plan.steps[0].target_pose == pytest.approx([110.0, -10.0, 80.0, 5.0])
    assert plan.steps[1].target_pose == pytest.approx([110.0, -10.0, -70.0, 5.0])


def test_detach_plan_uses_absolute_mode_target_z_and_returns_home():
    transform = DisplayTransform(0, 0, 640, 480, 640, 480)

    plan = build_click_pick_place_plan(
        mode="detach",
        display_xy=(10, 20),
        transform=transform,
        calibration=_linear_calibration(),
        hover_z_m=0.090,
        descend_distance_m=None,
        target_z_m=-0.050,
        r_deg=0.0,
        return_to_hover=False,
        movej_motion_type=1,
        movel_motion_type=2,
        return_home_pose_m=(0.16, 0.01, 0.06),
    )

    assert plan.steps[2].label == "suction OFF"
    assert plan.steps[2].suction_enabled is False
    assert plan.steps[1].target_pose[2] == pytest.approx(-50.0)
    assert plan.steps[-1].label == "MoveJ return home"
    assert plan.steps[-1].target_pose == pytest.approx([160.0, 10.0, 60.0, 0.0])

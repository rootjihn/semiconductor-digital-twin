import math

import pytest

from dobot_control.pixel_to_base import deproject_pixel_to_point


def test_deprojects_16uc1_depth_pixel_to_camera_optical_frame_meters():
    point = deproject_pixel_to_point(
        u=420,
        v=260,
        depth_raw=1500,
        encoding="16UC1",
        k=[500.0, 0.0, 320.0, 0.0, 500.0, 240.0, 0.0, 0.0, 1.0],
    )

    assert point == pytest.approx((0.3, 0.06, 1.5))


def test_deprojects_32fc1_depth_pixel_without_unit_conversion():
    point = deproject_pixel_to_point(
        u=270,
        v=300,
        depth_raw=2.0,
        encoding="32FC1",
        k=[500.0, 0.0, 320.0, 0.0, 400.0, 240.0, 0.0, 0.0, 1.0],
    )

    assert point == pytest.approx((-0.2, 0.3, 2.0))


def test_rejects_invalid_depth_values():
    assert (
        deproject_pixel_to_point(
            u=320,
            v=240,
            depth_raw=0,
            encoding="16UC1",
            k=[500.0, 0.0, 320.0, 0.0, 500.0, 240.0, 0.0, 0.0, 1.0],
        )
        is None
    )

    assert (
        deproject_pixel_to_point(
            u=320,
            v=240,
            depth_raw=math.nan,
            encoding="32FC1",
            k=[500.0, 0.0, 320.0, 0.0, 500.0, 240.0, 0.0, 0.0, 1.0],
        )
        is None
    )

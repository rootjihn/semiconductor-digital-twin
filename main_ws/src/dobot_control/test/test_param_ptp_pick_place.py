from dobot_control.param_ptp_pick_place import (
    FOLDED_HOME_JOINT_POSE,
    MOTION_TYPE_MOVJ_ANGLE,
    MOTION_TYPE_MOVJ_XYZ,
    MOTION_TYPE_MOVL_XYZ,
    PtpPointM,
    _triplet_from_values,
    build_param_ptp_steps,
)


def labels(steps):
    return [step.label for step in steps]


def test_build_full_pick_place_sequence():
    steps = build_param_ptp_steps(
        attach=PtpPointM(0.10, 0.02, 0.03),
        detach=PtpPointM(0.20, -0.01, 0.04),
    )

    assert labels(steps) == [
        'MoveJ attach hover',
        'MoveL attach descend',
        'suction ON',
        'MoveL attach hover',
        'MoveJ detach hover',
        'MoveL detach descend',
        'suction OFF',
        'MoveL detach hover',
        'MoveJ folded home',
    ]
    assert steps[0].motion_type == MOTION_TYPE_MOVJ_XYZ
    assert steps[0].target_pose == [100.0, 20.0, 90.0, 0.0]
    assert steps[1].motion_type == MOTION_TYPE_MOVL_XYZ
    assert steps[1].target_pose == [100.0, 20.0, 30.0, 0.0]
    assert steps[2].suction_enabled is True
    assert steps[4].target_pose == [200.0, -10.0, 100.0, 0.0]
    assert steps[5].target_pose == [200.0, -10.0, 40.0, 0.0]
    assert steps[6].suction_enabled is False
    assert steps[-1].motion_type == MOTION_TYPE_MOVJ_ANGLE
    assert steps[-1].target_pose == FOLDED_HOME_JOINT_POSE


def test_build_attach_only_sequence_still_returns_home():
    steps = build_param_ptp_steps(attach=PtpPointM(0.10, 0.02, 0.03), detach=None)

    assert labels(steps) == [
        'MoveJ attach hover',
        'MoveL attach descend',
        'suction ON',
        'MoveL attach hover',
        'MoveJ folded home',
    ]


def test_build_detach_only_sequence():
    steps = build_param_ptp_steps(attach=None, detach=PtpPointM(0.20, -0.01, 0.04))

    assert labels(steps) == [
        'MoveJ detach hover',
        'MoveL detach descend',
        'suction OFF',
        'MoveL detach hover',
        'MoveJ folded home',
    ]


def test_incomplete_group_is_skipped():
    point, missing = _triplet_from_values({'ax': '0.1', 'ay': '', 'az': '0.03'}, 'a')

    assert point is None
    assert missing == ['ay']


def test_complete_group_accepts_string_launch_values():
    point, missing = _triplet_from_values({'dx': '0.2', 'dy': '-0.01', 'dz': '0.04'}, 'd')

    assert point == PtpPointM(0.2, -0.01, 0.04)
    assert missing == []

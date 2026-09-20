"""Verify wheel direction, combined motion and invalid command handling."""

from arduino_bridge.velocity_protocol import wheel_command


def test_forward_and_reverse():
    assert wheel_command(0.08, 0, 0.20) == 'V1 80 80\n'
    assert wheel_command(-0.08, 0, 0.20) == 'V1 -80 -80\n'


def test_turns_match_physical_motor_mapping():
    assert wheel_command(0, 0.3, 0.20) == 'V1 30 -30\n'
    assert wheel_command(0, -0.3, 0.20) == 'V1 -30 30\n'


def test_curved_motion_and_proportional_saturation():
    assert wheel_command(0.10, 0.3, 0.20) == 'V1 100 54\n'
    assert wheel_command(0.20, 1.0, 0.20) == 'V1 100 33\n'


def test_individual_wheels_match_observed_hardware():
    assert wheel_command(0.02, 0.2, 0.20) == 'V1 40 0\n'
    assert wheel_command(0.02, -0.2, 0.20) == 'V1 0 40\n'


def test_stop_and_invalid_commands():
    assert wheel_command(0, 0, 0.20) == 'S'
    for invalid in (float('nan'), float('inf'), -float('inf')):
        assert wheel_command(invalid, 0, 0.20) == 'S'
        assert wheel_command(0, invalid, 0.20) == 'S'


def test_speed_limit_in_both_directions():
    assert wheel_command(0.15, 0, 0.20) == 'V1 100 100\n'
    assert wheel_command(-0.15, 0, 0.20) == 'V1 -100 -100\n'
    assert wheel_command(0, 2, 0.20) == 'V1 100 -100\n'

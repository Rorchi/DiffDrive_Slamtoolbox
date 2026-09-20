"""Verify wheel direction, combined motion and invalid command handling."""

from arduino_bridge.velocity_protocol import wheel_command


def test_forward_and_reverse():
    assert wheel_command(0.08, 0, 0.20) == 'V1 80 80\n'
    assert wheel_command(-0.08, 0, 0.20) == 'V1 -80 -80\n'


def test_turns_match_physical_motor_mapping():
    assert wheel_command(0, 0.3, 0.20) == 'V1 -30 30\n'
    assert wheel_command(0, -0.3, 0.20) == 'V1 30 -30\n'


def test_curved_motion_and_proportional_saturation():
    assert wheel_command(0.10, 0.3, 0.20) == 'V1 70 130\n'
    assert wheel_command(0.20, 1.0, 0.20) == 'V1 50 150\n'


def test_stop_and_invalid_commands():
    assert wheel_command(0, 0, 0.20) == 'S'
    for invalid in (float('nan'), float('inf'), -float('inf')):
        assert wheel_command(invalid, 0, 0.20) == 'S'
        assert wheel_command(0, invalid, 0.20) == 'S'

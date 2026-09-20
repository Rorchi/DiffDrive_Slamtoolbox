"""Check navigation limits and references before allowing on-robot tests."""

import json
from pathlib import Path
import xml.etree.ElementTree as ET

import yaml


ROOT = Path(__file__).resolve().parents[1]


def parameters(filename):
    """Read a checked-in ROS parameter document."""
    return yaml.safe_load((ROOT / 'config' / filename).read_text())


def test_velocity_envelope_fits_wheel_limit():
    config = parameters('nav2_navigation.yaml')
    bridge = parameters('arduino_bridge.yaml')['serial_bridge_node']['ros__parameters']
    smooth = config['velocity_smoother']['ros__parameters']
    vx, vy, wz = smooth['max_velocity']
    assert vy == 0.0
    assert vx + wz * bridge['wheel_base'] / 2 <= 0.100001
    assert smooth['velocity_timeout'] < bridge['cmd_vel_timeout']
    assert smooth['min_velocity'][0] == 0.0
    assert config['controller_server']['ros__parameters']['FollowPath']['desired_linear_vel'] <= vx


def test_cost_distance_matches_actual_inflation():
    nav = parameters('nav2_navigation.yaml')
    costmap = parameters('nav2_costmaps.yaml')['local_costmap']['local_costmap']['ros__parameters']
    rpp = nav['controller_server']['ros__parameters']['FollowPath']
    inflation = costmap['inflation_layer']
    assert rpp['inflation_cost_scaling_factor'] == inflation['cost_scaling_factor']
    assert rpp['cost_scaling_dist'] <= costmap['inflation_layer']['inflation_radius']
    assert rpp['use_collision_detection']
    assert not nav['planner_server']['ros__parameters']['GridBased']['allow_unknown']


def test_stop_zone_encloses_padded_footprint():
    nav = parameters('nav2_navigation.yaml')['collision_monitor']['ros__parameters']
    foot = parameters('nav2_footprint.yaml')['local_costmap']['local_costmap']['ros__parameters']
    points = json.loads(foot['footprint'])
    zone = nav['StopZone']['points']
    margin = foot['footprint_padding']
    assert min(zone[::2]) < min(p[0] for p in points) - margin
    assert max(zone[::2]) > max(p[0] for p in points) + margin
    assert min(zone[1::2]) < min(p[1] for p in points) - margin
    assert max(zone[1::2]) > max(p[1] for p in points) + margin
    assert nav['cmd_vel_in_topic'] != nav['cmd_vel_out_topic']
    assert nav['cmd_vel_out_topic'] == '/cmd_vel'
    assert nav['source_timeout'] <= 0.5


def test_behavior_trees_have_bounded_nonmoving_recovery():
    for path in (ROOT / 'behavior_trees').glob('*.xml'):
        root = ET.parse(path).getroot()
        assert root.find('.//RecoveryNode').attrib['number_of_retries'] == '2'
        for tag in ('Spin', 'BackUp', 'DriveOnHeading', 'ClearEntireCostmap'):
            assert root.find('.//' + tag) is None
        follow = root.find('.//FollowPath')
        assert follow.attrib['controller_id'] == 'FollowPath'
        assert follow.attrib['goal_checker_id'] == 'goal_checker'
        assert root.find('.//Wait') is not None

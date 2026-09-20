#!/usr/bin/env python3
"""Passively record Arduino battery telemetry alongside ROS motion data."""
import csv
from datetime import datetime
import math
from pathlib import Path
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from sensor_msgs.msg import BatteryState


class Recorder(Node):
    def __init__(self):
        super().__init__('speed_current_recorder')
        folder = Path(__file__).resolve().parents[2] / 'measurements'
        folder.mkdir(exist_ok=True)
        self.path = folder / (datetime.now().strftime('speed_current_%Y%m%d_%H%M%S_%f') + '.csv')
        self.file = self.path.open('x', newline='')
        self.writer = csv.writer(self.file)
        self.writer.writerow(['elapsed_s', 'phase', 'command_v_mps', 'command_w_rad_s',
                              'command_age_s', 'measured_v_mps', 'measured_w_rad_s',
                              'odom_age_s', 'voltage_V', 'ros_current_A',
                              'discharge_current_A', 'battery_present'])
        self.start = time.monotonic()
        self.command = (0.0, 0.0)
        self.command_time = -math.inf
        self.change_time = self.start
        self.odom = (math.nan, math.nan)
        self.odom_time = -math.inf
        self.groups = {}
        self.create_subscription(Twist, '/cmd_vel', self.on_command, qos_profile_sensor_data)
        self.create_subscription(Odometry, '/wheel/odometry_raw', self.on_odom, qos_profile_sensor_data)
        self.create_subscription(BatteryState, '/battery', self.on_battery, qos_profile_sensor_data)
        self.create_timer(3.0, self.status)
        self.count = 0
        print(f'Kayıt: {self.path}\nHazır. Test sonrası Ctrl+C ile bitir.', flush=True)

    def on_command(self, msg):
        now = time.monotonic()
        command = (msg.linear.x, msg.angular.z)
        if command != self.command or now - self.command_time > 0.5:
            self.change_time = now
        self.command, self.command_time = command, now

    def on_odom(self, msg):
        self.odom = (msg.twist.twist.linear.x, msg.twist.twist.angular.z)
        self.odom_time = time.monotonic()

    def on_battery(self, msg):
        now = time.monotonic()
        cmd_age, odom_age = now - self.command_time, now - self.odom_time
        phase = 'no_fresh_command'
        if cmd_age <= 0.5:
            phase = 'startup' if now - self.change_time < 1.0 else 'command_steady'
        self.writer.writerow([now-self.start, phase, *self.command, cmd_age,
                              *self.odom, odom_age, msg.voltage, msg.current,
                              -msg.current, msg.present])
        self.file.flush()
        self.count += 1
        if (phase == 'command_steady' and odom_age <= 0.3 and msg.present
                and all(math.isfinite(x) for x in (*self.odom, msg.current, msg.voltage))):
            key = tuple(round(x, 3) for x in self.command)
            self.groups.setdefault(key, []).append((*self.odom, -msg.current, msg.voltage))

    def status(self):
        print(f'{self.count} batarya mesajı kaydedildi.', flush=True)

    def finish(self):
        self.file.close()
        print(f'\nCSV: {self.path}')
        for (v, w), rows in self.groups.items():
            n = len(rows)
            print(f'Hedef v={v:.3f} m/s, w={w:.3f} rad/s; n={n}; '
                  f'ölçülen v ort={sum(r[0] for r in rows)/n:.4f} m/s; '
                  f'akım ort={sum(r[2] for r in rows)/n:.3f} A; '
                  f'yayımlanan akım maks={max(r[2] for r in rows):.3f} A; '
                  f'gerilim ort={sum(r[3] for r in rows)/n:.2f} V')
        if not self.groups:
            print('Özet için yeterli güncel/geçerli veri yok; CSV korunmuştur.')


def main():
    rclpy.init()
    node = Recorder()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.finish()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()

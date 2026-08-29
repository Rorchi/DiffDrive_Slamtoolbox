#!/usr/bin/env python3

import json
import math
import serial
import rclpy

from rclpy.node import Node

from sensor_msgs.msg import BatteryState, Imu, JointState
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Twist
from std_msgs.msg import Float32


class SerialBridgeNode(Node):

    def __init__(self):
        super().__init__('serial_bridge_node')

        # ---------------- SERIAL ----------------
        self.port = self.declare_parameter('port', '/dev/arduino').value
        self.baudrate = self.declare_parameter('baudrate', 115200).value

        try:
            self.ser = serial.Serial(
                self.port,
                self.baudrate,
                timeout=1.0
            )

            self.ser.setDTR(False)
            self.ser.setRTS(False)
            self.ser.flush()

            self.get_logger().info(
                f'Seri port {self.port} başarıyla açıldı.'
            )

        except Exception as e:
            self.get_logger().error(
                f'Seri port açılamadı: {e}'
            )
            return

        # ---------------- SUBSCRIBER ----------------
        self.cmd_sub = self.create_subscription(
            Twist,
            '/cmd_vel',
            self.cmd_vel_callback,
            10
        )

        # ---------------- PUBLISHERS ----------------
        self.imu_pub = self.create_publisher(
            Imu,
            '/imu/data',
            10
        )

        self.odom_pub = self.create_publisher(
            Odometry,
            '/odom',
            10
        )

        self.joint_pub = self.create_publisher(
            JointState,
            '/joint_states',
            10
        )

        self.battery_pub = self.create_publisher(
            BatteryState,
            '/battery_state',
            10
        )

        self.battery_power_pub = self.create_publisher(
            Float32,
            '/battery/power',
            10
        )

        # ---------------- ROBOT STATE ----------------
        self.wheel_radius = self.declare_parameter('wheel_radius', 0.04).value
        self.wheel_base = self.declare_parameter('wheel_base', 0.36).value
        self.encoder_ticks_per_rev = self.declare_parameter(
            'encoder_ticks_per_rev', 7000
        ).value

        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0

        self.prev_left = None
        self.prev_right = None

        self.last_time = self.get_clock().now()

        # ---------------- TIMER ----------------
        self.create_timer(0.02, self.read_serial)

    # ==========================================================
    # CMD_VEL CALLBACK
    # ==========================================================

    def cmd_vel_callback(self, msg):

        linear_x = msg.linear.x
        angular_z = msg.angular.z

        command = 'S'

        if linear_x > 0.0:
            command = 'W'

        elif linear_x < 0.0:
            command = 'X'

        elif angular_z > 0.0:
            command = 'A'

        elif angular_z < 0.0:
            command = 'D'

        else:
            command = 'S'

        try:
            self.ser.write(command.encode('utf-8'))

        except Exception as e:
            self.get_logger().error(
                f'Komut gönderme hatası: {e}'
            )

    # ==========================================================
    # SERIAL READ
    # ==========================================================

    def read_serial(self):

        if not self.ser.is_open:
            return

        try:

            if self.ser.in_waiting > 0:

                line = self.ser.readline() \
                    .decode('utf-8', errors='ignore') \
                    .strip()

                if not line:
                    return

                data = self.parse_line(line)

                if data is None:
                    return

                now = self.get_clock().now()

                dt = (
                    now - self.last_time
                ).nanoseconds * 1e-9

                if dt <= 0.0:
                    return

                self.publish_imu(now, data)
                self.publish_battery(now, data)
                self.update_odometry(now, dt, data)

                self.last_time = now

        except Exception as e:
            self.get_logger().error(
                f'Okuma Hatası: {e}'
            )

    # ==========================================================
    # PARSE SERIAL
    # ==========================================================

    def parse_line(self, line):

        try:

            values = json.loads(line)
            required_fields = {
                't_ms', 'ax', 'ay', 'az', 'gx', 'gy', 'gz', 'enc_l', 'enc_r'
            }
            if not isinstance(values, dict) or not required_fields.issubset(values):
                return None
            data = {key: float(values[key]) for key in required_fields}

            # Battery telemetry was added after the original bridge protocol.
            # Keep it optional so older firmware remains compatible.
            battery_fields = {
                'voltage', 'current', 'power', 'charge', 'capacity',
                'percentage'
            }
            if battery_fields.issubset(values):
                for key in battery_fields:
                    data[key] = float(values[key])
                data['battery_ok'] = bool(values.get('battery_ok', True))

            return data

        except (TypeError, ValueError, json.JSONDecodeError):
            return None

    # ==========================================================
    # IMU PUBLISH
    # ==========================================================

    def publish_imu(self, stamp, data):

        imu_msg = Imu()

        imu_msg.header.stamp = stamp.to_msg()
        imu_msg.header.frame_id = 'imu_link'

        imu_msg.linear_acceleration.x = float(
            data['ax']
        )

        imu_msg.linear_acceleration.y = float(
            data['ay']
        )

        imu_msg.linear_acceleration.z = data['az']

        imu_msg.angular_velocity.x = data['gx']
        imu_msg.angular_velocity.y = data['gy']

        imu_msg.angular_velocity.z = float(
            data['gz']
        )

        imu_msg.orientation.x = 0.0
        imu_msg.orientation.y = 0.0
        imu_msg.orientation.z = 0.0
        imu_msg.orientation.w = 1.0

        # Firmware yönelim (quaternion) göndermiyor.
        imu_msg.orientation_covariance[0] = -1.0

        imu_msg.angular_velocity_covariance = [
            0.01, 0.0, 0.0,
            0.0, 0.01, 0.0,
            0.0, 0.0, 0.01
        ]

        imu_msg.linear_acceleration_covariance = [
            0.01, 0.0, 0.0,
            0.0, 0.01, 0.0,
            0.0, 0.0, 0.01
        ]

        self.imu_pub.publish(imu_msg)

    # ==========================================================
    # BATTERY STATE PUBLISH
    # ==========================================================

    def publish_battery(self, stamp, data):

        if 'voltage' not in data:
            return

        battery_msg = BatteryState()
        battery_msg.header.stamp = stamp.to_msg()
        battery_msg.header.frame_id = 'battery_link'

        battery_ok = data['battery_ok']
        battery_msg.present = battery_ok
        battery_msg.power_supply_health = (
            BatteryState.POWER_SUPPLY_HEALTH_GOOD
            if battery_ok
            else BatteryState.POWER_SUPPLY_HEALTH_UNKNOWN
        )
        battery_msg.power_supply_technology = (
            BatteryState.POWER_SUPPLY_TECHNOLOGY_LIPO
        )

        if not battery_ok:
            battery_msg.voltage = math.nan
            battery_msg.current = math.nan
            battery_msg.power_supply_status = (
                BatteryState.POWER_SUPPLY_STATUS_UNKNOWN
            )
            battery_msg.charge = math.nan
            battery_msg.capacity = math.nan
            battery_msg.percentage = math.nan
            return self.battery_pub.publish(battery_msg)

        battery_msg.voltage = data['voltage']
        battery_msg.current = data['current']
        battery_msg.charge = data['charge']
        battery_msg.capacity = data['capacity']
        battery_msg.design_capacity = data['capacity']
        battery_msg.percentage = max(0.0, min(1.0, data['percentage']))
        battery_msg.location = 'main_battery'

        # Firmware follows BatteryState convention: discharge current is
        # negative and charge current is positive.
        if battery_msg.current < -0.01:
            battery_msg.power_supply_status = (
                BatteryState.POWER_SUPPLY_STATUS_DISCHARGING
            )
        elif battery_msg.current > 0.01:
            battery_msg.power_supply_status = (
                BatteryState.POWER_SUPPLY_STATUS_CHARGING
            )
        elif battery_msg.percentage >= 0.99:
            battery_msg.power_supply_status = (
                BatteryState.POWER_SUPPLY_STATUS_FULL
            )
        else:
            battery_msg.power_supply_status = (
                BatteryState.POWER_SUPPLY_STATUS_NOT_CHARGING
            )

        self.battery_pub.publish(battery_msg)

        power_msg = Float32()
        power_msg.data = data['power']
        self.battery_power_pub.publish(power_msg)

    # ==========================================================
    # JOINT STATE PUBLISH
    # ==========================================================

    def publish_joint_states(self, stamp, left_enc, right_enc):

        left_angle = (
            left_enc * 2.0 * math.pi
        ) / self.encoder_ticks_per_rev

        right_angle = (
            right_enc * 2.0 * math.pi
        ) / self.encoder_ticks_per_rev

        joint_msg = JointState()

        joint_msg.header.stamp = stamp.to_msg()

        joint_msg.name = [
            'left_front_wheel_joint',
            'right_front_wheel_joint',
            'left_rear_wheel_joint',
            'right_rear_wheel_joint'
        ]

        joint_msg.position = [
            left_angle,
            right_angle,
            left_angle,
            right_angle
        ]

        joint_msg.velocity = [
            0.0,
            0.0,
            0.0,
            0.0
        ]

        self.joint_pub.publish(joint_msg)

    # ==========================================================
    # ODOMETRY
    # ==========================================================

    def update_odometry(self, stamp, dt, data):

        left_enc = int(data['enc_l'])
        right_enc = int(data['enc_r'])

        self.publish_joint_states(stamp, left_enc, right_enc)

        if self.prev_left is None:

            self.prev_left = left_enc
            self.prev_right = right_enc

            return

        d_left_ticks = left_enc - self.prev_left
        d_right_ticks = right_enc - self.prev_right

        self.prev_left = left_enc
        self.prev_right = right_enc

        meters_per_tick = (
            2.0 * math.pi * self.wheel_radius
        ) / self.encoder_ticks_per_rev

        d_left = d_left_ticks * meters_per_tick
        d_right = d_right_ticks * meters_per_tick

        d_center = (d_left + d_right) / 2.0

        d_theta = (
            d_right - d_left
        ) / self.wheel_base

        self.x += d_center * math.cos(
            self.theta + d_theta / 2.0
        )

        self.y += d_center * math.sin(
            self.theta + d_theta / 2.0
        )

        self.theta += d_theta

        odom = Odometry()

        odom.header.stamp = stamp.to_msg()
        odom.header.frame_id = 'odom'
        odom.child_frame_id = 'base_link'

        odom.pose.pose.position.x = self.x
        odom.pose.pose.position.y = self.y

        odom.pose.pose.orientation.z = math.sin(
            self.theta / 2.0
        )

        odom.pose.pose.orientation.w = math.cos(
            self.theta / 2.0
        )

        odom.twist.twist.linear.x = d_center / dt
        odom.twist.twist.angular.z = d_theta / dt

        self.odom_pub.publish(odom)


def main(args=None):

    rclpy.init(args=args)

    node = SerialBridgeNode()

    try:
        rclpy.spin(node)

    except KeyboardInterrupt:
        pass

    finally:

        if hasattr(node, 'ser'):
            node.ser.close()

        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

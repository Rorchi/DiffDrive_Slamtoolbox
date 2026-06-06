#!/usr/bin/env python3

import math
import serial
import rclpy

from rclpy.node import Node

from std_msgs.msg import Float32
from sensor_msgs.msg import Imu
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Twist


class SerialBridgeNode(Node):

    def __init__(self):
        super().__init__('serial_bridge_node')

        # ---------------- SERIAL ----------------
        self.port = '/dev/arduino'
        self.baudrate = 115200

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

        self.oxygen_pub = self.create_publisher(
            Float32,
            '/oxygen',
            10
        )

        # ---------------- ROBOT STATE ----------------
        self.wheel_radius = 0.04
        self.wheel_base = 0.36
        self.encoder_ticks_per_rev = 7000

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

                if not line or "O2:" not in line:
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
                self.publish_oxygen(data)
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

            values = {}

            parts = line.split(',')

            for part in parts:

                if ':' in part:

                    key, val = part.split(':')

                    values[key.strip()] = float(val.strip())

            return values

        except Exception:
            return None

    # ==========================================================
    # IMU PUBLISH
    # ==========================================================

    def publish_imu(self, stamp, data):

        imu_msg = Imu()

        imu_msg.header.stamp = stamp.to_msg()
        imu_msg.header.frame_id = 'imu_link'

        imu_msg.linear_acceleration.x = float(
            data.get('GX', 0.0)
        )

        imu_msg.linear_acceleration.y = float(
            data.get('GY', 0.0)
        )

        imu_msg.linear_acceleration.z = 0.0

        imu_msg.angular_velocity.x = 0.0
        imu_msg.angular_velocity.y = 0.0

        imu_msg.angular_velocity.z = float(
            data.get('GZ', 0.0)
        )

        imu_msg.orientation.x = 0.0
        imu_msg.orientation.y = 0.0
        imu_msg.orientation.z = 0.0
        imu_msg.orientation.w = 1.0

        imu_msg.orientation_covariance = [
            0.01, 0.0, 0.0,
            0.0, 0.01, 0.0,
            0.0, 0.0, 0.01
        ]

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
    # OXYGEN PUBLISH
    # ==========================================================

    def publish_oxygen(self, data):

        msg = Float32()

        msg.data = float(
            data.get('O2', 0.0)
        )

        self.oxygen_pub.publish(msg)

    # ==========================================================
    # ODOMETRY
    # ==========================================================

    def update_odometry(self, stamp, dt, data):

        left_enc = int(data.get('E1', 0))
        right_enc = int(data.get('E2', 0))

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
            d_left - d_right
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
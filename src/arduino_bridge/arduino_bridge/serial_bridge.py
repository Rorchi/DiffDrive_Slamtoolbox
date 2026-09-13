#!/usr/bin/env python3
# Amaç: Arduino ile ROS 2 arasında komut ve sensör verisi aktarır.
# Çalışma: Seri porttan JSON paketlerini okuyup IMU, encoder, batarya, tekerlek
# odometrisi ve eklem durumlarını yayımlar. /cmd_vel komutlarını Arduino’ya
# iletir; komut zaman aşımında durdurma komutu gönderir. Odometri TF yayını
# publish_odom_tf parametresine bağlıdır.

"""Arduino Mega USB/JSON <-> ROS 2 bridge for Kâşif Çelebi."""

import json
import math

import rclpy
import serial
from geometry_msgs.msg import TransformStamped, Twist
from nav_msgs.msg import Odometry
from rclpy.node import Node
from sensor_msgs.msg import BatteryState, Imu, JointState
from std_msgs.msg import Bool, Float32, Int64MultiArray
from tf2_ros import TransformBroadcaster


class SerialBridgeNode(Node):
    def __init__(self):
        super().__init__('serial_bridge_node')

        self.port = self.declare_parameter('port', '/dev/arduino').value
        self.baudrate = int(self.declare_parameter('baudrate', 115200).value)
        self.wheel_radius = float(
            self.declare_parameter('wheel_radius', 0.04).value
        )
        self.wheel_base = float(
            self.declare_parameter('wheel_base', 0.20).value
        )
        self.encoder_ticks_per_rev = float(
            self.declare_parameter('encoder_ticks_per_rev', 7000.0).value
        )
        self.imu_gyro_z_scale = float(
            self.declare_parameter('imu_gyro_z_scale', 1.0).value
        )
        self.wheel_yaw_scale = float(
            self.declare_parameter('wheel_yaw_scale', 1.0).value
        )
        self.publish_odom_tf = bool(
            self.declare_parameter('publish_odom_tf', False).value
        )
        self.odom_topic = str(
            self.declare_parameter(
                'odom_topic', '/wheel/odometry_raw'
            ).value
        )
        self.cmd_vel_timeout = float(
            self.declare_parameter('cmd_vel_timeout', 0.5).value
        )
        self.max_encoder_delta = int(
            self.declare_parameter('max_encoder_delta', 100000).value
        )
        self.max_serial_packets = int(
            self.declare_parameter('max_serial_packets', 10).value
        )
        self.max_device_dt_ms = int(
            self.declare_parameter('max_device_dt_ms', 1000).value
        )

        if self.wheel_radius <= 0.0:
            raise ValueError('wheel_radius sifirdan buyuk olmalidir')
        if self.wheel_base <= 0.0:
            raise ValueError('wheel_base sifirdan buyuk olmalidir')
        if self.encoder_ticks_per_rev <= 0.0:
            raise ValueError('encoder_ticks_per_rev sifirdan buyuk olmalidir')
        if self.imu_gyro_z_scale == 0.0:
            raise ValueError('imu_gyro_z_scale sifir olamaz')
        if self.wheel_yaw_scale == 0.0:
            raise ValueError('wheel_yaw_scale sifir olamaz')
        if self.cmd_vel_timeout <= 0.0:
            raise ValueError('cmd_vel_timeout sifirdan buyuk olmalidir')
        if self.max_encoder_delta <= 0:
            raise ValueError('max_encoder_delta sifirdan buyuk olmalidir')
        if self.max_serial_packets <= 0:
            raise ValueError('max_serial_packets sifirdan buyuk olmalidir')
        if self.max_device_dt_ms <= 0:
            raise ValueError('max_device_dt_ms sifirdan buyuk olmalidir')

        self.ser = None
        try:
            self.ser = serial.Serial(
                self.port,
                self.baudrate,
                timeout=0.2,
                write_timeout=0.2,
            )
            self.ser.setDTR(False)
            self.ser.setRTS(False)
            self.ser.reset_input_buffer()
            self.get_logger().info(
                f'Seri port {self.port}, {self.baudrate} baud ile acildi.'
            )
        except (OSError, serial.SerialException) as exc:
            self.get_logger().fatal(f'Seri port acilamadi: {exc}')
            raise

        self.cmd_sub = self.create_subscription(
            Twist, '/cmd_vel', self.cmd_vel_callback, 10
        )

        self.imu_pub = self.create_publisher(Imu, '/imu/data_raw', 10)
        self.encoder_pub = self.create_publisher(
            Int64MultiArray, '/wheel/encoders', 10
        )
        self.odom_pub = self.create_publisher(Odometry, self.odom_topic, 10)
        self.joint_pub = self.create_publisher(
            JointState, '/joint_states', 10
        )
        self.battery_pub = self.create_publisher(
            BatteryState, '/battery', 10
        )
        self.battery_power_pub = self.create_publisher(
            Float32, '/battery/power', 10
        )
        self.battery_time_pub = self.create_publisher(
            Float32, '/battery/remaining_minutes', 10
        )
        self.low_battery_pub = self.create_publisher(
            Bool, '/battery/low', 10
        )

        self.tf_broadcaster = (
            TransformBroadcaster(self) if self.publish_odom_tf else None
        )

        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0
        self.prev_left = None
        self.prev_right = None
        self.prev_device_time_ms = None
        self.last_cmd_time = self.get_clock().now()
        self.stop_command_sent = True

        self.create_timer(0.02, self.read_serial)
        self.create_timer(0.05, self.check_cmd_vel_timeout)

        if self.publish_odom_tf:
            self.get_logger().warning(
                'odom -> base_link TF serial_bridge tarafindan yayinlaniyor'
            )
        else:
            self.get_logger().info(
                'Odometri TF yayini kapali; odom -> base_link EKF\'ye ait'
            )

    def cmd_vel_callback(self, msg):
        if msg.linear.x > 0.0:
            command = 'W'
        elif msg.linear.x < 0.0:
            command = 'X'
        elif msg.angular.z > 0.0:
            command = 'D'
        elif msg.angular.z < 0.0:
            command = 'A'
        else:
            command = 'S'

        self.last_cmd_time = self.get_clock().now()
        self.stop_command_sent = command == 'S'
        self.write_command(command)

    def write_command(self, command):
        try:
            self.ser.write(command.encode('ascii'))
        except (
            OSError,
            serial.SerialException,
            serial.SerialTimeoutException,
        ) as exc:
            self.get_logger().error(
                f'Komut gonderme hatasi: {exc}', throttle_duration_sec=5.0
            )

    def check_cmd_vel_timeout(self):
        if self.stop_command_sent:
            return

        elapsed = (
            self.get_clock().now() - self.last_cmd_time
        ).nanoseconds * 1e-9
        if elapsed >= self.cmd_vel_timeout:
            self.write_command('S')
            self.stop_command_sent = True
            self.get_logger().warning(
                'cmd_vel zaman asimi: dur komutu gonderildi',
                throttle_duration_sec=5.0,
            )

    def read_serial(self):
        if self.ser is None or not self.ser.is_open:
            return

        try:
            packets_read = 0
            while (
                self.ser.in_waiting > 0
                and packets_read < self.max_serial_packets
            ):
                line = self.ser.readline().decode(
                    'utf-8', errors='replace'
                ).strip()
                packets_read += 1
                if not line:
                    continue

                data = self.parse_line(line)
                if data is None:
                    self.get_logger().warning(
                        'Gecersiz seri paket yok sayildi',
                        throttle_duration_sec=5.0,
                    )
                    continue

                now = self.get_clock().now()
                if data['imu_ok']:
                    self.publish_imu(now, data)
                self.publish_battery(now, data)
                self.update_odometry(now, data)
        except (OSError, serial.SerialException) as exc:
            self.get_logger().error(
                f'Seri port okuma hatasi: {exc}',
                throttle_duration_sec=5.0,
            )

    @staticmethod
    def parse_line(line):
        try:
            values = json.loads(line)
            required_fields = {
                't_ms', 'ax', 'ay', 'az', 'gx', 'gy', 'gz',
                'enc_l', 'enc_r',
            }
            if not isinstance(values, dict):
                return None
            if not required_fields.issubset(values):
                return None

            data = {
                key: float(values[key])
                for key in ('ax', 'ay', 'az', 'gx', 'gy', 'gz')
            }
            data['t_ms'] = int(values['t_ms'])
            data['enc_l'] = int(values['enc_l'])
            data['enc_r'] = int(values['enc_r'])
            data['imu_ok'] = values.get('imu_ok', True) is True
            data['battery_ok'] = values.get('battery_ok', False) is True
            data['low_battery'] = values.get('low_battery', False) is True

            battery_fields = (
                'voltage', 'current', 'power', 'charge',
                'capacity', 'percentage',
            )
            for key in battery_fields:
                if key in values:
                    data[key] = float(values[key])

            remaining = values.get('remaining_minutes')
            data['remaining_minutes'] = (
                None if remaining is None else float(remaining)
            )
            numeric_values = [
                value for value in data.values()
                if isinstance(value, (int, float))
                and not isinstance(value, bool)
            ]
            if not all(math.isfinite(value) for value in numeric_values):
                return None
            return data
        except (TypeError, ValueError, json.JSONDecodeError):
            return None

    def publish_imu(self, stamp, data):
        msg = Imu()
        msg.header.stamp = stamp.to_msg()
        msg.header.frame_id = 'imu_link'
        msg.orientation.w = 1.0
        msg.orientation_covariance[0] = -1.0
        msg.angular_velocity.x = data['gx']
        msg.angular_velocity.y = data['gy']
        msg.angular_velocity.z = data['gz'] * self.imu_gyro_z_scale
        msg.linear_acceleration.x = data['ax']
        msg.linear_acceleration.y = data['ay']
        msg.linear_acceleration.z = data['az']
        msg.angular_velocity_covariance = [
            0.01, 0.0, 0.0,
            0.0, 0.01, 0.0,
            0.0, 0.0, 0.01,
        ]
        msg.linear_acceleration_covariance = [
            0.01, 0.0, 0.0,
            0.0, 0.01, 0.0,
            0.0, 0.0, 0.01,
        ]
        self.imu_pub.publish(msg)

    def publish_battery(self, stamp, data):
        msg = BatteryState()
        msg.header.stamp = stamp.to_msg()
        msg.header.frame_id = 'base_link'
        msg.temperature = math.nan
        msg.cell_voltage = [math.nan] * 4
        msg.power_supply_technology = (
            BatteryState.POWER_SUPPLY_TECHNOLOGY_LIPO
        )
        msg.location = 'main_battery'

        power_msg = Float32()
        remaining_msg = Float32()
        low_msg = Bool()

        required = {
            'voltage', 'current', 'power', 'charge',
            'capacity', 'percentage',
        }
        battery_ok = data['battery_ok'] and required.issubset(data)

        if not battery_ok:
            msg.voltage = math.nan
            msg.current = math.nan
            msg.charge = math.nan
            msg.capacity = math.nan
            msg.design_capacity = 3.3
            msg.percentage = math.nan
            msg.power_supply_status = (
                BatteryState.POWER_SUPPLY_STATUS_UNKNOWN
            )
            msg.power_supply_health = (
                BatteryState.POWER_SUPPLY_HEALTH_UNKNOWN
            )
            msg.present = False
            power_msg.data = math.nan
            remaining_msg.data = math.nan
            low_msg.data = False
        else:
            msg.voltage = data['voltage']
            msg.current = data['current']
            msg.charge = data['charge']
            msg.capacity = data['capacity']
            msg.design_capacity = data['capacity']
            msg.percentage = max(0.0, min(1.0, data['percentage']))
            msg.power_supply_health = BatteryState.POWER_SUPPLY_HEALTH_GOOD
            msg.present = True
            power_msg.data = data['power']
            remaining = data['remaining_minutes']
            remaining_msg.data = (
                math.nan if remaining is None else remaining
            )
            low_msg.data = data['low_battery']

            if msg.current < -0.01:
                msg.power_supply_status = (
                    BatteryState.POWER_SUPPLY_STATUS_DISCHARGING
                )
            elif msg.current > 0.01:
                msg.power_supply_status = (
                    BatteryState.POWER_SUPPLY_STATUS_CHARGING
                )
            elif msg.percentage >= 0.99:
                msg.power_supply_status = (
                    BatteryState.POWER_SUPPLY_STATUS_FULL
                )
            else:
                msg.power_supply_status = (
                    BatteryState.POWER_SUPPLY_STATUS_NOT_CHARGING
                )

        self.battery_pub.publish(msg)
        self.battery_power_pub.publish(power_msg)
        self.battery_time_pub.publish(remaining_msg)
        self.low_battery_pub.publish(low_msg)

    def publish_joint_states(self, stamp, left_enc, right_enc):
        left_angle = (
            left_enc * 2.0 * math.pi
        ) / self.encoder_ticks_per_rev
        right_angle = (
            right_enc * 2.0 * math.pi
        ) / self.encoder_ticks_per_rev

        msg = JointState()
        msg.header.stamp = stamp.to_msg()
        msg.name = [
            'left_front_wheel_joint',
            'right_front_wheel_joint',
            'left_rear_wheel_joint',
            'right_rear_wheel_joint',
        ]
        msg.position = [
            left_angle, right_angle, left_angle, right_angle,
        ]
        msg.velocity = [0.0, 0.0, 0.0, 0.0]
        self.joint_pub.publish(msg)

    def update_odometry(self, stamp, data):
        left_enc = int(data['enc_l'])
        right_enc = int(data['enc_r'])

        self.encoder_pub.publish(
            Int64MultiArray(data=[left_enc, right_enc])
        )
        self.publish_joint_states(stamp, left_enc, right_enc)

        if self.prev_left is None:
            self.reset_encoder_baseline(left_enc, right_enc, data['t_ms'])
            return

        delta_ms = self.device_time_delta_ms(data['t_ms'])
        if delta_ms is None or delta_ms > self.max_device_dt_ms:
            self.get_logger().warning(
                'Arduino zamani resetlendi veya veri araligi cok buyuk; '
                'encoder referansi yenilendi',
                throttle_duration_sec=5.0,
            )
            self.reset_encoder_baseline(left_enc, right_enc, data['t_ms'])
            return
        dt = delta_ms / 1000.0

        d_left_ticks = left_enc - self.prev_left
        d_right_ticks = right_enc - self.prev_right
        if (
            abs(d_left_ticks) > self.max_encoder_delta
            or abs(d_right_ticks) > self.max_encoder_delta
        ):
            self.get_logger().warning(
                'Fiziksel siniri asan encoder sicrama paketi reddedildi',
                throttle_duration_sec=5.0,
            )
            self.reset_encoder_baseline(left_enc, right_enc, data['t_ms'])
            return

        self.prev_left = left_enc
        self.prev_right = right_enc
        self.prev_device_time_ms = data['t_ms'] & 0xFFFFFFFF

        meters_per_tick = (
            2.0 * math.pi * self.wheel_radius
        ) / self.encoder_ticks_per_rev
        d_left = d_left_ticks * meters_per_tick
        d_right = d_right_ticks * meters_per_tick
        d_center = (d_left + d_right) / 2.0
        d_theta = (
            (d_right - d_left) / self.wheel_base
        ) * self.wheel_yaw_scale

        self.x += d_center * math.cos(self.theta + d_theta / 2.0)
        self.y += d_center * math.sin(self.theta + d_theta / 2.0)
        self.theta = math.atan2(
            math.sin(self.theta + d_theta),
            math.cos(self.theta + d_theta),
        )

        odom = Odometry()
        odom.header.stamp = stamp.to_msg()
        odom.header.frame_id = 'odom'
        odom.child_frame_id = 'base_link'
        odom.pose.pose.position.x = self.x
        odom.pose.pose.position.y = self.y
        odom.pose.pose.orientation.z = math.sin(self.theta / 2.0)
        odom.pose.pose.orientation.w = math.cos(self.theta / 2.0)
        odom.twist.twist.linear.x = d_center / dt
        odom.twist.twist.angular.z = d_theta / dt
        odom.pose.covariance = [
            0.02, 0.0, 0.0, 0.0, 0.0, 0.0,
            0.0, 0.05, 0.0, 0.0, 0.0, 0.0,
            0.0, 0.0, 1.0e6, 0.0, 0.0, 0.0,
            0.0, 0.0, 0.0, 1.0e6, 0.0, 0.0,
            0.0, 0.0, 0.0, 0.0, 1.0e6, 0.0,
            0.0, 0.0, 0.0, 0.0, 0.0, 0.05,
        ]
        odom.twist.covariance = [
            0.05, 0.0, 0.0, 0.0, 0.0, 0.0,
            0.0, 0.10, 0.0, 0.0, 0.0, 0.0,
            0.0, 0.0, 1.0e6, 0.0, 0.0, 0.0,
            0.0, 0.0, 0.0, 1.0e6, 0.0, 0.0,
            0.0, 0.0, 0.0, 0.0, 1.0e6, 0.0,
            0.0, 0.0, 0.0, 0.0, 0.0, 0.05,
        ]
        self.odom_pub.publish(odom)

        if self.tf_broadcaster is not None:
            transform = TransformStamped()
            transform.header.stamp = odom.header.stamp
            transform.header.frame_id = 'odom'
            transform.child_frame_id = 'base_link'
            transform.transform.translation.x = self.x
            transform.transform.translation.y = self.y
            transform.transform.rotation.z = math.sin(self.theta / 2.0)
            transform.transform.rotation.w = math.cos(self.theta / 2.0)
            self.tf_broadcaster.sendTransform(transform)

    def device_time_delta_ms(self, current_time_ms):
        current = current_time_ms & 0xFFFFFFFF
        previous = self.prev_device_time_ms
        if previous is None:
            return None
        if current >= previous:
            delta = current - previous
        elif previous - current > 0x80000000:
            delta = (0x100000000 - previous) + current
        else:
            return None
        return delta if delta > 0 else None

    def reset_encoder_baseline(self, left_enc, right_enc, device_time_ms):
        self.prev_left = left_enc
        self.prev_right = right_enc
        self.prev_device_time_ms = device_time_ms & 0xFFFFFFFF

    def close_serial(self):
        if self.ser is not None and self.ser.is_open:
            try:
                self.ser.write(b'S')
                self.ser.flush()
            except (
                OSError,
                serial.SerialException,
                serial.SerialTimeoutException,
            ):
                pass
            self.ser.close()


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = SerialBridgeNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.close_serial()
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()

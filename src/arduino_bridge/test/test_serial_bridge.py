# Amaç: Seri veri çözümleme ve cihaz zaman hesabını doğrular.
# Çalışma: pytest ile geçerli, eksik ve sonlu olmayan JSON değerlerini sınar;
# cihaz sayacının normal ilerlemesini, taşmasını ve geriye gitmesini
# seri port açmadan kontrol eder.

from arduino_bridge.serial_bridge import SerialBridgeNode


VALID_PACKET = (
    '{"t_ms":100,"ax":0,"ay":0,"az":9.81,'
    '"gx":0,"gy":0,"gz":0,"enc_l":10,"enc_r":11}'
)


def test_parse_valid_packet():
    data = SerialBridgeNode.parse_line(VALID_PACKET)

    assert data is not None
    assert data['t_ms'] == 100
    assert data['enc_l'] == 10
    assert data['imu_ok'] is True


def test_parse_rejects_missing_and_non_finite_values():
    assert SerialBridgeNode.parse_line('{"t_ms":1}') is None
    assert SerialBridgeNode.parse_line(
        VALID_PACKET.replace('9.81', 'NaN')
    ) is None


def test_device_time_delta_and_wraparound():
    node = object.__new__(SerialBridgeNode)

    node.prev_device_time_ms = 90
    assert node.device_time_delta_ms(100) == 10

    node.prev_device_time_ms = 0xFFFFFFF0
    assert node.device_time_delta_ms(5) == 21

    node.prev_device_time_ms = 100
    assert node.device_time_delta_ms(90) is None

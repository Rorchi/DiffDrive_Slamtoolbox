<!--
Amaç: Arduino ile Jetson arasında kullanılan seri mesaj sözleşmesini açıklar.
Çalışma: Bağlantı, JSON alanları, birimler ve komut biçimleri üzerinden firmware
ile ROS 2 köprüsünün aynı veriyi nasıl yorumlaması gerektiğini tanımlar.
-->

# Arduino - Jetson seri protokolü

## Bağlantı

Mega2560 Pro Mini kartı USB ile Jetson'a bağlanır. Jetson, ATmega2560'a
doğrudan erişmez; karttaki USB-seri dönüştürücüsünün sunduğu seri portu okur.
CH340/CH341 tabanlı kartlar için udev kuralı `scripts/usb_serial/` altında
bulunur ve hedefte `/dev/arduino` bağlantısını oluşturur.

Kuralı Jetson'a kurduktan sonra kullanıcı `dialout` grubunda olmalıdır:

```bash
sudo install -m 644 scripts/usb_serial/99-kasif-usb-serial.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger
sudo usermod -aG dialout $USER
```

Grup değişikliğinin etkinleşmesi için yeniden oturum açın. Bağlantıyı
`ls -l /dev/arduino` ile doğrulayın.

## Mesaj biçimi

Arduino her satırda bir JSON nesnesi gönderir. `serial_bridge` bu biçimi
doğrudan işler:

```json
{"t_ms":1121,"ax":-0.014365,"ay":0.002394,"az":12.205640,"gx":0.000224,"gy":0.000685,"gz":0.000116,"enc_l":0,"enc_r":0}
```

- `t_ms`: Arduino açıldıktan sonraki zaman, milisaniye.
- `ax`, `ay`, `az`: doğrusal ivme, m/s².
- `gx`, `gy`, `gz`: açısal hız, rad/s.
- `enc_l`, `enc_r`: sol ve sağ encoder'ın kümülatif tick sayısı.

İsteğe bağlı sağlık ve batarya alanları şunlardır: `imu_ok`, `battery_ok`,
`low_battery`, `voltage`, `current`, `power`, `charge`, `capacity`,
`percentage` ve `remaining_minutes`.

Köprü `/imu/data_raw`, `/wheel/odometry_raw`, `/wheel/encoders`, `/battery`
ve `/joint_states` yayınlar. Firmware yönelim
(quaternion) göndermediği için `Imu.orientation` bilinmiyor olarak işaretlenir.
Sabit halde ivme vektörünün büyüklüğü yaklaşık 9.81 m/s² olmalıdır; bu değer
farklıysa IMU ölçeklendirmesi/kalibrasyonu firmware tarafında düzeltilmelidir.

Varsayılan yapılandırmada köprü `odom -> base_link` TF'sini yayınlamaz.
Bu dönüşümün tek sahibi `robot_localization` EKF düğümüdür. Köprü yalnızca
EKF kullanılmayan bağımsız testlerde `publish_odom_tf: true` ile TF yayınlar.
Son `/cmd_vel` mesajından sonra 0.5 saniye içinde yeni komut gelmezse köprü
güvenlik amacıyla Arduino'ya dur (`S`) komutu gönderir.

IMU gyro yönü `imu_gyro_z_scale`, encoder tabanlı yaw yönü ise
`wheel_yaw_scale` ile kalibre edilir. Kaşif Çelebi'nin ölçülen yapılandırması
IMU için `1.0`, wheel yaw için `-1.0` kullanır. Bu çarpanlar ham seri
protokolünü değiştirmez ve teleop komut eşlemesine uygulanmaz.

Araç firmware'indeki motor yönlerine göre pozitif `/cmd_vel.angular.z`
Arduino'ya `D`, negatif değer ise `A` olarak gönderilir. Böylece standart
`teleop_twist_keyboard` kullanımında `J` fiziksel sola, `L` fiziksel sağa
döndürür.

## Sağlık kontrolleri

```bash
ros2 topic echo /imu/data_raw --once
ros2 topic echo /wheel/odometry_raw --once
ros2 topic hz /imu/data_raw
ros2 run tf2_ros tf2_echo odom base_link
```

Firmware kaynak kodu bu depoda henüz bulunmadığından `arduino/mega2560/`
altına, kullanılan `.ino` dosyası ve pin bağlantı şeması eklenmelidir.

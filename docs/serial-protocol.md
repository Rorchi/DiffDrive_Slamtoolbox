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

Köprü `/imu/data`, `/odom` ve `/joint_states` yayınlar. Firmware yönelim
(quaternion) göndermediği için `Imu.orientation` bilinmiyor olarak işaretlenir.
Sabit halde ivme vektörünün büyüklüğü yaklaşık 9.81 m/s² olmalıdır; bu değer
farklıysa IMU ölçeklendirmesi/kalibrasyonu firmware tarafında düzeltilmelidir.

## Sağlık kontrolleri

```bash
ros2 topic echo /imu/data --once
ros2 topic echo /odom --once
ros2 topic hz /imu/data
ros2 run tf2_ros tf2_echo odom base_link
```

Firmware kaynak kodu bu depoda henüz bulunmadığından `arduino/mega2560/`
altına, kullanılan `.ino` dosyası ve pin bağlantı şeması eklenmelidir.

<!--
Amaç: SLAM hazırlığı, kalibrasyon ve hata giderme çalışmalarını belgeler.
Çalışma: TF zinciri, sensör füzyonu ve haritalama ayarlarını yapılan kontroller
ve bulgularla açıklar; robotun haritalama kurulumuna başvuru sağlar.
-->

# Kaşif Çelebi SLAM hazırlık, kalibrasyon ve hata giderme raporu

## 1. Amaç

Bu çalışma, diferansiyel sürüşlü Kaşif Çelebi robotunu ROS 2 Humble üzerinde
`robot_localization`, RPLidar ve `slam_toolbox` kullanarak haritalamaya hazır
hâle getirmek için yapıldı.

Hedef TF zinciri:

```text
map --slam_toolbox--> odom --robot_localization/EKF--> base_link
                                                     ├── imu_link
                                                     └── laser_frame
```

Bu yapıda:

- Arduino köprüsü ham encoder odometrisi ile ham IMU mesajlarını yayınlar.
- EKF, encoder ve IMU verisini birleştirerek kesintisiz lokal odometri üretir.
- `slam_toolbox`, lidar taramalarını kullanarak `map -> odom` düzeltmesini
  yayınlar.
- Aynı TF'nin birden fazla düğüm tarafından yayınlanmasına izin verilmez.

## 2. Başlangıçtaki proje durumu

İlk incelemede aşağıdaki parçalar mevcuttu:

- Arduino JSON seri köprüsü
- `/odom`, IMU ve joint-state yayınları
- RPLidar A1 launch entegrasyonu
- Robot URDF/Xacro modeli
- Donanım ve robot-model launch dosyaları

Eksik veya sorunlu kısımlar:

- `robot_localization` kurulmamıştı.
- EKF parametre dosyası yoktu.
- `mapping.launch.py` ve `slam_toolbox` parametreleri yoktu.
- Arduino köprüsü doğrudan `odom -> base_link` TF'si yayımlıyordu.
- EKF de aynı TF'yi yayınladığında TF çakışması oluşacaktı.
- Odom mesajlarının covariance alanları boştu.
- Odometri zaman farkı Jetson'ın paket işleme zamanından hesaplanıyordu.
- Encoder reseti ve sayaç taşmasına karşı koruma yoktu.
- `/cmd_vel` kesildiğinde otomatik durdurma watchdog'u yoktu.
- IMU, encoder yaw yönü ve etkin tekerlek açıklığı kalibre edilmemişti.

## 3. SLAM öncesi yapılan düzeltmeler

### 3.1 Ham topic yapısı

Arduino köprüsü şu topic'leri yayınlayacak şekilde düzenlendi:

```text
/imu/data_raw
/wheel/odometry_raw
/wheel/encoders
/joint_states
/battery
/battery/power
/battery/remaining_minutes
/battery/low
```

EKF çıktısı:

```text
/odometry/filtered
```

Ham odometri ile filtrelenmiş odometrinin farklı topic'lerde tutulması,
verinin kaynağını ve filtre sonucunu ayrı ayrı analiz etmeyi kolaylaştırdı.

### 3.2 TF çakışmasının önlenmesi

Arduino köprüsüne aşağıdaki parametre eklendi:

```yaml
publish_odom_tf: false
```

Nihai TF sorumluluğu:

```text
slam_toolbox          map -> odom
robot_localization    odom -> base_link
robot_state_publisher base_link -> sensör ve tekerlek frame'leri
serial_bridge         dinamik TF yayınlamaz
```

Köprü, yalnızca EKF kullanılmayan bağımsız testlerde
`publish_odom_tf: true` ile TF yayınlayabilir.

### 3.3 Odometri güvenilirliği

`Odometry.pose.covariance` ve `Odometry.twist.covariance` alanlarına
muhafazakâr başlangıç değerleri eklendi. Böylece EKF ham encoder ölçümünü
kusursuz bir ölçüm olarak değerlendirmiyor.

Diferansiyel robotun yana hareket edemediği bilgisi EKF'ye `vy = 0` ölçümü
olarak verildi. Bu değişiklik yanal covariance büyümesini sınırlar.

### 3.4 Zamanlama ve encoder güvenliği

- Odometri `dt` hesabı Arduino'nun `t_ms` alanına geçirildi.
- 32-bit milisaniye sayacı taşması desteklendi.
- Arduino yeniden başlarsa encoder referansı sıfırlanıyor.
- Fiziksel sınırı aşan encoder sıçramaları reddediliyor.
- Bir timer çağrısında seri tampondan birden fazla paket okunabiliyor.
- `NaN` ve sonsuz sensör değerleri reddediliyor.

### 3.5 Hareket güvenliği

Son `/cmd_vel` mesajından sonra yeni komut gelmezse köprü Arduino'ya dur
komutu gönderir:

```yaml
cmd_vel_timeout: 0.5
```

Bu watchdog, teleop veya ROS düğümü beklenmedik şekilde kapanırsa aracın son
hareket komutuyla devam etmesini önler.

## 4. EKF sabit durum testi

İlk sabit kayıt:

```text
/home/orin/stationary_ekf_check
```

Kayıt süresi yaklaşık 92.6 saniyeydi.

Ölçülen topic frekansları:

```text
/imu/data_raw          10.00 Hz
/wheel/odometry_raw    10.00 Hz
/odometry/filtered     10.00 Hz
```

IMU sonuçları:

```text
ortalama ax            -0.0043 m/s²
ortalama ay            -0.0022 m/s²
ortalama az             9.8081 m/s²
ivme vektörü            9.8084 m/s²
gyro-z ortalama bias   -0.0000808 rad/s
gyro-z std. sapma       0.001399 rad/s
```

Encoder odometrisi araç hareketsizken sıfır konum ve hız değişimi gösterdi.
EKF yaklaşık 92 saniyede `0.34 derece` yaw sürüklenmesi gösterdi. Bu değer
küçüktü; fakat EKF'ye yalnızca hız bileşenleri verildiği için pozisyon
covariance değerleri büyüyordu. Bunun üzerine wheel odometry'den `vy = 0`
kısıtı füzyona eklendi.

Diagnostics mesajlarının tamamı `OK` seviyesindeydi.

## 5. Haritalama altyapısının eklenmesi

Şu dosyalar oluşturuldu:

```text
src/robot_bringup/config/ekf.yaml
src/robot_bringup/config/slam_toolbox.yaml
src/robot_bringup/config/mapping.rviz
src/robot_bringup/launch/mapping.launch.py
```

`mapping.launch.py` şu bileşenleri tek komutla başlatır:

```text
Arduino serial bridge
RPLidar
robot_state_publisher
robot_localization EKF
slam_toolbox online async mapping
RViz
```

RViz fixed frame'i `map` olarak ayarlandı ve `/map`, `/scan`, RobotModel ile
TF görünümleri eklendi.

## 6. Haritalama sırasında bulunan hatalar

### 6.1 Robotun RViz'de sürekli dönüp geri gelmesi

`first_mapping_test` kaydında robot hareketsiz olmasına rağmen RViz'de yaklaşık
0 derece ile -86 derece arasında sürekli gidip geliyordu.

Rosbag analizi:

```text
0 derece civarındaki EKF mesajları     259
-86 derece civarındaki EKF mesajları   250
30 dereceden büyük ardışık sıçrama     500 / 508
```

Sebep, `hardwareRobotmodel.launch.py` açıkken ayrıca `mapping.launch.py`
başlatılmasıydı. İki EKF, iki robot-state publisher ve muhtemelen iki lidar
sürücüsü aynı anda çalışıyordu.

Çözüm:

- Bütün eski launch süreçleri kapatıldı.
- Yalnızca `mapping.launch.py` çalıştırıldı.
- `/odometry/filtered` ve `/scan` için publisher sayısı bir olarak doğrulandı.

### 6.2 İlk haritanın üst üste binmesi

İlk hareketli kayıt:

```text
/home/orin/slam_rosbag
```

Kaydedilen harita:

```text
/home/orin/map.pgm
/home/orin/map.yaml
```

Kayıt yaklaşık 200 saniye ve 7.15 metre hareket içeriyordu. Analizde wheel yaw
ile IMU gyro-z arasında güçlü ters korelasyon bulundu:

```text
wheel/IMU korelasyonu  -0.962
|IMU yaw hızı|         yaklaşık 1.44 x |wheel yaw hızı|
```

EKF'nin net yaw sonucu ham odometriden ciddi biçimde ayrılıyordu:

```text
ham odometri net yaw   +124.31 derece
EKF net yaw              -9.27 derece
```

`slam_toolbox` yanlış lokal yönelim tahminini düzeltmeye çalışırken büyük
`map -> odom` sıçramaları oluşturdu:

```text
toplam konum düzeltmesi     7.71 m
toplam açı düzeltmesi       111.38 derece
en büyük konum sıçraması    2.14 m
en büyük açı sıçraması      21.0 derece
```

Bu sıçramalar aynı duvarların farklı konum ve açılarda tekrar çizilmesine
neden oldu.

### 6.3 Yanlış ara yön düzeltmesi ve `map2`

İlk değerlendirmede yalnızca komut işaretine bakılarak IMU gyro-z yönü ters
çevrildi ve etkin wheel-base yaklaşık 0.25 m olarak ayarlandı. İkinci testte
gerçek robot ile RViz'in sağ-sol yönlerinin ters olduğu gözlendi. Bu fiziksel
gözlem hangi sensörün yanlış işarette olduğunu kesinleştirdi:

- Ham IMU yönü fiziksel dönüşle uyumluydu.
- Encoder tabanlı wheel yaw yönü tersti.
- IMU'yu ters çevirmek iki ölçümü birbiriyle uyumlu fakat fiziksel dönüşe ters
  hâle getirmişti.

İkinci kayıt:

```text
/home/orin/slam_rosbag2
```

İkinci harita:

```text
/home/orin/map2.pgm
/home/orin/map2.yaml
```

Bu kayıtta wheel ve IMU korelasyonu `+0.983` oldu; fakat ikisi de fiziksel
dönüşe tersti. Harita merkez çevresinde yıldız biçiminde üst üste bindi.

Ölçümler:

```text
hareket mesafesi             4.92 m
map -> odom konum düzeltmesi 6.71 m
map -> odom açı düzeltmesi   229.86 derece
en büyük açı sıçraması       21.0 derece
```

### 6.4 Nihai yön ve ölçek kalibrasyonu

`slam_rosbag2` kaydında, wheel-base 0.25 m iken:

```text
|IMU yaw hızı| yaklaşık 1.25 x |wheel yaw hızı|
```

Buradan etkin tekerlek açıklığı:

```text
0.25 / 1.25 = yaklaşık 0.20 m
```

olarak hesaplandı. Bu değer URDF geometrisindeki yaklaşık 0.20 m sağ-sol
tekerlek açıklığıyla da uyumluydu.

Nihai ayarlar:

```yaml
wheel_base: 0.20
imu_gyro_z_scale: 1.0
wheel_yaw_scale: -1.0
```

Wheel yaw hesabı:

```python
d_theta = (
    (d_right - d_left) / wheel_base
) * wheel_yaw_scale
```

Bu ayarlardan sonra gerçek robot ile RViz hareketi aynı yöne geldi ve harita
önemli ölçüde iyileşti.

### 6.5 Teleop sağ-sol yönleri

Sensör ve odometri yönleri düzeltildikten sonra gerçek robot ile RViz uyumluydu
fakat standart teleop tuşları ters davranıyordu:

```text
önce: J -> sağ, L -> sol
```

Arduino firmware'indeki `A/D` motor yönleri nedeniyle yalnızca komut eşlemesi
değiştirildi:

```python
elif msg.angular.z > 0.0:
    command = 'D'
elif msg.angular.z < 0.0:
    command = 'A'
```

Nihai davranış:

```text
J -> fiziksel sol
L -> fiziksel sağ
```

Bu değişiklik encoder, IMU, EKF veya TF hesabını değiştirmedi.

### 6.6 Diğer gözlemler

- `Gecersiz seri paket yok sayildi` uyarısı, Arduino'dan gelen bir satırın
  zorunlu JSON alanlarını veya sonlu sayısal değer kontrollerini geçemediğini
  belirtir. Açılışta tek sefer görülmesi yarım başlangıç satırından
  kaynaklanabilir; sürekli görülmesi protokol veya seri hat sorunudur.
- Lidar minimum menzili sürücü kapasitesiyle eşleştirilerek `0.20 m` yapıldı.
- RViz zaman zaman message-filter queue uyarısı verdi. Rosbag analizinde lidar
  yaklaşık 7 Hz ve tarama başına 1080 ışın üretiyordu. Geçerli ışın sayısı
  yeterliydi; bu uyarı harita bozulmasının birincil nedeni değildi.
- `/cmd_vel` watchdog uyarıları komut akışı 0.5 saniye kesildiğinde güvenli dur
  komutunun gönderildiğini gösteriyordu.

## 7. Nihai yapılandırma özeti

Arduino bridge:

```yaml
wheel_radius: 0.04
wheel_base: 0.20
encoder_ticks_per_rev: 7000.0
imu_gyro_z_scale: 1.0
wheel_yaw_scale: -1.0
odom_topic: /wheel/odometry_raw
publish_odom_tf: false
cmd_vel_timeout: 0.5
```

EKF:

```text
girişler:
  /wheel/odometry_raw -> vx, vy=0, yaw rate
  /imu/data_raw       -> gyro-z

çıkışlar:
  /odometry/filtered
  odom -> base_link
```

SLAM:

```text
scan_topic       /scan
base_frame       base_link
odom_frame       odom
map_frame        map
resolution       0.05 m
min_laser_range  0.20 m
max_laser_range  12.0 m
```

## 8. Kullanılan komutlar

### 8.1 Paket kurulumu

```bash
sudo apt update
sudo apt install ros-humble-robot-localization \
  ros-humble-slam-toolbox \
  ros-humble-teleop-twist-keyboard
```

Paket kontrolü:

```bash
ros2 pkg prefix robot_localization
ros2 pkg prefix slam_toolbox
ros2 pkg prefix teleop_twist_keyboard
ros2 pkg prefix rplidar_ros
```

### 8.2 USB ve seri port kontrolü

```bash
lsusb
ls -l /dev/ttyUSB* /dev/ttyACM* 2>/dev/null
ls -l /dev/arduino /dev/rplidar
groups
```

USB bağlantısını canlı izlemek için:

```bash
sudo dmesg -w
```

Seri port yetkisi için:

```bash
sudo usermod -aG dialout $USER
```

Bu komuttan sonra yeniden oturum açmak veya sistemi yeniden başlatmak gerekir.

### 8.3 Derleme ve test

```bash
cd ~/DiffDrive_Slamtoolbox
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
```

Testler:

```bash
colcon test
colcon test-result --verbose
```

Son doğrulama sonucu:

```text
3 paket derlendi
8 test
0 hata
0 başarısızlık
1 atlanan test
```

### 8.4 Topic ve sensör kontrolü

```bash
ros2 topic list
ros2 topic hz /imu/data_raw
ros2 topic hz /wheel/odometry_raw
ros2 topic hz /odometry/filtered
ros2 topic hz /scan
ros2 topic hz /map
```

Tek mesaj görüntüleme:

```bash
ros2 topic echo /imu/data_raw --once
ros2 topic echo /wheel/odometry_raw --once
ros2 topic echo /odometry/filtered --once
ros2 topic echo /scan --once
```

### 8.5 TF kontrolü

```bash
ros2 run tf2_ros tf2_echo odom base_link
ros2 run tf2_ros tf2_echo map base_link
ros2 run tf2_ros tf2_echo base_link imu_link
ros2 run tf2_ros tf2_echo base_link laser_frame
```

Publisher kontrolü:

```bash
ros2 topic info /odometry/filtered --verbose
ros2 topic info /scan --verbose
ros2 topic info /tf --verbose
```

### 8.6 Çakışan ROS süreçlerini kontrol etme

```bash
ps aux | grep -E \
  "ekf_node|serial_bridge|robot_state_publisher|rplidar|slam_toolbox" \
  | grep -v grep
```

ROS daemon önbelleğini yenileme:

```bash
ros2 daemon stop
ros2 daemon start
```

Mapping sırasında `hardwareRobotmodel.launch.py` ayrıca çalıştırılmamalıdır.
Yalnızca `mapping.launch.py` kullanılmalıdır.

### 8.7 Haritalamayı başlatma

```bash
cd ~/DiffDrive_Slamtoolbox
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch robot_bringup mapping.launch.py
```

### 8.8 Teleop

```bash
source /opt/ros/humble/setup.bash
source ~/DiffDrive_Slamtoolbox/install/setup.bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard \
  --ros-args \
  -p speed:=0.08 \
  -p turn:=0.25 \
  -p repeat_rate:=10.0 \
  -p key_timeout:=0.5
```

Arduino köprüsü halen hız büyüklüğünü doğrudan motor PWM değerine çevirmiyor;
firmware `W/X/A/D/S` yön komutlarını uygular. Bu nedenle gerçek hız firmware
tarafından belirlenir.

### 8.9 Sabit durum rosbag kaydı

```bash
ros2 bag record \
  -o stationary_ekf_check \
  -d 30 \
  /imu/data_raw \
  /wheel/odometry_raw \
  /odometry/filtered \
  /diagnostics \
  /tf \
  /tf_static
```

### 8.10 Mapping rosbag kaydı

```bash
ros2 bag record \
  -o slam_mapping_check \
  /scan \
  /map \
  /imu/data_raw \
  /wheel/odometry_raw \
  /wheel/encoders \
  /odometry/filtered \
  /tf \
  /tf_static \
  /diagnostics \
  /cmd_vel \
  /rosout
```

### 8.11 Haritayı kaydetme

```bash
mkdir -p ~/maps
ros2 run nav2_map_server map_saver_cli \
  -f ~/maps/kasif_map
```

Bu işlem normal olarak şu dosyaları üretir:

```text
kasif_map.yaml
kasif_map.pgm
```

## 9. Önerilen haritalama yöntemi

1. Eski launch süreçlerinin kapalı olduğunu doğrulayın.
2. Yalnızca `mapping.launch.py` başlatın.
3. Robotu ilk 5-10 saniye hareketsiz bırakın.
4. Düşük hızda ve yumuşak dönüşlerle ilerleyin.
5. Ani hızlanma, frenleme ve hızlı yerinde dönüşlerden kaçının.
6. Aynı koridor ve odalara farklı yönlerden geri dönerek loop closure sağlayın.
7. RViz'de lidar noktalarının duvarların üzerine oturduğunu izleyin.
8. Duvarlar çift çizilmeye başlarsa sürüşü durdurup rosbag'i analiz edin.
9. Harita düzgün kapandığında farklı bir dosya adıyla kaydedin.

## 10. Sonuç

Çalışma sonunda:

- Encoder, IMU ve EKF dönüş yönleri fiziksel robotla uyumlu hâle getirildi.
- Gerçek robot ve RViz sağ-sol/ileri-geri hareketleri eşleştirildi.
- Teleop tuşları ROS standardına uygun hâle getirildi.
- `map -> odom -> base_link` TF zincirinde tek yayıncı sorumluluğu sağlandı.
- Lidar menzili ve SLAM parametreleri gerçek robot için yapılandırıldı.
- Haritanın üst üste binmesine yol açan duplicate launch ve yaw yön/ölçek
  sorunları rosbag verileriyle teşhis edilerek düzeltildi.
- Nihai haritalama sonucu önceki denemelere göre belirgin biçimde iyileşti.

Bir sonraki aşama, düzgün kaydedilmiş statik haritayı `map_server` ile açıp
AMCL kullanarak lokalizasyon kurmaktır.

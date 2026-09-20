# İlk Nav2 navigasyon profili

Bu profil SmacPlanner2D ve Regulated Pure Pursuit (RPP) ile ilk düşük hızlı
navigasyon içindir. MPPI henüz eklenmedi; önce temel yol takibi doğrulanacak.

## Yapılandırma

- Global planner: SmacPlanner2D, bilinmeyen alana yol yok, tolerans 0.10 m,
  saniyede bir BT plan yenileme, dahili yumuşatma.
- Controller: RPP, 20 Hz, istenen ileri hız 0.06 m/s, lookahead 0.15–0.35 m.
  Engelde/yüksek eğrilikte yavaşlama ve ileri yörünge çarpışma kontrolü açık.
  RPP engel etrafında bağımsız alternatif yerel yol aramaz; yeni global yol
  veya duruş gerekir.
- Hedef: 0.12 m konum, 0.20 rad yön toleransı. Progress checker 30 s içinde
  0.05 m ilerleme ister; düşük hızlı ilk yönelme için zaman bırakılır.
- Smoother: 20 Hz OPEN_LOOP, 0.07 m/s ve +/-0.30 rad/s sınırları;
  ivmeler 0.10 m/s² ve 0.50 rad/s², doğrusal frenleme 0.20 m/s².
  0.07 + 0.30 * 0.20 / 2 = 0.10 m/s tekerlek sınırına uyar.
- RPP min hızları 0.02 m/s başlangıç adayıdır; zeminde sürtünme nedeniyle
  sürdürülemiyorsa ölçümle ayarlanmalı. Başarılı hedef takibi henüz ölçülmedi.
- Ortak costmap/footprint dosyaları kullanılır. Inflation 0.25 m / scaling 8;
  RPP inflation_cost_scaling_factor aynı 8 değerini kullanır.
- Collision Monitor: xacro dış sınırından her yönde 10 cm geniş duruş polygon'u,
  iki veya daha fazla lidar noktası içeri girince duruş. Humble max_points=1
  eşiği kullanılır. source_timeout=0.5 s. Bu bölge fren mesafesinin ölçülmüş
  garantisi değildir; lidarın min menzili ve eğimi algılamayı sınırlar.
- Recovery: iki yeniden deneme, arada 2 s Wait. Spin/BackUp/Clear yok.
  RPP'nin normal yol/son yönelime dönmesi recovery spin'den ayrıdır.
- Akım eşiğine bağlı otomatik durdurma eklenmedi (kullanıcı tercihi).

Komut zinciri:

```
controller_server + behavior_server -> /cmd_vel_nav
velocity_smoother -> /cmd_vel_smoothed
collision_monitor -> /cmd_vel
Arduino bridge -> V1 sağ sol
```

Nav2 çalışırken /cmd_vel'e teleop veya ayrı test script'i yayın yapmamalıdır;
bunlar Collision Monitor'ü atlar ve aynı motor girişinde iki kaynak oluşturur.

## Eksik bağımlılıkların kurulumu

Şu anda Nav2 navigasyon sunucuları kurulu değil. Kullanıcı terminalinde:

```bash
sudo apt install ros-humble-navigation2 ros-humble-nav2-bringup \
  ros-humble-nav2-smac-planner \
  ros-humble-nav2-regulated-pure-pursuit-controller \
  ros-humble-nav2-velocity-smoother ros-humble-nav2-collision-monitor
cd ~/DiffDrive_Slamtoolbox
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-up-to robot_bringup
source install/setup.bash
```

## Başlatma

Önce ayrı çalışan hardware/mapping/localization launch'larını kapatın.
Nav2 planner/controller kendi global/local costmap'lerini başlatır.

```bash
ros2 launch robot_bringup navigation.launch.py rviz:=true
```

Varsayılan rviz=false; ayrı bilgisayarda config/navigation.rviz kullanılabilir.
Lokalizasyon zaten tek başına açıksa start_localization:=false seçilebilir.
Map ve use_sim_time seçenekleri vardır; canlı robotta use_sim_time=false.
RViz 2D Pose Estimate ile başlangıç pozunu belirtin. Nav2 lifecycle manager
bond_timeout=4.0 kullanır.

Hedef verilene kadar navigasyon hareket üretmez. İlk aşama düğümlerin
active olması, TF, costmap ve lidar hizasının kontrolüdür:

```bash
ros2 lifecycle get /planner_server
ros2 lifecycle get /controller_server
ros2 lifecycle get /bt_navigator
ros2 lifecycle get /velocity_smoother
ros2 lifecycle get /collision_monitor
```

Sonra açık alanda 0.3–0.5 m ileride tek hedef, mevcut yöne yakın hedef oku ile
kontrollü ilk test yapılabilir. Görev iptali RViz Navigation 2 panelindeki
Cancel ile yapılır. Başarı, duruş, hedef iptali, engel ve scan kaybı davranışı
sahada ayrıca doğrulanmalıdır. Komut kaybında köprü/firmware watchdog'ları
var; bunlar donanım durdurma garantisi değildir.

## Doğrulama sınırı

YAML hız zarfı, footprint/duruş polygon'u, controller-inflation uyumu ve BT
recovery kısıtları test edildi; launch oluşturma/syntax kontrolleri yapıldı.
Canlı robot hedefi gönderilmedi. Nav2 eklentileri kurulduktan sonra plugin
 yükleme ve lifecycle aktivasyonu doğrulanmalı.

Lidarın fiziksel eğimi ve AMCL kayması kullanıcı tarafından sonraya bırakıldı.
Bu konular çözülmeden harita üzerinde doğru ve çarpışmasız otonom sürüş
iddiasında bulunulamaz. Smac 2D tam yönelimli dikdörtgen gövde uygulanabilirliği
arama yapmaz; dar geçiş/yerinde dönüşte footprint kontrolü ve saha doğrulaması
özellikle önemlidir. Bu profil optimal saha ayarı değil, devreye alma başlangıcıdır.

Humble kaynakları:
- https://github.com/ros-navigation/navigation2/blob/humble/nav2_smac_planner/README.md
- https://github.com/ros-navigation/navigation2/blob/humble/nav2_regulated_pure_pursuit_controller/README.md
- https://github.com/ros-navigation/navigation2/blob/humble/nav2_collision_monitor/params/collision_monitor_params.yaml
- https://github.com/ros-navigation/navigation2/blob/humble/nav2_bringup/params/nav2_params.yaml

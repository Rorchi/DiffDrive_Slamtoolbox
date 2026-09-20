# Kaşif Çelebi navigasyon planı

Tarih: 18 Eylül 2026. Durum: tasarım; henüz robot üzerinde uygulanmadı.

## 1. Karar ve kapsam

Hedef: kayıtlı map3 üzerinde, kapalı alanda, düşük hızlı hedefe navigasyon.
İlk sürüm tek hedef; ardından çoklu hedef. Haritalama ile navigasyon ayrı
çalışacak. AMCL map→odom, EKF odom→base_link dönüşümünün tek sahibi olacak.

| İşlev | Seçim | Gerekçe |
|---|---|---|
| Global planner | SmacPlanner2D | Diferansiyel robot için maliyet duyarlı 2D A*, dahili yol yumuşatma |
| İlk devreye alma controller'ı | Regulated Pure Pursuit (RPP) | Yol takibi ve hız arayüzünü daha az ayar ile doğrulamak |
| Hedef çalışma controller'ı | MPPI, DiffDrive | Yol çevresindeki alternatif yerel yörüngeleri değerlendirerek engellerden kaçınmak |
| Lokalizasyon | Mevcut AMCL + EKF | Kayıtlı harita ve mevcut sensör zinciriyle uyum |
| Komut düzenleme | Velocity Smoother | Ölçülen hız/ivme sınırlarını uygulamak |
| Son komut denetimi | Collision Monitor | Lidar girdisiyle yavaşlatma/durdurma; smoother sonrasında |
| Görev yürütme | Nav2 BT Navigator | Planlama, takip, yeniden planlama ve sınırlı kurtarma |

RPP ve MPPI aynı anda komut üretmeyecek; ayrı seçilebilir profiller olacak.
MPPI zamanlama ve saha testlerini geçerse varsayılan yapılacak. RPP tanılama
ve daha basit, kontrollü ortam profili olarak kalacak. RPP engel çevresinde
alternatif yerel yol arayan bir optimizer değildir; duruş ve global yeniden
planlamaya dayanır. MPPI de hareketli insanları gelecekteki konumlarıyla
izleyen bir tahmin sistemi değildir; güncel costmap üzerinden çalışır.

## 2. Depoda doğrulanan durum ve önkoşul

- ROS 2 Humble, Jetson Orin, RPLidar A1; map3 çözünürlüğü 0.05 m.
- EKF hedef yayın frekansı 30 Hz; gerçek frekans/gecikme sahada ölçülecek.
- Tekerlek yarıçapı 0.04 m, wheel_base 0.20 m, encoder 7000 tick/tur.
- AMCL yapılandırılmış; hareketli saha doğrulaması bu incelemede yapılmadı.
- Kurulu Nav2 parçaları lokalizasyon ağırlıklı; controller/planner paketlerinin
  kurulumu ve sürümleri uygulama aşamasında doğrulanacak.
- Firmware kaynağı depoda yok. Pinler, motor sürücüsü ve hız kontrolü bilinmiyor.

**Öncelikli engel:** serial_bridge.py içindeki cmd_vel_callback yalnız W/X/D/A/S
gönderiyor. Hız büyüklüğü kayboluyor; linear.x sıfır değilse angular.z işlenmiyor.
Örneğin v=0.10 m/s, w=0.30 rad/s komutu yalnız ileriye dönüşüyor. Mevcut
arayüzle Nav2'nin hız/ivme sınırları fiziksel harekete uygulanmış sayılmaz.

İlk iş paketi, firmware ile birlikte gerçek hız komut protokolünü tasarlamaktır:

1. SI birimlerinde v,w veya sol/sağ tekerlek hedef hızlarını aktaran, paket
   sınırı belirli ve sürümlü protokol; bozuk/eksik/geçersiz komut reddi.
2. Diferansiyel dönüşüm: v_left=v−wL/2, v_right=v+wL/2;
   wheel_rad_s=v_wheel/r. L=0.20 ve r=0.04 mevcut kalibrasyon başlangıcıdır.
3. Encoder geri beslemeli sol/sağ hız regülasyonu, doygunluk, ölü bölge ve
   ivme sınırları. PWM değerleri hız yerine geçmez.
4. Pozitif v ileri, pozitif w sola olacak biçimde motor/encoder yön testi.
   Mevcut wheel_yaw_scale=-1 düzeltmesi motor yön eşlemesiyle karıştırılmayacak.
5. Mevcut 0.5 s köprü timeout'una ek olarak firmware tarafında bağımsız
   watchdog; Jetson veya USB kesilince de duruş. Fiziksel durdurma imkânı.
6. Düz, yerinde dönüş ve eşzamanlı v,w komutları için istenen/ölçülen hız
   kaydı; frenleme mesafesi, en küçük sürdürülebilir hız ve gecikme ölçümü.

Bu koşullar geçilmeden otonom hareket testi yapılmayacak. Costmap ve motorsuz
planlama çalışmaları paralel ilerleyebilir.

## 3. Alternatiflerin değerlendirilmesi

| Seçenek | Bu projedeki rolü |
|---|---|
| NavFn | Basit karşılaştırma profili; ilk tercih Smac 2D |
| Smac Hybrid-A* | Minimum dönüş yarıçapı olan araçlarda anlamlı; yerinde dönebilen bu robotta ilk ihtiyaç değil |
| Smac State Lattice | Dar alanlarda yönelim ve polygon footprint ile uygulanabilir yol gereksinimi ortaya çıkarsa yeniden değerlendirilecek |
| DWB | Daha geleneksel yerel yörünge örnekleme alternatifi; MPPI başarısız olursa karşılaştırma adayı |
| RPP | Devreye alma ve kontrollü yol takibi profili |
| MPPI | Nihai yerel manevra profili; CPU bütçesi ve ayar maliyeti ölçülecek |

Smac 2D yönelime bağlı tam gövde uygulanabilirliğini garanti etmez. Robot
dikdörtgen ve base_link'e göre asimetriktir; dar kapılar ve yerinde dönüşler
ayrıca sınanacak. Polygon tanımlamak, 2D global aramayı SE2 aramasına dönüştürmez.
Sistematik sıkışma varsa yalnız inflation azaltmak yerine State Lattice
veya daha korumacı global geometri değerlendirilecek.

## 4. Costmap ve robot geometrisi

URDF şasi/tekerlek izdüşümünden yaklaşık x=[−0.18,+0.07], y=[−0.12,+0.12] m
elde ediliyor. Başlangıç polygon'u [[0.07,0.12],[0.07,-0.12],[-0.18,-0.12],
[-0.18,0.12]] olabilir; kablo, bağlantı parçaları ve gerçek dış ölçüler
ölçülmeden nihai footprint olarak kullanılmayacak. Base_link merkezini
geometrik merkez varsaymayacağız. İlk padding adayı 0.02 m.

| Ayar | Global costmap | Local costmap |
|---|---|---|
| Frame | map | odom |
| Robot frame | base_link | base_link |
| Çözünürlük | 0.05 m | 0.05 m |
| Alan | Kayıtlı harita | 3×3 m rolling window |
| Katmanlar | Static + Obstacle + Inflation | Obstacle + Inflation |
| Engel kaynağı | /scan | /scan |
| Güncelleme başlangıcı | 2 Hz | 10 Hz |
| Yayın başlangıcı | 1 Hz | 5 Hz |
| Inflation başlangıcı | 0.35 m, scaling 3.0 | 0.35 m, scaling 3.0 |

Bunlar ölçümle ayarlanacak tasarım değerleridir. Inflation radius kesin bir
minimum duvar mesafesi değildir. Koridor geçişi gerçek footprint, padding,
maliyet alanı ve controller ile birlikte doğrulanacak. Globalde bilinmeyen
alan takip edilecek ve planner için allow_unknown=false başlangıcı seçilecek.
Obstacle marking ve raytracing clearing açık olacak; başlangıç menzil adayları
2.5 m marking / 3.0 m clearing, gerçek scan kalitesiyle doğrulanacak.
Geçersiz/sonsuz lidar ölçümlerinin clearing davranışı test edilecek.

2D lidar düzlemi dışındaki alçak veya çıkıntılı engeller algılanmayabilir.
Mevcut RGB kamera mesafe sensörü olarak kabul edilmeyecek; test alanı sensörün
algıladığı engellerle sınırlandırılacak. Scan frekansı URDF'deki simülasyon
değerinden alınmayacak; gerçek /scan üzerinden ölçülecek.

## 5. Controller ve hız profilleri

Tüm sayılar ilk saha denemesi adaylarıdır; donanım ölçümü üstün gelir.

| Parametre | Başlangıç adayı |
|---|---|
| Controller | 20 Hz |
| Doğrusal hız | İlk 0.08 m/s; başarılı test sonrası üst sınır 0.15 m/s |
| Açısal hız sınırı | 0.40 rad/s |
| Doğrusal ivme / fren ivmesi büyüklüğü | 0.15 / 0.25 m/s² |
| Açısal ivme büyüklüğü | 0.50 rad/s² |
| Hedef toleransı | 0.15 m, 0.20 rad |
| Progress checker | Başlangıçta 15 s içinde 0.10 m; yerinde dönüş davranışıyla doğrula |
| Global yeniden planlama | BT üzerinden 1 Hz |

RPP: hız ölçekli lookahead, başlangıç 0.25 m, aralık 0.15–0.40 m;
eğrilik/engel maliyetiyle yavaşlama ve çarpışma kontrolü açık. rotate-to-heading
açık, reversing kapalı. Son yönelim ve keskin köşe davranışı sahada sınanacak.

MPPI: DiffDrive; model_dt=0.05 s, time_steps=40 (2 s ufuk), batch_size=1000,
iteration_count=1 başlangıcı. vx_min=0, vx_max=0.15, wz_max=0.40;
v_y komutu yok. Constraint, Obstacles, Goal, GoalAngle, PathAlign, PathFollow,
PathAngle ve PreferForward critic'leri Humble örneğiyle başlatılacak.
ObstaclesCritic polygon kontrolü açık olacak; Humble'daki inflation_radius ve
cost_scaling_factor değerleri costmap ile eşleşecek. Düşük hız nedeniyle kısa
uzamsal ufka uygun path critic offset/eşik ayarı yapılacak; örnek robotun
yüksek hız ayarları aynen kopyalanmayacak.

Jetson GPU varlığı MPPI'nin GPU kullanacağı anlamına gelmez; Humble uygulaması
CPU üzerinde çalışır. 20 Hz için controller çevriminin p95 süresi <40 ms
mühendislik hedefidir; tam yükte tekrarlanan 50 ms aşımı olmamalı. Başarısızsa
önce görselleştirme/yük azaltılır, ardından batch/frekans/ufuk tutarlı ayarlanır.

## 6. Komut zinciri, lifecycle ve davranış ağacı

```text
map3 → map_server → global costmap → Smac 2D → global yol
/scan → local costmap → RPP veya MPPI ← /odometry/filtered
controller + behavior server → /cmd_vel_nav
  → velocity smoother → /cmd_vel_smoothed
  → collision monitor → /cmd_vel → Arduino bridge → hız denetimi
```

Teleop eklendiğinde komut seçici smoother önünde olacak; /cmd_vel'e bağımsız
ikinci yayıncı bırakılmayacak. Gerekirse ilk testte teleop ve Nav2 modları
birbirini dışlayacak. Smoother başlangıç 20 Hz OPEN_LOOP; odometri gecikmesi
ölçülüp uygunsa CLOSED_LOOP değerlendirilir. Bu seçim firmware'deki kapalı
çevrim tekerlek hız kontrolünden bağımsızdır.

Collision Monitor son hız katmanı olacak; scan kaybı ve TF arızasında duruş
doğrulanacak. Bölge mesafeleri gövde kenarından itibaren v*t_gecikme +
v²/(2*a_fren) + ölçüm payı ile belirlenecek; dönüşte tüm gövde süpürmesi hesaba
katılacak. Yazılım katmanı bağımsız donanım durdurmanın yerini tutmaz.

BT: planla → takip et + 1 Hz yeniden planla. Geçici engelde bekle ve yeniden
planla; kalıcı engelde alternatif yol, yoksa sınırlı deneme sonrası başarısız
sonuç ve duruş. İlk sürümde otomatik geri kaçış kapalı. Spin recovery ancak
dönüş footprint'i doğrulandıktan sonra açılacak. Costmap temizliği engelleri
yok sayarak ilerlemek için kullanılmayacak; güncel scan yeniden işlenmeli.
Cancel, yeni hedef ve goal reached olaylarında sıfır komut/duruş sınanacak.

Localization launch bir kez include edilecek; donanım, EKF, RSP, AMCL ve map
server yeniden oluşturulmayacak. Ayrı navigation lifecycle manager yalnız
yeni Nav2 düğümlerini yönetecek. AMCL başlangıç pozu, geçerli TF ve güncel scan
olmadan sürüş başlatılmayacak. Humble Twist arayüzü korunacak; yeni dağıtımların
TwistStamped varsayımları aktarılmayacak.

## 7. İş paketleri ve geçiş ölçütleri

| Sıra | Çıktı | Geçiş ölçütü |
|---|---|---|
| 1 | Firmware kaynağı, hız protokolü, bridge ve hız regülatörü | Ayrı ve birleşik v,w takibi; watchdog/USB kaybında duruş |
| 2 | Fiziksel ölçüler, hız/ivme/gecikme kaydı | Footprint kesinleşmiş; tekrarlanabilir düşük hız ve frenleme |
| 3 | Lokalizasyon saha doğrulaması | Düz/dönüş rotasında scan-map uyumu; TF çatışması ve sürekli atlama yok |
| 4 | Global/local costmap ve Smac | Motorlar devre dışıyken geçerli/engelli hedeflerde doğru plan/başarısızlık |
| 5 | RPP + smoother + monitor | Düz yol, 90° köşe, hedef yönelimi, iptal ve engelde duruş |
| 6 | MPPI profili | Aynı rota setinde daha iyi yerel manevra; süre bütçesine uyum |
| 7 | BT ve hata senaryoları | Kapalı koridor, lidar kaybı, süreç/USB kesilmesi, erişilemez hedefte kontrollü duruş |
| 8 | Varsayılan profil ve kullanıcı belgesi | Tek komut bringup; tekrarlı kabul testi ve kayıtlı parametre sürümü |

Önerilen saha kabul seti: 10 sabit hedef/rota, en az üç tur; en az %95 hedef
başarısı, sıfır temas, hedef hatası ≤0.15 m/0.20 rad. Bunlar önerilen kabul
ölçütleridir, mevcut performans iddiası değildir. Dar geçiş, U dönüşü,
sonradan eklenen engel, tamamen kapanan yol ve hedef iptali ayrıca test edilir.
Engel testleri önce sabit nesneyle ve düşük hızda yapılır.

Her profilde başarı, süre, yol uzunluğu, yanal hata, minimum gövde açıklığı,
recovery sayısı, controller çevrim süresi ve CPU yükü kaydedilir. İstenen ve
ölçülen hız karşılaştırılır. Rosbag: /scan, /tf, /tf_static, /map, /amcl_pose,
/odometry/filtered, /wheel/odometry_raw, komut zincirindeki üç topic, /plan,
costmap çıktıları, /diagnostics ve /rosout. Topic adları gerçek kurulumda
doğrulanır. Fiziksel hedef hatası yalnız AMCL'nin kendi tahminiyle ölçülmez.

## 8. Uygulama dosyaları

- config/nav2_params.yaml: ortak costmap, planner, controller ve checker ayarları.
- config/nav2_rpp.yaml ve config/nav2_mppi.yaml: açıkça seçilen controller profilleri.
- config/collision_monitor.yaml: ölçülmüş algılama/duruş bölgeleri.
- behavior_trees/navigate_safe.xml: sınırlı recovery ve yeniden planlama.
- launch/navigation.launch.py: lokalizasyonu bir kez başlatan üst seviye launch.
- config/navigation.rviz: map, scan, AMCL, odometri, footprint, global/local
  costmap, plan, waypoint, Navigation 2 paneli ve Nav2 action hedef araçları.
- package.xml ve kurulum tanımı: yeni bağımlılıklar ve dosyaların paketlenmesi.
- Arduino firmware, serial_bridge ve protokol/test belgeleri: gerçek hız arayüzü.

Launch, BT node adları, plugin adlandırması ve parametreler kurulu Humble
sürümünün örnekleri/plugin XML'leri üzerinden doğrulanacak; Rolling/Jazzy YAML
dosyaları doğrudan kullanılmayacak. Planlama aşamasında paket kurulmadı,
çalışan yapılandırma değiştirilmedi ve fiziksel test yapılmadı.

## Kaynaklar

- [Nav2 Humble Smac planner](https://github.com/ros-navigation/navigation2/blob/humble/nav2_smac_planner/README.md)
- [Nav2 Humble RPP](https://github.com/ros-navigation/navigation2/blob/humble/nav2_regulated_pure_pursuit_controller/README.md)
- [Nav2 Humble MPPI](https://github.com/ros-navigation/navigation2/blob/humble/nav2_mppi_controller/README.md)
- [Nav2 tuning guide](https://docs.nav2.org/rolling/configuration_and_development/tuning_guide/) — kavramsal karşılaştırma; Humble parametre referansı değildir.
- [Collision Monitor zinciri](https://ros-navigation.github.io/mkdocs.nav2.org/rolling/tutorials/general_tutorials/using_collision_monitor/using_collision_monitor/) — sürüme özgü ayarlar uygulamada doğrulanacak.

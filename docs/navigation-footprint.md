# Xacro'dan navigasyon footprint'i

Referans base_link, +x ileri, +y sol. Mevcut düz model esas alındı.

| Geometri | x sınırı (m) | y sınırı (m) |
|---|---|---|
| Alt şasi | -0.180 … +0.070 | -0.080 … +0.080 |
| Üst şasi | -0.140 … +0.010 | -0.065 … +0.065 |
| Ön tekerlek çifti | -0.040 … +0.040 | -0.120 … +0.120 |
| Arka tekerlek çifti | -0.170 … -0.090 | -0.120 … +0.120 |
| Lidar | -0.100 … -0.030 | -0.035 … +0.035 |
| Kamera (rpy dönüşümüyle) | +0.040 … +0.070 | -0.018 … +0.018 |

Şasi merkezinin x değeri: joint +0.070 ve collision origin -0.125 toplamı
-0.055 m; kutu uzunluğu 0.250 m. Tekerleklerde y merkezleri +/-0.100 m,
kalınlık 0.040 m; silindirler 90 derece döndüğü için en dış y +/-0.120 m.
Kamera dönüşü yerel y boyutunu base_link x eksenine taşır. IMU ve optik
frame için ek collision geometrisi yok.

Tüm geometrileri kapsayan dikdörtgen: x=[-0.18,0.07], y=[-0.12,0.12].
Uzunluk 25 cm, genişlik 24 cm. Base_link geometrik merkezde değil;
merkezin base_link'e göre x değeri -5.5 cm. Bu nedenle footprint'i
base_link etrafında +/-12.5 cm olarak merkezlemek yanlış olur.

config/nav2_footprint.yaml iki costmap için aynı polygon'u ve 0.02 m
padding'i hazırlar. Padding mühendislik başlangıç payıdır, xacro ölçüsü
değildir. Dikdörtgenin padding sonrası sınırları x=[-0.20,0.09],
y=[-0.14,0.14], boyutu 29 x 28 cm olur. Inflation ayrı sonraki ayardır.

Bu dosya navigation.launch.py tarafından iki costmap için yüklenir.
Kurulum ve görsel kontrol için navigation-start.md belgesine bakın.
Xacro dışında kalan fiziksel parçalar ve kullanıcının bildirdiği lidar/
şasi eğimi bu hesapta yok. Kullanıcının isteğiyle fiziksel düzeltme sonraya
bırakıldı. Lidar/şasi geometrisi değiştiğinde model ve footprint yeniden
değerlendirilmelidir. Fiziksel çarpışma testi yapılmadı.

# Mega2560 — sayısal tekerlek hızı arayüzü

Kaynak: https://github.com/Rorchi/DiffDrive_slamtoolbox_ArduinoCode
Temel commit: `418743e21174c369eeb10c63c815aff1605985ed`.
Bu dizin değiştirilmiş yerel kopyadır; kaynak depoya gönderilmedi.

Motor A sol (PWM 5, IN1/IN2 7/8), Motor B sağ (PWM 6, IN1/IN2 9/10).
İleri pin seviyeleri kaynak firmware'in W komutundan alındı.
Sol encoder 2/3, sağ encoder 18/19; STBY 11. Sensör, IMU kalibrasyonu,
batarya ve encoder telemetrisi kaynak firmware'den korundu.

## İlk adım

115200 baud ASCII: `V1 <sol_mm_s> <sag_mm_s>\n`.
Her tekerlek ±150 mm/s ile sınırlıdır; pozitif ileri, negatif geri.
Tek `S` baytı PWM'yi sıfırlar. Eski W/X/A/D sürüş komutları desteklenmez.
Geçersiz tamamlanmış paket ve taşma durdurur; eksik paket hedefi yenilemez.
Son geçerli V1 paketinden 500 ms sonra firmware PWM'yi sıfırlar.
Bu timeout fiziksel fren mesafesini ifade etmez.

| Hareket | Paket (sonuna LF) |
|---|---|
| İleri | `V1 80 80` |
| Sola yerinde dönüş | `V1 -30 30` |
| Sağa yerinde dönüş | `V1 30 -30` |
| İlerlerken sola | `V1 70 130` |

Köprünün `command_protocol:=wheel_v1` modu v,w'yi bu komuta dönüştürür;
doygunlukta iki tekerlek orantılı küçültülür. Varsayılan `legacy` korunmuştur:
firmware ve köprü modu birlikte değiştirilmelidir. Yeni firmware eski modla
sürüş yapmaz. Çalışan launch/YAML değiştirilmedi.

Hız geri beslemesi gerçek dt ile tick/s hesaplar. 7000 tick/tur ve 0.04 m
tekerlek yarıçapı kullanılır. Mevcut artımlı PWM regülatörü korunmuştur;
kazancı yeni düşük hızlarda henüz ayarlanmamıştır. Geri besleme hız büyüklüğünü
kullanır; motor/encoder yönü fiziksel testte doğrulanmalıdır. Bu sürüm
navigasyon için tamamlanmış ve ayarlanmış bir hız denetleyicisi değildir.
Yön değişiminde PWM kesilir, ölçülen hız 50 tick/s altına indikten sonraki
çevrimde ters yön uygulanır. Kontrol çevrimi 100 ms; 250 ms üzeri gecikmede
hedef sıfırlanır. MCU donmasına karşı bu yazılım timeout'u yeterli değildir.

## Derleme ve ilk fiziksel kontrol

PlatformIO: bu dizinde `pio run`. Mega2560, Arduino framework ve INA219
bağımlılığı platformio.ini içindedir. Donanıma yükleme yapılmadı.

İlk kontrol robot sabitlenmiş ve tekerlekler havadayken: 10 Hz `V1 40 0\n`
ile yalnız sol tekerleğin ileri dönmesi ve akış kesilince durması gözlenecek.
Diğer fiziksel testlere bu gözlemden sonra geçilecek. Aynı seri porta köprü
ve test terminali birlikte bağlanmamalı. Çalışan firmware geri dönüş için
saklanmalı. Python dönüşüm ve host C++ parser testleri eklendi; tam AVR
firmware derlemesi ve fiziksel hız takibi henüz doğrulanmadı.

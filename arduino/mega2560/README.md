<!--
Amaç: Arduino Mega2560 firmware dizininin durumunu ve belge gereksinimlerini açıklar.
Çalışma: Firmware kaynağının henüz depoda bulunmadığını belirtir; kaynak
eklendiğinde kart, pin, protokol ve kalibrasyon bilgilerinin nasıl
belgeleneceğine rehberlik eder.
-->

# Mega2560 firmware

Bu dizin, Jetson'a bağlı Arduino Mega2560 Pro Mini kartının firmware'i için
ayrılmıştır. Mevcut firmware kaynak dosyası depoda bulunmadığı için burada
örnek veya varsayımsal `.ino` dosyası oluşturulmadı.

Firmware eklendiğinde şu öğeleri aynı değişiklikte belgeleyin:

- Arduino IDE/PlatformIO kart tanımı ve baud hızı;
- encoder, motor sürücü ve IMU pinleri;
- seri mesaj biçimi (`docs/serial-protocol.md` ile uyumlu olmalı);
- encoder çözünürlüğü, tekerlek yarıçapı ve tekerlekler arası mesafe;
- IMU eksen yönleri, birimleri ve kalibrasyon yöntemi.

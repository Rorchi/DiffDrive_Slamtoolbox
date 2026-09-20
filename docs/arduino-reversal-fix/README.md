# Yön değişiminde eş zamanlı kalkış düzeltmesi

Temel kaynak: Rorchi/DiffDrive_slamtoolbox_ArduinoCode,
commit `68076340dbbe560ea8012d3e2d024a7858b8da5d`.

`main.cpp`, bu sürümün yalnız runWheelControl fonksiyonuna yapılan eklemeyi
 içerir. Motorlardan biri yön değiştirme beklemesindeyken iki kanal da PWM=0
 tutulur; gerekli yön geçişleri tamamlanınca sonraki kontrol çevriminde normal
 hız regülasyonu iki kanalda birlikte devam eder. Mevcut 200 ms bekleme,
 duruş örneği kontrolü, hız kazançları ve seri alan sırası korunur.

Bu, motorların fiziksel olarak tam aynı anda kalkacağını garanti etmez;
 yazılımın tek kanalı bekletirken diğerini sürmesi düzeltilir.

Arduino projesinin src/main.cpp dosyasını buradaki main.cpp ile değiştirin.
Mevcut wheel_protocol.h ve platformio.ini aynı kalır. Tam AVR derlemesi ve
 donanıma yükleme bu ortamda yapılmadı. GitHub'a değişiklik gönderilmedi.
Derleme/yüklemeden sonra tekerlekler havadayken önceki dönüş–dur–ileri testi
 tekrarlanmalıdır; yerde otonom sürüş için henüz onay değildir.

Doğrulama: `python3 test_control.py`, gerçek kontrol fonksiyonlarını sahte
 pin/encoder girdileriyle host g++ üzerinde derler. İki yöndeki geçişler,
 durmadan ters yöne geçmeme, iptal, zaman aralığı hatası ve düz kalkış
 sınanır. Test eski kaynakta eş zamanlı bekleme assertion'ında başarısız,
 düzeltilmiş kaynakta başarılıdır. Bu test AVR/saha doğrulamasının yerini tutmaz.

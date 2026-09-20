# Hız–akım kaydı

record_speed_current.py hareket komutu göndermez ve seri portu açmaz.
Çalışan ROS köprüsünün /battery, /wheel/odometry_raw ve /cmd_vel mesajlarını
measurements/ altında tarihli CSV dosyasına kaydeder. Test bitince Ctrl+C
özet basar. Komutun ilk 1 saniyesi özetten çıkarılır; 0.5 s'den eski komut
ve 0.3 s'den eski odometri özet hesabına alınmaz. Ham kayıt korunur.

ROS akım işareti korunur, ayrıca tüketim için -current sütunu yazılır.
Ölçüm INA219'un bağlı olduğu besleme hattına aittir; ayrı motor akımları
olarak yorumlanmaz. Önceki sürüşlerde akım kaydı yoktur.

İncelenen firmware akımı filtreler ve 2.1 A üstündeki ölçümü güncellemeden
reddeder. Bu nedenle yayımlanan maksimum, gerçek anlık tepe akımı değildir;
yeni ROS mesajı ölçümün sensörde yenilendiğini garanti etmez. Kısa testler
ön gözlemdir; yük, gerilim, filtre geçişi ve ölçüm geçerliliği doğrulanmadan
hassas güç/enerji karşılaştırması yapılamaz. Ham akım ve sensör ölçüm zamanı
ayrı yayınlanırsa kayıt daha sonra bunlarla genişletilmelidir.

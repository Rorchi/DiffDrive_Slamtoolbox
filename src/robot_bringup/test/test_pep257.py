# Amaç: robot_bringup Python açıklama dizelerinin biçimini denetler.
# Çalışma: pytest içinden ament_pep257 çalıştırılarak paket ve test dizinindeki
# docstring kuralları kontrol edilir; sıfır dönüş kodu beklenir.

from ament_pep257.main import main


def test_pep257():
    rc = main(argv=['.', 'test'])
    assert rc == 0

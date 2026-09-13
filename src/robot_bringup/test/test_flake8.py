# Amaç: robot_bringup Python dosyalarının kod biçimini denetler.
# Çalışma: pytest içinden ament_flake8 çalıştırılır; bulunan biçim hataları
# testin başarısız olmasına neden olur.

from ament_flake8.main import main_with_errors


def test_flake8():
    rc, errors = main_with_errors(argv=[])
    assert rc == 0, '\n'.join(errors)

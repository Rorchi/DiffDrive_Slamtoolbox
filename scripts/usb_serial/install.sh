#!/usr/bin/env bash
# Amaç: Jetson’da Arduino USB seri bağlantısını ve kalıcı cihaz adlarını kurar.
# Çalışma: sudo ile çalıştırıldığında orin kullanıcısını dialout grubuna ekler,
# brltty servislerini maskeler, WCH ch341 sürücüsünü derleyip kurar ve
# udev kurallarını yükler. USB cihazını yeniden bağlayıp sonucu listeler.

# Jetson Orin: Arduino CH340 sürücüsü + udev isimleri + dialout.
# Format sonrası: sudo ./scripts/usb_serial/install.sh
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Kök yetki gerekli: sudo $0" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KVER="$(uname -r)"
DRIVER_SRC="/tmp/ch341ser_linux"

echo "==> 1/6  orin kullanıcısını dialout grubuna ekle"
usermod -aG dialout orin

echo "==> 2/6  brltty CH340'ı (1a86:7523) braille cihaz sanmasın"
systemctl stop brltty.service 2>/dev/null || true
systemctl mask brltty.service 2>/dev/null || true
systemctl stop brltty-udev.service 2>/dev/null || true
systemctl mask brltty-udev.service 2>/dev/null || true

echo "==> 3/6  WCH ch341 sürücüsünü derle ve kalıcı kur"
if [[ ! -d "${DRIVER_SRC}/driver" ]]; then
  git clone --depth 1 https://github.com/WCHSoftGroup/ch341ser_linux.git "${DRIVER_SRC}"
fi
make -C "${DRIVER_SRC}/driver" clean || true
make -C "${DRIVER_SRC}/driver"
make -C "${DRIVER_SRC}/driver" install
echo ch341 > /etc/modules-load.d/ch341.conf
depmod -a
modprobe usbserial || true
modprobe ch341

echo "==> 4/6  udev kurallarını kur"
install -m 644 "${SCRIPT_DIR}/99-kasif-usb-serial.rules" \
  /etc/udev/rules.d/99-kasif-usb-serial.rules
udevadm control --reload-rules
udevadm trigger

echo "==> 5/6  CH340 USB cihazını sürücüye yeniden bağla"
for dev in /sys/bus/usb/devices/*; do
  if [[ -f "${dev}/idVendor" ]] && grep -qi '^1a86$' "${dev}/idVendor" \
     && grep -qi '^7523$' "${dev}/idProduct"; then
    name="$(basename "${dev}")"
    echo "    rebind ${name}"
    echo "${name}" > /sys/bus/usb/drivers/usb/unbind || true
    sleep 1
    echo "${name}" > /sys/bus/usb/drivers/usb/bind || true
  fi
done

sleep 2
echo "==> 6/6  sonuç"
echo "lsmod:"
lsmod | grep -i ch34 || echo "  (ch341 görünmüyor)"
echo "cihazlar:"
ls -l /dev/arduino /dev/rplidar /dev/ttyUSB* /dev/ttyCH341* /dev/ttyACM* 2>/dev/null || true
echo
echo "Not: dialout için oturumu kapatıp açın (veya newgrp dialout)."
echo "Lidar takılı değilse /dev/rplidar henüz oluşmaz; Arduino takılıysa /dev/arduino beklenir."

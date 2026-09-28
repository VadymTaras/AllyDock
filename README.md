# ⚓ AllyDock (v1.1.0)
### Autonomous Docking, Intelligent Display Detection & 3-Tier Adaptive Optimization Suite for ASUS ROG Ally on Bazzite OS

[![Project](https://img.shields.io/badge/Project-AllyDock-orange.svg)](#)
[![Version](https://img.shields.io/badge/Version-v1.1.0-blue.svg)](VERSION)
[![OS](https://img.shields.io/badge/OS-Bazzite%2043%20%7C%2044-purple.svg)](https://bazzite.gg)
[![Hardware](https://img.shields.io/badge/Hardware-ASUS%20ROG%20Ally%20(RC71L)-red.svg)](https://rog.asus.com/gaming-handhelds/rog-ally/rog-ally-2023/)
[![Kernel](https://img.shields.io/badge/Kernel-Linux%206.17.x%20(fsync)-green.svg)](https://kernel.org)
[![Status](https://img.shields.io/badge/Status-Tested%20%26%20Verified-success.svg)](#таблиця-протестованого-середовища-та-сумісності)
[![Desktop](https://img.shields.io/badge/Desktop-KDE%20Plasma%206%20(Wayland)-informational.svg)](https://kde.org)

> [!IMPORTANT]
> **Автономний комплекс стикування та оптимізацій AllyDock v1.1.0**  
> Репозиторій **AllyDock** містить вивірений комплекс скриптів автоматизації, udev-правил, системних служб `systemd`, хуків виходу зі сну, профілю Handheld Daemon (`hhd`), налаштувань Steam Input Desktop Layout та **інтелектуального детектора дисплеїв з 3-рівневим адаптивним профілюванням (Handheld 45 FPS vs 60Hz TV vs AMD FreeSync/VRR Uncapped)** для портативної ігрової консолі **ASUS ROG Ally (RC71L)** під керуванням операційної системи **Bazzite OS**.
> Пакет **AllyDock** протестовано у бойових умовах: він розпізнає параметри підключеного дисплея через бінарний EDID та DRM, автоматично підбирає оптимальний TDP та ліміт кадрів, усуває баги петлі геймпада (flapping loop), керує PipeWire аудіо та робить десктопний режим стіків ергономічним.

> [!NOTE]
> **Personal Backup & Disclaimer**  
> Репозиторій створено для резервного копіювання та автоматизованого розгортання конфігураційного сетапу автора на базі ASUS ROG Ally (RC71L) та Bazzite OS. Код надається «AS-IS» без гарантій та офіційної підтримки. Ви можете вільно форкати, модифікувати та адаптувати ці скрипти під власні потреби.

---

## 🏷️ Теги та ключові слова (SEO / Discoverability)

`allydock` • `ally-dock` • `asus-rog-ally` • `rog-ally` • `bazzite-os` • `display-detection` • `edid-parser` • `amd-freesync` • `vrr` • `handheld-daemon` • `hhd` • `steam-input` • `docked-mode` • `tdp-switcher` • `mangohud-fps` • `pipewire-audio` • `decky-loader` • `ge-proton` • `linux-gaming` • `kde-plasma-6` • `handheld-pc` • `gamepad-flapping-fix`

---

## 📋 Таблиця протестованого середовища та сумісності (Tested Environment & Compatibility Matrix)

| Компонент / Підсистема | Версія / Конфігурація | Примітки |
| :--- | :--- | :--- |
| **Апаратна платформа** | **ASUS ROG Ally (RC71L.319)** | AMD Ryzen Z1 Extreme, 16GB LPDDR5, 120Hz FreeSync Premium |
| **Операційна система** | **Bazzite 43 / 44 (Kinoite)** | Ядро Linux `6.17.x-ba29.fc43.x86_64` (fsync kernel) |
| **Графічне середовище** | **KDE Plasma 6 (Wayland)** | Gamescope Session у Game Mode, SDDM безпарольний автологін |
| **Display Detection** | **`bin/ally-detect-display.py`** | Чистий Python 3: парсинг EDID (CEA-861, DisplayID, FreeSync OUI `0x00001a`, HDMI VRR OUI `0xc45dd8`, VESA checksum) |
| **Adaptive Profiler** | **`bin/ally-docked-mode.sh`** | 3 рівні: Handheld (45 FPS/15W), TV 60Hz (60 FPS/25W), AMD VRR (0 Uncapped/30W Turbo) |
| **Демон геймпада** | **Handheld Daemon (`hhd`)** | Версія `2888122e`, сумісність з Bazzite 44 `inputplumber` |
| **Decky Loader** | **v3.2.9** (`plugin_loader.service`) | Сумісність з `decky-lsfg-vk`, `CssLoader`, `Junk-Store`, `Bazzite Buddy` |
| **Proton Runner** | **`GE-Proton11-7`** | Змінна середовища: `PROTON_FSR4_RDNA3_UPGRADE=1` |
| **Аудіо-сервер (Sound)** | **PipeWire + WirePlumber** | DSP-фільтр каліброваних динаміків + Valve HRTF 7.1 (`sadie_d1.sofa`) |
| **Накопичувач (SSD)** | **Samsung PM991a 1TB NVMe** (`SAMSUNG MZ9LQ1T0HBLB-00B00`) | Btrfs сабволюми `subvol=root` (`/`) та `subvol=home` (`/var/home`) |

---

## 🚀 Ключові можливості AllyDock (Key Features & Architecture)

### 1. 🖥️ Інтелектуальне визначення дисплея та 3-рівневе адаптивне профілювання (Intelligent Display Detection & 3-Tier Profiling)
- **Детектор дисплеїв (`bin/ally-detect-display.py`):**
  - Реалізований на чистому Python 3 (стандартна бібліотека, нуль сторонніх залежностей).
  - Сканує DRM конектори ядра `/sys/class/drm/card*-*/status` (ігноруючи внутрішній `eDP` та віртуальний `Writeback`).
  - Читає бінарний файл `edid` коннектора та проводить сувору верифікацію:
    - Перевірка магічного VESA заголовка `00 FF FF FF FF FF FF 00`.
    - Перевірка контрольної суми базового блоку та розширень (`sum(block) % 256 == 0`).
  - Витягує точну комерційну назву монітора з дескрипторів `0xFC` (наприклад, "LG OLED TV", "ASUS ROG XG27").
  - Розраховує максимальну підтримувану герцовку (`max_hz`) з детальних DTD таймінгів, стандартних таймінгів та блоку обмежень діапазону `0xFD`.
  - Сканує розширення CTA-861 та DisplayID на наявність:
    - **AMD FreeSync** (Vendor-Specific Data Block, IEEE OUI `0x00001a`);
    - **HDMI Forum VRR** (HF-VSDB, IEEE OUI `0xc45dd8`);
    - **VESA Adaptive-Sync** (DisplayID 2.0 блок `0x22`).
  - Перевіряє DRM властивість `vrr_capable` через sysfs та `drm_info`.
  - Підтримує вивід у форматах `--shell` (для прямого підхоплення у bash) та `--json`.

- **3 адаптивні профілі роботи:**
  1. 📱 **`handheld` (Нічого не підключено / Портатив):**
     - **TDP:** `balanced` (15–20W)
     - **CPU EPP:** `balance_power`
     - **GPU DPM:** `auto`
     - **Цільовий FPS:** **45 FPS** (записується у `MangoHud.conf` та `ally-fps.state` для тихої роботи, плавності на 120Hz екрані 2:1 pulldown та економії батареї)
     - **Аудіо:** калібрований DSP-профіль динаміків `ROG Ally`
     - **Контролер:** вбудований у режимі `mode=uinput`
  2. 📺 **`docked_tv_60` (Звичайний телевізор або офісний 60 Гц монітор):**
     - **TDP:** `performance` (25W)
     - **CPU EPP:** `balance_performance`
     - **GPU DPM:** `auto`
     - **Цільовий FPS:** **60 FPS** (фіксований лок для усунення розривів кадрів та зайвого нагріву на ТБ)
     - **Аудіо:** HDMI (`alsa_output.pci-0000_09_00.1.hdmi-stereo`)
     - **Контролер:** Console-Style режим (якщо підключено зовнішній геймпад — вбудований ховається в `mode=hidden`, зовнішній стає Player 1)
  3. ⚡ **`docked_amd_vrr` (AMD FreeSync / 120Hz+ ігровий монітор):**
     - **TDP:** `performance` (Turbo 30W)
     - **CPU EPP:** `performance`
     - **GPU DPM:** `high` (примусові максимальні частоти графічного чіпа RDNA3)
     - **Цільовий FPS:** **0 (Uncapped / без обмежень кадрової частоти)**
     - **Аудіо:** HDMI
     - **Контролер:** Console-Style режим

- **Безпечний фолбек (Fail-Safe Architecture):**
  - Якщо зовнішній дисплей підключено, але EDID пошкоджено, відсутній або збій читання — автоматично вмикається безпечний `docked_tv_60` (60 FPS, 25W).
  - Якщо зовнішній дисплей відключено — гарантовано активується `handheld` (45 FPS, 15W).

---

### 2. 🎮 Режим Console-Style (Docked Mode Switcher & Controller Arbitration)
- **Проблема:** При встановленні ROG Ally у док-станцію та підключенні телевізора разом із бездротовим або USB-геймпадом (наприклад, Xbox або DualSense) вбудований геймпад консолі залишався першим пристроєм у системі. Більшість ігор призначали зовнішній контролер як «Гравець 2» (Player 2), через що грати з дивана було неможливо без ручних маніпуляцій.
- **Рішення AllyDock:** Скрипт `ally-docked-mode.sh` у зв'язці з udev відстежує стан підключення зовнішнього дисплея та зовнішнього геймпада:
  - **ТВ + зовнішній геймпад:** Вбудований контролер Ally миттєво ховається через API HHD (`controllers.rog_ally.controller_mode.mode=hidden`), і зовнішній геймпад стає **Гравцем 1 (Player 1)**.
  - **ТВ без зовнішнього контролера:** Вбудований контролер залишається активним (`mode=uinput`) для комфортної гри з рук перед великим екраном.
  - **Портативний режим (Handheld):** Контролер автоматично активується у вихідний стан.

---

### 3. 🛡️ Виправлення петлі геймпада (Controller Flapping Fix)
- **Проблема (Чому відвалювався геймпад):**
  1. Раніше скрипти відключали контролер шляхом фізичного unbind USB-інтерфейсу ядра: `echo 1-2:1.0 > /sys/bus/usb/drivers/xpad/unbind`. Це ламало дескриптори у Gamescope (`Failed to open device /dev/input/event17`) та спричиняло помилки ядра URB (`unable to receive magic message: -32`).
  2. HHD емулює пристрій `Xbox Elite` для роботи задніх пелюсток (M1/M2). Скрипти старого зразка через помилку детекції вважали цей **віртуальний Xbox Elite контролер зовнішнім геймпадом**!
  3. Це породжувало нескінченну рекурсивну петлю (flapping loop 10+ разів на хвилину): консоль виявляла свій власний віртуальний геймпад, вимикала його, бачила що геймпадів нема, вмикала знову, і так по колу.
- **Рішення AllyDock:**
  - Повністю вилучено `xpad unbind`. Перемикання виконується виключно через програмний HHD API.
  - Додано строгу udev-фільтрацію з ігноруванням `/devices/virtual/input/*`, що надійно відрізняє справжні фізичні геймпади від емульованих віртуальних вузлів.
  - Реалізовано файловий м'ютекс (`flock` на `/var/home/V/.local/share/ally-docked.lock`), що усуває race condition при масових подіях підключення.

---

### 4. 🔊 Розумний аудіо-роутер PipeWire (HDMI TV vs DSP-динаміки)
- **Проблема:** У системі PipeWire присутні 4 аудіо-виходи: сирий ЦАП ALC294 (`analog-stereo`), HDMI вихід (`hdmi-stereo`), просторовий фільтр `effect_input.spatializer` та калібрований DSP-вузол `ROG Ally`. При перемиканні телевізора звук часто потрапляв на сирий ALC294 (звук був плаский, тихий, без басів) або залишався в консолі.
- **Рішення AllyDock:** `ally-docked-mode.sh` автоматично перемикає активний Default Audio Sink:
  - При підключенні до ТБ звук йде на `alsa_output.pci-0000_09_00.1.hdmi-stereo` (динаміки телевізора/саундбар).
  - При відключенні від ТБ звук повертається на фірмовий калібрувальний DSP-еквалайзер **`ROG Ally`** (насичений звук із глибоким басом).

---

### 5. 🐕 Надійний Watchdog & System-Sleep Hook
- **Динамічний Watchdog (`bin/hhd-watchdog.sh`):** Автоматично визначає активний стек у системі (`hhd.service` у Bazzite 43 чи `inputplumber.service` у Bazzite 44) і перезапускає саме його. Працює як systemd timer кожні 15 хвилин без навантаження на процесор.
- **Хук виходу зі сну (`sleep/10-hhd-watchdog-sleep.sh`):** Встановлюється у `/etc/systemd/system-sleep/`. При пробудженні консолі відновлює стан контролерів та запобігає зависанню введення.

---

### 6. 📜 Steam Desktop Layout: Плавний вертикальний Turbo-скролінг
- **Проблема:** У стандартному Desktop Layout стіки відповідають лише за поодинокі натискання клавіш або стрілок, що робить прокрутку сторінок у браузері надзвичайно повільною та незручною.
- **Рішення AllyDock:** У конфігураціях `desktop_xboxone.vdf` та `desktop_neptune.vdf` лівий стік налаштовано на `mouse_wheel SCROLL_UP` та `mouse_wheel SCROLL_DOWN` із параметрами **Turbo Repeat**:
  ```vdf
  "hold_repeats" "1"
  "repeat_rate"  "20"
  ```
  Відхилення лівого стіка вгору або вниз забезпечує безперервне, плавне гортання сайтів і документів.

---

### 7. 🎯 Прецизійний правий стік (Cursor Precision & Smoothing)
- **Проблема:** Тремтіння курсора під час спроби натиснути на дрібні кнопки інтерфейсу або нелінійний непередбачуваний рух.
- **Рішення AllyDock:** Додано точні коефіцієнти позиціонування:
  - `"sensitivity" "130"` — калібрована чутливість.
  - `"response_curve" "2"` — експоненційна крива: мікрорухи біля центру стіка дають піксельну точність, глибоке відхилення стіка швидко переміщує курсор через весь екран.
  - `"mouse_smoothing" "1"` — апаратне згладжування тремтіння пальців.
  - `"deadzone_inner_radius" "6000"` — зона спокою, що виключає випадковий дрейф курсора.

---

## 📂 Структура репозиторію та опис файлів

```
devices/allydock/
├── VERSION                          # Файл версії конфігураційного пакету AllyDock (1.1.0)
├── README.md                        # Детальна документація, специфікація та інструкції AllyDock
├── restore.sh                       # Єдиний bash-скрипт відновлення конфігурацій (one-command setup)
├── bin/
│   ├── ally-detect-display.py       # Детектор дисплеїв: EDID, VESA checksum, FreeSync, HDMI VRR, Hz
│   ├── ally-docked-mode.sh          # Головний адаптивний оркестратор (3 профілі, TDP, EPP, FPS, Audio)
│   └── hhd-watchdog.sh              # Сторожовий демон самовідновлення сервісів HHD / InputPlumber
├── hhd/
│   └── state.yml                    # Експортований робочий стан HHD (DualSense/Xbox, paddles as Steam Input)
├── sleep/
│   └── 10-hhd-watchdog-sleep.sh     # Системний хук /etc/systemd/system-sleep/ для виходу з режиму сну
├── steam/
│   ├── desktop_neptune.vdf          # Патчений шаблон Steam Input Desktop Layout (Neptune / Deck style)
│   └── desktop_xboxone.vdf          # Патчений шаблон Steam Input Desktop Layout (Xbox One / Ally style)
├── systemd/
│   ├── ally-docked.service          # Одноразовий системний сервіс обробки подій підключення док-станції
│   ├── hhd-watchdog.service         # Фонова служба перевірки стану демонів введення
│   └── hhd-watchdog.timer           # Таймер регулярного опитування watchdog (кожні 15 хвилин)
└── udev/
    └── 99-ally-docked.rules         # Udev-правила реакції на DRM/HDMI дисплеї та USB геймпади
```

---

## ⚡ Швидке розгортання та відновлення AllyDock (Quick Start)

Якщо ви перевстановили Bazzite OS, зробили rebase на нову версію Fedora або розгортаєте комплекс AllyDock:

### Крок 1. Клонуйте репозиторій та перейдіть у каталог проекту
```bash
git clone https://github.com/VadymTaras/rog-ally-bazzite-config.git
cd rog-ally-bazzite-config
```

### Крок 2. Запустіть скрипт відновлення з правами суперкористувача
```bash
sudo ./restore.sh
```

Скрипт автоматично:
- Створить необхідні каталоги в системі та домашньому каталозі користувача `V` (`/var/home/V/`).
- Встановить та надасть права на виконання скриптам `ally-docked-mode.sh`, `ally-detect-display.py` та `hhd-watchdog.sh`.
- Встановить udev-правила та виконає `udevadm control --reload-rules && udevadm trigger`.
- Розгорне служби `ally-docked.service`, `hhd-watchdog.service` та активує `hhd-watchdog.timer`.
- Встановить системний хук `/etc/systemd/system-sleep/10-hhd-watchdog-sleep.sh`.
- Відновить конфігурацію `/etc/hhd/state.yml` з коректними правами доступу.
- Встановить модифіковані шаблони Steam Input Desktop Layout у `controller_base`.

### Крок 3. Перезавантажте консоль
```bash
sudo systemctl reboot
```

---

## 🕹️ Керування та гарячі клавіші у системі

### Апаратний режим миші (Hardware Mouse Mode від HHD)
Працює на рівні мікроконтролера MCU (`0b05:1abe`) навіть тоді, коли Steam вимкнено або завис:
- 🔘 **Увімкнення/Вимкнення:** Затиснути кнопку **Armoury Crate** (кнопка праворуч від екрана з фірмовим логотипом ROG / трикутником) на **~1.5 секунди**.
  - **Подвійна вібрація:** Режим апаратної миші увімкнено!
  - **Одинарна вібрація:** Повернення у режим стандартного геймпада.
- 🕹️ **Правий стік:** Рух курсора миші по екрану.
- 🔘 **RB (Правий бампер):** Лівий клік миші (LMB).
- 🔘 **RT (Правий тригер):** Правий клік миші (RMB).
- 🕹️ **Лівий стік / D-Pad:** Вертикальний скролінг коліщатком.

### Програмний режим миші (Steam Input Desktop Layout)
Активний за замовчуванням у робочому столі KDE Plasma 6 при запущеному у фоні Steam:
- 🕹️ **Правий стік:** Прецизійне керування курсором миші (експоненційна крива + згладжування тремтіння).
- 🕹️ **Лівий стік:** Плавний вертикальний скролінг сторінок з функцією Turbo автоповтору.
- 🔘 **RT (Правий тригер):** Лівий клік миші (LMB).
- 🔘 **LT (Лівий тригер):** Правий клік миші (RMB).

### Віртуальна клавіатура у Desktop Mode
- ⌨️ **Шорткат HHD:** Швидкий короткий тап по кнопці **Armoury Crate** (кнопка праворуч від екрана).
- 👆 **Сенсорний екран (Gesture):** Свайп пальцем знизу вгору від нижнього краю екрана.
- 🎮 **Шорткат Steam:** Кнопка **Command Center** (ліворуч від екрана) + **`X`**.
- 🖥️ **Wayland Virtual Keyboard:** При натисканні на текстові поля вводу в KDE Plasma екранна клавіатура з'являється автоматично.

---

## 🛠️ Корисні команди для діагностики та керування

### Детальний статус системи та дисплея
```bash
/var/home/V/.local/bin/ally-docked-mode.sh status
```

### Запуск детектора дисплея безпосередньо
```bash
# Людський вивід:
/var/home/V/.local/bin/ally-detect-display.py

# JSON формат:
/var/home/V/.local/bin/ally-detect-display.py --json

# Shell формат (для eval/скриптів):
/var/home/V/.local/bin/ally-detect-display.py --shell
```

### Ручне перемикання профілів
```bash
# Примусово активувати портативний профіль (15W Balanced, 45 FPS, динаміки):
/var/home/V/.local/bin/ally-docked-mode.sh handheld

# Примусово активувати телевізійний 60Hz профіль (25W Performance, 60 FPS, HDMI):
/var/home/V/.local/bin/ally-docked-mode.sh docked-tv

# Примусово активувати ігровий VRR профіль (30W Turbo, Uncapped FPS, GPU High DPM, HDMI):
/var/home/V/.local/bin/ally-docked-mode.sh docked-vrr
```

### Ручне керування кадровою частотою (FPS Target)
```bash
/var/home/V/.local/bin/ally-docked-mode.sh fps-45
/var/home/V/.local/bin/ally-docked-mode.sh fps-60
/var/home/V/.local/bin/ally-docked-mode.sh fps-uncapped
```

### Ручне перемикання аудіо
```bash
# Звук на HDMI телевізора:
/var/home/V/.local/bin/ally-docked-mode.sh audio-hdmi

# Звук на калібровані DSP динаміки ROG Ally:
/var/home/V/.local/bin/ally-docked-mode.sh audio-speaker
```

### Перевірка логів та служб
```bash
/var/home/V/.local/bin/ally-docked-mode.sh log
systemctl status hhd-watchdog.timer
systemctl status hhd-watchdog.service
```

---

## 📜 Ліцензія та авторство

Комплекс **AllyDock** розроблено, оптимізовано та протестовано для ASUS ROG Ally на базі Bazzite OS. Розповсюджується під ліцензією MIT — вільно використовуйте, модифікуйте та інтегруйте у власні збірки!

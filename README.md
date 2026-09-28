# ⚓ AllyDock (v1.0.0)
### Autonomous Docking & System Optimization Suite for ASUS ROG Ally on Bazzite OS

[![Project](https://img.shields.io/badge/Project-AllyDock-orange.svg)](#)
[![Version](https://img.shields.io/badge/Version-v1.0.0-blue.svg)](VERSION)
[![OS](https://img.shields.io/badge/OS-Bazzite%2043%20%7C%2044-purple.svg)](https://bazzite.gg)
[![Hardware](https://img.shields.io/badge/Hardware-ASUS%20ROG%20Ally%20(RC71L)-red.svg)](https://rog.asus.com/gaming-handhelds/rog-ally/rog-ally-2023/)
[![Kernel](https://img.shields.io/badge/Kernel-Linux%206.17.x%20(fsync)-green.svg)](https://kernel.org)
[![Status](https://img.shields.io/badge/Status-Tested%20%26%20Verified-success.svg)](#таблиця-протестованого-середовища-та-сумісності)
[![Desktop](https://img.shields.io/badge/Desktop-KDE%20Plasma%206%20(Wayland)-informational.svg)](https://kde.org)

> [!IMPORTANT]
> **Автономний комплекс стикування та оптимізацій AllyDock**  
> Репозиторій **AllyDock** містить вивірений комплекс скриптів автоматизації, udev-правил, системних служб `systemd`, хуків виходу зі сну, профілю Handheld Daemon (`hhd`) та налаштувань Steam Input Desktop Layout для портативної ігрової консолі **ASUS ROG Ally (RC71L)** під керуванням операційної системи **Bazzite OS**.
> Пакет **AllyDock** протестовано у бойових умовах: він виправляє критичні баги петлі геймпада (controller flapping loop), усуває проблеми зі звуком та сном, додає безшовне автоматичне керування TDP і аудіо при підключенні до ТБ (Console-Style-style Docked Mode), а також перетворює керування робочим столом стіками на комфортне та надточне.

> [!NOTE]
> **Personal Backup & Disclaimer**  
> Репозиторій створено для резервного копіювання та автоматизованого розгортання конфігураційного сетапу автора на базі ASUS ROG Ally (RC71L) та Bazzite OS. Код надається «AS-IS» без гарантій та офіційної підтримки. Ви можете вільно форкати, модифікувати та адаптувати ці скрипти під власні потреби.

---

## 🏷️ Теги та ключові слова (SEO / Discoverability)

`allydock` • `ally-dock` • `asus-rog-ally` • `rog-ally` • `bazzite-os` • `handheld-daemon` • `hhd` • `steam-input` • `docked-mode` • `tdp-switcher` • `pipewire-audio` • `decky-loader` • `ge-proton` • `linux-gaming` • `kde-plasma-6` • `handheld-pc` • `gamepad-flapping-fix`

---

## 📋 Таблиця протестованого середовища та сумісності (Tested Environment & Compatibility Matrix)

| Компонент / Підсистема | Протестована версія / Специфікація | Примітки |
| :--- | :--- | :--- |
| **Проєкт (Suite)** | **AllyDock v1.0.0** | Autonomous Docking & System Optimization Suite |
| **Пристрій (Hardware)** | **ASUS ROG Ally (RC71L)** | AMD Ryzen Z1 Extreme (8C/16T, RDNA 3), MCU `0b05:1abe` |
| **Операційна система (OS)** | **Bazzite 43** (Kinoite build `43.20260420`)<br>**Bazzite 44** (Stable build `44.20260921`) | Fedora Atomic Desktop (ostree-based immutable OS) |
| **Ядро Linux (Kernel)** | **`6.17.7-ba29.fc43.x86_64`** | З нативними патчами fsync, HDR та розширеннями ASUS WMI |
| **Handheld Daemon** | **`hhd` v2.88.x** (build `v2888122e`) | Керування контролером, емуляція DualSense/Xbox, TDP |
| **Стільничне середовище** | **KDE Plasma 6 (Wayland)** | Включно з автовикликом Wayland Virtual Keyboard |
| **Steam UI & Керування** | **Steam Game Mode + Steam Input Desktop Layout** | Патчені шаблони з плавним Turbo-скролінгом та експоненційною кривою миші |
| **Decky Loader** | **v3.2.9** (`plugin_loader.service`) | Сумісність з `decky-lsfg-vk`, `CssLoader`, `Junk-Store`, `Bazzite Buddy` |
| **Proton Runner** | **`GE-Proton11-7`** | Змінна середовища: `PROTON_FSR4_RDNA3_UPGRADE=1` |
| **Аудіо-сервер (Sound)** | **PipeWire + WirePlumber** | DSP-фільтр каліброваних динаміків + Valve HRTF 7.1 (`sadie_d1.sofa`) |
| **Накопичувач (SSD)** | **Samsung PM991a 1TB NVMe** (`SAMSUNG MZ9LQ1T0HBLB-00B00`) | Btrfs сабволюми `subvol=root` (`/`) та `subvol=home` (`/var/home`) |

---

## 🚀 Ключові проблеми, які вирішує AllyDock (Key Features & Problems Solved)

### 1. 🎮 Режим Console-Style (Docked Mode Switcher)
- **Проблема:** При встановленні ROG Ally у док-станцію та підключенні телевізора разом із бездротовим або USB-геймпадом (наприклад, Xbox або DualSense) вбудований геймпад консолі залишався першим пристроєм у системі. Більшість ігор призначали зовнішній контролер як «Гравець 2» (Player 2), через що грати з дивана було неможливо без ручних маніпуляцій.
- **Рішення AllyDock:** Скрипт `ally-docked-mode.sh` у зв'язці з udev відстежує стан підключення зовнішнього дисплея та зовнішнього геймпада:
  - **ТВ + зовнішній геймпад:** Вбудований контролер Ally миттєво ховається через API HHD (`controllers.rog_ally.controller_mode.mode=hidden`), і зовнішній геймпад стає **Гравцем 1 (Player 1)**.
  - **ТВ без зовнішнього контролера:** Вбудований контролер залишається активним (`mode=uinput`) для комфортної гри з рук перед великим екраном.
  - **Портативний режим (Handheld):** Контролер автоматично активується у вихідний стан.

### 2. 🛡️ Виправлення петлі геймпада (Controller Flapping Fix)
- **Проблема (Чому відвалювався геймпад):**
  1. Раніше скрипти відключали контролер шляхом фізичного unbind USB-інтерфейсу ядра: `echo 1-2:1.0 > /sys/bus/usb/drivers/xpad/unbind`. Це ламало дескриптори у Gamescope (`Failed to open device /dev/input/event17`) та спричиняло помилки ядра URB (`unable to receive magic message: -32`).
  2. HHD емулює пристрій `Xbox Elite` для роботи задніх пелюсток (M1/M2). Скрипти старого зразка через помилку детекції вважали цей **віртуальний Xbox Elite контролер зовнішнім геймпадом**!
  3. Це породжувало нескінченну рекурсивну петлю (flapping loop 10+ разів на хвилину): консоль виявляла свій власний віртуальний геймпад, вимикала його, бачила що геймпадів нема, вмикала знову, і так по колу.
- **Рішення AllyDock:**
  - Повністю вилучено `xpad unbind`. Перемикання виконується виключно через програмний HHD API.
  - Додано строгу udev-фільтрацію з ігноруванням `/devices/virtual/input/*`, що надійно відрізняє справжні фізичні геймпади від емульованих віртуальних вузлів.
  - Реалізовано файловий м'ютекс (`flock` на `/var/home/V/.local/share/ally-docked.lock`), що усуває race condition при масових подіях підключення.

### 3. ⚡ Автоматичне керування TDP (Handheld vs Docked)
- **Docked Mode (на ТБ):** Автоматично встановлює профіль **`performance` (Turbo 25W–30W)** через HHD (`tdp.asus.tdp_v2.mode=performance`) та системний ACPI `platform_profile`. Забезпечує максимальний фреймрейт та роздільну здатність на великому екрані.
- **Handheld Mode (у руках):** Автоматично знижує TDP до **`balanced` (15W–20W)** для комфортної температури корпусу, тихої роботи кулерів та економії заряду батареї.

### 4. 🔊 Розумний аудіо-роутер PipeWire (HDMI TV vs DSP-динаміки)
- **Проблема:** У системі PipeWire присутні 4 аудіо-виходи: сирий ЦАП ALC294 (`analog-stereo`), HDMI вихід (`hdmi-stereo`), просторовий фільтр `effect_input.spatializer` та калібрований DSP-вузол `ROG Ally`. При перемиканні телевізора звук часто потрапляв на сирий ALC294 (звук був плаский, тихий, без басів) або залишався в консолі.
- **Рішення AllyDock:** `ally-docked-mode.sh` автоматично перемикає активний Default Audio Sink:
  - При підключенні до ТБ звук йде на `alsa_output.pci-0000_09_00.1.hdmi-stereo` (динаміки телевізора/саундбар).
  - При відключенні від ТБ звук повертається на фірмовий калібрувальний DSP-еквалайзер **`ROG Ally`** (насичений звук із глибоким басом).

### 5. 🐕 Надійний Watchdog & System-Sleep Hook
- **Динамічний Watchdog (`bin/hhd-watchdog.sh`):** Автоматично визначає активний стек у системі (`hhd.service` у Bazzite 43 чи `inputplumber.service` у Bazzite 44) і перезапускає саме його. Працює як systemd timer кожні 15 хвилин без навантаження на процесор.
- **Хук виходу зі сну (`sleep/10-hhd-watchdog-sleep.sh`):** Встановлюється у `/etc/systemd/system-sleep/`. При пробудженні консолі відновлює стан контролерів та запобігає зависанню введення.

### 6. 📜 Steam Desktop Layout: Плавний вертикальний Turbo-скролінг
- **Проблема:** У стандартному Desktop Layout стіки відповідають лише за поодинокі натискання клавіш або стрілок, що робить прокрутку сторінок у браузері надзвичайно повільною та незручною.
- **Рішення AllyDock:** У конфігураціях `desktop_xboxone.vdf` та `desktop_neptune.vdf` лівий стік налаштовано на `mouse_wheel SCROLL_UP` та `mouse_wheel SCROLL_DOWN` із параметрами **Turbo Repeat**:
  ```vdf
  "hold_repeats" "1"
  "repeat_rate"  "20"
  ```
  Відхилення лівого стіка вгору або вниз забезпечує безперервне, плавне гортання сайтів і документів.

### 7. 🎯 Прецизійний правий стік (Cursor Precision & Smoothing)
- **Проблема:** Тремтіння курсора під час спроби натиснути на дрібні кнопки інтерфейсу або нелінійний непередбачуваний рух.
- **Рішення AllyDock:** Групу `joystick_mouse` відкалібровано для ювелірного наведення:
  - `"sensitivity" "130"` — збалансована швидкість переміщення.
  - `"response_curve" "2"` — експоненційна крива: мікрорухи біля центру стіка дають піксельну точність, глибоке відхилення стіка швидко переміщує курсор через весь екран.
  - `"mouse_smoothing" "1"` — апаратне згладжування тремтіння пальців.
  - `"deadzone_inner_radius" "6000"` — зона спокою, що виключає випадковий дрейф курсора.

---

## 📂 Структура репозиторію та опис файлів

```
devices/allydock/
├── VERSION                          # Файл версії конфігураційного пакету AllyDock (1.0.0)
├── README.md                        # Детальна документація, специфікація та інструкції AllyDock
├── restore.sh                       # Єдиний bash-скрипт відновлення конфігурацій (one-command setup)
├── bin/
│   ├── ally-docked-mode.sh          # Головний оркестратор Docked Mode (Player 1, TDP, Audio, flock)
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

Якщо ви перевстановили Bazzite OS, зробили rebase на нову версію Fedora або розгортаєте комплекс AllyDock вперше:

### Крок 1. Клонуйте репозиторій та перейдіть у каталог проекту
```bash
git clone https://github.com/VadymTaras/rog-ally-bazzite-config.git
cd rog-ally-bazzite-config
```
*(або скористайтеся аліасом репозиторію: `git clone https://github.com/VadymTaras/AllyDock.git && cd AllyDock`)*

### Крок 2. Запустіть скрипт відновлення з правами суперкористувача
```bash
sudo ./restore.sh
```

Скрипт автоматично:
- Створить необхідні каталоги в системі та домашньому каталозі користувача `V` (`/var/home/V/`).
- Скопіює та надасть права на виконання скриптам `bin/ally-docked-mode.sh` та `bin/hhd-watchdog.sh`.
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

## 🛠️ Корисні команди для діагностики

Перевірка статусу поточного режиму AllyDock (Docked vs Handheld, активний аудіо-вихід, TDP):
```bash
/var/home/V/.local/bin/ally-docked-mode.sh status
```

Примусове перемикання звуку на HDMI телевізора:
```bash
/var/home/V/.local/bin/ally-docked-mode.sh audio-hdmi
```

Примусове повернення звуку на калібровані динаміки ROG Ally:
```bash
/var/home/V/.local/bin/ally-docked-mode.sh audio-speaker
```

Перевірка роботи таймера та служб HHD Watchdog:
```bash
systemctl status hhd-watchdog.timer
systemctl status hhd-watchdog.service
```

---

## 📜 Ліцензія та авторство

Комплекс **AllyDock** оптимізовано та протестовано для персонального ігрового сетапу ASUS ROG Ally на базі Bazzite OS. Розповсюджується під ліцензією MIT — вільно використовуйте, модифікуйте та інтегруйте у власні збірки!

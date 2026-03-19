#!/usr/bin/env python3
"""
Автомобильный диагностический сканер OBD-II
Графический интерфейс (tkinter)
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import time
import sys
from datetime import datetime

try:
    import updater
    UPDATER_AVAILABLE = True
except ImportError:
    UPDATER_AVAILABLE = False

# ── Проверка зависимостей ────────────────────────────────
DEMO_MODE_FORCED = False
try:
    import obd
    from obd import OBDStatus
except ImportError:
    DEMO_MODE_FORCED = True

# ─────────────────────────────────────────────────────────
# Данные
# ─────────────────────────────────────────────────────────

DTC_DESCRIPTIONS = {
    "P0100": "Неисправность цепи расходомера воздуха (MAF)",
    "P0101": "Расходомер воздуха вне диапазона",
    "P0102": "Низкий сигнал расходомера воздуха",
    "P0103": "Высокий сигнал расходомера воздуха",
    "P0110": "Неисправность датчика температуры впускного воздуха",
    "P0115": "Неисправность датчика температуры охлаждающей жидкости",
    "P0120": "Неисправность датчика положения дроссельной заслонки",
    "P0130": "Лямбда-зонд (банк 1, д.1) — нет реакции",
    "P0131": "Лямбда-зонд (банк 1, д.1) — низкое напряжение",
    "P0132": "Лямбда-зонд (банк 1, д.1) — высокое напряжение",
    "P0171": "Система слишком бедная смесь (банк 1)",
    "P0172": "Система слишком богатая смесь (банк 1)",
    "P0300": "Случайные пропуски зажигания",
    "P0301": "Пропуск зажигания в цилиндре №1",
    "P0302": "Пропуск зажигания в цилиндре №2",
    "P0303": "Пропуск зажигания в цилиндре №3",
    "P0304": "Пропуск зажигания в цилиндре №4",
    "P0340": "Неисправность датчика положения распредвала",
    "P0400": "Неисправность системы EGR",
    "P0420": "Каталитический нейтрализатор ниже нормы (банк 1)",
    "P0430": "Каталитический нейтрализатор ниже нормы (банк 2)",
    "P0440": "Неисправность системы EVAP",
    "P0442": "Малая утечка в системе EVAP",
    "P0455": "Большая утечка в системе EVAP",
    "P0500": "Неисправность датчика скорости",
    "P0505": "Неисправность системы холостого хода",
    "P0700": "Неисправность системы управления КПП",
    "P0715": "Неисправность датчика входного вала КПП",
    "P0730": "Некорректное передаточное число",
    "C0031": "Неисправность датчика ABS — переднее левое колесо",
    "C0034": "Неисправность датчика ABS — переднее правое колесо",
    "C0037": "Неисправность датчика ABS — заднее левое колесо",
    "C0040": "Неисправность датчика ABS — заднее правое колесо",
    "B0001": "Неисправность воспламенителя фронтальной подушки",
    "B0002": "Неисправность воспламенителя боковой подушки",
    "U0001": "Неисправность шины CAN",
    "U0100": "Потеря связи с блоком управления двигателем",
    "U0121": "Потеря связи с блоком управления ABS",
}

DEMO_ERRORS = [
    ("P0301", "Активная",    "Пропуск зажигания в цилиндре №1",              "🔴 Высокая"),
    ("P0420", "Активная",    "Каталитический нейтрализатор ниже нормы",      "⚠️ Средняя"),
    ("P0172", "Замороженная","Система слишком богатая смесь (банк 1)",        "⚠️ Средняя"),
    ("U0001", "Ожидающая",   "Неисправность шины CAN",                       "🟡 Низкая"),
    ("C0031", "Активная",    "Датчик ABS — переднее левое колесо",            "🔴 Высокая"),
]

DEMO_LIVE = [
    ("Обороты двигателя",             "820",   "об/мин"),
    ("Скорость",                       "0",     "км/ч"),
    ("Темп. охлаждающей жидкости",    "91",    "°C"),
    ("Нагрузка двигателя",             "23.5",  "%"),
    ("Положение дроссельной заслонки","15.3",  "%"),
    ("Уровень топлива",                "68",    "%"),
    ("Лямбда-зонд (банк 1, д.1)",     "0.71",  "В"),
    ("Кратк. коррекция топлива б.1",  "8.6",   "%"),
    ("Расход воздуха (MAF)",           "3.20",  "г/с"),
    ("Опережение зажигания",           "12.0",  "°"),
    ("Темп. впускного воздуха",        "24",    "°C"),
    ("Давление во впускном коллект.", "101",   "кПа"),
]

DEMO_MONITORS = [
    ("MIL (Check Engine)",          "Да",  "Готов"),
    ("Пропуски зажигания",          "Да",  "Не завершён"),
    ("Топливная система",            "Да",  "Готов"),
    ("Каталитический нейтрализатор","Да",  "Не завершён"),
    ("Система EVAP",                 "Да",  "Готов"),
    ("Лямбда-зонд",                 "Да",  "Не завершён"),
    ("Подогрев лямбда-зонда",       "Да",  "Готов"),
]

COLORS = {
    "bg":         "#0f1117",
    "panel":      "#1a1d27",
    "border":     "#2a2d3e",
    "accent":     "#00d4ff",
    "accent2":    "#7b5ea7",
    "green":      "#00ff9d",
    "red":        "#ff4757",
    "yellow":     "#ffa502",
    "text":       "#e8eaf6",
    "text_dim":   "#7880a0",
    "row_even":   "#1e2133",
    "row_odd":    "#171a28",
}

# ─────────────────────────────────────────────────────────
# Главное окно
# ─────────────────────────────────────────────────────────

class OBDApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("OBD-II Диагностика автомобиля")
        self.geometry("1100x750")
        self.minsize(900, 600)
        self.configure(bg=COLORS["bg"])

        self.connection = None
        self.demo_mode  = DEMO_MODE_FORCED
        self.scanning   = False
        self.live_running = False

        self._build_ui()
        self._update_status("Готов к подключению", COLORS["text_dim"])

        # Проверка обновлений через 2 сек после запуска
        if UPDATER_AVAILABLE:
            self.after(2000, self._check_updates_silent)

    # ── Интерфейс ─────────────────────────────────────────

    def _build_ui(self):
        # Заголовок
        hdr = tk.Frame(self, bg=COLORS["bg"], pady=12)
        hdr.pack(fill="x", padx=20)

        tk.Label(hdr, text="🚗  OBD-II ДИАГНОСТИКА", font=("Consolas", 20, "bold"),
                 bg=COLORS["bg"], fg=COLORS["accent"]).pack(side="left")

        self.status_label = tk.Label(hdr, text="", font=("Consolas", 10),
                                     bg=COLORS["bg"], fg=COLORS["text_dim"])
        self.status_label.pack(side="right", padx=10)

        # Разделитель
        tk.Frame(self, bg=COLORS["border"], height=1).pack(fill="x", padx=20)

        # Панель управления
        ctrl = tk.Frame(self, bg=COLORS["panel"], pady=10)
        ctrl.pack(fill="x", padx=20, pady=(12, 0))

        tk.Label(ctrl, text="Порт:", bg=COLORS["panel"], fg=COLORS["text"],
                 font=("Consolas", 10)).pack(side="left", padx=(12, 4))

        self.port_var = tk.StringVar(value="AUTO")
        self.port_entry = tk.Entry(ctrl, textvariable=self.port_var, width=14,
                                   bg=COLORS["bg"], fg=COLORS["text"],
                                   insertbackground=COLORS["accent"],
                                   relief="flat", font=("Consolas", 10),
                                   highlightbackground=COLORS["border"],
                                   highlightthickness=1)
        self.port_entry.pack(side="left", padx=4)

        self.demo_var = tk.BooleanVar(value=DEMO_MODE_FORCED)
        demo_cb = tk.Checkbutton(ctrl, text="Демо-режим",
                                  variable=self.demo_var,
                                  bg=COLORS["panel"], fg=COLORS["text_dim"],
                                  selectcolor=COLORS["bg"],
                                  activebackground=COLORS["panel"],
                                  font=("Consolas", 10),
                                  state="disabled" if DEMO_MODE_FORCED else "normal")
        demo_cb.pack(side="left", padx=14)

        tk.Label(ctrl, text="Протокол:", bg=COLORS["panel"], fg=COLORS["text"],
                 font=("Consolas", 10)).pack(side="left", padx=(12, 4))

        self.proto_var = tk.StringVar(value="AUTO")
        proto_cb = ttk.Combobox(ctrl, textvariable=self.proto_var, width=16,
                                 font=("Consolas", 9), state="readonly",
                                 values=["AUTO", "ISO 9141-2 (до 2008)", "KWP2000", "CAN 11bit", "CAN 29bit"])
        proto_cb.pack(side="left", padx=4)

        self.btn_connect = self._btn(ctrl, "⚡ Подключить", self._connect, COLORS["accent"])
        self.btn_connect.pack(side="left", padx=6)

        self.btn_scan = self._btn(ctrl, "🔍 Сканировать", self._scan, COLORS["green"])
        self.btn_scan.pack(side="left", padx=6)
        self.btn_scan.config(state="disabled")

        self.btn_clear = self._btn(ctrl, "🗑 Сбросить ошибки", self._clear_dtc, COLORS["yellow"])
        self.btn_clear.pack(side="left", padx=6)
        self.btn_clear.config(state="disabled")

        self.btn_save = self._btn(ctrl, "💾 Сохранить отчёт", self._save_report, COLORS["accent2"])
        self.btn_save.pack(side="right", padx=12)
        self.btn_save.config(state="disabled")

        # Вкладки
        style = ttk.Style(self)
        style.theme_use("default")
        style.configure("TNotebook", background=COLORS["bg"], borderwidth=0)
        style.configure("TNotebook.Tab",
                         background=COLORS["panel"], foreground=COLORS["text_dim"],
                         font=("Consolas", 10), padding=[14, 6])
        style.map("TNotebook.Tab",
                  background=[("selected", COLORS["border"])],
                  foreground=[("selected", COLORS["accent"])])

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=20, pady=12)

        self.tab_dtc      = self._make_tab("🔴  Коды ошибок")
        self.tab_live     = self._make_tab("📡  Реальное время")
        self.tab_monitors = self._make_tab("🧪  Готовность систем")
        self.tab_log      = self._make_tab("📋  Журнал")

        self._build_dtc_tab()
        self._build_live_tab()
        self._build_monitor_tab()
        self._build_log_tab()

    def _btn(self, parent, text, cmd, color):
        return tk.Button(parent, text=text, command=cmd,
                         bg=color, fg=COLORS["bg"],
                         font=("Consolas", 9, "bold"),
                         relief="flat", padx=10, pady=5,
                         cursor="hand2",
                         activebackground=COLORS["bg"],
                         activeforeground=color)

    def _make_tab(self, name):
        frame = tk.Frame(self.nb, bg=COLORS["bg"])
        self.nb.add(frame, text=name)
        return frame

    # ── Вкладка: Коды ошибок ──────────────────────────────

    def _build_dtc_tab(self):
        f = self.tab_dtc

        self.dtc_summary = tk.Label(f, text="Подключитесь и запустите сканирование",
                                     bg=COLORS["bg"], fg=COLORS["text_dim"],
                                     font=("Consolas", 11))
        self.dtc_summary.pack(pady=(14, 6))

        cols = ("Код", "Тип", "Описание", "Критичность")
        self.dtc_tree = self._make_tree(f, cols, (90, 120, 480, 120))
        self.dtc_tree.pack(fill="both", expand=True, padx=16, pady=8)

    # ── Вкладка: Параметры реального времени ─────────────

    def _build_live_tab(self):
        f = self.tab_live

        top = tk.Frame(f, bg=COLORS["bg"])
        top.pack(fill="x", padx=16, pady=10)

        self.btn_live = self._btn(top, "▶ Запустить мониторинг", self._toggle_live, COLORS["green"])
        self.btn_live.pack(side="left")
        self.btn_live.config(state="disabled")

        self.live_hz = tk.Label(top, text="", bg=COLORS["bg"], fg=COLORS["text_dim"],
                                 font=("Consolas", 9))
        self.live_hz.pack(side="left", padx=14)

        cols = ("Параметр", "Значение", "Ед. изм.")
        self.live_tree = self._make_tree(f, cols, (320, 140, 100))
        self.live_tree.pack(fill="both", expand=True, padx=16, pady=8)

    # ── Вкладка: Мониторы ────────────────────────────────

    def _build_monitor_tab(self):
        f = self.tab_monitors
        cols = ("Система", "Поддерживается", "Готовность")
        self.mon_tree = self._make_tree(f, cols, (280, 160, 160))
        self.mon_tree.pack(fill="both", expand=True, padx=16, pady=16)

    # ── Вкладка: Журнал ──────────────────────────────────

    def _build_log_tab(self):
        f = self.tab_log
        self.log_box = scrolledtext.ScrolledText(
            f, bg=COLORS["panel"], fg=COLORS["text_dim"],
            font=("Consolas", 9), relief="flat",
            insertbackground=COLORS["accent"],
            state="disabled"
        )
        self.log_box.pack(fill="both", expand=True, padx=16, pady=16)

    # ── Вспомогательные ──────────────────────────────────

    def _make_tree(self, parent, columns, widths):
        style = ttk.Style()
        style.configure("Custom.Treeview",
                         background=COLORS["row_odd"],
                         foreground=COLORS["text"],
                         fieldbackground=COLORS["row_odd"],
                         rowheight=28,
                         font=("Consolas", 9))
        style.configure("Custom.Treeview.Heading",
                         background=COLORS["border"],
                         foreground=COLORS["accent"],
                         font=("Consolas", 9, "bold"),
                         relief="flat")
        style.map("Custom.Treeview", background=[("selected", COLORS["accent2"])])

        frame = tk.Frame(parent, bg=COLORS["bg"])
        frame.pack(fill="both", expand=True)

        sb = ttk.Scrollbar(frame)
        sb.pack(side="right", fill="y")

        tree = ttk.Treeview(frame, columns=columns, show="headings",
                             yscrollcommand=sb.set, style="Custom.Treeview")
        sb.config(command=tree.yview)

        for col, w in zip(columns, widths):
            tree.heading(col, text=col)
            tree.column(col, width=w, minwidth=60)

        tree.tag_configure("even", background=COLORS["row_even"])
        tree.tag_configure("odd",  background=COLORS["row_odd"])
        tree.tag_configure("red",  background="#2a1a1a", foreground=COLORS["red"])
        tree.tag_configure("ok",   background="#0d2a1a", foreground=COLORS["green"])

        tree.pack(side="left", fill="both", expand=True)
        return tree

    def _log(self, msg, color="default"):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_box.config(state="normal")
        self.log_box.insert("end", f"[{ts}] {msg}\n")
        self.log_box.see("end")
        self.log_box.config(state="disabled")

    def _update_status(self, text, color=None):
        self.status_label.config(text=text, fg=color or COLORS["text_dim"])

    # ── Действия ─────────────────────────────────────────

    def _get_protocol_number(self):
        """Перевод названия протокола в номер ELM327."""
        mapping = {
            "AUTO":              None,
            "ISO 9141-2 (до 2008)": obd.protocols.ISO_9141_2       if not DEMO_MODE_FORCED else None,
            "KWP2000":           obd.protocols.ISO_14230_4_KWP      if not DEMO_MODE_FORCED else None,
            "CAN 11bit":         obd.protocols.ISO_15765_4_11bit_500k if not DEMO_MODE_FORCED else None,
            "CAN 29bit":         obd.protocols.ISO_15765_4_29bit_500k if not DEMO_MODE_FORCED else None,
        }
        return mapping.get(self.proto_var.get(), None)

    # ── Обновления ───────────────────────────────────────

    def _check_updates_silent(self):
        """Тихая проверка в фоне при запуске."""
        if not UPDATER_AVAILABLE:
            return
        self._log("Проверка обновлений...")
        updater.check_async(
            on_update_found=lambda info: self.after(0, lambda: self._show_update_dialog(info)),
            on_error=lambda: self._log("Нет связи — проверка обновлений пропущена"),
        )

    def _show_update_dialog(self, info: dict):
        """Диалог с предложением обновиться."""
        ver  = info["version"]
        desc = info["description"]
        size = info.get("size_mb", 0)

        answer = messagebox.askyesno(
            "Доступно обновление",
            f"Новая версия: {ver}\n"
            f"Текущая версия: {updater.get_current_version()}\n\n"
            f"Что нового:\n{desc}\n\n"
            f"Размер: {size} МБ\n\n"
            f"Установить сейчас?",
        )
        if not answer:
            return

        self._do_update(info)

    def _do_update(self, info: dict):
        """Скачать и применить обновление с прогрессом."""
        win = tk.Toplevel(self)
        win.title("Обновление")
        win.geometry("380x140")
        win.resizable(False, False)
        win.configure(bg=COLORS["bg"])
        win.grab_set()

        tk.Label(win, text="Загрузка обновления...",
                 bg=COLORS["bg"], fg=COLORS["text"],
                 font=("Consolas", 11)).pack(pady=(20, 8))

        bar = ttk.Progressbar(win, length=320, mode="determinate")
        bar.pack(pady=4)

        lbl = tk.Label(win, text="0%", bg=COLORS["bg"],
                       fg=COLORS["text_dim"], font=("Consolas", 9))
        lbl.pack()

        def progress(pct):
            self.after(0, lambda: bar.configure(value=pct))
            self.after(0, lambda: lbl.configure(text=f"{pct}%"))

        def do_download():
            ok = updater.apply_update(info["download_url"], progress_cb=progress)
            if ok:
                self.after(0, lambda: self._on_update_ready(win))
            else:
                self.after(0, lambda: self._on_update_failed(win))

        threading.Thread(target=do_download, daemon=True).start()

    def _on_update_ready(self, win):
        win.destroy()
        messagebox.showinfo(
            "Обновление готово",
            "Обновление загружено!\n\nПрограмма закроется и перезапустится с новой версией."
        )
        self.destroy()
        sys.exit(0)

    def _on_update_failed(self, win):
        win.destroy()
        messagebox.showerror("Ошибка", "Не удалось загрузить обновление.\nПроверьте токен и интернет-соединение.")

    def _connect(self):
        if self.demo_var.get() or DEMO_MODE_FORCED:
            self.demo_mode = True
            self._update_status("● Демо-режим активен", COLORS["yellow"])
            self._log("Демо-режим: используются тестовые данные")
            self.btn_scan.config(state="normal")
            self.btn_live.config(state="normal")
            return

        port = self.port_var.get().strip()
        if port.upper() == "AUTO":
            port = None

        proto_name = self.proto_var.get()
        self._log(f"Подключение: порт={port or 'авто'}, протокол={proto_name}")
        self._update_status("⟳ Подключение...", COLORS["yellow"])

        def do_connect():
            try:
                target_port = port
                if target_port is None:
                    # Сканируем доступные порты
                    found_ports = obd.scan_serial()
                    if not found_ports:
                        self.after(0, lambda: self._on_connect_fail(
                            "OBD-адаптер не найден.\n\n"
                            "Убедитесь, что адаптер подключён к USB/Bluetooth\n"
                            "и драйвер установлен."
                        ))
                        return
                    self.after(0, lambda: self._log(f"Найдены порты: {', '.join(found_ports)}"))
                    target_port = found_ports[0]
                    self.after(0, lambda: self._log(f"Пробуем порт: {target_port}"))

                timeout = 30 if "9141" in proto_name else 10
                conn = obd.OBD(
                    portstr=target_port,
                    fast=False,
                    timeout=timeout,
                )
                if conn.status() == OBDStatus.NOT_CONNECTED:
                    self.after(0, lambda: self._on_connect_fail(
                        "Адаптер не отвечает.\n\n"
                        "Для Kia Magentis 2004 выберите протокол\n"
                        "'ISO 9141-2 (до 2008)' и попробуйте снова."
                    ))
                else:
                    self.after(0, lambda: self._log(f"Подключено на порту: {target_port}"))
                    self.connection = conn
                    self.after(0, self._on_connect_ok)
            except Exception as e:
                self.after(0, lambda: self._on_connect_fail(str(e)))

        threading.Thread(target=do_connect, daemon=True).start()

    def _on_connect_ok(self):
        self._update_status("● Подключено", COLORS["green"])
        self._log("Подключено к автомобилю!")
        self.btn_scan.config(state="normal")
        self.btn_live.config(state="normal")

    def _on_connect_fail(self, msg):
        self._update_status("● Не подключено", COLORS["red"])
        self._log(f"Ошибка подключения: {msg}")
        messagebox.showerror("Ошибка подключения",
            f"{msg}\n\nПроверьте:\n"
            "• Адаптер вставлен в OBD-II разъём\n"
            "• Зажигание включено\n"
            "• Правильный COM-порт\n"
            "• Bluetooth сопряжён\n\n"
            "Включите Демо-режим для теста без адаптера.")

    def _scan(self):
        if self.scanning:
            return
        self.scanning = True
        self._log("Начало сканирования...")
        self._update_status("⟳ Сканирование...", COLORS["yellow"])

        # Очистить таблицы
        for tree in (self.dtc_tree, self.mon_tree):
            tree.delete(*tree.get_children())

        threading.Thread(target=self._do_scan, daemon=True).start()

    def _do_scan(self):
        time.sleep(1.2)  # имитация времени сканирования
        if self.demo_mode:
            errors   = DEMO_ERRORS
            monitors = DEMO_MONITORS
        else:
            errors   = self._real_scan_dtc()
            monitors = self._real_scan_monitors()

        self.after(0, lambda: self._populate_dtc(errors))
        self.after(0, lambda: self._populate_monitors(monitors))
        self.after(0, lambda: self._on_scan_done(errors))

    def _populate_dtc(self, errors):
        self.dtc_tree.delete(*self.dtc_tree.get_children())
        for i, row in enumerate(errors):
            tag = "red" if "Высокая" in row[3] else ("even" if i % 2 == 0 else "odd")
            self.dtc_tree.insert("", "end", values=row, tags=(tag,))

        count = len(errors)
        color = COLORS["red"] if count else COLORS["green"]
        self.dtc_summary.config(
            text=f"Найдено ошибок: {count}" if count else "✅ Ошибок не найдено!",
            fg=color
        )

    def _populate_monitors(self, monitors):
        for i, row in enumerate(monitors):
            ready = row[2]
            tag = "ok" if ready == "Готов" else ("even" if i % 2 == 0 else "odd")
            self.mon_tree.insert("", "end", values=row, tags=(tag,))

    def _on_scan_done(self, errors):
        self.scanning = False
        count = len(errors)
        self._update_status(f"● Сканирование завершено — найдено ошибок: {count}",
                             COLORS["red"] if count else COLORS["green"])
        self._log(f"Сканирование завершено. Найдено ошибок: {count}")
        self.btn_save.config(state="normal")
        if errors:
            self.btn_clear.config(state="normal")
            self.nb.select(0)

    # ── Live Data ────────────────────────────────────────

    def _toggle_live(self):
        if self.live_running:
            self.live_running = False
            self.btn_live.config(text="▶ Запустить мониторинг", bg=COLORS["green"])
            self.live_hz.config(text="")
            self._log("Мониторинг остановлен")
        else:
            self.live_running = True
            self.btn_live.config(text="⏹ Остановить мониторинг", bg=COLORS["red"])
            self._log("Мониторинг запущен")
            threading.Thread(target=self._live_loop, daemon=True).start()

    def _live_loop(self):
        cycle = 0
        while self.live_running:
            t0 = time.time()
            if self.demo_mode:
                data = [(p, v, u) for p, v, u in DEMO_LIVE]
                # немного «живости»
                import random
                data[0] = ("Обороты двигателя", str(800 + random.randint(-50, 150)), "об/мин")
                data[2] = ("Темп. охлаждающей жидкости", str(89 + random.randint(0, 5)), "°C")
            else:
                data = self._real_live_data()

            self.after(0, lambda d=data: self._update_live_table(d))
            elapsed = time.time() - t0
            hz = f"{1/elapsed:.1f} Hz" if elapsed > 0 else ""
            self.after(0, lambda h=hz: self.live_hz.config(text=h))
            cycle += 1
            time.sleep(max(0, 0.8 - elapsed))

    def _update_live_table(self, data):
        self.live_tree.delete(*self.live_tree.get_children())
        for i, (param, val, unit) in enumerate(data):
            tag = "even" if i % 2 == 0 else "odd"
            self.live_tree.insert("", "end", values=(param, val, unit), tags=(tag,))

    # ── Сброс ошибок ────────────────────────────────────

    def _clear_dtc(self):
        if not messagebox.askyesno("Сброс ошибок",
            "Сбросить все коды ошибок?\n\nЭто удалит историю неисправностей из памяти ЭБУ."):
            return
        if self.demo_mode:
            self.dtc_tree.delete(*self.dtc_tree.get_children())
            self.dtc_summary.config(text="✅ Ошибки сброшены (демо)", fg=COLORS["green"])
            self._log("Коды ошибок сброшены (демо)")
            self.btn_clear.config(state="disabled")
        else:
            try:
                self.connection.query(obd.commands.CLEAR_DTC)
                self._log("Коды ошибок сброшены")
                self.dtc_tree.delete(*self.dtc_tree.get_children())
                self.btn_clear.config(state="disabled")
            except Exception as e:
                self._log(f"Ошибка сброса: {e}")

    # ── Сохранение отчёта ────────────────────────────────

    def _save_report(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Текстовый файл", "*.txt"), ("Все файлы", "*.*")],
            initialfile=f"diagnostic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        if not path:
            return

        lines = []
        lines.append("ОТЧЁТ ДИАГНОСТИКИ АВТОМОБИЛЯ")
        lines.append(f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
        lines.append("=" * 60)

        lines.append("\nКОДЫ ОШИБОК (DTC):")
        items = self.dtc_tree.get_children()
        if items:
            for it in items:
                v = self.dtc_tree.item(it, "values")
                lines.append(f"  [{v[1]}] {v[0]} — {v[2]} ({v[3]})")
        else:
            lines.append("  Ошибок не найдено.")

        lines.append("\nПАРАМЕТРЫ РЕАЛЬНОГО ВРЕМЕНИ:")
        for it in self.live_tree.get_children():
            v = self.live_tree.item(it, "values")
            lines.append(f"  {v[0]}: {v[1]} {v[2]}")

        lines.append("\nГОТОВНОСТЬ СИСТЕМ:")
        for it in self.mon_tree.get_children():
            v = self.mon_tree.item(it, "values")
            lines.append(f"  {v[0]}: поддерживается={v[1]}, готовность={v[2]}")

        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        self._log(f"Отчёт сохранён: {path}")
        messagebox.showinfo("Готово", f"Отчёт сохранён:\n{path}")

    # ── Реальное подключение (если есть obd) ─────────────

    def _real_scan_dtc(self):
        result = []
        try:
            for cmd, label in [(obd.commands.GET_DTC, "Активная"),
                                (obd.commands.GET_FREEZE_DTC, "Замороженная")]:
                resp = self.connection.query(cmd)
                if not resp.is_null():
                    for dtc in resp.value:
                        code = str(dtc[0]) if dtc[0] else "???"
                        desc = DTC_DESCRIPTIONS.get(code, "Нет описания")
                        sev  = "🔴 Высокая" if code.startswith(("P03","C0","P07")) else \
                               "🟡 Низкая"  if code.startswith("U0") else "⚠️ Средняя"
                        result.append((code, label, desc, sev))
        except Exception as e:
            self._log(f"Ошибка считывания DTC: {e}")
        return result

    def _real_scan_monitors(self):
        result = []
        try:
            resp = self.connection.query(obd.commands.STATUS)
            if not resp.is_null() and resp.value:
                s = resp.value
                checks = [
                    ("Пропуски зажигания",  getattr(s, "MISFIRE_MONITORING", None)),
                    ("Топливная система",    getattr(s, "FUEL_SYSTEM_MONITORING", None)),
                    ("Катализатор",          getattr(s, "CATALYST_MONITORING", None)),
                    ("Система EVAP",         getattr(s, "EVAPORATIVE_SYSTEM_MONITORING", None)),
                    ("Лямбда-зонд",         getattr(s, "OXYGEN_SENSOR_MONITORING", None)),
                    ("EGR",                  getattr(s, "EGR_MONITORING", None)),
                ]
                for name, mon in checks:
                    if mon is not None:
                        avail = "Да" if getattr(mon, "available", False) else "Нет"
                        comp  = "Готов" if getattr(mon, "complete", False) else "Не завершён"
                        result.append((name, avail, comp))
        except Exception as e:
            self._log(f"Ошибка считывания мониторов: {e}")
        return result

    def _real_live_data(self):
        cmds = [
            (obd.commands.RPM,          "Обороты двигателя",           "об/мин"),
            (obd.commands.SPEED,        "Скорость",                     "км/ч"),
            (obd.commands.COOLANT_TEMP, "Темп. охлаждающей жидкости",  "°C"),
            (obd.commands.ENGINE_LOAD,  "Нагрузка двигателя",           "%"),
            (obd.commands.THROTTLE_POS, "Положение дроссельной засл.", "%"),
            (obd.commands.FUEL_LEVEL,   "Уровень топлива",              "%"),
            (obd.commands.MAF,          "Расход воздуха (MAF)",          "г/с"),
            (obd.commands.INTAKE_TEMP,  "Темп. впускного воздуха",      "°C"),
        ]
        result = []
        for cmd, label, unit in cmds:
            try:
                resp = self.connection.query(cmd)
                if not resp.is_null() and resp.value is not None:
                    v = resp.value.magnitude if hasattr(resp.value, "magnitude") else resp.value
                    result.append((label, f"{v:.1f}" if isinstance(v, float) else str(v), unit))
                else:
                    result.append((label, "Нет данных", unit))
            except Exception:
                result.append((label, "Ошибка", unit))
        return result


# ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = OBDApp()
    app.mainloop()

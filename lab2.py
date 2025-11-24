import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import threading
import queue
from PIL import Image, ExifTags

# Подавляем ошибку о слишком большом изображении (DecompressionBombError),
# так как мы работаем с доверенными файлами для лабы.
# В реальном приложении это требует осторожности.
Image.MAX_IMAGE_PIXELS = None


class ImageMetadataApp(tk.Tk):
    """
    GUI-приложение для анализа метаданных изображений из выбранной папки.
    """

    def __init__(self):
        super().__init__()
        self.title("Анализатор метаданных изображений (Лаб. работа №2)")
        self.geometry("1200x700")
        self.minsize(800, 500)
        self.configure(bg="#f0f0f0")

        # --- Переменные состояния ---
        self.data_queue = queue.Queue()
        self.current_scan_thread = None
        self.supported_extensions = (
            '.jpg', '.jpeg', '.gif', '.tif', '.tiff', '.bmp', '.png', '.pcx'
        )

        # --- Стили ---
        style = ttk.Style(self)
        style.configure("Treeview.Heading", font=("Arial", 10, "bold"))
        style.configure("TButton", font=("Arial", 10))
        style.configure("TLabel", background="#f0f0f0", font=("Arial", 10))
        style.configure("TFrame", background="#f0f0f0")

        # --- Создание виджетов ---
        self._create_widgets()
        self._check_queue()

    def _create_widgets(self):
        """Создает и размещает все виджеты в главном окне."""

        # --- Верхняя панель управления ---
        control_frame = ttk.Frame(self, padding=10)
        control_frame.pack(fill="x")

        self.select_button = ttk.Button(
            control_frame,
            text="Выбрать папку для анализа",
            command=self._start_scan
        )
        self.select_button.pack(side="left", padx=(0, 10))

        self.scan_label = ttk.Label(control_frame, text="Для начала выберите папку.")
        self.scan_label.pack(side="left", fill="x", expand=True)

        # --- Фрейм для таблицы с прокруткой ---
        table_frame = ttk.Frame(self, padding=(10, 0, 10, 0))
        table_frame.pack(fill="both", expand=True)
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        # --- Определение колонок таблицы ---
        columns = ("filename", "size", "dpi", "depth", "compression", "extra")

        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")

        # Настройка заголовков
        self.tree.heading("filename", text="Имя файла", anchor="w")
        self.tree.heading("size", text="Размер (ШxВ)", anchor="center")
        self.tree.heading("dpi", text="Разрешение (DPI)", anchor="center")
        self.tree.heading("depth", text="Глубина цвета (бит)", anchor="center")
        self.tree.heading("compression", text="Сжатие", anchor="w")
        self.tree.heading("extra", text="Доп. инфо (для доп. баллов)", anchor="w")

        # Настройка ширины колонок
        self.tree.column("filename", width=250, stretch=True)
        self.tree.column("size", width=120, stretch=False, anchor="center")
        self.tree.column("dpi", width=120, stretch=False, anchor="center")
        self.tree.column("depth", width=150, stretch=False, anchor="center")
        self.tree.column("compression", width=150, stretch=False)
        self.tree.column("extra", width=300, stretch=True)

        # --- Скроллбары ---
        v_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        h_scroll = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")

        # --- Нижняя панель (статус и прогресс) ---
        status_frame = ttk.Frame(self, padding=10)
        status_frame.pack(fill="x")

        self.status_label = ttk.Label(status_frame, text="Готов к работе.")
        self.status_label.pack(side="left", fill="x", expand=True)

        self.progress_bar = ttk.Progressbar(status_frame, orient="horizontal", mode="determinate")
        self.progress_bar.pack(side="right", fill="x", expand=True)

    def _start_scan(self):
        """Инициирует выбор папки и запуск потока сканирования."""
        folder_path = filedialog.askdirectory(title="Выберите папку с изображениями")
        if not folder_path:
            return

        # Очистка предыдущих результатов
        self.tree.delete(*self.tree.get_children())
        self.scan_label.config(text=f"Сканирование папки: {folder_path}")
        self.status_label.config(text="Подготовка к сканированию...")
        self.progress_bar['value'] = 0
        self.select_button.config(state="disabled")

        # Запуск сканирования в отдельном потоке
        self.current_scan_thread = threading.Thread(
            target=self._scan_folder_thread,
            args=(folder_path,),
            daemon=True
        )
        self.current_scan_thread.start()

    def _scan_folder_thread(self, folder_path):
        """
        Рабочая функция потока. Рекурсивно сканирует папку
        и помещает результаты в очередь.
        """
        try:
            # Сбор всех файлов
            file_paths = []
            for root, _, files in os.walk(folder_path):
                for file in files:
                    if file.lower().endswith(self.supported_extensions):
                        file_paths.append(os.path.join(root, file))

            total_files = len(file_paths)
            if total_files == 0:
                self.data_queue.put(
                    ("status", f"В папке {folder_path} не найдено поддерживаемых изображений.")
                )
                self.data_queue.put(("progress", 0, 0))  # Обновить статус
                self.data_queue.put(("done",))  # Завершить
                return

            # Анализ каждого файла
            for i, file_path in enumerate(file_paths):
                try:
                    data = self._extract_metadata(file_path)
                    self.data_queue.put(("data", data))
                except Exception as e:
                    # Ошибка чтения конкретного файла
                    error_data = (
                        os.path.basename(file_path),
                        f"Ошибка: {e}", "N/A", "N/A", "N/A", "N/A"
                    )
                    self.data_queue.put(("data", error_data))

                self.data_queue.put(("progress", i + 1, total_files))

        except Exception as e:
            # Глобальная ошибка потока
            self.data_queue.put(("error", f"Ошибка сканирования: {e}"))
        finally:
            self.data_queue.put(("done",))

    def _check_queue(self):
        """
        Проверяет очередь данных из потока и обновляет GUI.
        Вызывается циклично через self.after().
        """
        try:
            while True:
                message = self.data_queue.get_nowait()
                msg_type, *payload = message

                if msg_type == "data":
                    self.tree.insert("", "end", values=payload[0])

                elif msg_type == "progress":
                    current, total = payload
                    self.progress_bar['value'] = (current / total) * 100
                    self.status_label.config(text=f"Обработано {current} из {total} файлов...")

                elif msg_type == "status":
                    self.status_label.config(text=payload[0])

                elif msg_type == "error":
                    messagebox.showerror("Ошибка", payload[0])

                elif msg_type == "done":
                    self.status_label.config(text="Сканирование завершено.")
                    self.scan_label.config(text="Выберите новую папку для анализа.")
                    self.select_button.config(state="normal")
                    self.progress_bar['value'] = 100  # Убедиться, что 100%
                    return  # Прекратить проверку до следующего сканирования

        except queue.Empty:
            pass  # Очередь пуста, ничего не делаем

        # Перепланируем проверку очереди
        self.after(100, self._check_queue)

    def _extract_metadata(self, file_path):
        """
        Извлекает метаданные из одного файла с помощью Pillow.
        """
        with Image.open(file_path) as img:
            filename = os.path.basename(file_path)
            size = f"{img.width} x {img.height}"
            dpi = self._get_dpi(img)
            depth = self._get_color_depth(img)
            compression = self._get_compression(img)
            extra = self._get_extra_info(img)

            return (filename, size, dpi, depth, compression, extra)

    def _get_dpi(self, img):
        """Помощник: получает DPI из разных источников."""
        if 'dpi' in img.info:
            dpi = img.info['dpi']
            return f"{int(dpi[0])} x {int(dpi[1])}"

        # Для JPEG (JFIF)
        if 'jfif_density' in img.info:
            density = img.info['jfif_density']
            unit = img.info.get('jfif_unit')
            if unit == 1:  # 1 = DPI, 2 = DPC
                return f"{int(density[0])} x {int(density[1])}"
            elif unit == 2:  # Конвертируем DPC в DPI
                return f"{int(density[0] * 2.54)} x {int(density[1] * 2.54)}"

        # Для TIFF (может быть в тегах)
        try:
            # Ищем теги EXIF (Tiff использует их)
            x_res_tag = 282
            y_res_tag = 283
            if hasattr(img, '_getexif') and img._getexif():
                exif = img._getexif()
                if x_res_tag in exif and y_res_tag in exif:
                    # Разрешение хранится как (числитель, знаменатель)
                    x_res = exif[x_res_tag][0][0] / exif[x_res_tag][0][1]
                    y_res = exif[y_res_tag][0][0] / exif[y_res_tag][0][1]
                    return f"{int(x_res)} x {int(y_res)}"
        except Exception:
            pass  # Не удалось прочитать EXIF/TIFF теги

        return "N/A"  # Не найдено

    def _get_color_depth(self, img):
        """Помощник: определяет глубину цвета."""
        mode = img.mode
        if mode == '1':
            return 1  # 1-битный, черно-белый
        elif mode == 'P':
            # 'P' (Палитра). Обычно 8 бит на пиксель (индекс в палитре).
            return 8
        elif mode in ('L', 'LA'):
            # 'L' (Grayscale)
            return 8 * len(img.getbands())
        elif mode in ('RGB', 'RGBA', 'CMYK', 'YCbCr'):
            # img.bits * кол-во каналов (img.bits обычно 8)
            return img.bits * len(img.getbands())
        else:
            return f"Неизв. ({mode})"

    def _get_compression(self, img):
        """Помощник: определяет тип сжатия."""
        # Общий тег 'compression' (особенно для TIFF)
        if 'compression' in img.info:
            return str(img.info['compression'])

        # Специфичные для формата
        fmt = img.format
        if fmt == 'JPEG':
            return "JPEG (DCT)"
        if fmt == 'PNG':
            return "Deflate"
        if fmt == 'GIF':
            return "LZW"
        if fmt == 'BMP':
            # BMP может быть не сжат или RLE
            return img.info.get('compression', 'None (uncompressed)')
        if fmt == 'PCX':
            return "RLE (PackBits)"

        return "N/A"

    def _get_extra_info(self, img):
        """Помощник: извлекает доп. информацию для доп. баллов."""
        fmt = img.format
        extra = []

        # Для GIF: кол-во цветов в палитре
        if fmt == 'GIF' and img.mode == 'P':
            try:
                palette_size = len(img.getpalette()) // 3
                extra.append(f"Палитра: {palette_size} цветов")
            except Exception:
                pass

        if fmt == 'JPEG':
            if 'quantization' in img.info:
                qt_count = len(img.info['quantization'])
                extra.append(f"Таблицы квантования: {qt_count} шт.")

            if hasattr(img, '_getexif') and img._getexif():
                exif_count = len(img._getexif())
                extra.append(f"EXIF-тегов: {exif_count}")

        if 'gamma' in img.info:
            extra.append(f"Gamma: {img.info['gamma']}")
        if 'sRGB' in img.info:
            extra.append(f"Профиль: sRGB (intent {img.info['sRGB']})")

        return "; ".join(extra) if extra else "N/A"


if __name__ == "__main__":
    app = ImageMetadataApp()
    app.mainloop()

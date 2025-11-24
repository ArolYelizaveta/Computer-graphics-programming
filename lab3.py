import tkinter as tk
from tkinter import ttk, filedialog
import cv2
import numpy as np
from PIL import Image, ImageTk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

plt.ioff()

class ImageProcessorApp(tk.Tk):
    """
    GUI-приложение для обработки изображений (Лаб. работа №3).
    ВАРИАНТ 16:
    1. Поэлементные операции (Линейное контрастирование + Негатив)
    2. Морфологическая обработка (Эрозия/Дилатация с выбором ядра)
    """

    def __init__(self):
        super().__init__()
        self.title("Лаб. №3 (Вариант 16): Контрастирование и Морфология")
        self.geometry("1300x900")
        self.minsize(1000, 750)

        self.bg_color = "#f0f2f5"
        self.configure(bg=self.bg_color)

        self.original_cv_image = None
        self.processed_cv_image = None
        self.params = {}

        style = ttk.Style(self)
        style.theme_use('clam')

        base_style = {"background": self.bg_color, "foreground": "black"}

        style.configure("TFrame", **base_style)
        style.configure("TLabel", font=("Segoe UI", 10), **base_style)
        style.configure("TButton", font=("Segoe UI", 9), background="#e1e4e8", foreground="black")
        style.configure("Header.TLabel", font=("Segoe UI", 11, "bold"), **base_style)
        style.configure("TCheckbutton", font=("Segoe UI", 10), **base_style)
        style.configure("TRadiobutton", font=("Segoe UI", 10), **base_style)
        style.configure("TLabelframe", **base_style, relief="groove")
        style.configure("TLabelframe.Label", font=("Segoe UI", 9, "bold"), **base_style)

        self._create_layout()

    def _create_layout(self):
        top_bar = ttk.Frame(self, padding=10)
        top_bar.pack(side="top", fill="x")

        btn_frame = ttk.Frame(top_bar)
        btn_frame.pack(side="left")
        ttk.Button(btn_frame, text="📂 Открыть", command=self._load_image).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="💾 Сохранить", command=self._save_image).pack(side="left", padx=5)

        mode_frame = ttk.Frame(top_bar)
        mode_frame.pack(side="left", padx=30)
        ttk.Label(mode_frame, text="Режим:").pack(side="left", padx=5)

        self.modes = [
            "Поэлементные операции (Контраст)",
            "Морфологическая обработка"
        ]
        self.mode_var = tk.StringVar(value=self.modes[0])
        self.mode_combo = ttk.Combobox(mode_frame, textvariable=self.mode_var, values=self.modes, state="readonly",
                                       width=35)
        self.mode_combo.pack(side="left", padx=5)
        self.mode_combo.bind("<<ComboboxSelected>>", self._on_mode_change)

        self.settings_frame = ttk.LabelFrame(self, text="Параметры", padding=10)
        self.settings_frame.pack(side="top", fill="x", padx=10, pady=5)
        self.controls_container = ttk.Frame(self.settings_frame)
        self.controls_container.pack(fill="x", expand=True)

        work_area = ttk.Frame(self)
        work_area.pack(fill="both", expand=True, padx=10, pady=5)

        left_col = ttk.Frame(work_area)
        left_col.pack(side="left", fill="both", expand=True, padx=5)
        ttk.Label(left_col, text="Исходное изображение", style="Header.TLabel").pack(pady=(0, 5))

        self.canvas_orig = tk.Canvas(left_col, bg="#e1e4e8", height=300, highlightthickness=0)
        self.canvas_orig.pack(side="top", fill="both", expand=True)

        self.hist_frame_orig = ttk.Frame(left_col, height=400)
        self.hist_frame_orig.pack(side="bottom", fill="both", expand=True, pady=5)

        right_col = ttk.Frame(work_area)
        right_col.pack(side="right", fill="both", expand=True, padx=5)
        ttk.Label(right_col, text="Результат обработки", style="Header.TLabel").pack(pady=(0, 5))

        self.canvas_proc = tk.Canvas(right_col, bg="#e1e4e8", height=300, highlightthickness=0)
        self.canvas_proc.pack(side="top", fill="both", expand=True)

        self.hist_frame_proc = ttk.Frame(right_col, height=400)
        self.hist_frame_proc.pack(side="bottom", fill="both", expand=True, pady=5)

        self._update_controls_ui()

    def _update_controls_ui(self):
        for widget in self.controls_container.winfo_children():
            widget.destroy()
        self.params.clear()

        mode = self.mode_var.get()

        if mode == "Поэлементные операции (Контраст)":
            g1 = self._create_control_group("Контрастность")
            self._add_slider(g1, "contrast", "Коэфф. (alpha)", 1.0, 0.1, 5.0)

            g2 = self._create_control_group("Яркость")
            self._add_slider(g2, "brightness", "Смещение (beta)", 0, -127, 127)

            g3 = self._create_control_group("Эффекты")
            self._add_checkbox(g3, "invert", "Инверсия (Негатив)")

        elif mode == "Морфологическая обработка":
            g1 = self._create_control_group("Тип операции")
            self._add_radio(g1, "morph_type", "Erosion", ["Erosion (Сужение)", "Dilation (Расширение)"])

            g2 = self._create_control_group("Структурный элемент")
            self._add_combo(g2, "kernel_shape", "Rect", ["Rect (Прямоугольник)", "Ellipse (Эллипс)", "Cross (Крест)"])
            self._add_slider(g2, "kernel_size", "Размер ядра (px)", 3, 1, 31)

        if self.original_cv_image is not None:
            self._apply_processing()

    def _create_control_group(self, title):
        frame = ttk.Frame(self.controls_container)
        frame.pack(side="left", fill="y", padx=20)
        ttk.Label(frame, text=title, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 10))
        return frame

    def _add_slider(self, parent, key, label, default, min_v, max_v):
        f = ttk.Frame(parent)
        f.pack(fill="x", pady=5)
        ttk.Label(f, text=label).pack(anchor="w")
        var = tk.DoubleVar(value=default)
        self.params[key] = var
        s = ttk.Scale(f, from_=min_v, to=max_v, variable=var, orient="horizontal", length=160,
                      command=lambda v: self._apply_processing())
        s.pack(fill="x")

    def _add_checkbox(self, parent, key, label):
        var = tk.BooleanVar(value=False)
        self.params[key] = var
        ttk.Checkbutton(parent, text=label, variable=var, command=self._apply_processing).pack(anchor="w", pady=5)

    def _add_radio(self, parent, key, default, options):
        var = tk.StringVar(value=default)
        self.params[key] = var
        for opt in options:
            val = opt.split()[0]
            ttk.Radiobutton(parent, text=opt, variable=var, value=val, command=self._apply_processing).pack(anchor="w",
                                                                                                            pady=2)

    def _add_combo(self, parent, key, default, values):
        var = tk.StringVar(value=default)
        self.params[key] = var
        cb = ttk.Combobox(parent, textvariable=var, values=values, state="readonly", width=20)
        cb.pack(fill="x", pady=5)
        cb.bind("<<ComboboxSelected>>", lambda e: self._apply_processing())

    def _on_mode_change(self, event):
        self._update_controls_ui()

    def _load_image(self):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp")])
        if not path: return

        stream = open(path, "rb")
        bytes = bytearray(stream.read())
        numpyarray = np.asarray(bytes, dtype=np.uint8)
        img = cv2.imdecode(numpyarray, cv2.IMREAD_UNCHANGED)
        stream.close()

        if img is None: return

        if len(img.shape) == 3 and img.shape[2] == 4:
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

        self.original_cv_image = img
        self._show_image(self.canvas_orig, img)
        self._draw_histogram(img, self.hist_frame_orig)
        self._apply_processing()

    def _save_image(self):
        if self.processed_cv_image is None: return
        path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png"), ("JPG", "*.jpg")])
        if path:
            is_success, im_buf = cv2.imencode(".png", self.processed_cv_image)
            if is_success: im_buf.tofile(path)

    def _show_image(self, canvas, cv_img):
        if cv_img is None: return

        if len(cv_img.shape) == 3:
            img_rgb = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        else:
            img_rgb = cv2.cvtColor(cv_img, cv2.COLOR_GRAY2RGB)

        h, w = img_rgb.shape[:2]

        cw = canvas.winfo_width() if canvas.winfo_width() > 10 else 400
        ch = canvas.winfo_height() if canvas.winfo_height() > 10 else 300

        scale = min(cw / w, ch / h)
        new_w, new_h = int(w * scale), int(h * scale)

        pil_img = Image.fromarray(img_rgb).resize((new_w, new_h), Image.Resampling.LANCZOS)
        img_tk = ImageTk.PhotoImage(pil_img)

        canvas.delete("all")
        canvas.create_image(cw // 2, ch // 2, image=img_tk, anchor="center")
        canvas.image = img_tk

    def _draw_histogram(self, cv_img, frame):
        for widget in frame.winfo_children():
            widget.destroy()
        if cv_img is None: return

        fig = plt.Figure(figsize=(5, 4), dpi=80)
        ax = fig.add_subplot(111)
        fig.patch.set_facecolor(self.bg_color)
        ax.set_facecolor('#ffffff')

        if len(cv_img.shape) == 2:
            hist = cv2.calcHist([cv_img], [0], None, [256], [0, 256])
            ax.plot(hist, color='black')
            ax.fill_between(range(256), hist.ravel(), color='gray', alpha=0.3)
        else:
            colors = ('b', 'g', 'r')
            for i, color in enumerate(colors):
                hist = cv2.calcHist([cv_img], [i], None, [256], [0, 256])
                ax.plot(hist, color=color, linewidth=1)

        ax.set_xlim([0, 256])
        ax.set_title("Гистограмма", fontsize=10)
        ax.grid(True, alpha=0.2)

        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def _apply_processing(self):
        if self.original_cv_image is None: return

        img = self.original_cv_image.copy()
        mode = self.mode_var.get()

        try:
            if mode == "Поэлементные операции (Контраст)":
                alpha = self.params['contrast'].get()
                beta = self.params['brightness'].get()
                img = cv2.convertScaleAbs(img, alpha=alpha, beta=beta)

                if self.params['invert'].get():
                    img = cv2.bitwise_not(img)

            elif mode == "Морфологическая обработка":
                op = self.params['morph_type'].get()
                shape_str = self.params['kernel_shape'].get()
                k_size = int(self.params['kernel_size'].get())

                if k_size % 2 == 0: k_size += 1

                if "Ellipse" in shape_str:
                    shape = cv2.MORPH_ELLIPSE
                elif "Cross" in shape_str:
                    shape = cv2.MORPH_CROSS
                else:
                    shape = cv2.MORPH_RECT

                kernel = cv2.getStructuringElement(shape, (k_size, k_size))

                if op == "Erosion":
                    img = cv2.erode(img, kernel, iterations=1)
                else:
                    img = cv2.dilate(img, kernel, iterations=1)

            self.processed_cv_image = img
            self._show_image(self.canvas_proc, img)
            self._draw_histogram(img, self.hist_frame_proc)

        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    app = ImageProcessorApp()
    app.mainloop()
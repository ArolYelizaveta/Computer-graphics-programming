import tkinter as tk
from tkinter import ttk, messagebox
import time
import math

# --- ЦВЕТА (Dark Theme) ---
COLORS = {
    "bg": "#2b2b2b",
    "panel_bg": "#313338",
    "canvas_bg": "#1e1e1e",
    "grid_line": "#333333",
    "grid_line_major": "#444444",
    "axis_line": "#5c5c5c",
    "text": "#e0e0e0",
    "accent": "#4a90e2",
    "pixel_default": "#00ff00",  # Зеленый
    "pixel_wu": "#00ffff",  # Циан
    "pixel_curve": "#ff00ff"  # Маджента
}


class RasterizationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Rasterization Lab: Interactive Grid")
        self.root.geometry("1200x800")
        self.root.configure(bg=COLORS["bg"])

        # Настройка стилей
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.configure_styles()

        # --- Состояние камеры ---
        self.cell_size = 20  # Зум (размер клетки)
        self.offset_x = 0  # Сдвиг камеры по X
        self.offset_y = 0  # Сдвиг камеры по Y

        self.drag_start_x = 0
        self.drag_start_y = 0

        # Данные для перерисовки
        self.last_points = []
        self.last_color = COLORS["pixel_default"]

        # --- Интерфейс ---
        self.setup_ui()

        # Первая отрисовка
        self.root.update()
        self.redraw_all()

    def configure_styles(self):
        self.style.configure("TFrame", background=COLORS["panel_bg"])
        self.style.configure("TLabel", background=COLORS["panel_bg"], foreground=COLORS["text"], font=("Segoe UI", 10))
        self.style.configure("TLabelframe", background=COLORS["panel_bg"], foreground=COLORS["accent"])
        self.style.configure("TLabelframe.Label", background=COLORS["panel_bg"], foreground=COLORS["accent"],
                             font=("Segoe UI", 10, "bold"))
        self.style.configure("TButton", background="#404249", foreground="white", borderwidth=0, focuscolor="none",
                             font=("Segoe UI", 9))
        self.style.map("TButton", background=[("active", COLORS["accent"])])
        self.style.configure("Header.TLabel", font=("Segoe UI", 12, "bold"), foreground=COLORS["accent"])

    def setup_ui(self):
        # Панель слева
        control_frame = ttk.Frame(self.root, padding="15")
        control_frame.pack(side=tk.LEFT, fill=tk.Y)

        ttk.Label(control_frame, text="⚙️ Управление", style="Header.TLabel").pack(pady=(0, 15))

        # Координаты
        coord_frame = ttk.LabelFrame(control_frame, text="Координаты", padding="10")
        coord_frame.pack(fill="x", pady=5)
        # Вставим ваши значения по умолчанию (770, 8)
        self.create_coord_input(coord_frame, "Start (P1):", "770", "8", "x1", "y1")
        self.create_coord_input(coord_frame, "End (P2/R):", "790", "20", "x2", "y2")
        self.create_coord_input(coord_frame, "Control (P3):", "780", "30", "x3", "y3")

        # Кнопки
        algo_frame = ttk.LabelFrame(control_frame, text="Алгоритмы", padding="10")
        algo_frame.pack(fill="x", pady=10)

        btns = [
            ("Step-by-Step", "step"), ("DDA (ЦДА)", "dda"),
            ("Bresenham Line", "bres_line"), ("Bresenham Circle", "bres_circle"),
            ("Wu's Antialiasing", "wu"), ("Castle-Piteway (Curve)", "castle")
        ]
        for text, cmd in btns:
            ttk.Button(algo_frame, text=text, command=lambda c=cmd: self.run_algo(c)).pack(fill='x', pady=2)

        # Инфо и статус
        info_frame = ttk.Frame(control_frame)
        info_frame.pack(fill="x", pady=20)
        self.status_label = ttk.Label(info_frame, text="Готов", foreground="#888")
        self.status_label.pack(anchor="w")
        self.cursor_label = ttk.Label(info_frame, text="Курсор: (0, 0)", font=("Consolas", 9))
        self.cursor_label.pack(anchor="w", pady=(5, 0))

        # Подсказка по управлению
        help_text = "Управление:\n🖱️ ЛКМ (Drag): Двигать сетку\n🖱️ Колесо: Масштаб (Zoom)"
        ttk.Label(info_frame, text=help_text, font=("Segoe UI", 9, "italic"), foreground="#aaa").pack(anchor="w",
                                                                                                      pady=10)

        ttk.Button(control_frame, text="Найти центр (0,0)", command=self.reset_view).pack(side=tk.BOTTOM, fill='x',
                                                                                          pady=5)

        # Холст
        canvas_container = tk.Frame(self.root, bg=COLORS["bg"])
        canvas_container.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH)

        self.canvas = tk.Canvas(canvas_container, bg=COLORS["canvas_bg"], highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # === ПРИВЯЗКА СОБЫТИЙ МЫШИ ===
        self.canvas.bind("<ButtonPress-1>", self.on_drag_start)
        self.canvas.bind("<B1-Motion>", self.on_drag_move)
        self.canvas.bind("<Motion>", self.on_mouse_move)
        self.canvas.bind("<MouseWheel>", self.on_zoom)  # Windows/Mac
        self.canvas.bind("<Button-4>", self.on_zoom)  # Linux
        self.canvas.bind("<Button-5>", self.on_zoom)  # Linux

    def create_coord_input(self, parent, label_text, def_x, def_y, var_x_name, var_y_name):
        f = ttk.Frame(parent)
        f.pack(fill="x", pady=2)
        ttk.Label(f, text=label_text, width=12).pack(side=tk.LEFT)
        entry_x = ttk.Entry(f, width=5, justify="center");
        entry_x.insert(0, def_x);
        entry_x.pack(side=tk.LEFT, padx=2)
        ttk.Label(f, text=",").pack(side=tk.LEFT)
        entry_y = ttk.Entry(f, width=5, justify="center");
        entry_y.insert(0, def_y);
        entry_y.pack(side=tk.LEFT, padx=2)
        setattr(self, f"entry_{var_x_name}", entry_x)
        setattr(self, f"entry_{var_y_name}", entry_y)

    # --- Математика координат ---
    def get_center(self):
        return self.canvas.winfo_width() // 2, self.canvas.winfo_height() // 2

    def logical_to_screen(self, lx, ly):
        cx, cy = self.get_center()
        sx = cx + self.offset_x + (lx * self.cell_size)
        sy = cy + self.offset_y - (ly * self.cell_size)
        return sx, sy

    def screen_to_logical(self, sx, sy):
        cx, cy = self.get_center()
        lx = (sx - cx - self.offset_x) / self.cell_size
        ly = (cy + self.offset_y - sy) / self.cell_size
        return round(lx), round(ly)

    # --- Обработчики мыши ---
    def on_drag_start(self, event):
        self.drag_start_x = event.x
        self.drag_start_y = event.y

    def on_drag_move(self, event):
        # Двигаем камеру
        dx = event.x - self.drag_start_x
        dy = event.y - self.drag_start_y
        self.offset_x += dx
        self.offset_y += dy
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        self.redraw_all()

    def on_zoom(self, event):
        if event.num == 5 or event.delta < 0:
            scale = 0.9
        else:
            scale = 1.1

        new_size = self.cell_size * scale
        if 2 < new_size < 200:
            self.cell_size = new_size
            self.redraw_all()

    def on_mouse_move(self, event):
        lx, ly = self.screen_to_logical(event.x, event.y)
        self.cursor_label.config(text=f"Курсор: ({lx}, {ly})")

        # Подсветка клетки
        self.canvas.delete("highlight")
        sx, sy = self.logical_to_screen(lx, ly)
        hs = self.cell_size
        self.canvas.create_rectangle(sx - hs / 2, sy - hs / 2, sx + hs / 2, sy + hs / 2, outline="#666",
                                     tags="highlight")

    # --- Отрисовка ---
    def redraw_all(self):
        self.canvas.delete("all")
        self.draw_infinite_grid()
        self.draw_points()

    def draw_infinite_grid(self):
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if w < 10: return

        cx, cy = w // 2, h // 2
        grid_cx = cx + self.offset_x
        grid_cy = cy + self.offset_y

        # Рисуем вертикальные
        start_col = math.floor((0 - grid_cx) / self.cell_size)
        end_col = math.ceil((w - grid_cx) / self.cell_size)

        for i in range(start_col, end_col + 1):
            x = grid_cx + i * self.cell_size
            color = COLORS["axis_line"] if i == 0 else (
                COLORS["grid_line_major"] if i % 10 == 0 else COLORS["grid_line"])
            width = 2 if i == 0 else 1
            self.canvas.create_line(x, 0, x, h, fill=color, width=width)

        # Рисуем горизонтальные
        start_row = math.floor((grid_cy - h) / self.cell_size)
        end_row = math.ceil(grid_cy / self.cell_size)

        for i in range(start_row, end_row + 1):
            y = grid_cy - i * self.cell_size
            color = COLORS["axis_line"] if i == 0 else (
                COLORS["grid_line_major"] if i % 10 == 0 else COLORS["grid_line"])
            width = 2 if i == 0 else 1
            self.canvas.create_line(0, y, w, y, fill=color, width=width)

        # Буквы осей
        self.canvas.create_text(grid_cx + 15, 15, text="Y", fill="white", font=("Arial", 10, "bold"))
        self.canvas.create_text(w - 15, grid_cy - 15, text="X", fill="white", font=("Arial", 10, "bold"))

    def draw_points(self):
        pad = 1 if self.cell_size > 5 else 0
        for p in self.last_points:
            sx, sy = self.logical_to_screen(p[0], p[1])

            # Простая обработка цвета
            color = self.last_color
            if len(p) == 3 and p[2] < 1.0:  # Если есть альфа (Ву)
                # Затемняем цвет (хак для имитации прозрачности на темном фоне)
                intensity = p[2]
                if self.last_color == COLORS["pixel_wu"]:  # Cyan #00ffff
                    # Уменьшаем G и B, R остается 0
                    val = int(255 * intensity)
                    color = f"#00{val:02x}{val:02x}"
                else:  # Default Green #00ff00
                    val = int(255 * intensity)
                    color = f"#00{val:02x}00"

            self.canvas.create_rectangle(
                sx - self.cell_size / 2 + pad, sy - self.cell_size / 2 + pad,
                sx + self.cell_size / 2 - pad, sy + self.cell_size / 2 - pad,
                fill=color, outline=""
            )

    def reset_view(self):
        self.offset_x = 0
        self.offset_y = 0
        self.cell_size = 20
        self.redraw_all()

    def focus_on_point(self, x, y):
        # Автоматически сдвигаем камеру, чтобы точка (x,y) была в центре
        self.offset_x = -(x * self.cell_size)
        self.offset_y = (y * self.cell_size)
        self.redraw_all()

    def run_algo(self, algo_type):
        try:
            x1, y1 = int(self.entry_x1.get()), int(self.entry_y1.get())
            x2, y2 = int(self.entry_x2.get()), int(self.entry_y2.get())
            x3, y3 = int(self.entry_x3.get()), int(self.entry_y3.get())

            # АВТО-ФОКУС: Переместить камеру к начальной точке,
            # так как 770 очень далеко
            self.focus_on_point(x1, y1)

            if algo_type == "wu":
                self.last_color = COLORS["pixel_wu"]
            elif algo_type == "castle":
                self.last_color = COLORS["pixel_curve"]
            else:
                self.last_color = COLORS["pixel_default"]

            start = time.perf_counter()

            if algo_type == "step":
                pts = self.algo_step(x1, y1, x2, y2)
            elif algo_type == "dda":
                pts = self.algo_dda(x1, y1, x2, y2)
            elif algo_type == "bres_line":
                pts = self.algo_bresenham_line(x1, y1, x2, y2)
            elif algo_type == "bres_circle":
                pts = self.algo_bresenham_circle(x1, y1, abs(x2))
            elif algo_type == "wu":
                pts = self.algo_wu(x1, y1, x2, y2)
            elif algo_type == "castle":
                pts = self.algo_castle_pitway(x1, y1, x3, y3, x2, y2)
            else:
                pts = []

            dt = (time.perf_counter() - start) * 1000
            self.status_label.config(text=f"Выполнено: {algo_type} ({dt:.4f} мс)")
            self.last_points = pts
            self.redraw_all()

        except ValueError:
            messagebox.showerror("Ошибка", "Введите числа")

    # --- АЛГОРИТМЫ (Без изменений) ---
    def algo_step(self, x1, y1, x2, y2):
        pts = []
        if x1 == x2 and y1 == y2: return [(x1, y1)]
        dx, dy = x2 - x1, y2 - y1
        if abs(dx) >= abs(dy):
            k = dy / dx if dx != 0 else 0;
            b = y1 - k * x1;
            step = 1 if x2 > x1 else -1
            for x in range(x1, x2 + step, step): pts.append((x, round(k * x + b)))
        else:
            k = dx / dy if dy != 0 else 0;
            b = x1 - k * y1;
            step = 1 if y2 > y1 else -1
            for y in range(y1, y2 + step, step): pts.append((round(k * y + b), y))
        return pts

    def algo_dda(self, x1, y1, x2, y2):
        pts = [];
        dx, dy = x2 - x1, y2 - y1;
        steps = max(abs(dx), abs(dy))
        if steps == 0: return [(x1, y1)]
        x_inc, y_inc = dx / steps, dy / steps;
        x, y = x1, y1
        for _ in range(int(steps) + 1): pts.append((round(x), round(y))); x += x_inc; y += y_inc
        return pts

    def algo_bresenham_line(self, x1, y1, x2, y2):
        pts = [];
        dx, dy = abs(x2 - x1), abs(y2 - y1);
        sx = 1 if x1 < x2 else -1;
        sy = 1 if y1 < y2 else -1;
        err = dx - dy
        while True:
            pts.append((x1, y1))
            if x1 == x2 and y1 == y2: break
            e2 = 2 * err
            if e2 > -dy: err -= dy; x1 += sx
            if e2 < dx: err += dx; y1 += sy
        return pts

    def algo_bresenham_circle(self, xc, yc, r):
        pts = [];
        x, y, d = 0, r, 3 - 2 * r

        def add(x, y):
            return [(xc + x, yc + y), (xc - x, yc + y), (xc + x, yc - y), (xc - x, yc - y), (xc + y, yc + x),
                    (xc - y, yc + x), (xc + y, yc - x), (xc - y, yc - x)]

        while y >= x:
            pts.extend(add(x, y));
            x += 1
            if d > 0:
                y -= 1; d += 4 * (x - y) + 10
            else:
                d += 4 * x + 6
        return pts

    def algo_wu(self, x1, y1, x2, y2):
        pts = []

        def fpart(x):
            return x - int(x)

        def rfpart(x):
            return 1 - fpart(x)

        steep = abs(y2 - y1) > abs(x2 - x1)
        if steep: x1, y1 = y1, x1; x2, y2 = y2, x2
        if x1 > x2: x1, x2 = x2, x1; y1, y2 = y2, y1
        dx, dy = x2 - x1, y2 - y1
        gradient = dy / dx if dx != 0 else 1.0
        xend = round(x1);
        yend = y1 + gradient * (xend - x1);
        xgap = rfpart(x1 + 0.5);
        xpxl1, ypxl1 = xend, int(yend)
        if steep:
            pts.extend([(ypxl1, xpxl1, rfpart(yend) * xgap), (ypxl1 + 1, xpxl1, fpart(yend) * xgap)])
        else:
            pts.extend([(xpxl1, ypxl1, rfpart(yend) * xgap), (xpxl1, ypxl1 + 1, fpart(yend) * xgap)])
        intery = yend + gradient
        xend = round(x2);
        yend = y2 + gradient * (xend - x2);
        xgap = fpart(x2 + 0.5);
        xpxl2, ypxl2 = xend, int(yend)
        if steep:
            pts.extend([(ypxl2, xpxl2, rfpart(yend) * xgap), (ypxl2 + 1, xpxl2, fpart(yend) * xgap)])
        else:
            pts.extend([(xpxl2, ypxl2, rfpart(yend) * xgap), (xpxl2, ypxl2 + 1, fpart(yend) * xgap)])
        for x in range(xpxl1 + 1, xpxl2):
            if steep:
                pts.extend([(int(intery), x, rfpart(intery)), (int(intery) + 1, x, fpart(intery))])
            else:
                pts.extend([(x, int(intery), rfpart(intery)), (x, int(intery) + 1, fpart(intery))])
            intery += gradient
        return pts

    def algo_castle_pitway(self, x1, y1, xc, yc, x2, y2):
        pts = set();
        step = 0.005;
        t = 0.0
        while t <= 1.0:
            xa = x1 + (xc - x1) * t;
            ya = y1 + (yc - y1) * t
            xb = xc + (x2 - xc) * t;
            yb = yc + (y2 - yc) * t
            x = xa + (xb - xa) * t;
            y = ya + (yb - ya) * t
            pts.add((round(x), round(y)))
            t += step
        return list(pts)


if __name__ == "__main__":
    root = tk.Tk()
    app = RasterizationApp(root)
    root.mainloop()
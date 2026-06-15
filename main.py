import sqlite3, tkinter as tk, tkinter.ttk as ttk, tkinter.filedialog, tkinter.messagebox
from PIL import Image, ImageTk, ImageDraw
import os, shutil, csv

DATA_DIR = os.path.join("Задание 1", "Прил_2_ОЗ_КОД 09.02.07-2-2026-М1", "import")
DB = "bike.db"

# Создаём папку для данных, если её нет
os.makedirs(DATA_DIR, exist_ok=True)

# --- Создание заглушки для фото ---
DEFAULT_PICTURE = os.path.join(DATA_DIR, "picture.png")
if not os.path.exists(DEFAULT_PICTURE):
    img = Image.new("RGB", (300, 200), color="lightgray")
    draw = ImageDraw.Draw(img)
    draw.text((100, 90), "Нет фото", fill="black")
    img.save(DEFAULT_PICTURE)
    print("Создана заглушка picture.png")

# ------------------------------------------------------------
# ИНИЦИАЛИЗАЦИЯ БД С ПРИНУДИТЕЛЬНЫМ ПЕРЕСОЗДАНИЕМ И ПОДРОБНЫМ ЛОГОМ
# ------------------------------------------------------------
def init_db():
    # Удаляем старую БД (чтобы всегда загружать свежие данные из CSV)
    if os.path.exists(DB):
        os.remove(DB)
        print("Старая база данных удалена.")
    
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.executescript('''
        PRAGMA foreign_keys=ON;
        CREATE TABLE users (id INTEGER PRIMARY KEY, login TEXT UNIQUE, password TEXT, full_name TEXT, role_id INTEGER);
        CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT, price REAL, category TEXT, brand TEXT, image_path TEXT, stock INTEGER, discount REAL);
        CREATE TABLE pickup_points (id INTEGER PRIMARY KEY, address TEXT, work_hours TEXT, phone TEXT);
        CREATE TABLE orders (id INTEGER PRIMARY KEY, user_id INTEGER, pickup_point_id INTEGER, order_date TEXT, status TEXT, total_amount REAL,
            FOREIGN KEY(user_id) REFERENCES users(id), FOREIGN KEY(pickup_point_id) REFERENCES pickup_points(id));
        CREATE TABLE order_items (id INTEGER PRIMARY KEY, order_id INTEGER, product_id INTEGER, quantity INTEGER, unit_price REAL,
            FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE, FOREIGN KEY(product_id) REFERENCES products(id));
    ''')
    print("Таблицы созданы.")

    # ----- 1. Пункты выдачи -----
    pickup_map = {}
    pickup_csv = os.path.join(DATA_DIR, "Пункты выдачи_import.csv")
    if os.path.exists(pickup_csv):
        with open(pickup_csv, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            cnt = 0
            for idx, row in enumerate(reader, start=1):
                if row and row[0].strip():
                    addr = row[0].strip()
                    c.execute("INSERT INTO pickup_points (address) VALUES (?)", (addr,))
                    pickup_map[idx] = c.lastrowid
                    cnt += 1
            print(f"Загружено пунктов выдачи: {cnt}")
    else:
        print(f"Файл не найден: {pickup_csv}")
        c.execute("INSERT INTO pickup_points (address) VALUES ('ул. Ленина, д.10')")
        pickup_map[1] = 1

    # ----- 2. Пользователи -----
    role_map = {"Администратор": 4, "Менеджер": 3, "Авторизированный клиент": 2}
    users_csv = os.path.join(DATA_DIR, "user_import.csv")
    if os.path.exists(users_csv):
        with open(users_csv, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f, delimiter=";")
            cnt = 0
            for row in reader:
                role = row.get("Роль сотрудника", "").strip()
                rid = role_map.get(role, 2)
                login = row.get("Логин", "").strip()
                pwd = row.get("Пароль", "").strip()
                fio = row.get("ФИО", "").strip()
                if login and pwd:
                    c.execute("INSERT INTO users (login, password, full_name, role_id) VALUES (?,?,?,?)", (login, pwd, fio, rid))
                    cnt += 1
            print(f"Загружено пользователей: {cnt}")
    else:
        print(f"Файл не найден: {users_csv}")
        # Тестовые пользователи
        c.execute("INSERT INTO users (login, password, full_name, role_id) VALUES ('client','c','Клиент',2)")
        c.execute("INSERT INTO users (login, password, full_name, role_id) VALUES ('manager','m','Менеджер',3)")
        c.execute("INSERT INTO users (login, password, full_name, role_id) VALUES ('admin','a','Админ',4)")

    # ----- 3. Товары -----
    prod_by_article = {}
    tovar_csv = os.path.join(DATA_DIR, "Tovar.csv")
    if os.path.exists(tovar_csv):
        with open(tovar_csv, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f, delimiter=";")
            cnt = 0
            for row in reader:
                art = row.get("Артикул", "").strip()
                name = row.get("Наименование товара", "").strip()
                if not art or not name:
                    continue
                try:
                    price = float(row.get("Цена", "0").replace(",", "."))
                except:
                    price = 0.0
                cat = row.get("Категория товара", "").strip()
                brand = row.get("Производитель", "").strip()
                try:
                    disc = float(row.get("Действующая скидка", "0").replace(",", "."))
                except:
                    disc = 0.0
                try:
                    stock = int(row.get("Кол-во на складе", "0"))
                except:
                    stock = 0
                photo = row.get("Фото", "").strip()
                img_path = os.path.join(DATA_DIR, photo) if photo else None
                if img_path and not os.path.exists(img_path):
                    img_path = None
                c.execute("INSERT INTO products (name, price, category, brand, image_path, stock, discount) VALUES (?,?,?,?,?,?,?)",
                          (name, price, cat, brand, img_path, stock, disc))
                prod_by_article[art] = c.lastrowid
                cnt += 1
            print(f"Загружено товаров: {cnt}")
    else:
        print(f"Файл не найден: {tovar_csv}")
        # Тестовые товары
        for i, (name, price, cat, brand, stock, disc) in enumerate([
            ('Горный велосипед', 25000, 'Горный', 'Author', 10, 5),
            ('Городской велосипед', 18000, 'Городской', 'Stels', 5, 20),
            ('Детский велосипед', 12000, 'Детский', 'Forward', 0, 10)
        ], start=1):
            img_path = os.path.join(DATA_DIR, f"{i}.jpg") if os.path.exists(os.path.join(DATA_DIR, f"{i}.jpg")) else None
            c.execute("INSERT INTO products (name, price, category, brand, image_path, stock, discount) VALUES (?,?,?,?,?,?,?)",
                      (name, price, cat, brand, img_path, stock, disc))

    # ----- 4. Заказы -----
    c.execute("SELECT id, full_name FROM users")
    user_by_name = {row[1]: row[0] for row in c.fetchall()}

    orders_csv = os.path.join(DATA_DIR, "Заказ_import.csv")
    order_cnt = 0
    item_cnt = 0
    if os.path.exists(orders_csv):
        with open(orders_csv, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f, delimiter=";")
            for row in reader:
                if not row.get("Номер заказа", "").strip():
                    continue
                artikuls_raw = row.get("Артикул заказа", "").strip()
                if not artikuls_raw:
                    continue
                parts = [p.strip() for p in artikuls_raw.split(",")]
                items = []
                for i in range(0, len(parts), 2):
                    if i+1 < len(parts):
                        try:
                            qty = int(parts[i+1])
                            items.append((parts[i], qty))
                        except:
                            pass
                if not items:
                    continue
                # Дата заказа
                order_date = row.get("Дата заказа", "").strip()
                if order_date:
                    try:
                        d, m, y = order_date.split(".")
                        order_date = f"{y}-{m}-{d}"
                    except:
                        order_date = None
                status_raw = row.get("Статус заказа", "").strip().lower()
                status = "new" if status_raw == "новый" else "delivered" if status_raw == "завершен" else "new"
                pickup_num = row.get("Адрес пункта выдачи", "").strip()
                pickup_id = pickup_map.get(int(pickup_num)) if pickup_num.isdigit() else None
                client_name = row.get("ФИО авторизированного клиента", "").strip()
                user_id = user_by_name.get(client_name)
                if not user_id:
                    continue
                c.execute("INSERT INTO orders (user_id, pickup_point_id, order_date, status, total_amount) VALUES (?,?,?,?,0)",
                          (user_id, pickup_id, order_date, status))
                order_id = c.lastrowid
                order_cnt += 1
                for art, qty in items:
                    prod_id = prod_by_article.get(art)
                    if not prod_id:
                        continue
                    c.execute("SELECT price, discount FROM products WHERE id=?", (prod_id,))
                    prod = c.fetchone()
                    unit_price = prod[0] * (1 - prod[1]/100) if prod and prod[1] else (prod[0] if prod else 0)
                    c.execute("INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (?,?,?,?)",
                              (order_id, prod_id, qty, unit_price))
                    item_cnt += 1
            print(f"Загружено заказов: {order_cnt}")
            print(f"Загружено позиций заказов: {item_cnt}")
    else:
        print(f"Файл не найден: {orders_csv}")

    conn.commit()
    # Итоговая статистика
    print("\n=== ИТОГОВАЯ СТАТИСТИКА ===")
    print(f"Пользователей: {c.execute('SELECT COUNT(*) FROM users').fetchone()[0]}")
    print(f"Товаров: {c.execute('SELECT COUNT(*) FROM products').fetchone()[0]}")
    print(f"Пунктов выдачи: {c.execute('SELECT COUNT(*) FROM pickup_points').fetchone()[0]}")
    print(f"Заказов: {c.execute('SELECT COUNT(*) FROM orders').fetchone()[0]}")
    print(f"Позиций в заказах: {c.execute('SELECT COUNT(*) FROM order_items').fetchone()[0]}")
    print("==========================\n")
    conn.close()

# ------------------------------------------------------------
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ И КЛАСС App (без изменений)
# ------------------------------------------------------------
def get_conn():
    return sqlite3.connect(DB)

def load_image(path, size=(100,100)):
    try:
        img = Image.open(path)
        img.thumbnail(size, Image.LANCZOS)
        return ImageTk.PhotoImage(img)
    except:
        return None

def save_uploaded_image(file, old_path=None):
    if old_path and os.path.exists(old_path) and "picture.png" not in old_path:
        os.remove(old_path)
    dst = os.path.join(DATA_DIR, os.path.basename(file))
    shutil.copy(file, dst)
    img = Image.open(dst)
    img.thumbnail((300,200), Image.LANCZOS)
    img.save(dst)
    return dst

def find_icon():
    for name in ["icon.ico", "icon.jpg", "icon.png"]:
        path = os.path.join(DATA_DIR, name)
        if os.path.exists(path):
            return path
    return None

class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("ВелосипедDrive")
        icon = find_icon()
        if icon:
            if icon.endswith(".ico"):
                self.root.iconbitmap(icon)
            else:
                img = ImageTk.PhotoImage(file=icon)
                self.root.iconphoto(True, img)
        self.root.geometry("1100x700")
        self.user = None
        self.show_login()
        self.root.mainloop()

    def show_login(self):
        for w in self.root.winfo_children(): w.destroy()
        logo_path = os.path.join(DATA_DIR, "logo.png")
        if os.path.exists(logo_path):
            img = Image.open(logo_path)
            img.thumbnail((200,100), Image.LANCZOS)
            logo = ImageTk.PhotoImage(img)
            tk.Label(self.root, image=logo).pack(pady=10)
            self.root.logo = logo
        tk.Label(self.root, text="Логин").pack()
        self.ent_login = tk.Entry(self.root); self.ent_login.pack()
        tk.Label(self.root, text="Пароль").pack()
        self.ent_pass = tk.Entry(self.root, show="*"); self.ent_pass.pack()
        tk.Button(self.root, text="Войти", command=self.do_login, bg="#6A5ACD", fg="white").pack(pady=5)
        tk.Button(self.root, text="Гость", command=lambda: self.start_app(None, "guest"), bg="#4B0082", fg="white").pack()

    def do_login(self):
        conn = get_conn(); c = conn.cursor()
        c.execute("SELECT * FROM users WHERE login=? AND password=?", (self.ent_login.get(), self.ent_pass.get()))
        user = c.fetchone()
        conn.close()
        if user:
            role_map = {2:'client', 3:'manager', 4:'admin'}
            self.start_app(user, role_map[user[4]])
        else:
            tk.messagebox.showerror("Ошибка", "Неверный логин/пароль")

    def start_app(self, user, role):
        self.user = user
        self.role = role
        for w in self.root.winfo_children(): w.destroy()
        top = tk.Frame(self.root, bg="#6A5ACD", height=50); top.pack(fill=tk.X)
        name = user[3] if user else "Гость"
        tk.Label(top, text=f"{name} ({role})", bg="#6A5ACD", fg="white").pack(side=tk.RIGHT, padx=10)
        tk.Button(top, text="Выйти", command=self.show_login, bg="#4B0082", fg="white").pack(side=tk.LEFT, padx=10)
        if role in ('manager','admin'):
            tk.Button(top, text="Заказы", command=self.show_orders, bg="#4B0082", fg="white").pack(side=tk.LEFT, padx=10)
        self.content = tk.Frame(self.root, bg="white")
        self.content.pack(fill=tk.BOTH, expand=True)
        self.show_products()

    def show_products(self):
        for w in self.content.winfo_children(): w.destroy()
        filter_frame = tk.Frame(self.content, bg="white")
        filter_frame.pack(fill=tk.X, pady=5)
        self.search_var = tk.StringVar()
        self.discount_filter = tk.StringVar(value="Все")
        self.sort_var = tk.StringVar(value="id")
        self.sort_order = tk.StringVar(value="ASC")
        if self.role in ('manager','admin'):
            tk.Label(filter_frame, text="Поиск:", bg="white").pack(side=tk.LEFT, padx=5)
            tk.Entry(filter_frame, textvariable=self.search_var).pack(side=tk.LEFT, padx=5)
            tk.Label(filter_frame, text="Скидка:", bg="white").pack(side=tk.LEFT, padx=5)
            cb = ttk.Combobox(filter_frame, textvariable=self.discount_filter, values=["Все","0-11.99","12-18.99","19+"], width=10)
            cb.pack(side=tk.LEFT, padx=5)
            tk.Label(filter_frame, text="Сортировка:", bg="white").pack(side=tk.LEFT, padx=5)
            ttk.Combobox(filter_frame, textvariable=self.sort_var, values=["price","stock","discount","id"], width=8).pack(side=tk.LEFT)
            tk.Button(filter_frame, text="▲", command=lambda: self.set_sort_order("ASC"), width=2).pack(side=tk.LEFT)
            tk.Button(filter_frame, text="▼", command=lambda: self.set_sort_order("DESC"), width=2).pack(side=tk.LEFT)
            tk.Button(filter_frame, text="Добавить товар", command=self.add_edit_product, bg="#4B0082", fg="white").pack(side=tk.RIGHT, padx=10)
        columns = ("id","Фото","Название","Категория","Производитель","Цена","Скидка","Остаток","Итоговая цена")
        self.tree = ttk.Treeview(self.content, columns=columns, show="headings", height=20)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100 if col!="Фото" else 120)
        self.tree.pack(fill=tk.BOTH, expand=True)
        if self.role == 'admin':
            self.tree.bind("<Double-1>", lambda e: self.add_edit_product(self.get_selected_product_id()))
        self.search_var.trace('w', lambda *a: self.refresh_products())
        self.discount_filter.trace('w', lambda *a: self.refresh_products())
        self.sort_var.trace('w', lambda *a: self.refresh_products())
        self.refresh_products()

    def set_sort_order(self, order):
        self.sort_order.set(order)
        self.refresh_products()

    def get_selected_product_id(self):
        sel = self.tree.selection()
        if sel: return int(self.tree.item(sel[0])['values'][0])
        return None

    def refresh_products(self):
        for row in self.tree.get_children(): self.tree.delete(row)
        conn = get_conn(); c = conn.cursor()
        sql = "SELECT * FROM products WHERE 1=1"
        params = []
        search = self.search_var.get().strip()
        if search:
            sql += " AND (name LIKE ? OR category LIKE ? OR brand LIKE ?)"
            like = f"%{search}%"
            params.extend([like, like, like])
        df = self.discount_filter.get()
        if df == "0-11.99": sql += " AND discount BETWEEN 0 AND 11.99"
        elif df == "12-18.99": sql += " AND discount BETWEEN 12 AND 18.99"
        elif df == "19+": sql += " AND discount >= 19"
        sort_col = self.sort_var.get()
        if sort_col in ('price','stock','discount','id'):
            sql += f" ORDER BY {sort_col} {self.sort_order.get()}"
        else:
            sql += " ORDER BY id"
        c.execute(sql, params)
        products = c.fetchall()
        conn.close()
        for p in products:
            final_price = p[2] * (1 - p[7]/100) if p[7] else p[2]
            bg = "white"
            if p[6] <= 0: bg = "lightgray"
            elif p[7] > 15: bg = "#483D8B"
            img_path = p[5] if p[5] and os.path.exists(p[5]) else DEFAULT_PICTURE
            img = load_image(img_path, (80,80))
            item_id = self.tree.insert("", tk.END, values=(p[0], "", p[1], p[3], p[4],
                f"{p[2]:.2f}", f"{p[7]}%", p[6], f"{final_price:.2f}"), tags=(bg,))
            if img:
                self.tree.set(item_id, "Фото", img)
                self.tree.photo_img = img
            self.tree.tag_configure(bg, background=bg)

    def add_edit_product(self, product_id=None):
        win = tk.Toplevel(self.root)
        win.title("Редактировать товар" if product_id else "Новый товар")
        win.grab_set()
        data = {}
        if product_id:
            conn = get_conn(); c = conn.cursor()
            c.execute("SELECT * FROM products WHERE id=?", (product_id,))
            data = c.fetchone()
            conn.close()
        fields = ['name','price','category','brand','stock','discount']
        entries = {}
        for i, f in enumerate(fields):
            tk.Label(win, text=f).grid(row=i, column=0)
            e = tk.Entry(win)
            e.grid(row=i, column=1)
            if data:
                val = data[fields.index(f)+1] if f!='price' else data[2]
                e.insert(0, str(val))
            entries[f] = e
        row = len(fields)
        tk.Label(win, text="Изображение").grid(row=row, column=0)
        img_label = tk.Label(win, text="Не выбрано")
        img_label.grid(row=row, column=1)
        img_path = data[5] if data else None
        def choose_img():
            nonlocal img_path
            f = tk.filedialog.askopenfilename(filetypes=[("Image","*.jpg *.png")])
            if f:
                img_path = save_uploaded_image(f, img_path)
                img_label.config(text=os.path.basename(img_path))
        tk.Button(win, text="Выбрать фото", command=choose_img).grid(row=row, column=2)
        def save():
            try:
                name = entries['name'].get().strip()
                price = float(entries['price'].get())
                category = entries['category'].get().strip()
                brand = entries['brand'].get().strip()
                stock = int(entries['stock'].get())
                discount = float(entries['discount'].get())
            except:
                tk.messagebox.showerror("Ошибка","Проверьте цену, остаток и скидку")
                return
            conn = get_conn(); c = conn.cursor()
            if product_id:
                c.execute("UPDATE products SET name=?, price=?, category=?, brand=?, image_path=?, stock=?, discount=? WHERE id=?",
                          (name, price, category, brand, img_path, stock, discount, product_id))
            else:
                c.execute("INSERT INTO products (name,price,category,brand,image_path,stock,discount) VALUES (?,?,?,?,?,?,?)",
                          (name, price, category, brand, img_path, stock, discount))
            conn.commit(); conn.close()
            win.destroy()
            self.refresh_products()
        tk.Button(win, text="Сохранить", command=save, bg="#4B0082", fg="white").grid(row=row+1, columnspan=2, pady=10)
        if product_id and self.role=='admin':
            def delete():
                if tk.messagebox.askyesno("Удалить","Удалить товар?"):
                    try:
                        conn = get_conn(); c = conn.cursor()
                        c.execute("DELETE FROM products WHERE id=?", (product_id,))
                        conn.commit(); conn.close()
                        win.destroy()
                        self.refresh_products()
                    except:
                        tk.messagebox.showerror("Ошибка","Товар в заказах, нельзя удалить")
            tk.Button(win, text="Удалить", command=delete, bg="red", fg="white").grid(row=row+2, columnspan=2)

    def show_orders(self):
        for w in self.content.winfo_children(): w.destroy()
        columns = ("ID","Клиент","Пункт выдачи","Дата","Статус","Сумма")
        self.orders_tree = ttk.Treeview(self.content, columns=columns, show="headings")
        for col in columns:
            self.orders_tree.heading(col, text=col)
            self.orders_tree.column(col, width=120)
        self.orders_tree.pack(fill=tk.BOTH, expand=True)
        if self.role == 'admin':
            tk.Button(self.content, text="Добавить заказ", command=lambda: self.add_edit_order(), bg="#4B0082", fg="white").pack(pady=5)
            self.orders_tree.bind("<Double-1>", lambda e: self.add_edit_order(self.get_selected_order_id()))
        self.refresh_orders()

    def get_selected_order_id(self):
        sel = self.orders_tree.selection()
        if sel: return int(self.orders_tree.item(sel[0])['values'][0])
        return None

    def refresh_orders(self):
        for row in self.orders_tree.get_children(): self.orders_tree.delete(row)
        conn = get_conn(); c = conn.cursor()
        c.execute("SELECT o.id, u.full_name, p.address, o.order_date, o.status, o.total_amount FROM orders o LEFT JOIN users u ON o.user_id=u.id LEFT JOIN pickup_points p ON o.pickup_point_id=p.id")
        for row in c.fetchall():
            self.orders_tree.insert("", tk.END, values=row)
        conn.close()

    def add_edit_order(self, order_id=None):
        win = tk.Toplevel(self.root)
        win.title("Редактировать заказ" if order_id else "Новый заказ")
        win.grab_set()
        data = {}
        if order_id:
            conn = get_conn(); c = conn.cursor()
            c.execute("SELECT * FROM orders WHERE id=?", (order_id,))
            data = c.fetchone()
            conn.close()
        tk.Label(win, text="ID пользователя").grid(row=0,column=0)
        e_user = tk.Entry(win); e_user.grid(row=0,column=1)
        tk.Label(win, text="ID пункта выдачи").grid(row=1,column=0)
        e_pickup = tk.Entry(win); e_pickup.grid(row=1,column=1)
        tk.Label(win, text="Дата (ГГГГ-ММ-ДД)").grid(row=2,column=0)
        e_date = tk.Entry(win); e_date.grid(row=2,column=1)
        tk.Label(win, text="Статус").grid(row=3,column=0)
        e_status = ttk.Combobox(win, values=['new','processing','shipped','delivered','cancelled'])
        e_status.grid(row=3,column=1)
        if data:
            e_user.insert(0, data[1])
            e_pickup.insert(0, data[2] if data[2] else '')
            e_date.insert(0, data[3])
            e_status.set(data[4])
        def save():
            try:
                uid = int(e_user.get())
                pid = int(e_pickup.get()) if e_pickup.get().strip() else None
                date = e_date.get()
                status = e_status.get()
                conn = get_conn(); c = conn.cursor()
                if order_id:
                    c.execute("UPDATE orders SET user_id=?, pickup_point_id=?, order_date=?, status=? WHERE id=?", (uid, pid, date, status, order_id))
                else:
                    c.execute("INSERT INTO orders (user_id, pickup_point_id, order_date, status, total_amount) VALUES (?,?,?,?,0)", (uid, pid, date, status))
                conn.commit(); conn.close()
                win.destroy()
                self.refresh_orders()
            except:
                tk.messagebox.showerror("Ошибка","Проверьте данные")
        tk.Button(win, text="Сохранить", command=save, bg="#4B0082", fg="white").pack(pady=10)
        if order_id and self.role=='admin':
            def delete():
                if tk.messagebox.askyesno("Удалить","Удалить заказ?"):
                    conn = get_conn(); c = conn.cursor()
                    c.execute("DELETE FROM orders WHERE id=?", (order_id,))
                    conn.commit(); conn.close()
                    win.destroy()
                    self.refresh_orders()
            tk.Button(win, text="Удалить", command=delete, bg="red", fg="white").pack()

if __name__ == "__main__":
    init_db()
    App()
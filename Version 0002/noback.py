#!/usr/bin/env python3
"""
NoBack v4 - Interface clara com botões centralizados e instalação automática (venv)
Salve como noback_v4.py e execute.

Dependências (instaladas automaticamente no venv):
  rembg, pillow, onnxruntime, tkinterdnd2
"""
import os
import sys
import subprocess
from pathlib import Path
import threading

# ---------------------------
# Virtualenv / instalação automática
# ---------------------------
VENV_DIR = os.path.expanduser("~/.noback_venv")
PYTHON_BIN = os.path.join(VENV_DIR, "bin", "python3")

def ensure_venv():
    if not os.path.exists(PYTHON_BIN):
        print("🔧 Criando ambiente isolado...")
        subprocess.check_call([sys.executable, "-m", "venv", VENV_DIR])
    print("📦 Instalando/atualizando dependências no venv...")
    subprocess.check_call([PYTHON_BIN, "-m", "pip", "install", "--upgrade", "pip"])
    subprocess.check_call([
        PYTHON_BIN, "-m", "pip", "install",
        "rembg", "pillow", "onnxruntime", "tkinterdnd2"
    ])

def restart_in_venv():
    if sys.executable != PYTHON_BIN:
        print("🔄 Reiniciando dentro do venv...")
        os.execv(PYTHON_BIN, [PYTHON_BIN] + sys.argv)

# Executa etapa de venv -> reinicia no venv automaticamente.
ensure_venv()
restart_in_venv()

# ---------------------------
# Imports (agora já dentro do venv)
# ---------------------------
from rembg import remove
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinterdnd2 import TkinterDnD, DND_FILES

SUPPORTED_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"}

# ---------------------------
# Processamento de imagem
# ---------------------------
def process_image(in_path: Path, out_dir: Path) -> Path:
    """Remove fundo e recorta até o limite da informação (bbox dos pixels não transparentes)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    with Image.open(in_path).convert("RGBA") as im:
        out = remove(im)
        bbox = out.getbbox()
        if bbox:
            out = out.crop(bbox)
        base = in_path.stem
        out_path = out_dir / f"{base}_nobg.png"
        out.save(out_path, format="PNG")
        return out_path

def iter_images_in_dir(folder: Path):
    for p in folder.rglob("*"):
        if p.suffix.lower() in SUPPORTED_EXTS:
            yield p

# ---------------------------
# Utilitários de desenho (rounded rect)
# ---------------------------
def create_rounded_rect(canvas, x1, y1, x2, y2, r, **kwargs):
    """Desenha um retângulo com cantos arredondados no Canvas."""
    canvas.create_rectangle(x1+r, y1, x2-r, y2, **kwargs)
    canvas.create_rectangle(x1, y1+r, x2, y2-r, **kwargs)
    canvas.create_arc(x2-2*r, y1, x2, y1+2*r, start=0, extent=90, style='pieslice', **kwargs)
    canvas.create_arc(x1, y1, x1+2*r, y1+2*r, start=90, extent=90, style='pieslice', **kwargs)
    canvas.create_arc(x1, y2-2*r, x1+2*r, y2, start=180, extent=90, style='pieslice', **kwargs)
    canvas.create_arc(x2-2*r, y2-2*r, x2, y2, start=270, extent=90, style='pieslice', **kwargs)

def create_rounded_rect_outline(canvas, x1, y1, x2, y2, r, dash=None, width=1, outline="#666"):
    """Desenha contorno arredondado (pontilhado opcional)."""
    canvas.create_arc(x2-2*r, y1, x2, y1+2*r, start=0, extent=90, style='arc', outline=outline, width=width, dash=dash)
    canvas.create_arc(x1, y1, x1+2*r, y1+2*r, start=90, extent=90, style='arc', outline=outline, width=width, dash=dash)
    canvas.create_arc(x1, y2-2*r, x1+2*r, y2, start=180, extent=90, style='arc', outline=outline, width=width, dash=dash)
    canvas.create_arc(x2-2*r, y2-2*r, x2, y2, start=270, extent=90, style='arc', outline=outline, width=width, dash=dash)
    canvas.create_line(x1+r, y1, x2-r, y1, fill=outline, width=width, dash=dash)
    canvas.create_line(x1+r, y2, x2-r, y2, fill=outline, width=width, dash=dash)
    canvas.create_line(x1, y1+r, x1, y2-r, fill=outline, width=width, dash=dash)
    canvas.create_line(x2, y1+r, x2, y2-r, fill=outline, width=width, dash=dash)

# ---------------------------
# UI principal
# ---------------------------
class NoBackApp(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        self.title("NoBack - Remoção de Fundo")
        self.geometry("820x760")
        self.minsize(760, 640)
        self.configure(bg="#e9e9e9")
        self.input_paths = []
        self.output_dir = Path.home() / "Downloads"
        self.logo_img = None
        self.flag_img = None
        self._build_ui()

        try:
            self.drop_target_register(DND_FILES)
            self.dnd_bind("<<Drop>>", self.on_drop)
        except Exception:
            pass

    def _build_ui(self):
        pad_x = 28
        # topo
        top_frame = tk.Frame(self, bg="#e9e9e9")
        top_frame.pack(fill="x", padx=pad_x, pady=(18,6))

        title = tk.Label(
            top_frame,
            text="NoBack - Remoção de Fundo",
            font=("Arial", 20, "bold"),
            bg="#e9e9e9",
            fg="#111"
        )
        title.pack(pady=10)

        # Dropzone
        dz_frame = tk.Frame(self, bg="#e9e9e9")
        dz_frame.pack(fill="x", padx=pad_x, pady=(6,4))
        self.dz_width = 760
        self.dz_height = 260
        self.dz_canvas = tk.Canvas(
            dz_frame,
            width=self.dz_width,
            height=self.dz_height,
            bg="#d9d9d9",
            highlightthickness=0
        )
        self.dz_canvas.pack()
        x1, y1, x2, y2 = 12, 12, self.dz_width-12, self.dz_height-12
        radius = 18
        create_rounded_rect(self.dz_canvas, x1, y1, x2, y2, radius, fill="#d1d1d1", outline="")
        create_rounded_rect_outline(self.dz_canvas, x1, y1, x2, y2, radius, dash=(6,6), width=3, outline="#6d6d6d")
        self.dz_canvas.create_text(
            self.dz_width/2,
            self.dz_height/2 - 10,
            text="Arraste fotos ou pastas aqui\nou use os botões abaixo para selecionar",
            font=("Arial", 16, "bold"),
            fill="#222",
            justify="center"
        )

        # Botões centralizados
        btns_frame = tk.Frame(self, bg="#e9e9e9")
        btns_frame.pack(padx=pad_x, pady=(14,6))
        btns_frame.columnconfigure((0,1,2), weight=1)

        self._create_button(btns_frame, "UPLOAD", self.choose_files, "#66aaff", "white").grid(row=0, column=0, padx=12)
        self._create_button(btns_frame, "Selecionar Pasta", self.choose_folder, "#4b84a6", "white").grid(row=0, column=1, padx=12)
        self._create_button(btns_frame, "Selecionar Saída", self.choose_output, "#4b84a6", "white").grid(row=0, column=2, padx=12)

        # Saída
        out_frame = tk.Frame(self, bg="#e9e9e9")
        out_frame.pack(fill="x", padx=pad_x, pady=(6,6))
        tk.Label(out_frame, text="Selecionar saída", font=("Arial", 12, "bold"), bg="#e9e9e9", fg="#111").pack(anchor="w")
        path_display = tk.Entry(out_frame, font=("Arial", 11), bd=0, relief="solid")
        path_display.pack(fill="x", pady=(6,0))
        path_display.insert(0, str(self.output_dir))
        self.out_entry = path_display

        # Progresso
        prog_frame = tk.Frame(self, bg="#e9e9e9")
        prog_frame.pack(fill="x", padx=pad_x, pady=(18,6))
        tk.Label(prog_frame, text="Progresso da remoção", font=("Arial", 12, "bold"), bg="#e9e9e9", fg="#111").pack(anchor="w")
        self.pb_w = 760 - 24
        self.pb_h = 28
        self.pb_canvas = tk.Canvas(prog_frame, width=self.pb_w, height=self.pb_h, bg="#444444", highlightthickness=0)
        self.pb_canvas.pack(pady=(8,0))
        self.pb_canvas.create_rectangle(0, 0, self.pb_w, self.pb_h, fill="#444444", outline="")
        self.pb_bar = self.pb_canvas.create_rectangle(0, 0, 0, self.pb_h, fill="#d95c5c", outline="")
        self.pb_text = self.pb_canvas.create_text(self.pb_w/2, self.pb_h/2, text="0%", font=("Arial", 11, "bold"), fill="white")

        # Log
        log_frame = tk.Frame(self, bg="#e9e9e9")
        log_frame.pack(fill="both", expand=True, padx=pad_x, pady=(12,6))
        self.log_widget = tk.Text(log_frame, height=10, bg="#f6f6f6", fg="#111", font=("Arial", 11), bd=1, relief="solid")
        self.log_widget.pack(fill="both", expand=True)
        self.log_widget.configure(state="disabled")

        # Botão principal
        bottom_frame = tk.Frame(self, bg="#e9e9e9")
        bottom_frame.pack(fill="x", padx=pad_x, pady=(10,18))
        self._create_button(bottom_frame, "Remover Fundo", self.start_process, "#44ddaa", "white", width=220, height=60).pack(pady=6)

        # 🔧 Garante exibição imediata do botão
        self.update_idletasks()
        self.geometry(self.geometry())

    def _create_button(self, parent, text, command, bg="#66aaff", fg="white", width=160, height=48):
        c = tk.Canvas(parent, width=width, height=height, bg=self["bg"], highlightthickness=0)
        radius = int(height/2)
        create_rounded_rect(c, 2, 2, width-2, height-2, radius, fill=bg, outline="")
        c.create_text(width/2, height/2, text=text, font=("Arial", 11, "bold"), fill=fg)
        c.bind("<Button-1>", lambda e: command())
        c.bind("<Enter>", lambda e: c.config(cursor="hand2"))
        c.bind("<Leave>", lambda e: c.config(cursor=""))
        return c

    # Helpers
    def append_log(self, text: str):
        self.log_widget.configure(state="normal")
        self.log_widget.insert("end", text + "\n")
        self.log_widget.see("end")
        self.log_widget.configure(state="disabled")

    def set_progress(self, fraction: float):
        w = max(0, min(1, fraction)) * self.pb_w
        self.pb_canvas.coords(self.pb_bar, 0, 0, w, self.pb_h)
        pct = int(round(fraction * 100))
        self.pb_canvas.itemconfigure(self.pb_text, text=f"{pct}%")
        self.pb_canvas.update_idletasks()

    # Escolha
    def choose_files(self):
        files = filedialog.askopenfilenames(title="Escolha imagens",
            filetypes=[("Imagens", "*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff")])
        if files:
            self.input_paths = list(map(Path, files))
            self.append_log(f"{len(self.input_paths)} arquivo(s) selecionado(s).")

    def choose_folder(self):
        folder = filedialog.askdirectory(title="Escolha uma pasta com imagens")
        if folder:
            self.input_paths = list(iter_images_in_dir(Path(folder)))
            self.append_log(f"{len(self.input_paths)} arquivo(s) encontrados na pasta.")

    def choose_output(self):
        folder = filedialog.askdirectory(title="Escolha a pasta de saída")
        if folder:
            self.output_dir = Path(folder)
            self.out_entry.delete(0, 'end')
            self.out_entry.insert(0, str(self.output_dir))
            self.append_log(f"Pasta de saída: {self.output_dir}")

    def on_drop(self, event):
        try:
            paths = self.tk.splitlist(event.data)
        except Exception:
            paths = [event.data]
        all_files = []
        for p in paths:
            p = Path(p)
            if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS:
                all_files.append(p)
            elif p.is_dir():
                all_files.extend(iter_images_in_dir(p))
        if all_files:
            self.input_paths = all_files
            self.append_log(f"{len(all_files)} arquivo(s) carregados por arrastar e soltar.")

    # Processamento em thread
    def start_process(self):
        if not self.input_paths:
            messagebox.showwarning("Atenção", "Selecione arquivos ou uma pasta primeiro.")
            return
        if not self.output_dir:
            messagebox.showwarning("Atenção", "Selecione a pasta de saída.")
            return
        t = threading.Thread(target=self._process_all, daemon=True)
        t.start()

    def _process_all(self):
        total = len(self.input_paths)
        self.append_log(f"{total} arquivo(s) a processar.")
        self.set_progress(0.0)
        for idx, p in enumerate(self.input_paths, start=1):
            try:
                self.append_log(f"Processando: {p.name} ...")
                out = process_image(p, self.output_dir)
                self.append_log(f"✓ {p.name} → {out.name}")
            except Exception as e:
                self.append_log(f"✗ Erro em {p.name}: {e}")
            self.set_progress(idx / total)
        self.append_log("🎉 Concluído!")
        self.set_progress(1.0)

# ---------------------------
# Main
# ---------------------------
if __name__ == "__main__":
    app = NoBackApp()
    app.mainloop()


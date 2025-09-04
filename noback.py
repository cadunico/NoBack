#!/usr/bin/env python3
import os
import sys
import subprocess
from pathlib import Path

# --- configuração do ambiente virtual ---
VENV_DIR = os.path.expanduser("~/.noback_venv")
PYTHON_BIN = os.path.join(VENV_DIR, "bin", "python3")

def ensure_venv():
    """Cria o venv se não existir e instala dependências."""
    if not os.path.exists(PYTHON_BIN):
        print("🔧 Configurando ambiente isolado...")
        subprocess.check_call([sys.executable, "-m", "venv", VENV_DIR])

    # instala dependências dentro do venv
    print("📦 Instalando dependências dentro do ambiente isolado...")
    subprocess.check_call([PYTHON_BIN, "-m", "pip", "install", "--upgrade", "pip"])
    subprocess.check_call([PYTHON_BIN, "-m", "pip", "install", "rembg", "pillow", "onnxruntime", "tkinterdnd2"])

def restart_in_venv():
    """Reexecuta o script dentro do venv."""
    if sys.executable != PYTHON_BIN:
        print("🔄 Reiniciando dentro do ambiente isolado...")
        os.execv(PYTHON_BIN, [PYTHON_BIN] + sys.argv)

# --- configuração inicial ---
ensure_venv()
restart_in_venv()

# --- imports (já dentro do venv) ---
from rembg import remove
from PIL import Image
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinterdnd2 import TkinterDnD, DND_FILES

SUPPORTED_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"}

def process_image(in_path: Path, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    with Image.open(in_path).convert("RGBA") as im:
        out = remove(im)
        base = in_path.stem
        out_path = out_dir / f"{base}_nobg.png"
        out.save(out_path, format="PNG")
        return out_path

def iter_images_in_dir(folder: Path):
    for p in folder.rglob("*"):
        if p.suffix.lower() in SUPPORTED_EXTS:
            yield p

class App(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        self.title("NoBack – Remoção de Fundo")
        self.geometry("600x450")
        self.input_paths = []
        self.output_dir = None

        self._build_ui()
        self.drop_target_register(DND_FILES)
        self.dnd_bind("<<Drop>>", self.on_drop)

    def _build_ui(self):
        ttk.Label(self, text="Arraste fotos ou pastas aqui\nou use os botões abaixo:",
                  font=("Arial", 12)).pack(pady=10)

        ttk.Button(self, text="Selecionar Fotos", command=self.choose_files).pack(pady=5)
        ttk.Button(self, text="Selecionar Pasta", command=self.choose_folder).pack(pady=5)
        ttk.Button(self, text="Selecionar Saída", command=self.choose_output).pack(pady=5)

        # Barra de progresso
        self.progress = ttk.Progressbar(self, mode="determinate")
        self.progress.pack(fill="x", padx=20, pady=20)

        # Log
        self.log = tk.Text(self, height=10)
        self.log.pack(fill="both", expand=True, padx=20, pady=10)
        self.log.configure(state="disabled")

        # Botão principal de ação
        start_btn = ttk.Button(self, text="🚀 Remover Fundo", command=self.process)
        start_btn.pack(pady=15, ipadx=10, ipady=5)

    def append_log(self, text: str):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")
        self.update_idletasks()

    def choose_files(self):
        files = filedialog.askopenfilenames(
            title="Escolha imagens",
            filetypes=[("Imagens", "*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff")]
        )
        if files:
            self.input_paths = list(map(Path, files))
            self.append_log(f"{len(files)} arquivo(s) selecionado(s).")

    def choose_folder(self):
        folder = filedialog.askdirectory(title="Escolha uma pasta com imagens")
        if folder:
            self.input_paths = list(iter_images_in_dir(Path(folder)))
            self.append_log(f"{len(self.input_paths)} arquivo(s) encontrados na pasta.")

    def choose_output(self):
        folder = filedialog.askdirectory(title="Escolha a pasta de saída")
        if folder:
            self.output_dir = Path(folder)
            self.append_log(f"Pasta de saída: {self.output_dir}")

    def on_drop(self, event):
        paths = self.tk.splitlist(event.data)
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

    def process(self):
        if not self.input_paths:
            messagebox.showwarning("Atenção", "Selecione arquivos ou uma pasta primeiro.")
            return
        if not self.output_dir:
            messagebox.showwarning("Atenção", "Selecione a pasta de saída.")
            return

        self.progress.configure(maximum=len(self.input_paths), value=0)
        self.append_log(f"Iniciando processamento de {len(self.input_paths)} arquivos...")

        for idx, f in enumerate(self.input_paths, start=1):
            try:
                out_path = process_image(f, self.output_dir)
                self.append_log(f"✓ {f.name} → {out_path.name}")
            except Exception as e:
                self.append_log(f"✗ Erro em {f.name}: {e}")
            self.progress.configure(value=idx)
            self.update_idletasks()

        self.append_log("🎉 Concluído!")

if __name__ == "__main__":
    App().mainloop()


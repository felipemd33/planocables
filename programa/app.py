"""Ventana sencilla: elegir planos PDF -> PDF buscable + listado de cables en Excel."""
import os, sys, threading, queue, traceback, subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class App(tk.Tk):
    def __init__(self, files=()):
        super().__init__()
        self.title('Planos eléctricos → Listado de cables')
        self.geometry('760x520'); self.minsize(620, 420)
        self.q = queue.Queue(); self.files = list(files); self.outs = []
        pad = dict(padx=10, pady=6)

        top = ttk.Frame(self); top.pack(fill='x', **pad)
        ttk.Button(top, text='Elegir plano(s) PDF…', command=self.pick).pack(side='left')
        self.lbl = ttk.Label(top, text='Ningún archivo elegido', foreground='#555')
        self.lbl.pack(side='left', padx=10)

        opt = ttk.LabelFrame(self, text='Qué generar'); opt.pack(fill='x', **pad)
        self.v_pdf = tk.BooleanVar(value=True); self.v_xls = tk.BooleanVar(value=True); self.v_ocr = tk.BooleanVar(value=True)
        ttk.Checkbutton(opt, text='PDF buscable (Ctrl+F encuentra los números)', variable=self.v_pdf).pack(anchor='w', padx=8, pady=2)
        ttk.Checkbutton(opt, text='Listado de cables en Excel (número, color, sección, hojas)', variable=self.v_xls).pack(anchor='w', padx=8, pady=2)
        ttk.Checkbutton(opt, text='Usar OCR como apoyo para textos que no reconozca (recomendado)', variable=self.v_ocr).pack(anchor='w', padx=8, pady=2)

        out = ttk.Frame(self); out.pack(fill='x', **pad)
        ttk.Label(out, text='Guardar en:').pack(side='left')
        self.v_out = tk.StringVar(value='(carpeta "2 - Resultados")')
        ttk.Entry(out, textvariable=self.v_out).pack(side='left', fill='x', expand=True, padx=6)
        ttk.Button(out, text='Cambiar…', command=self.pick_out).pack(side='left')

        run = ttk.Frame(self); run.pack(fill='x', **pad)
        self.btn = ttk.Button(run, text='▶  Procesar', command=self.start); self.btn.pack(side='left')
        self.bar = ttk.Progressbar(run, mode='determinate'); self.bar.pack(side='left', fill='x', expand=True, padx=10)
        self.btn_open = ttk.Button(run, text='Abrir carpeta', command=self.open_folder, state='disabled'); self.btn_open.pack(side='left')

        self.txt = tk.Text(self, height=14, wrap='word', font=('Consolas', 9)); self.txt.pack(fill='both', expand=True, **pad)
        self.after(100, self.poll)
        if self.files:
            self.lbl.config(text=self.names())

    def names(self):
        return ', '.join(os.path.basename(f) for f in self.files)

    def pick(self):
        f = filedialog.askopenfilenames(title='Elegir plano(s)', filetypes=[('PDF', '*.pdf')])
        if f:
            self.files = list(f); self.lbl.config(text=self.names())

    def pick_out(self):
        d = filedialog.askdirectory(title='Carpeta de salida')
        if d:
            self.v_out.set(d)

    def log(self, m):
        self.q.put(('log', m))

    def start(self):
        if not self.files:
            messagebox.showinfo('Falta el plano', 'Elige primero uno o más planos PDF.'); return
        self.btn.config(state='disabled'); self.btn_open.config(state='disabled'); self.txt.delete('1.0', 'end'); self.outs = []
        threading.Thread(target=self.work, daemon=True).start()

    def work(self):
        try:
            from cli import run
            outdir = self.v_out.get()
            outdir = None if outdir.startswith('(') else outdir
            for k, f in enumerate(self.files):
                def lg(m, k=k):
                    self.log(m)
                    if m.startswith('Hoja '):
                        try:
                            a, b = m.split(':')[0].split()[1].split('/')
                            self.q.put(('prog', (k + int(a) / int(b)) / len(self.files) * 100))
                        except Exception:
                            pass
                res, outs = run(f, outdir, self.v_pdf.get(), self.v_xls.get(), self.v_ocr.get(), log=lg)
                self.outs += outs
            self.q.put(('done', None))
        except Exception:
            self.q.put(('err', traceback.format_exc()))

    def poll(self):
        try:
            while True:
                k, v = self.q.get_nowait()
                if k == 'log':
                    self.txt.insert('end', v + '\n'); self.txt.see('end')
                elif k == 'prog':
                    self.bar['value'] = v
                elif k == 'done':
                    self.bar['value'] = 100; self.btn.config(state='normal'); self.btn_open.config(state='normal')
                    self.txt.insert('end', '\nTerminado.\n'); self.txt.see('end')
                elif k == 'err':
                    self.btn.config(state='normal'); self.txt.insert('end', '\nERROR:\n' + v); self.txt.see('end')
        except queue.Empty:
            pass
        self.after(100, self.poll)

    def open_folder(self):
        if self.outs:
            subprocess.Popen(['explorer', '/select,', os.path.normpath(self.outs[-1])])


if __name__ == '__main__':
    App([a for a in sys.argv[1:] if a.lower().endswith('.pdf')]).mainloop()

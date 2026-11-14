import copy
import json
import os
import sys
import shutil
import subprocess
import unicodedata
import webbrowser
from urllib.parse import urlparse
import updater
import tkinter as tk
from datetime import date, datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

APP_NAME = 'Organizator Cantari Betel Padureni'
APP_VERSION = '11.0.6'
DATA_DIR = Path(os.environ.get('APPDATA', str(Path.home()))) / 'OrganizatorCantari'
DATA_FILE = DATA_DIR / 'cantari.json'
BACKUP_DIR = DATA_DIR / 'backup'
PROGRAMS_FILE = DATA_DIR / 'programe.json'
DEFAULT_PROGRAMS = ['Dimineață', 'Seară', 'Tineri']


PALETTES = {
    'dark': {'bg':'#101522','panel':'#182033','panel2':'#222d44','fg':'#eef2ff','muted':'#a7b3ca','accent':'#647dff','accent2':'#394b84','entry':'#28344b','select':'#34476b','danger':'#ed6379'},
    'light': {'bg':'#f3f6fc','panel':'#ffffff','panel2':'#e8edf8','fg':'#17233c','muted':'#5c6b85','accent':'#445ddd','accent2':'#dce4ff','entry':'#f0f3fb','select':'#dbe5ff','danger':'#c33c54'}
}

def search_key(value):
    """Căutare fără diferență între majuscule și diacritice românești."""
    value = str(value).casefold().translate(str.maketrans({'ș':'s','ş':'s','ț':'t','ţ':'t'}))
    return ''.join(ch for ch in unicodedata.normalize('NFKD', value)
                   if not unicodedata.combining(ch))


def blank_data():
    return {'version':1,'theme':'dark','categories':[]}

def normalize(raw):
    if isinstance(raw, list):
        raw = {'version':1,'theme':'dark','categories':raw}
    if not isinstance(raw, dict):
        raise ValueError('Fișierul trebuie să conțină un obiect JSON.')
    cats = raw.get('categories', [])
    if not isinstance(cats, list):
        raise ValueError('Lista de categorii este invalidă.')
    result = blank_data()
    result['theme'] = raw.get('theme') if raw.get('theme') in PALETTES else 'dark'
    for cat in cats:
        if not isinstance(cat, dict):
            continue
        category = {'name':str(cat.get('name','Categorie')),'days':[]}
        for day in cat.get('days', []):
            if not isinstance(day, dict):
                continue
            entry = {'name':str(day.get('name','Zi')),'date':str(day.get('date','')),'program':str(day.get('program','Program principal')),'songs':[]}
            for song in day.get('songs', []):
                if isinstance(song, dict):
                    entry['songs'].append({'title':str(song.get('title','')),'number':str(song.get('number','')),'link':str(song.get('link',''))})
            category['days'].append(entry)
        result['categories'].append(category)
    return result

def get_programs():
    try:
        saved = json.loads(PROGRAMS_FILE.read_text(encoding='utf-8'))
        if isinstance(saved, list):
            return list(dict.fromkeys(str(x).strip() for x in saved if str(x).strip()))
    except (OSError, ValueError):
        pass
    return DEFAULT_PROGRAMS.copy()


def add_program_name(name):
    name = name.strip()
    if not name:
        return False
    programs = get_programs()
    if name.casefold() in [p.casefold() for p in programs]:
        return False
    programs.append(name)
    PROGRAMS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROGRAMS_FILE.write_text(json.dumps(programs, ensure_ascii=False, indent=2), encoding='utf-8')
    return True


def remove_program_name(name):
    programs = [p for p in get_programs() if p.casefold() != name.casefold()]
    PROGRAMS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROGRAMS_FILE.write_text(json.dumps(programs, ensure_ascii=False, indent=2), encoding='utf-8')
    return programs


class DarkProgramSelector(tk.Frame):
    def __init__(self, parent, options, selected, colors):
        super().__init__(parent, bg=colors['entry'], highlightthickness=1,
                         highlightbackground=colors['muted'])
        self.colors = colors
        self.options = list(options)
        self.value = tk.StringVar(value=selected)
        self.entry = tk.Entry(self, textvariable=self.value, state='readonly',
                              readonlybackground=colors['entry'], fg=colors['fg'],
                              relief='flat', bd=0, font=('Segoe UI', 10), cursor='hand2')
        self.entry.pack(side='left', fill='x', expand=True, padx=(9,0), ipady=7)
        self.arrow = tk.Label(self, text='▼', bg=colors['entry'], fg=colors['fg'],
                              font=('Segoe UI', 9), width=3, cursor='hand2')
        self.arrow.pack(side='right', fill='y')
        self.entry.bind('<Button-1>', self.open_menu)
        self.arrow.bind('<Button-1>', self.open_menu)
        self.menu = None

    def get(self):
        return self.value.get()

    def set(self, value):
        self.value.set(value)

    def __setitem__(self, key, value):
        if key == 'values':
            self.options = list(value)
        else:
            super().__setitem__(key, value)

    def open_menu(self, event=None):
        if self.menu is not None and self.menu.winfo_exists():
            self.menu.destroy()
            self.menu = None
            return
        popup = tk.Toplevel(self)
        self.menu = popup
        popup.overrideredirect(True)
        popup.configure(bg=self.colors['accent'])
        listing = tk.Listbox(popup, font=('Segoe UI', 10), activestyle='none',
                             bg=self.colors['panel2'], fg=self.colors['fg'],
                             selectbackground=self.colors['select'],
                             selectforeground=self.colors['fg'],
                             highlightthickness=0, relief='flat', bd=0,
                             exportselection=False, height=min(max(len(self.options),1),8))
        listing.pack(fill='both', expand=True, padx=1, pady=1)
        for item in self.options:
            listing.insert('end', item)
        popup.geometry(f'{max(self.winfo_width(),180)}x{min(max(len(self.options),1),8)*25+2}+{self.winfo_rootx()}+{self.winfo_rooty()+self.winfo_height()}')
        for idx, item in enumerate(self.options):
            if item == self.get():
                listing.selection_set(idx)
                listing.see(idx)
                break
        def close():
            popup.destroy()
            self.menu = None
        def choose(event=None):
            selection = listing.curselection()
            if selection:
                self.set(self.options[selection[0]])
            close()
        listing.bind('<ButtonRelease-1>', choose)
        listing.bind('<Return>', choose)
        listing.bind('<Escape>', lambda e: close())
        popup.bind('<FocusOut>', lambda e: close() if popup.winfo_exists() else None)
        listing.focus_set()


class Dialog(tk.Toplevel):
    def __init__(self, parent, title, fields, values=None, optional_keys=()):
        super().__init__(parent)
        self.result = None
        self.optional_keys = set(optional_keys)
        self.title(title)
        self.transient(parent)
        self.resizable(False, False)
        self.configure(bg=parent.colors['panel'])
        self.inputs = {}
        values = values or {}
        self.columnconfigure(0, weight=1)
        frame = ttk.Frame(self, padding=20)
        frame.grid(sticky='nsew')
        for i, (key, label) in enumerate(fields):
            ttk.Label(frame, text=label).grid(row=i*2, column=0, sticky='w', pady=(0,5))
            if key == 'program':
                program_row = ttk.Frame(frame)
                program_row.grid(row=i*2+1, column=0, sticky='ew', pady=(0,13))
                program_row.columnconfigure(0, weight=1)
                current = str(values.get(key, 'Dimineață'))
                options = get_programs()
                if current and current not in options:
                    options.insert(0, current)
                ent = DarkProgramSelector(program_row, options, current if current else 'Dimineață', parent.colors)
                ent.grid(row=0, column=0, sticky='ew')
                ttk.Button(program_row, text='+ Alt program', command=lambda e=ent: self.add_program(e)).grid(row=0, column=1, padx=(8,0))
                ttk.Button(program_row, text='Șterge program', command=lambda e=ent: self.delete_program(e)).grid(row=0, column=2, padx=(8,0))
            else:
                ent = ttk.Entry(frame, width=43)
                ent.grid(row=i*2+1, column=0, sticky='ew', pady=(0,13))
                ent.insert(0, str(values.get(key,'')))
            self.inputs[key] = ent
        buttons = ttk.Frame(frame)
        buttons.grid(row=len(fields)*2, column=0, sticky='e')
        ttk.Button(buttons, text='Anulează', command=self.destroy).pack(side='right', padx=(8,0))
        ttk.Button(buttons, text='Salvează', style='Accent.TButton', command=self.save).pack(side='right')
        self.bind('<Return>', lambda e:self.save())
        self.bind('<Escape>', lambda e:self.destroy())
        self.protocol('WM_DELETE_WINDOW', self.destroy)
        self.update_idletasks()
        x=parent.winfo_rootx()+(parent.winfo_width()-self.winfo_width())//2
        y=parent.winfo_rooty()+(parent.winfo_height()-self.winfo_height())//2
        self.geometry(f'+{max(0,x)}+{max(0,y)}')
        self.grab_set()
        next(iter(self.inputs.values())).focus_set()
        self.wait_window()

    def delete_program(self, combo):
        name = combo.get().strip()
        if not name:
            messagebox.showinfo('Program', 'Selectează un program din listă.', parent=self)
            return
        if not messagebox.askyesno('Șterge program',
                f'Elimini „{name}” din lista de programe disponibile?\\n\\nCântările și programele deja create NU vor fi șterse.',
                icon='warning', parent=self):
            return
        remaining = remove_program_name(name)
        combo['values'] = remaining
        combo.set(remaining[0] if remaining else '')
        messagebox.showinfo('Program eliminat',
            'Programul a fost eliminat din listă. Programele deja create au rămas neschimbate.', parent=self)

    def add_program(self, combo):
        popup = tk.Toplevel(self)
        popup.title('Adaugă program')
        popup.transient(self)
        popup.resizable(False, False)
        popup.configure(bg=self.master.colors['panel'])
        wrap = ttk.Frame(popup, padding=18)
        wrap.pack(fill='both', expand=True)
        ttk.Label(wrap, text='Numele programului nou:').pack(anchor='w', pady=(0,7))
        entry = ttk.Entry(wrap, width=34)
        entry.pack(fill='x', pady=(0,12))
        def confirm(event=None):
            name = entry.get().strip()
            if not name:
                messagebox.showwarning('Nume lipsă', 'Scrie numele programului.', parent=popup)
                return
            if not add_program_name(name):
                messagebox.showinfo('Program existent', 'Programul există deja.', parent=popup)
            combo['values'] = get_programs()
            combo.set(next((x for x in get_programs() if x.casefold() == name.casefold()), name))
            popup.destroy()
        ttk.Button(wrap, text='Adaugă', style='Accent.TButton', command=confirm).pack(side='right')
        popup.bind('<Return>', confirm)
        popup.bind('<Escape>', lambda e: popup.destroy())
        popup.grab_set()
        entry.focus_set()
        popup.wait_window()

    def save(self):
        values = {k:widget.get().strip() for k,widget in self.inputs.items()}
        if any(not value for key, value in values.items() if key not in self.optional_keys):
            messagebox.showwarning('Câmpuri obligatorii','Completează toate câmpurile.',parent=self)
            return
        link = values.get('link', '')
        if link:
            parsed = urlparse(link)
            if parsed.scheme.lower() not in ('https', 'http') or not parsed.netloc:
                messagebox.showwarning('Link invalid', 'Introdu un link complet, de exemplu https://www.youtube.com/watch?v=...', parent=self)
                return
        self.result = values
        self.destroy()

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry('1160x750')
        self.minsize(850,560)
        self.data = blank_data()
        self.cat_idx = None
        self.day_idx = None
        self.query = tk.StringVar()
        self.cat_query = tk.StringVar()
        self.day_query = tk.StringVar()
        self.status = tk.StringVar(value='Pregătit')
        self.search_results = []
        self.search_pos = -1
        self.load_data()
        self.colors = PALETTES[self.data['theme']]
        self.setup_styles()
        self.build_ui()
        self.render_all()
        self.bind_all('<Control-f>', self.focus_search)
        self.bind_all('<Control-F>', self.focus_search)
        self.bind_all('<F3>', self.next_result)
        self.bind_all('<Shift-F3>', lambda e:self.next_result(e, -1))
        self.protocol('WM_DELETE_WINDOW', self.destroy)
        self.after(1800, lambda: self.check_updates(silent=True))

    def load_data(self):
        try:
            if DATA_FILE.exists():
                self.data = normalize(json.loads(DATA_FILE.read_text(encoding='utf-8')))
        except Exception as exc:
            messagebox.showwarning('Date indisponibile',f'Nu am putut încărca datele salvate:\n{exc}\n\nDatele originale nu vor fi suprascrise automat.')
            self.data = blank_data()
            self.readonly = True
        else:
            self.readonly = False

    def automatic_backup(self):
        """Păstrează maximum 30 de copii, una pe zi, înainte de prima salvare."""
        if not DATA_FILE.is_file():
            return
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        target = BACKUP_DIR / ('cantari-' + date.today().isoformat() + '.json')
        if not target.exists():
            # Copia de siguranță conține datele anterioare modificării.
            shutil.copy2(DATA_FILE, target)
        for old in sorted(BACKUP_DIR.glob('cantari-????-??-??.json'))[:-30]:
            old.unlink()

    def persist(self):
        if self.readonly:
            return
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            self.automatic_backup()
            temp = DATA_FILE.with_suffix('.tmp')
            temp.write_text(json.dumps(self.data,ensure_ascii=False,indent=2),encoding='utf-8')
            os.replace(temp,DATA_FILE)
        except Exception as exc:
            messagebox.showerror('Eroare la salvare',f'Nu s-au putut salva datele:\n{exc}')

    def setup_styles(self):
        c=self.colors
        self.configure(bg=c['bg'])
        style=ttk.Style(self)
        style.theme_use('clam')
        style.configure('.', background=c['panel'], foreground=c['fg'], font=('Segoe UI',10))
        style.configure('TFrame',background=c['panel'])
        style.configure('Root.TFrame',background=c['bg'])
        style.configure('TLabel',background=c['panel'],foreground=c['fg'])
        style.configure('Muted.TLabel',background=c['panel'],foreground=c['muted'])
        style.configure('Title.TLabel',background=c['panel'],foreground=c['fg'],font=('Segoe UI Semibold',17))
        style.configure('TButton',background=c['panel2'],foreground=c['fg'],padding=(11,8),borderwidth=0)
        style.map('TButton',background=[('active',c['select'])])
        style.configure('Accent.TButton',background=c['accent'],foreground='#ffffff')
        style.map('Accent.TButton',background=[('active',c['accent2'])])
        style.configure('Danger.TButton',background=c['panel2'],foreground=c['danger'])
        style.configure('TEntry',fieldbackground=c['entry'],foreground=c['fg'],insertcolor=c['fg'],padding=7,borderwidth=0)
        style.configure('Treeview',background=c['panel'],fieldbackground=c['panel'],foreground=c['fg'],rowheight=36,borderwidth=0,font=('Segoe UI',10))
        style.configure('Treeview.Heading',background=c['panel2'],foreground=c['fg'],padding=10,font=('Segoe UI Semibold',10))
        style.map('Treeview',background=[('selected',c['select'])],foreground=[('selected',c['fg'])])
        style.configure('TScrollbar',background=c['panel2'],troughcolor=c['panel'])

    def build_ui(self):
        c=self.colors
        header=ttk.Frame(self,style='Root.TFrame',padding=(18,14))
        header.pack(fill='x')
        tk.Label(header,text='♫',bg=c['bg'],fg=c['accent'],font=('Segoe UI',27,'bold')).pack(side='left',padx=(0,10))
        title_area=tk.Frame(header,bg=c['bg'])
        title_area.pack(side='left')
        tk.Label(title_area,text=APP_NAME,bg=c['bg'],fg=c['fg'],font=('Segoe UI Semibold',21),anchor='w').pack(anchor='w')
        tk.Label(title_area,text=f'Autor Bodea Emanuel | Versiunea {APP_VERSION}',bg=c['bg'],fg=c['muted'],font=('Segoe UI',10),anchor='w').pack(anchor='w',pady=(2,0))
        ttk.Button(header,text='Verifică actualizări',command=self.check_updates).pack(side='right',padx=(8,0))
        ttk.Button(header,text='☼  Schimbă tema',command=self.toggle_theme).pack(side='right',padx=(8,0))
        ttk.Button(header,text='Import JSON',command=self.import_json).pack(side='right',padx=(8,0))
        ttk.Button(header,text='Export JSON',command=self.export_json).pack(side='right')

        main=ttk.Frame(self,style='Root.TFrame',padding=(18,0,18,12))
        main.pack(fill='both',expand=True)
        main.columnconfigure(0,weight=20,minsize=240)
        main.columnconfigure(1,weight=23,minsize=270)
        main.columnconfigure(2,weight=57,minsize=540)
        main.rowconfigure(0,weight=1)
        self.panels=[]
        for col in range(3):
            panel=ttk.Frame(main,padding=14)
            panel.grid(row=0,column=col,sticky='nsew',padx=(0,10) if col<2 else 0)
            panel.columnconfigure(0,weight=1)
            panel.rowconfigure(2,weight=1)
            self.panels.append(panel)

        p=self.panels[0]
        ttk.Label(p,text='Categorii',style='Title.TLabel').grid(row=0,column=0,sticky='w',pady=(0,10))
        cat_top=ttk.Frame(p);cat_top.grid(row=1,column=0,sticky='ew',pady=(0,12));cat_top.columnconfigure(1,weight=1)
        ttk.Button(cat_top,text='+ Categorie',style='Accent.TButton',command=self.add_category).grid(row=0,column=0,sticky='w',padx=(0,9))
        self.cat_search_entry=ttk.Entry(cat_top,textvariable=self.cat_query)
        self.cat_search_entry.grid(row=0,column=1,sticky='ew')
        self.cat_query.trace_add('write',lambda *_:self.render_categories())
        self.cat_tree=self.tree(p,('name',),('Categorie',))
        self.cat_tree.column('name',width=170,minwidth=90,stretch=True,anchor='center')
        self.cat_tree.grid(row=2,column=0,sticky='nsew')
        self.cat_tree.bind('<<TreeviewSelect>>',self.select_category)
        self.cat_tree.bind('<Double-1>',self.edit_category)
        bar=ttk.Frame(p);bar.grid(row=3,column=0,sticky='ew',pady=(12,0))
        ttk.Button(bar,text='Redenumește',command=self.edit_category).pack(side='left')
        ttk.Button(bar,text='Șterge',style='Danger.TButton',command=self.delete_category).pack(side='right')

        p=self.panels[1]
        ttk.Label(p,text='Zile și date',style='Title.TLabel').grid(row=0,column=0,sticky='w',pady=(0,10))
        day_top=ttk.Frame(p);day_top.grid(row=1,column=0,sticky='ew',pady=(0,12));day_top.columnconfigure(1,weight=1)
        ttk.Button(day_top,text='+ Zi',style='Accent.TButton',command=self.add_day).grid(row=0,column=0,sticky='w',padx=(0,9))
        self.day_search_entry=ttk.Entry(day_top,textvariable=self.day_query)
        self.day_search_entry.grid(row=0,column=1,sticky='ew')
        self.day_search_entry.insert(0,'')
        self.day_query.trace_add('write',lambda *_:self.render_days_filtered())
        self.day_tree=self.tree(p,('name','date','program'),('Zi','Dată','Program'))
        self.day_tree.column('name',width=135,minwidth=75,stretch=True,anchor='center')
        self.day_tree.column('date',width=100,minwidth=85,stretch=True,anchor='center')
        self.day_tree.column('program',width=155,minwidth=100,stretch=True,anchor='center')
        self.day_tree.grid(row=2,column=0,sticky='nsew')
        self.day_tree.bind('<<TreeviewSelect>>',self.select_day)
        self.day_tree.bind('<Double-1>',self.edit_day)
        bar=ttk.Frame(p);bar.grid(row=3,column=0,sticky='ew',pady=(12,0))
        ttk.Button(bar,text='Editează',command=self.edit_day).pack(side='left')
        ttk.Button(bar,text='Șterge',style='Danger.TButton',command=self.delete_day).pack(side='right')

        p=self.panels[2]
        ttk.Label(p,text='Cântări',style='Title.TLabel').grid(row=0,column=0,sticky='w',pady=(0,10))
        top=ttk.Frame(p);top.grid(row=1,column=0,sticky='ew',pady=(0,12));top.columnconfigure(1,weight=1)
        ttk.Button(top,text='+ Cântare',style='Accent.TButton',command=self.add_song).grid(row=0,column=0,sticky='w',padx=(0,9))
        self.search_entry=ttk.Entry(top,textvariable=self.query)
        self.search_entry.grid(row=0,column=1,sticky='ew')
        self.search_entry.insert(0,'')
        self.query.trace_add('write',lambda *_:self.render_songs())
        self.song_tree=self.tree(p,('number','title','link'),('Nr.','Titlul cântării','Link'))
        self.song_tree.column('number',width=65,minwidth=50,stretch=False,anchor='center')
        self.song_tree.column('title',width=270,minwidth=140,stretch=True,anchor='center')
        self.song_tree.column('link',width=115,minwidth=85,stretch=True,anchor='center')
        self.song_tree.grid(row=2,column=0,sticky='nsew')
        self.song_tree.bind('<Double-1>',self.song_double_click)
        self.song_tree.bind('<ButtonPress-1>',self.song_drag_start,add='+')
        self.song_tree.bind('<ButtonRelease-1>',self.song_drag_end,add='+')
        # Culorile pentru linkuri sunt aplicate doar in coloana Link, nu pe intregul rand.
        self.link_labels = {}
        self.after(150, self.refresh_link_labels)
        bar=ttk.Frame(p);bar.grid(row=3,column=0,sticky='ew',pady=(12,0))
        ttk.Button(bar,text='Editează',command=self.edit_song).pack(side='left')
        ttk.Button(bar,text='Copiază în...',command=self.copy_song).pack(side='left',padx=(8,0))
        ttk.Button(bar,text='Istoric',command=self.song_history).pack(side='left',padx=(8,0))
        ttk.Button(bar,text='Deschide link',command=self.open_song_link).pack(side='left',padx=(8,0))
        ttk.Button(bar,text='Șterge',style='Danger.TButton',command=self.delete_song).pack(side='right')
        self.status_label=tk.Label(self,textvariable=self.status,bg=c['bg'],fg=c['muted'],anchor='w',font=('Segoe UI',9),padx=20,pady=9)
        self.status_label.pack(fill='x')

    def check_updates(self, silent=False):
        import threading
        if getattr(self, '_checking_updates', False):
            if not silent:
                self._update_manual_requested = True
                self.status.set('Verific actualizările...')
            return
        self._checking_updates = True
        self._update_manual_requested = not silent
        self.status.set('Verific actualizările...')
        def task():
            try:
                result = updater.find_update(APP_VERSION)
                self.after(0, lambda: self.update_result(result, False))
            except Exception as exc:
                error = str(exc)
                self.after(0, lambda: self.update_error(error, False))
        threading.Thread(target=task, daemon=True).start()

    def update_error(self, error, silent=False):
        self._checking_updates = False
        self.status.set('Verificarea actualizărilor nu a reușit.')
        if getattr(self, '_update_manual_requested', False):
            messagebox.showwarning('Actualizări', error, parent=self)
        self._update_manual_requested = False

    def update_result(self, result, silent=False):
        self._checking_updates = False
        manual = getattr(self, '_update_manual_requested', False)
        self._update_manual_requested = False
        if result is None:
            self.status.set('Ai deja cea mai recentă versiune.')
            if manual:
                messagebox.showinfo('Actualizări', 'Ai deja cea mai recentă versiune.', parent=self)
            return
        version, notes, url, checksum = result
        self.status.set(f'Actualizare disponibilă: v{version}')
        if not messagebox.askyesno('Actualizare disponibilă',
            f'Versiune instalată: {APP_VERSION}\nVersiune nouă: {version}\n\nNoutăți:\n{notes[:700]}\n\nDescarci și instalezi actualizarea?', parent=self):
            return
        self.status.set('Descarc actualizarea...')
        import threading
        def task():
            try:
                staged = updater.download_verified(url, checksum)
                self.after(0, lambda: self.install_update(staged))
            except Exception as exc:
                error = str(exc)
                self.after(0, lambda: self.download_update_error(error))
        threading.Thread(target=task, daemon=True).start()

    def download_update_error(self, error):
        self.status.set('Descărcarea actualizării a eșuat.')
        messagebox.showerror('Actualizare eșuată', error, parent=self)

    def install_update(self, staged):
        if not messagebox.askyesno('Instalează actualizarea',
            'Descărcarea s-a încheiat și fișierul a fost verificat.\n\nAplicația se va închide pentru a înlocui executabilul. Continui?', parent=self):
            try: staged.unlink(missing_ok=True)
            except OSError: pass
            self.status.set('Instalarea actualizării a fost anulată.')
            return
        try:
            updater.launch_installer(staged)
        except Exception as exc:
            messagebox.showerror('Actualizare eșuată', str(exc), parent=self)
            self.status.set('Instalarea actualizării a eșuat.')
            return
        self.destroy()

    def tree(self,parent,columns,headings):
        tree=ttk.Treeview(parent,columns=columns,show='headings',selectmode='browse')
        for key,title in zip(columns,headings):
            tree.heading(key,text=title)
            tree.column(key,width=180,anchor='center',stretch=False)
        # Permite doar separatorul Zi/Dată și Titlul cântării/Link.
        tree.bind('<Button-1>', lambda event, widget=tree: self.block_column_resize(event, widget), add='+')
        tree.bind('<B1-Motion>', lambda event, widget=tree: self.block_column_resize(event, widget), add='+')
        return tree

    def block_column_resize(self, event, widget):
        if widget.identify_region(event.x, event.y) != 'separator':
            return
        # Detectăm separatorul după poziția sa reală, nu după indexul
        # returnat de identify_column (poate diferi între versiuni Tk).
        columns = list(widget['columns'])
        boundaries = []
        position = 0
        for col in columns[:-1]:
            position += int(widget.column(col, 'width'))
            boundaries.append(position)
        if widget is self.day_tree:
            allowed = {0}  # Zi | Dată
        elif widget is self.song_tree:
            allowed = {1}  # Titlul cântării | Link
        else:
            allowed = set()
        if not any(abs(event.x - boundaries[i]) <= 8 for i in allowed):
            return 'break'


    def render_all(self):
        self.render_categories()
        self.render_days()
        self.render_songs()

    def render_categories(self):
        self.cat_tree.delete(*self.cat_tree.get_children())
        query=search_key(self.cat_query.get().strip())
        for i,cat in enumerate(self.data['categories']):
            if query and query not in search_key(cat['name']):
                continue
            self.cat_tree.insert('', 'end',iid=str(i),values=(cat['name'],))
        if self.cat_idx is not None and self.cat_tree.exists(str(self.cat_idx)):
            self.cat_tree.selection_set(str(self.cat_idx))
        else:
            self.cat_idx=None
            self.day_idx=None
            self.render_days()
            self.render_songs()

    def render_days(self):
        self.render_days_filtered()

    def render_days_filtered(self):
        self.day_tree.delete(*self.day_tree.get_children())
        if self.cat_idx is None:return
        query=search_key(self.day_query.get().strip())
        for i,day in enumerate(self.data['categories'][self.cat_idx]['days']):
            if query and query not in search_key(day['date']) and query not in search_key(day['name']) and query not in search_key(day.get('program','Program principal')):
                continue
            self.day_tree.insert('','end',iid=str(i),values=(day['name'],day['date'],day.get('program','Program principal')))
        if self.day_idx is not None and self.day_tree.exists(str(self.day_idx)):
            self.day_tree.selection_set(str(self.day_idx))
        else:
            self.day_idx=None
            self.render_songs()

    def render_songs(self):
        self.clear_link_labels()
        self.song_tree.delete(*self.song_tree.get_children())
        self.search_results=[]
        if self.day_idx is None or self.cat_idx is None:
            self.status.set('Selectează o categorie și o zi pentru a vedea cântările.');return
        q=search_key(self.query.get().strip())
        for i,song in enumerate(self.songs()):
            if q and q not in search_key(song['title']):continue
            self.song_tree.insert('','end',iid=str(i),values=(song['number'],song['title'],'Deschide' if song.get('link','').strip() else '—'))
            self.search_results.append(str(i))
        self.search_pos=-1
        self.status.set(f'{len(self.search_results)} cântări afișate din {len(self.songs())} • Ctrl+F: căutare • F3: următorul rezultat • dublu click: editare')

    def clear_link_labels(self):
        for label in getattr(self, 'link_labels', {}).values():
            label.destroy()
        self.link_labels = {}

    def refresh_link_labels(self):
        # Treeview nu permite stilizarea unei singure celule. Folosim etichete
        # suprapuse doar peste celulele Link, cu text albastru si subliniat.
        try:
            if not self.song_tree.winfo_exists():
                return
            current = set()
            for iid in self.song_tree.get_children():
                if self.cat_idx is None or self.day_idx is None:
                    continue
                try:
                    song = self.songs()[int(iid)]
                except (IndexError, ValueError):
                    continue
                if not song.get('link', '').strip():
                    continue
                bbox = self.song_tree.bbox(iid, 'link')
                if not bbox:
                    continue
                x, y, width, height = bbox
                if width <= 0 or height <= 0:
                    continue
                current.add(iid)
                selected = iid in self.song_tree.selection()
                bg = self.colors['select'] if selected else self.colors['panel']
                if iid not in self.link_labels:
                    label = tk.Label(self.song_tree, text='Deschide',
                        font=('Segoe UI', 10, 'underline'), fg=self.colors['accent'],
                        cursor='hand2', bd=0, padx=0, pady=0)
                    label.bind('<Button-1>', lambda event, row=iid: self.open_link_for_row(row))
                    self.link_labels[iid] = label
                label = self.link_labels[iid]
                label.configure(bg=bg, fg=self.colors['accent'])
                label.place(x=x, y=y, width=width, height=height)
            for iid in list(self.link_labels):
                if iid not in current:
                    self.link_labels.pop(iid).destroy()
        except tk.TclError:
            return
        self.after(150, self.refresh_link_labels)

    def open_link_for_row(self, iid):
        if self.song_tree.exists(iid):
            self.song_tree.selection_set(iid)
            self.open_song_link()

    def days(self):return self.data['categories'][self.cat_idx]['days']
    def songs(self):return self.days()[self.day_idx]['songs']
    def select_category(self,event=None):
        selection=self.cat_tree.selection()
        self.cat_idx=int(selection[0]) if selection else None
        self.day_idx=None
        self.render_days();self.render_songs()
    def select_day(self,event=None):
        selection=self.day_tree.selection()
        self.day_idx=int(selection[0]) if selection else None
        self.render_songs()
    def get_cat(self):
        if self.cat_idx is None:messagebox.showinfo('Selectează categoria','Alege mai întâi o categorie.',parent=self);return False
        return True
    def get_day(self):
        if not self.get_cat():return False
        if self.day_idx is None:messagebox.showinfo('Selectează ziua','Alege mai întâi o zi.',parent=self);return False
        return True
    def selected_song(self):
        selection=self.song_tree.selection()
        if not selection:messagebox.showinfo('Selectează cântarea','Alege mai întâi o cântare.',parent=self);return None
        return int(selection[0])
    def dialog(self,title,fields,values=None,optional_keys=()):
        return Dialog(self,title,fields,values,optional_keys).result
    def commit(self):
        self.persist();self.render_all()

    def add_category(self):
        result=self.dialog('Categorie nouă',[('name','Numele categoriei')])
        if result:
            self.data['categories'].append({'name':result['name'],'days':[]})
            self.cat_idx=len(self.data['categories'])-1;self.day_idx=None;self.commit()
    def edit_category(self,event=None):
        if not self.get_cat():return
        cat=self.data['categories'][self.cat_idx]
        result=self.dialog('Redenumește categoria',[('name','Numele categoriei')],cat)
        if result:cat['name']=result['name'];self.commit()
    def delete_category(self):
        if not self.get_cat():return
        cat=self.data['categories'][self.cat_idx]
        if messagebox.askyesno('Confirmă ștergerea',f'Ștergi categoria „{cat["name"]}” și toate zilele și cântările din ea?',icon='warning',parent=self):
            del self.data['categories'][self.cat_idx];self.cat_idx=None;self.day_idx=None;self.commit()

    def add_day(self):
        if not self.get_cat():return
        result=self.dialog('Zi nouă',[('name','Numele zilei'),('date','Data (ZZ.LL.AAAA)'),('program','Programul')],{'name':self.day_name(),'date':date.today().strftime('%d.%m.%Y'),'program':'Dimineață'})
        if result:
            self.days().append({'name':result['name'],'date':result['date'],'program':result['program'],'songs':[]})
            self.day_idx=len(self.days())-1;self.commit()
    def day_name(self):
        names={0:'Luni',1:'Marți',2:'Miercuri',3:'Joi',4:'Vineri',5:'Sâmbătă',6:'Duminică'}
        return names[date.today().weekday()]
    def edit_day(self,event=None):
        if not self.get_day():return
        day=self.days()[self.day_idx]
        result=self.dialog('Editează ziua',[('name','Numele zilei'),('date','Data (ZZ.LL.AAAA)'),('program','Numele programului')],{'name':day['name'],'date':day['date'],'program':day.get('program','Program principal')})
        if result:day.update(result);self.commit()
    def delete_day(self):
        if not self.get_day():return
        day=self.days()[self.day_idx]
        if messagebox.askyesno('Confirmă ștergerea',f'Ștergi programul „{day.get("program", "Program principal")}” din {day["name"]} ({day["date"]}) și toate cântările sale?',icon='warning',parent=self):
            del self.days()[self.day_idx];self.day_idx=None;self.commit()

    def song_drag_start(self, event):
        # Mutarea este dezactivată la căutare, pentru a nu schimba ordinea ascunsă.
        self._song_drag = None
        if self.query.get().strip() or self.cat_idx is None or self.day_idx is None:
            return
        if self.song_tree.identify_region(event.x,event.y) != 'cell':
            return
        row = self.song_tree.identify_row(event.y)
        if row:
            self._song_drag = (self.cat_idx, self.day_idx, int(row), event.x_root, event.y_root)

    def song_drag_end(self, event):
        drag = getattr(self, '_song_drag', None)
        self._song_drag = None
        if not drag or self.query.get().strip():
            return
        cat, day, source, start_x, start_y = drag
        if cat != self.cat_idx or day != self.day_idx:
            return
        if abs(event.y_root - start_y) < 8:
            return
        dest_row = self.song_tree.identify_row(event.y)
        if not dest_row:
            return
        target = int(dest_row)
        songs = self.songs()
        if source == target or not (0 <= source < len(songs) and 0 <= target < len(songs)):
            return
        item = songs.pop(source)
        songs.insert(target, item)
        self.commit()
        self.song_tree.selection_set(str(target))
        self.song_tree.focus(str(target))
        self.song_tree.see(str(target))
        self.status.set('Ordinea cântărilor a fost salvată.')

    def copy_song(self):
        if not self.get_day():
            return
        idx = self.selected_song()
        if idx is None:
            return
        song = copy.deepcopy(self.songs()[idx])
        destinations = []
        for ci, category in enumerate(self.data['categories']):
            for di, day in enumerate(category['days']):
                if ci == self.cat_idx and di == self.day_idx:
                    continue
                label = f"{category['name']} / {day['name']} ({day['date']}) / {day.get('program','Program principal')}"
                destinations.append((label, ci, di))
        if not destinations:
            messagebox.showinfo('Copiere', 'Adaugă mai întâi o altă zi în care să copiezi cântarea.', parent=self)
            return
        window = tk.Toplevel(self)
        window.title('Copiază cântarea în altă zi')
        window.transient(self)
        window.geometry('540x360')
        window.configure(bg=self.colors['panel'])
        ttk.Label(window, text=f"Copiază: {song['number']} — {song['title']}", wraplength=490).pack(padx=16,pady=(16,8),anchor='w')
        ttk.Label(window, text='Alege ziua de destinație:').pack(padx=16,anchor='w')
        listing = tk.Listbox(window, exportselection=False, font=('Segoe UI',10))
        listing.pack(fill='both',expand=True,padx=16,pady=10)
        for label, _, _ in destinations:
            listing.insert('end',label)
        listing.selection_set(0)
        def perform():
            selected = listing.curselection()
            if not selected:
                return
            _, ci, di = destinations[selected[0]]
            self.data['categories'][ci]['days'][di]['songs'].append(copy.deepcopy(song))
            self.persist()
            window.destroy()
            self.status.set('Cântarea a fost copiată în ziua selectată.')
            messagebox.showinfo('Copiere reușită','Cântarea a fost copiată. Originalul a rămas neschimbat.',parent=self)
        ttk.Button(window,text='Copiază cântarea',command=perform,style='Accent.TButton').pack(pady=(0,16))
        window.grab_set()
        window.focus_set()

    def song_history(self):
        if not self.get_day():
            return
        idx = self.selected_song()
        if idx is None:
            return
        song = self.songs()[idx]
        number = song.get('number','').strip().casefold()
        title = song.get('title','').strip().casefold()
        matches = []
        for category in self.data['categories']:
            for day in category['days']:
                for entry in day['songs']:
                    if (number and entry.get('number','').strip().casefold() == number
                        and entry.get('title','').strip().casefold() == title):
                        matches.append((day.get('date',''), category['name'], f"{day['name']} / {day.get('program','Program principal')}"))
        def sort_key(entry):
            try:
                return datetime.strptime(entry[0], '%d.%m.%Y')
            except ValueError:
                return datetime.min
        matches.sort(key=sort_key, reverse=True)
        window = tk.Toplevel(self)
        window.title('Istoricul programărilor')
        window.transient(self)
        window.geometry('610x420')
        window.configure(bg=self.colors['panel'])
        ttk.Label(window,text=f"Istoric: {song['number']} — {song['title']}",wraplength=560).pack(padx=16,pady=(16,6),anchor='w')
        ttk.Label(window,text=f"Programată de {len(matches)} ori. Datele arată programările, nu confirmă interpretarea.",wraplength=560).pack(padx=16,pady=(0,8),anchor='w')
        tree = ttk.Treeview(window,columns=('date','category','day'),show='headings')
        for key, heading, width in [('date','Data',120),('category','Categorie',190),('day','Zi',180)]:
            tree.heading(key,text=heading)
            tree.column(key,width=width,anchor='center')
        tree.pack(fill='both',expand=True,padx=16,pady=(0,16))
        for entry in matches:
            tree.insert('','end',values=entry)
        window.grab_set()
        window.focus_set()

    def add_song(self):
        if not self.get_day():return
        result=self.dialog('Cântare nouă',[('number','Numărul cântării'),('title','Titlul cântării'),('link','Link (opțional, https://...)')],optional_keys=('link',))
        if result:self.songs().append(result);self.commit()
    def edit_song(self,event=None):
        if not self.get_day():return
        idx=self.selected_song()
        if idx is None:return
        song=self.songs()[idx]
        result=self.dialog('Editează cântarea',[('number','Numărul cântării'),('title','Titlul cântării'),('link','Link (opțional, https://...)')],song,optional_keys=('link',))
        if result:song.update(result);self.commit()
    def song_double_click(self,event):
        row=self.song_tree.identify_row(event.y)
        col=self.song_tree.identify_column(event.x)
        if not row:return
        self.song_tree.selection_set(row)
        if col=='#3':
            self.open_song_link()
        else:
            self.edit_song()

    def open_song_link(self):
        if not self.get_day():return
        idx=self.selected_song()
        if idx is None:
            messagebox.showinfo('Selectează cântarea','Selectează o cântare din tabel.',parent=self)
            return
        link=self.songs()[idx].get('link','').strip()
        if not link:
            messagebox.showinfo('Fără link','Această cântare nu are încă un link. Folosește butonul Editează.',parent=self)
            return
        parsed=urlparse(link)
        if parsed.scheme.lower() not in ('https','http') or not parsed.netloc:
            messagebox.showwarning('Link invalid','Linkul trebuie să înceapă cu https:// sau http://.',parent=self)
            return
        chrome_candidates = [
            shutil.which('chrome'),
            os.path.join(os.environ.get('PROGRAMFILES', ''), 'Google', 'Chrome', 'Application', 'chrome.exe'),
            os.path.join(os.environ.get('PROGRAMFILES(X86)', ''), 'Google', 'Chrome', 'Application', 'chrome.exe'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Google', 'Chrome', 'Application', 'chrome.exe'),
        ]
        chrome = next((path for path in chrome_candidates if path and os.path.isfile(path)), None)
        if chrome:
            try:
                subprocess.Popen([chrome, link])
            except OSError as exc:
                messagebox.showerror('Eroare Chrome', f'Nu am putut deschide Chrome:\n{exc}', parent=self)
        else:
            messagebox.showwarning('Chrome negăsit', 'Google Chrome nu a fost găsit pe acest calculator. Voi încerca browserul implicit.', parent=self)
            webbrowser.open(link)

    def delete_song(self):
        if not self.get_day():return
        idx=self.selected_song()
        if idx is None:return
        song=self.songs()[idx]
        if messagebox.askyesno('Confirmă ștergerea',f'Ștergi cântarea „{song["title"]}” (nr. {song["number"]})?',icon='warning',parent=self):
            del self.songs()[idx];self.commit()

    def focus_search(self,event=None):
        self.search_entry.focus_set();self.search_entry.select_range(0,'end');return 'break'
    def next_result(self,event=None,direction=1):
        if not self.search_results:return 'break'
        self.search_pos=(self.search_pos+direction)%len(self.search_results)
        item=self.search_results[self.search_pos]
        self.song_tree.selection_set(item);self.song_tree.focus(item);self.song_tree.see(item)
        return 'break'

    def toggle_theme(self):
        self.data['theme']='light' if self.data['theme']=='dark' else 'dark'
        self.colors=PALETTES[self.data['theme']]
        self.persist()
        for child in self.winfo_children():child.destroy()
        self.setup_styles();self.build_ui();self.render_all()

    def export_json(self):
        filename=filedialog.asksaveasfilename(parent=self,title='Exportă backup',defaultextension='.json',filetypes=[('Fișiere JSON','*.json')],initialfile=f'cantari-backup-{date.today().isoformat()}.json')
        if not filename:return
        try:
            Path(filename).write_text(json.dumps(self.data,ensure_ascii=False,indent=2),encoding='utf-8')
            messagebox.showinfo('Backup creat','Fișierul JSON a fost exportat cu succes.',parent=self)
        except Exception as exc:messagebox.showerror('Eroare export',str(exc),parent=self)
    def import_json(self):
        filename=filedialog.askopenfilename(parent=self,title='Importă backup',filetypes=[('Fișiere JSON','*.json')])
        if not filename:return
        try:imported=normalize(json.loads(Path(filename).read_text(encoding='utf-8')))
        except Exception as exc:messagebox.showerror('Fișier invalid',str(exc),parent=self);return
        if not messagebox.askyesno('Confirmă importul','Importul înlocuiește toate categoriile și cântările actuale. Continui?',icon='warning',parent=self):return
        self.data=imported;self.readonly=False;self.cat_idx=None;self.day_idx=None
        self.colors=PALETTES[self.data['theme']]
        self.persist()
        for child in self.winfo_children():child.destroy()
        self.setup_styles();self.build_ui();self.render_all()

if __name__=='__main__':
    App().mainloop()

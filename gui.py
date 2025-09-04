# --- ISTRUZIONI DI INSTALLAZIONE ---
# Esegui: pip install beautifulsoup4 pyppeteer aiohttp
import tkinter as tk
from tkinter import ttk, scrolledtext
import json
import multiprocessing as mp
import threading
import supreme_bot
import sys
import queue
import asyncio
import os
from datetime import datetime, timedelta

class QueueWriter:
    def __init__(self, queue): self.queue = queue
    def write(self, text): self.queue.put(text)
    def flush(self): pass

def run_bot_process(log_queue, keywords, color, size, proxy, show_browser):
    sys.stdout = QueueWriter(log_queue)
    sys.stderr = QueueWriter(log_queue)
    try:
        asyncio.run(supreme_bot.main(product_keywords=keywords, color=color, size=size, proxy=proxy, show_browser=show_browser))
    except Exception as e:
        print(f"ERRORE FATALE NEL PROCESSO DEL BOT: {e}")

class SupremeBotGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Supreme Bot"); self.geometry("850x750")
        style = ttk.Style(self); style.configure("TLabel", padding=5, font=('Helvetica', 10)); style.configure("TEntry", padding=5, font=('Helvetica', 10)); style.configure("TButton", padding=5, font=('Helvetica', 10, 'bold')); style.configure("TFrame", padding=10); style.configure("TLabelframe", padding=10); style.configure("TLabelframe.Label", font=('Helvetica', 11, 'bold'))
        main_frame = ttk.Frame(self, padding="10"); main_frame.pack(expand=True, fill=tk.BOTH)
        config_frame = ttk.Frame(main_frame); config_frame.pack(fill=tk.X, pady=5)

        task_frame = ttk.Labelframe(config_frame, text="Task, Prodotto e Scheduling"); task_frame.pack(fill=tk.X, expand=True, side=tk.LEFT, padx=5, anchor="n")
        self.create_labeled_entry(task_frame, "Parole Chiave (AND)", "keywords_entry", note="(Tutte le parole devono essere nel titolo)")
        self.create_labeled_entry(task_frame, "Colore", "color_entry")
        self.create_labeled_entry(task_frame, "Taglia", "size_entry")
        self.create_labeled_entry(task_frame, "Proxy (opzionale)", "proxy_entry")
        self.create_labeled_entry(task_frame, "Data (YYYY-MM-DD)", "schedule_date_entry")
        self.create_labeled_entry(task_frame, "Ora (HH:MM:SS)", "schedule_time_entry")
        self.show_browser_var = tk.BooleanVar(); self.create_check_button(task_frame, "Mostra Browser (lento)", self.show_browser_var)

        delivery_frame = ttk.Labelframe(config_frame, text="Contatto e Spedizione"); delivery_frame.pack(fill=tk.X, expand=True, side=tk.LEFT, padx=5, anchor="n")
        self.create_labeled_entry(delivery_frame, "Email", "email_entry"); self.create_labeled_entry(delivery_frame, "Nome", "first_name_entry"); self.create_labeled_entry(delivery_frame, "Cognome", "last_name_entry"); self.create_labeled_entry(delivery_frame, "Indirizzo", "address_entry"); self.create_labeled_entry(delivery_frame, "Apt/Suite", "apt_entry"); self.create_labeled_entry(delivery_frame, "Codice Paese (IT, US)", "country_code_entry"); self.create_labeled_entry(delivery_frame, "CAP", "postal_code_entry"); self.create_labeled_entry(delivery_frame, "Città", "city_entry"); self.create_labeled_entry(delivery_frame, "Provincia (Sigla, es. PD)", "province_code_entry"); self.create_labeled_entry(delivery_frame, "Telefono", "phone_entry")

        payment_frame = ttk.Labelframe(config_frame, text="Dettagli Pagamento"); payment_frame.pack(fill=tk.X, expand=True, side=tk.LEFT, padx=5, anchor="n")
        self.create_labeled_entry(payment_frame, "Nome su Carta", "card_name_entry"); self.create_labeled_entry(payment_frame, "Numero Carta", "card_num_entry"); self.create_labeled_entry(payment_frame, "Scadenza (MM/YY)", "card_exp_entry"); self.create_labeled_entry(payment_frame, "CVV", "card_cvv_entry")

        action_frame = ttk.Frame(main_frame); action_frame.pack(fill=tk.X, pady=10)
        self.save_button = ttk.Button(action_frame, text="Salva Config", command=self.save_config); self.save_button.pack(side=tk.LEFT, padx=5)
        self.load_button = ttk.Button(action_frame, text="Carica Config", command=self.load_config); self.load_button.pack(side=tk.LEFT, padx=5)
        self.start_button = ttk.Button(action_frame, text="Avvia/Programma Bot", command=self.start_or_schedule_bot); self.start_button.pack(side=tk.RIGHT, padx=5)

        log_frame = ttk.Labelframe(main_frame, text="Log"); log_frame.pack(expand=True, fill=tk.BOTH, pady=5)
        self.log_area = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=15, font=('Courier New', 9), bg="#f0f0f0"); self.log_area.pack(expand=True, fill=tk.BOTH); self.log_area.configure(state='disabled')

        self.log_queue = mp.Queue(); self.after(100, self.periodic_log_check)

    def create_widget_row(self, parent, label_text):
        frame = ttk.Frame(parent); frame.pack(fill=tk.X, pady=2, padx=5)
        label = ttk.Label(frame, text=label_text, width=25); label.pack(side=tk.LEFT, anchor="w")
        return frame

    def create_labeled_entry(self, parent, label_text, var_name, note=None):
        frame = self.create_widget_row(parent, label_text)
        entry = ttk.Entry(frame); entry.pack(side=tk.RIGHT, expand=True, fill=tk.X)
        setattr(self, var_name, entry)
        if note:
            note_label = ttk.Label(frame, text=note, font=('Helvetica', 8, 'italic'))
            note_label.pack(side=tk.RIGHT)

    def create_check_button(self, parent, label_text, var):
        frame = self.create_widget_row(parent, label_text)
        check = ttk.Checkbutton(frame, variable=var); check.pack(side=tk.RIGHT)

    def save_config(self):
        self.log("Salvataggio configurazione...\n")
        config = {"task_details": {}, "contact_details": {}, "delivery_address": {}, "payment_details": {}}
        for key, entry in self.__dict__.items():
            if "_entry" in key:
                field_name = key.replace("_entry", "")
                for cat in config:
                    if hasattr(self, f"{field_name}_entry"):
                        if cat == "task_details" and field_name in ["keywords", "color", "size", "proxy", "schedule_date", "schedule_time"]: config[cat][field_name] = entry.get()
                        elif cat == "contact_details" and field_name == "email": config[cat][field_name] = entry.get()
                        elif cat == "delivery_address" and field_name in ["first_name", "last_name", "address", "apt_suite_etc", "city", "country_code", "province_code", "postal_code", "phone"]: config[cat][field_name] = entry.get()
                        elif cat == "payment_details" and field_name in ["card_name", "card_num", "card_exp", "card_cvv"]: config[cat][field_name.replace('card_','')] = entry.get()
        config["task_details"]["show_browser"] = self.show_browser_var.get()
        try:
            with open("config.json", "w") as f: json.dump(config, f, indent=2)
            self.log("Configurazione salvata!\n")
        except Exception as e: self.log(f"Errore salvataggio: {e}\n")

    def load_config(self):
        self.log("Caricamento configurazione...\n")
        try:
            with open("config.json", "r") as f: config = json.load(f)
            for cat, details in config.items():
                for key, val in details.items():
                    entry_name = f"{key}_entry"
                    if key in ["name", "number", "exp", "cvv"]: entry_name = f"card_{key}_entry" # Handle payment details prefix
                    if hasattr(self, entry_name):
                        entry = getattr(self, entry_name)
                        entry.delete(0, tk.END); entry.insert(0, val or "")
            self.show_browser_var.set(config.get("task_details", {}).get("show_browser", False))
            self.log("Configurazione caricata!\n")
        except FileNotFoundError: self.log("ERRORE: 'config.json' non trovato.\n")
        except Exception as e: self.log(f"Errore caricamento: {e}\n")

    def start_or_schedule_bot(self):
        date_str = self.schedule_date_entry.get()
        time_str = self.schedule_time_entry.get()

        if date_str and time_str:
            try:
                schedule_dt_str = f"{date_str} {time_str}"
                schedule_dt = datetime.strptime(schedule_dt_str, "%Y-%m-%d %H:%M:%S")
                now = datetime.now()
                delay_seconds = (schedule_dt - now).total_seconds()

                if delay_seconds < 0:
                    self.log("ERRORE: La data e l'ora programmate sono nel passato.\n")
                    return

                self.log(f"Bot programmato per le {schedule_dt_str}. Attesa...\n")
                self.after(int(delay_seconds * 1000), self.run_bot_task)
            except ValueError:
                self.log("ERRORE: Formato data/ora non valido. Usa YYYY-MM-DD e HH:MM:SS.\n")
        else:
            self.run_bot_task()

    def run_bot_task(self):
        self.log("--- Avvio Bot ---\n"); self.start_button.config(state=tk.DISABLED)
        if not os.path.exists("config.json"):
            self.log("ERRORE: 'config.json' non trovato. Salva prima la configurazione.\n"); self.start_button.config(state=tk.NORMAL); return
        try:
            keywords = [k.strip() for k in self.keywords_entry.get().split(',')];
            if not all(keywords): raise ValueError("Le parole chiave sono obbligatorie.")
            args = (self.log_queue, keywords, self.color_entry.get() or None, self.size_entry.get() or None, self.proxy_entry.get() or None, self.show_browser_var.get())
            process = mp.Process(target=run_bot_process, args=args, daemon=True); process.start()
            threading.Thread(target=self.wait_for_process, args=(process,), daemon=True).start()
        except Exception as e:
            self.log(f"Errore avvio bot: {e}\n"); self.start_button.config(state=tk.NORMAL)

    def wait_for_process(self, process):
        process.join(); self.after(0, self.enable_buttons)

    def enable_buttons(self): self.start_button.config(state=tk.NORMAL)

    def periodic_log_check(self):
        while not self.log_queue.empty():
            try: self.log(self.log_queue.get_nowait(), end='')
            except queue.Empty: pass
        self.after(100, self.periodic_log_check)

    def log(self, message, end="\n"):
        self.log_area.configure(state='normal'); self.log_area.insert(tk.END, message + end); self.log_area.configure(state='disabled'); self.log_area.see(tk.END)

if __name__ == "__main__":
    app = SupremeBotGUI()
    app.mainloop()

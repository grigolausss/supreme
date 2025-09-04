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
from datetime import datetime

class QueueWriter:
    def __init__(self, queue): self.queue = queue
    def write(self, text): self.queue.put(text)
    def flush(self): pass

def run_bot_process(log_queue, keywords, color, size, proxy, show_browser):
    sys.stdout = QueueWriter(log_queue); sys.stderr = QueueWriter(log_queue)
    try:
        asyncio.run(supreme_bot.main(product_keywords=keywords, color=color, size=size, proxy=proxy, show_browser=show_browser))
    except Exception as e:
        print(f"ERRORE FATALE NEL PROCESSO DEL BOT: {e}")

class SupremeBotGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Supreme Bot"); self.geometry("850x700")
        self.bot_running = False
        style = ttk.Style(self); style.configure("TLabel", padding=5, font=('Helvetica', 10)); style.configure("TEntry", padding=5, font=('Helvetica', 10)); style.configure("TButton", padding=5, font=('Helvetica', 10, 'bold')); style.configure("TFrame", padding=10); style.configure("TLabelframe", padding=10); style.configure("TLabelframe.Label", font=('Helvetica', 11, 'bold'))
        main_frame = ttk.Frame(self, padding="10"); main_frame.pack(expand=True, fill=tk.BOTH)
        config_frame = ttk.Frame(main_frame); config_frame.pack(fill=tk.X, pady=5)
        task_frame = ttk.Labelframe(config_frame, text="Task, Prodotto e Scheduling"); task_frame.pack(fill=tk.X, expand=True, side=tk.LEFT, padx=5, anchor="n")
        self.create_labeled_entry(task_frame, "Parole Chiave (AND)", "keywords_entry", note="(Tutte le parole devono essere nel titolo)")
        self.create_labeled_entry(task_frame, "Colore", "color_entry"); self.create_labeled_entry(task_frame, "Taglia", "size_entry"); self.create_labeled_entry(task_frame, "Proxy (opzionale)", "proxy_entry"); self.create_labeled_entry(task_frame, "Data (YYYY-MM-DD)", "schedule_date_entry"); self.create_labeled_entry(task_frame, "Ora (HH:MM:SS)", "schedule_time_entry")
        self.show_browser_var = tk.BooleanVar(); self.create_check_button(task_frame, "Mostra Browser (lento)", self.show_browser_var)
        delivery_frame = ttk.Labelframe(config_frame, text="Contatto e Spedizione"); delivery_frame.pack(fill=tk.X, expand=True, side=tk.LEFT, padx=5, anchor="n")
        self.create_labeled_entry(delivery_frame, "Email", "email_entry"); self.create_labeled_entry(delivery_frame, "Nome", "first_name_entry"); self.create_labeled_entry(delivery_frame, "Cognome", "last_name_entry"); self.create_labeled_entry(delivery_frame, "Indirizzo", "address_entry"); self.create_labeled_entry(delivery_frame, "Apt/Suite", "apt_entry"); self.create_labeled_entry(delivery_frame, "Codice Paese (IT, US)", "country_code_entry"); self.create_labeled_entry(delivery_frame, "CAP", "postal_code_entry"); self.create_labeled_entry(delivery_frame, "Città", "city_entry"); self.create_labeled_entry(delivery_frame, "Provincia (Sigla, es. PD)", "province_code_entry"); self.create_labeled_entry(delivery_frame, "Telefono", "phone_entry")
        payment_frame = ttk.Labelframe(config_frame, text="Dettagli Pagamento"); payment_frame.pack(fill=tk.X, expand=True, side=tk.LEFT, padx=5, anchor="n")
        self.create_labeled_entry(payment_frame, "Nome su Carta", "card_name_entry"); self.create_labeled_entry(payment_frame, "Numero Carta", "card_num_entry"); self.create_labeled_entry(payment_frame, "Scadenza (MM/YY)", "card_exp_entry"); self.create_labeled_entry(payment_frame, "CVV", "card_cvv_entry")
        action_frame = ttk.Frame(main_frame); action_frame.pack(fill=tk.X, pady=10)
        self.save_button = ttk.Button(action_frame, text="Salva Config", command=self.save_config); self.save_button.pack(side=tk.LEFT, padx=5)
        self.load_button = ttk.Button(action_frame, text="Carica Config", command=self.load_config); self.load_button.pack(side=tk.LEFT, padx=5)
        self.start_button = ttk.Button(action_frame, text="Avvia/Programma", command=self.start_or_schedule_bot); self.start_button.pack(side=tk.RIGHT, padx=5)
        log_frame = ttk.Labelframe(main_frame, text="Log"); log_frame.pack(expand=True, fill=tk.BOTH, pady=5)
        self.log_area = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=15, font=('Courier New', 9), bg="#f0f0f0"); self.log_area.pack(expand=True, fill=tk.BOTH); self.log_area.configure(state='disabled')
        self.log_queue = mp.Queue(); self.after(100, self.periodic_log_check)

    def create_widget_row(self, parent, label_text):
        frame = ttk.Frame(parent); frame.pack(fill=tk.X, pady=2, padx=5)
        label = ttk.Label(frame, text=label_text, width=25); label.pack(side=tk.LEFT, anchor="w")
        return frame

    def create_labeled_entry(self, parent, label_text, var_name, note=None):
        frame = self.create_widget_row(parent, label_text)
        sub_frame = ttk.Frame(frame)
        sub_frame.pack(side=tk.RIGHT, expand=True, fill=tk.X)
        entry = ttk.Entry(sub_frame); entry.pack(fill=tk.X)
        setattr(self, var_name, entry)
        if note:
            note_label = ttk.Label(sub_frame, text=note, font=('Helvetica', 8, 'italic')); note_label.pack(anchor='w')

    def create_check_button(self, parent, label_text, var):
        frame = self.create_widget_row(parent, label_text)
        check = ttk.Checkbutton(frame, variable=var); check.pack(side=tk.RIGHT)

    def save_config(self):
        self.log("Salvataggio configurazione...\n")
        config_data = {
            "task_details": {"keywords": self.keywords_entry.get(), "color": self.color_entry.get(), "size": self.size_entry.get(), "proxy": self.proxy_entry.get(), "schedule_date": self.schedule_date_entry.get(), "schedule_time": self.schedule_time_entry.get(), "show_browser": self.show_browser_var.get()},
            "contact_details": {"email": self.email_entry.get()},
            "delivery_address": {"first_name": self.first_name_entry.get(), "last_name": self.last_name_entry.get(), "address": self.address_entry.get(), "apt_suite_etc": self.apt_entry.get(), "city": self.city_entry.get(), "country_code": self.country_code_entry.get(), "province_code": self.province_code_entry.get(), "postal_code": self.postal_code_entry.get(), "phone": self.phone_entry.get()},
            "payment_details": {"name_on_card": self.card_name_entry.get(), "card_number": self.card_num_entry.get(), "expiration_date": self.card_exp_entry.get(), "security_code": self.card_cvv_entry.get()}
        }
        try:
            with open("config.json", "w") as f: json.dump(config_data, f, indent=2)
            self.log("Configurazione salvata!\n")
        except Exception as e: self.log(f"Errore salvataggio: {e}\n")

    def load_config(self):
        self.log("Caricamento configurazione...\n")
        try:
            if not os.path.exists("config.json"):
                self.log("Nessun file config.json trovato. Inserisci i dati e salva.\n")
                return
            with open("config.json", "r") as f: config_data = json.load(f)

            task = config_data.get("task_details", {}); delivery = config_data.get("delivery_address", {}); payment = config_data.get("payment_details", {}); contact = config_data.get("contact_details", {})

            entries = {
                "keywords": self.keywords_entry, "color": self.color_entry, "size": self.size_entry,
                "proxy": self.proxy_entry, "schedule_date": self.schedule_date_entry, "schedule_time": self.schedule_time_entry,
                "email": self.email_entry, "first_name": self.first_name_entry, "last_name": self.last_name_entry,
                "address": self.address_entry, "apt_suite_etc": self.apt_entry, "city": self.city_entry,
                "country_code": self.country_code_entry, "province_code": self.province_code_entry,
                "postal_code": self.postal_code_entry, "phone": self.phone_entry,
                "name_on_card": self.card_name_entry, "card_number": self.card_num_entry,
                "expiration_date": self.card_exp_entry, "security_code": self.card_cvv_entry
            }

            all_details = {**task, **delivery, **payment, **contact}
            for key, entry_widget in entries.items():
                entry_widget.delete(0, tk.END)
                entry_widget.insert(0, str(all_details.get(key, "")))

            self.show_browser_var.set(task.get("show_browser", False))
            self.log("Configurazione caricata!\n")
        except Exception as e: self.log(f"Errore caricamento: {e}\n")

    def start_or_schedule_bot(self):
        if self.bot_running:
            self.signal_resume()
            return

        date_str = self.schedule_date_entry.get(); time_str = self.schedule_time_entry.get()
        if date_str and time_str:
            try:
                schedule_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")
                delay_seconds = (schedule_dt - datetime.now()).total_seconds()
                if delay_seconds < 0: self.log("ERRORE: Orario programmato è nel passato.\n"); return
                self.log(f"Bot programmato per le {schedule_dt}. Attesa...\n")
                self.after(int(delay_seconds * 1000), self.run_bot_task)
            except ValueError: self.log("ERRORE: Formato data/ora non valido.\n")
        else:
            self.run_bot_task()

    def run_bot_task(self):
        self.log("--- Avvio Bot ---\n"); self.start_button.config(text="In Esecuzione...")
        self.start_button.config(state=tk.DISABLED); self.bot_running = True
        if not os.path.exists("config.json"):
            self.log("ERRORE: 'config.json' non trovato.\n"); self.reset_ui_state(); return
        try:
            keywords = [k.strip() for k in self.keywords_entry.get().split(',')];
            if not all(keywords): raise ValueError("Parole chiave obbligatorie.")
            args = (self.log_queue, keywords, self.color_entry.get() or None, self.size_entry.get() or None, self.proxy_entry.get() or None, self.show_browser_var.get())
            process = mp.Process(target=run_bot_process, args=args, daemon=True); process.start()
            threading.Thread(target=self.wait_for_process, args=(process,), daemon=True).start()
        except Exception as e:
            self.log(f"Errore avvio bot: {e}\n"); self.reset_ui_state()

    def signal_resume(self):
        self.log("--- Segnale di Continuazione Inviato ---\n")
        with open("resume_signal.txt", "w") as f: f.write("resume")
        self.start_button.config(text="In Esecuzione...")
        self.start_button.config(state=tk.DISABLED)

    def wait_for_process(self, process):
        process.join(); self.after(0, self.reset_ui_state)

    def reset_ui_state(self):
        self.bot_running = False
        self.start_button.config(state=tk.NORMAL); self.start_button.config(text="Avvia/Programma")

    def periodic_log_check(self):
        while not self.log_queue.empty():
            try:
                line = self.log_queue.get_nowait()
                if "PAUSA: " in line:
                    self.start_button.config(state=tk.NORMAL)
                    self.start_button.config(text="CONTINUA")
                self.log(line, end='')
            except queue.Empty: pass
        self.after(100, self.periodic_log_check)

    def log(self, message, end="\n"):
        self.log_area.configure(state='normal'); self.log_area.insert(tk.END, message + end); self.log_area.configure(state='disabled'); self.log_area.see(tk.END)

if __name__ == "__main__":
    app = SupremeBotGUI()
    app.mainloop()

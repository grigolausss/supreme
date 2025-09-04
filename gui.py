import tkinter as tk
from tkinter import ttk, scrolledtext
import json
import threading
import supreme_bot
import sys
import queue
import asyncio
import os

class QueueWriter:
    """Una classe simile a un file per reindirizzare l'output a una coda."""
    def __init__(self, queue):
        self.queue = queue
    def write(self, text):
        self.queue.put(text)
    def flush(self):
        pass

class SupremeBotGUI(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Supreme Bot")
        self.geometry("850x750")

        style = ttk.Style(self)
        style.configure("TLabel", padding=5, font=('Helvetica', 10))
        style.configure("TEntry", padding=5, font=('Helvetica', 10))
        style.configure("TButton", padding=5, font=('Helvetica', 10, 'bold'))
        style.configure("TFrame", padding=10)
        style.configure("TLabelframe", padding=10)
        style.configure("TLabelframe.Label", font=('Helvetica', 11, 'bold'))

        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(expand=True, fill=tk.BOTH)
        config_frame = ttk.Frame(main_frame)
        config_frame.pack(fill=tk.X, pady=5)

        task_frame = ttk.Labelframe(config_frame, text="Task e Prodotto")
        task_frame.pack(fill=tk.X, expand=True, side=tk.LEFT, padx=5, anchor="n")
        self.create_labeled_entry(task_frame, "Parole Chiave (virgola)", "keywords_entry")
        self.create_labeled_entry(task_frame, "Colore", "color_entry")
        self.create_labeled_entry(task_frame, "Taglia", "size_entry")
        self.create_labeled_entry(task_frame, "Proxy (opzionale)", "proxy_entry")
        self.mode_var = tk.StringVar(value="Normale")
        self.create_option_menu(task_frame, "Modalità", self.mode_var, ["Normale", "Sicura"])
        self.show_browser_var = tk.BooleanVar()
        self.create_check_button(task_frame, "Mostra Browser (lento)", self.show_browser_var)

        delivery_frame = ttk.Labelframe(config_frame, text="Contatto e Spedizione")
        delivery_frame.pack(fill=tk.X, expand=True, side=tk.LEFT, padx=5, anchor="n")
        self.create_labeled_entry(delivery_frame, "Email", "email_entry")
        self.create_labeled_entry(delivery_frame, "Nome", "first_name_entry")
        self.create_labeled_entry(delivery_frame, "Cognome", "last_name_entry")
        self.create_labeled_entry(delivery_frame, "Indirizzo", "address_entry")
        self.create_labeled_entry(delivery_frame, "Apt/Suite", "apt_entry")
        self.create_labeled_entry(delivery_frame, "Paese (es. IT, US)", "country_code_entry")
        self.create_labeled_entry(delivery_frame, "CAP", "postal_code_entry")
        self.create_labeled_entry(delivery_frame, "Città", "city_entry")
        self.create_labeled_entry(delivery_frame, "Provincia (es. PD, MI)", "province_code_entry")
        self.create_labeled_entry(delivery_frame, "Telefono", "phone_entry")

        payment_frame = ttk.Labelframe(config_frame, text="Dettagli Pagamento")
        payment_frame.pack(fill=tk.X, expand=True, side=tk.LEFT, padx=5, anchor="n")
        self.create_labeled_entry(payment_frame, "Nome su Carta", "card_name_entry")
        self.create_labeled_entry(payment_frame, "Numero Carta", "card_num_entry")
        self.create_labeled_entry(payment_frame, "Scadenza (MM/YY)", "card_exp_entry")
        self.create_labeled_entry(payment_frame, "CVV", "card_cvv_entry")

        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, pady=10)
        self.save_button = ttk.Button(action_frame, text="Salva Configurazione", command=self.save_config)
        self.save_button.pack(side=tk.LEFT, padx=5)
        self.load_button = ttk.Button(action_frame, text="Carica Configurazione", command=self.load_config)
        self.load_button.pack(side=tk.LEFT, padx=5)
        self.start_button = ttk.Button(action_frame, text="Avvia Bot", command=self.start_bot)
        self.start_button.pack(side=tk.RIGHT, padx=5)

        log_frame = ttk.Labelframe(main_frame, text="Log")
        log_frame.pack(expand=True, fill=tk.BOTH, pady=5)
        self.log_area = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=15, font=('Courier New', 9), bg="#f0f0f0")
        self.log_area.pack(expand=True, fill=tk.BOTH)
        self.log_area.configure(state='disabled')

        self.log_queue = queue.Queue()
        self.queue_writer = QueueWriter(self.log_queue)
        sys.stdout = self.queue_writer
        sys.stderr = self.queue_writer
        self.after(100, self.periodic_log_check)

    def create_widget_row(self, parent, label_text):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=2, padx=5)
        label = ttk.Label(frame, text=label_text, width=25)
        label.pack(side=tk.LEFT, anchor="w")
        return frame

    def create_labeled_entry(self, parent, label_text, entry_var_name):
        frame = self.create_widget_row(parent, label_text)
        entry = ttk.Entry(frame)
        entry.pack(side=tk.RIGHT, expand=True, fill=tk.X)
        setattr(self, entry_var_name, entry)

    def create_option_menu(self, parent, label_text, var, options):
        frame = self.create_widget_row(parent, label_text)
        menu = ttk.OptionMenu(frame, var, options[0], *options)
        menu.pack(side=tk.RIGHT, expand=True, fill=tk.X)

    def create_check_button(self, parent, label_text, var):
        frame = self.create_widget_row(parent, label_text)
        check = ttk.Checkbutton(frame, variable=var)
        check.pack(side=tk.RIGHT)

    def save_config(self):
        self.log("Salvataggio configurazione...")
        config_data = {
            "task_details": {"keywords": self.keywords_entry.get(), "color": self.color_entry.get(), "size": self.size_entry.get(), "proxy": self.proxy_entry.get(), "mode": self.mode_var.get(), "show_browser": self.show_browser_var.get()},
            "contact_details": {"email": self.email_entry.get()},
            "delivery_address": {"first_name": self.first_name_entry.get(), "last_name": self.last_name_entry.get(), "address": self.address_entry.get(), "apt_suite_etc": self.apt_entry.get(), "city": self.city_entry.get(), "country_code": self.country_code_entry.get(), "province_code": self.province_code_entry.get(), "postal_code": self.postal_code_entry.get(), "phone": self.phone_entry.get()},
            "payment_details": {"name_on_card": self.card_name_entry.get(), "card_number": self.card_num_entry.get(), "expiration_date": self.card_exp_entry.get(), "security_code": self.card_cvv_entry.get()}
        }
        try:
            with open("config.json", "w") as f:
                json.dump(config_data, f, indent=2)
            self.log("Configurazione salvata con successo!\n")
        except Exception as e:
            self.log(f"Errore salvataggio: {e}\n")

    def load_config(self):
        self.log("Caricamento configurazione...")
        try:
            with open("config.json", "r") as f:
                config_data = json.load(f)

            task = config_data.get("task_details", {}); delivery = config_data.get("delivery_address", {}); payment = config_data.get("payment_details", {}); contact = config_data.get("contact_details", {})

            for entry, val in [(self.keywords_entry, task.get("keywords")), (self.color_entry, task.get("color")), (self.size_entry, task.get("size")), (self.proxy_entry, task.get("proxy")), (self.email_entry, contact.get("email")), (self.first_name_entry, delivery.get("first_name")), (self.last_name_entry, delivery.get("last_name")), (self.address_entry, delivery.get("address")), (self.apt_entry, delivery.get("apt_suite_etc")), (self.city_entry, delivery.get("city")), (self.country_code_entry, delivery.get("country_code")), (self.province_code_entry, delivery.get("province_code")), (self.postal_code_entry, delivery.get("postal_code")), (self.phone_entry, delivery.get("phone")), (self.card_name_entry, payment.get("name_on_card")), (self.card_num_entry, payment.get("card_number")), (self.card_exp_entry, payment.get("expiration_date")), (self.card_cvv_entry, payment.get("security_code"))]:
                entry.delete(0, tk.END); entry.insert(0, val or "")

            self.mode_var.set(task.get("mode", "Normale"))
            self.show_browser_var.set(task.get("show_browser", False))
            self.log("Configurazione caricata!\n")
        except FileNotFoundError:
            self.log("ERRORE: 'config.json' non trovato.\n")
        except Exception as e:
            self.log(f"Errore caricamento: {e}\n")

    def start_bot(self):
        self.log("--- Avvio Bot ---\n")
        self.start_button.config(state=tk.DISABLED)

        if not os.path.exists("config.json"):
            self.log("ERRORE: 'config.json' non trovato. Salva prima la configurazione.\n")
            self.start_button.config(state=tk.NORMAL)
            return

        try:
            keywords = [k.strip() for k in self.keywords_entry.get().split(',')]
            if not all(keywords): raise ValueError("Le parole chiave sono obbligatorie.")

            bot_thread = threading.Thread(target=self._run_bot_thread, args=(keywords, self.color_entry.get() or None, self.size_entry.get() or None, self.proxy_entry.get() or None, self.mode_var.get(), self.show_browser_var.get()), daemon=True)
            bot_thread.start()
        except Exception as e:
            self.log(f"Errore avvio bot: {e}\n")
            self.start_button.config(state=tk.NORMAL)

    def _run_bot_thread(self, keywords, color, size, proxy, mode, show_browser):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(supreme_bot.main(product_keywords=keywords, color=color, size=size, proxy=proxy, mode=mode, show_browser=show_browser))
            self.log("\n--- Esecuzione Bot Terminata ---\n")
        except Exception as e:
            self.log(f"\nERRORE nel thread del bot: {e}\n")
        finally:
            loop.close()
            self.after(0, self.enable_buttons)

    def enable_buttons(self):
        self.start_button.config(state=tk.NORMAL)

    def periodic_log_check(self):
        while not self.log_queue.empty():
            try:
                self.log(self.log_queue.get_nowait(), end='')
            except queue.Empty: pass
        self.after(100, self.periodic_log_check)

    def log(self, message, end="\n"):
        self.log_area.configure(state='normal')
        self.log_area.insert(tk.END, message + end)
        self.log_area.configure(state='disabled')
        self.log_area.see(tk.END)

if __name__ == "__main__":
    app = SupremeBotGUI()
    app.mainloop()

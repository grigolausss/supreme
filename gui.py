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

        # --- Stile ---
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

        # --- Frame per i Dettagli del Task ---
        task_frame = ttk.Labelframe(config_frame, text="Task e Prodotto")
        task_frame.pack(fill=tk.X, expand=True, side=tk.LEFT, padx=5, anchor="n")

        self.create_labeled_entry(task_frame, "Parole Chiave (virgola)", "keywords_entry")
        self.create_labeled_entry(task_frame, "Colore", "color_entry")
        self.create_labeled_entry(task_frame, "Taglia", "size_entry")
        self.create_labeled_entry(task_frame, "Proxy (opzionale)", "proxy_entry")

        # --- Dropdown Modalità ---
        mode_frame = ttk.Frame(task_frame)
        mode_frame.pack(fill=tk.X, pady=2, padx=5)
        mode_label = ttk.Label(mode_frame, text="Modalità")
        mode_label.pack(side=tk.LEFT, anchor="w")
        self.mode_var = tk.StringVar(value="Normale")
        self.mode_dropdown = ttk.OptionMenu(mode_frame, self.mode_var, "Normale", "Normale", "Sicura")
        self.mode_dropdown.pack(side=tk.RIGHT, expand=True, fill=tk.X)

        # --- Frame Contatto e Spedizione ---
        delivery_frame = ttk.Labelframe(config_frame, text="Contatto e Spedizione")
        delivery_frame.pack(fill=tk.X, expand=True, side=tk.LEFT, padx=5, anchor="n")
        self.create_labeled_entry(delivery_frame, "Email", "email_entry")
        self.create_labeled_entry(delivery_frame, "Nome", "first_name_entry")
        self.create_labeled_entry(delivery_frame, "Cognome", "last_name_entry")
        self.create_labeled_entry(delivery_frame, "Indirizzo", "address_entry")
        self.create_labeled_entry(delivery_frame, "Apt/Suite", "apt_entry")
        self.create_labeled_entry(delivery_frame, "Città", "city_entry")
        self.create_labeled_entry(delivery_frame, "Paese (2 lettere)", "country_code_entry")
        self.create_labeled_entry(delivery_frame, "Stato/Prov. (2 lettere)", "state_code_entry")
        self.create_labeled_entry(delivery_frame, "CAP", "postal_code_entry")
        self.create_labeled_entry(delivery_frame, "Telefono", "phone_entry")

        # --- Frame Pagamento ---
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

    def create_labeled_entry(self, parent, label_text, entry_var_name):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=2, padx=5)
        label = ttk.Label(frame, text=label_text, width=25)
        label.pack(side=tk.LEFT, anchor="w")
        entry = ttk.Entry(frame)
        entry.pack(side=tk.RIGHT, expand=True, fill=tk.X)
        setattr(self, entry_var_name, entry)

    def save_config(self):
        self.log("Salvataggio della configurazione in config.json...")
        config_data = {
            "task_details": {
                "keywords": self.keywords_entry.get(),
                "color": self.color_entry.get(),
                "size": self.size_entry.get(),
                "proxy": self.proxy_entry.get(),
                "mode": self.mode_var.get()
            },
            "contact_details": {"email": self.email_entry.get()},
            "delivery_address": {
                "first_name": self.first_name_entry.get(),
                "last_name": self.last_name_entry.get(),
                "address": self.address_entry.get(),
                "apt_suite_etc": self.apt_entry.get(),
                "city": self.city_entry.get(),
                "country_code": self.country_code_entry.get(),
                "state_code": self.state_code_entry.get(),
                "postal_code": self.postal_code_entry.get(),
                "phone": self.phone_entry.get()
            },
            "payment_details": {
                "name_on_card": self.card_name_entry.get(),
                "card_number": self.card_num_entry.get(),
                "expiration_date": self.card_exp_entry.get(),
                "security_code": self.card_cvv_entry.get()
            }
        }
        try:
            with open("config.json", "w") as f:
                json.dump(config_data, f, indent=2)
            self.log("Configurazione salvata con successo!")
        except Exception as e:
            self.log(f"Errore durante il salvataggio della configurazione: {e}")

    def load_config(self):
        self.log("Caricamento della configurazione da config.json...")
        try:
            with open("config.json", "r") as f:
                config_data = json.load(f)

            # Popola i campi della GUI
            task = config_data.get("task_details", {})
            self.keywords_entry.delete(0, tk.END); self.keywords_entry.insert(0, task.get("keywords", ""))
            self.color_entry.delete(0, tk.END); self.color_entry.insert(0, task.get("color", ""))
            self.size_entry.delete(0, tk.END); self.size_entry.insert(0, task.get("size", ""))
            self.proxy_entry.delete(0, tk.END); self.proxy_entry.insert(0, task.get("proxy", ""))
            self.mode_var.set(task.get("mode", "Normale"))

            contact = config_data.get("contact_details", {})
            self.email_entry.delete(0, tk.END); self.email_entry.insert(0, contact.get("email", ""))

            delivery = config_data.get("delivery_address", {})
            self.first_name_entry.delete(0, tk.END); self.first_name_entry.insert(0, delivery.get("first_name", ""))
            self.last_name_entry.delete(0, tk.END); self.last_name_entry.insert(0, delivery.get("last_name", ""))
            self.address_entry.delete(0, tk.END); self.address_entry.insert(0, delivery.get("address", ""))
            self.apt_entry.delete(0, tk.END); self.apt_entry.insert(0, delivery.get("apt_suite_etc", ""))
            self.city_entry.delete(0, tk.END); self.city_entry.insert(0, delivery.get("city", ""))
            self.country_code_entry.delete(0, tk.END); self.country_code_entry.insert(0, delivery.get("country_code", ""))
            self.state_code_entry.delete(0, tk.END); self.state_code_entry.insert(0, delivery.get("state_code", ""))
            self.postal_code_entry.delete(0, tk.END); self.postal_code_entry.insert(0, delivery.get("postal_code", ""))
            self.phone_entry.delete(0, tk.END); self.phone_entry.insert(0, delivery.get("phone", ""))

            payment = config_data.get("payment_details", {})
            self.card_name_entry.delete(0, tk.END); self.card_name_entry.insert(0, payment.get("name_on_card", ""))
            self.card_num_entry.delete(0, tk.END); self.card_num_entry.insert(0, payment.get("card_number", ""))
            self.card_exp_entry.delete(0, tk.END); self.card_exp_entry.insert(0, payment.get("expiration_date", ""))
            self.card_cvv_entry.delete(0, tk.END); self.card_cvv_entry.insert(0, payment.get("security_code", ""))

            self.log("Configurazione caricata con successo!")
        except FileNotFoundError:
            self.log("ERRORE: 'config.json' non trovato. Salva una configurazione prima di caricarla.")
        except Exception as e:
            self.log(f"Errore durante il caricamento della configurazione: {e}")

    def start_bot(self):
        self.log("Tentativo di avvio del bot...")
        self.start_button.config(state=tk.DISABLED)

        try:
            keywords_str = self.keywords_entry.get()
            if not keywords_str:
                self.log("ERRORE: Le parole chiave sono obbligatorie.")
                self.start_button.config(state=tk.NORMAL)
                return
            keywords = [k.strip() for k in keywords_str.split(',')]
            color = self.color_entry.get() or None
            size = self.size_entry.get() or None
            proxy = self.proxy_entry.get() or None
            mode = self.mode_var.get()

            bot_thread = threading.Thread(
                target=self._run_bot_thread,
                args=(keywords, color, size, proxy, mode),
                daemon=True
            )
            bot_thread.start()
        except Exception as e:
            self.log(f"Errore durante l'avvio del bot: {e}")
            self.start_button.config(state=tk.NORMAL)

    def _run_bot_thread(self, keywords, color, size, proxy, mode):
        try:
            self.log("Thread del bot avviato...")
            asyncio.run(supreme_bot.main(
                product_keywords=keywords,
                color=color,
                size=size,
                proxy=proxy,
                mode=mode
            ))
            self.log("Esecuzione del bot terminata.")
        except Exception as e:
            self.log(f"ERRORE nel thread del bot: {e}")
        finally:
            self.after(0, self.enable_buttons)

    def enable_buttons(self):
        self.start_button.config(state=tk.NORMAL)

    def periodic_log_check(self):
        while not self.log_queue.empty():
            try:
                line = self.log_queue.get_nowait()
                self.log(line, end='')
            except queue.Empty:
                pass
        self.after(100, self.periodic_log_check)

    def log(self, message, end="\n"):
        self.log_area.configure(state='normal')
        self.log_area.insert(tk.END, message + end)
        self.log_area.configure(state='disabled')
        self.log_area.see(tk.END)

if __name__ == "__main__":
    app = SupremeBotGUI()
    app.mainloop()

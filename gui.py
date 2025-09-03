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
        self.geometry("800x700")

        # --- Stile ---
        style = ttk.Style(self)
        style.configure("TLabel", padding=5, font=('Helvetica', 10))
        style.configure("TEntry", padding=5, font=('Helvetica', 10))
        style.configure("TButton", padding=5, font=('Helvetica', 10, 'bold'))
        style.configure("TFrame", padding=10)
        style.configure("TLabelframe", padding=10)
        style.configure("TLabelframe.Label", font=('Helvetica', 11, 'bold'))

        # --- Layout Principale ---
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(expand=True, fill=tk.BOTH)

        # --- Frame di Configurazione ---
        config_frame = ttk.Frame(main_frame)
        config_frame.pack(fill=tk.X, pady=5)

        # --- Frame per i Dettagli del Task ---
        task_frame = ttk.Labelframe(config_frame, text="Task e Prodotto")
        task_frame.pack(fill=tk.X, expand=True, side=tk.LEFT, padx=5, anchor="n")

        self.create_labeled_entry(task_frame, "Parole Chiave (separate da virgola)", "keywords_entry")
        self.create_labeled_entry(task_frame, "Colore", "color_entry")
        self.create_labeled_entry(task_frame, "Taglia", "size_entry")

        # --- Frame per i Dettagli di Contatto e Spedizione ---
        delivery_frame = ttk.Labelframe(config_frame, text="Contatto e Spedizione")
        delivery_frame.pack(fill=tk.X, expand=True, side=tk.LEFT, padx=5, anchor="n")

        self.create_labeled_entry(delivery_frame, "Email", "email_entry")
        self.create_labeled_entry(delivery_frame, "Nome", "first_name_entry")
        self.create_labeled_entry(delivery_frame, "Cognome", "last_name_entry")
        self.create_labeled_entry(delivery_frame, "Indirizzo", "address_entry")
        self.create_labeled_entry(delivery_frame, "Apt/Suite (opzionale)", "apt_entry")
        self.create_labeled_entry(delivery_frame, "Città", "city_entry")
        self.create_labeled_entry(delivery_frame, "Codice Paese (es. US, IT)", "country_code_entry")
        self.create_labeled_entry(delivery_frame, "Codice Stato/Prov. (es. CA, MI)", "state_code_entry")
        self.create_labeled_entry(delivery_frame, "CAP", "postal_code_entry")
        self.create_labeled_entry(delivery_frame, "Telefono", "phone_entry")

        # --- Frame Dettagli Pagamento ---
        payment_frame = ttk.Labelframe(config_frame, text="Dettagli Pagamento")
        payment_frame.pack(fill=tk.X, expand=True, side=tk.LEFT, padx=5, anchor="n")

        self.create_labeled_entry(payment_frame, "Nome su Carta", "card_name_entry")
        self.create_labeled_entry(payment_frame, "Numero Carta", "card_num_entry")
        self.create_labeled_entry(payment_frame, "Scadenza (MM/YY)", "card_exp_entry")
        self.create_labeled_entry(payment_frame, "CVV", "card_cvv_entry")

        # --- Frame Azioni ---
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, pady=10)

        self.save_button = ttk.Button(action_frame, text="Salva Configurazione", command=self.save_config)
        self.save_button.pack(side=tk.LEFT, padx=5)

        self.start_button = ttk.Button(action_frame, text="Avvia Bot", command=self.start_bot)
        self.start_button.pack(side=tk.RIGHT, padx=5)

        # --- Frame Log ---
        log_frame = ttk.Labelframe(main_frame, text="Log")
        log_frame.pack(expand=True, fill=tk.BOTH, pady=5)

        self.log_area = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=15, font=('Courier New', 9))
        self.log_area.pack(expand=True, fill=tk.BOTH)
        self.log_area.configure(state='disabled')

        # --- Setup per il reindirizzamento dei log ---
        self.log_queue = queue.Queue()
        self.queue_writer = QueueWriter(self.log_queue)
        sys.stdout = self.queue_writer
        sys.stderr = self.queue_writer

        self.after(100, self.periodic_log_check)

    def create_labeled_entry(self, parent, label_text, entry_var_name):
        """Crea una coppia Label-Entry e la salva come attributo dell'istanza."""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=2, padx=5)

        label = ttk.Label(frame, text=label_text)
        label.pack(side=tk.LEFT, anchor="w")

        entry = ttk.Entry(frame)
        entry.pack(side=tk.RIGHT, expand=True, fill=tk.X)

        setattr(self, entry_var_name, entry)

    def save_config(self):
        """Raccoglie i dati dalla GUI e li salva in config.json."""
        self.log("Salvataggio della configurazione in config.json...")

        config_data = {
            "contact_details": {
                "email": self.email_entry.get()
            },
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

    def start_bot(self):
        """Avvia il bot in un thread separato per non bloccare la GUI."""
        self.log("Tentativo di avvio del bot...")
        self.start_button.config(state=tk.DISABLED)
        self.save_button.config(state=tk.DISABLED)

        # Controlla se il file di configurazione esiste
        if not os.path.exists("config.json"):
            self.log("ERRORE: 'config.json' non trovato. Salva la configurazione prima di avviare il bot.")
            self.start_button.config(state=tk.NORMAL)
            self.save_button.config(state=tk.NORMAL)
            return

        # Raccogli i dati dalla GUI
        try:
            keywords_str = self.keywords_entry.get()
            if not keywords_str:
                self.log("ERRORE: Le parole chiave del prodotto sono obbligatorie.")
                self.start_button.config(state=tk.NORMAL)
                self.save_button.config(state=tk.NORMAL)
                return

            keywords = [k.strip() for k in keywords_str.split(',')]
            color = self.color_entry.get() or None
            size = self.size_entry.get() or None

            # Avvia il bot in un thread
            bot_thread = threading.Thread(
                target=self._run_bot_thread,
                args=(keywords, color, size),
                daemon=True
            )
            bot_thread.start()

        except Exception as e:
            self.log(f"Errore durante l'avvio del bot: {e}")
            self.start_button.config(state=tk.NORMAL)
            self.save_button.config(state=tk.NORMAL)

    def _run_bot_thread(self, keywords, color, size):
        """
        Funzione eseguita dal thread per avviare il loop asyncio del bot.
        """
        try:
            self.log("Thread del bot avviato...")
            # Qui è dove il bot viene eseguito.
            # In una implementazione futura, si catturerebbe l'output qui.
            asyncio.run(supreme_bot.main(product_keywords=keywords, color=color, size=size))
            self.log("Esecuzione del bot terminata.")
        except Exception as e:
            self.log(f"ERRORE nel thread del bot: {e}")
        finally:
            # Riabilita i pulsanti in modo sicuro per il thread
            self.after(0, self.enable_buttons)

    def enable_buttons(self):
        """Riabilita i pulsanti di azione."""
        self.start_button.config(state=tk.NORMAL)
        self.save_button.config(state=tk.NORMAL)

    def periodic_log_check(self):
        """Controlla la coda dei log e aggiorna la GUI."""
        while not self.log_queue.empty():
            try:
                line = self.log_queue.get_nowait()
                self.log(line, end='')
            except queue.Empty:
                pass
        self.after(100, self.periodic_log_check)

    def log(self, message, end="\n"):
        """Aggiunge un messaggio all'area di log."""
        self.log_area.configure(state='normal')
        self.log_area.insert(tk.END, message + end)
        self.log_area.configure(state='disabled')
        self.log_area.see(tk.END)

if __name__ == "__main__":
    app = SupremeBotGUI()
    app.mainloop()

# --- ISTRUZIONI DI INSTALLAZIONE ---
# Esegui: pip install beautifulsoup4 pyppeteer

import asyncio
import json
import random
import os
from pyppeteer import launch
from bs4 import BeautifulSoup

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
]

async def wait_for_resume_signal():
    """Attende il segnale di ripresa dall'utente."""
    while not os.path.exists("resume_signal.txt"):
        await asyncio.sleep(1)
    os.remove("resume_signal.txt")
    print("Segnale 'CONTINUA' ricevuto. Procedo...")

async def fill_checkout_form(page, config):
    """Riempie il modulo di checkout in modalità Co-Pilota."""
    print("Inizio compilazione modulo (modalità Co-Pilota)...")
    contact = config['contact_details']

    await asyncio.sleep(random.uniform(0.5, 1.0))

    # Compila i campi facili
    await page.type('#email', contact['email'], {'delay': random.randint(35, 85)})
    await page.type('#checkout_shipping_address_first_name', config['delivery_address']['first_name'], {'delay': random.randint(35, 85)})
    await page.type('#checkout_shipping_address_last_name', config['delivery_address']['last_name'], {'delay': random.randint(35, 85)})
    print("Campi iniziali compilati.")

    # --- PAUSA 1: Intervento manuale per l'indirizzo ---
    print("\nPAUSA: Inserisci manualmente Indirizzo, Città, CAP, Provincia e Telefono nel browser.")
    print("       Clicca 'CONTINUA' sulla GUI quando hai finito.")
    await wait_for_resume_signal()

    # --- PAUSA 2: Intervento manuale per la carta di credito ---
    print("\nPAUSA: Inserisci manualmente i dati della carta di credito nel browser.")
    print("       Clicca 'CONTINUA' sulla GUI per procedere al pagamento.")
    await wait_for_resume_signal()

    print("Accettazione termini e condizioni...")
    await page.evaluate("document.getElementById('checkout_terms_and_conditions').click();")
    print("Bot pronto per il click finale.")

async def main(product_keywords, color=None, size=None, proxy=None, show_browser=False):
    if not product_keywords: raise ValueError("Parole chiave obbligatorie.")
    try:
        with open('config.json', 'r') as f: config = json.load(f)
    except Exception as e:
        print(f"ERRORE: config.json non trovato o malformato: {e}"); return

    launch_args = {
        'headless': not show_browser,
        'args': [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--disable-infobars',
            '--window-size=1920,1080'
        ]
    }
    if proxy:
        print(f"Utilizzo del proxy: {proxy}"); launch_args['args'].append(f'--proxy-server={proxy}')

    browser = await launch(**launch_args)
    page = await browser.newPage()
    await page.setUserAgent(random.choice(USER_AGENTS))

    try:
        print("Parsing dell'HTML per trovare i prodotti...")
        await page.goto('https://eu.supreme.com/collections/all', {'waitUntil': 'networkidle2', 'timeout': 30000})
        script_content = await page.evaluate("() => document.getElementById('products-json').innerHTML")
        if not script_content: raise Exception("Impossibile trovare il JSON dei prodotti.")
        products_data = json.loads(script_content)
        products = products_data.get('products', [])

        print(f"Ricerca del prodotto: {product_keywords}...")
        target_product = next((p for p in products if all(k.lower() in p.get('title', '').lower() for k in product_keywords) and (not color or color.lower() in p.get('color', '').lower())), None)

        if not target_product: raise Exception("Prodotto non trovato.")

        print(f"Prodotto trovato: {target_product['title']} - {target_product['color']}")

        await page.goto(f"https://eu.supreme.com{target_product['url']}", {'waitUntil': 'networkidle2', 'timeout': 30000})

        if size:
            print(f"Selezione taglia: {size}...")
            await page.waitForSelector('select[data-testid="size-dropdown"]')
            option_value = await page.evaluate(f'''(size_text) => {{
                const select = document.querySelector('select[data-testid="size-dropdown"]');
                for (let i = 0; i < select.options.length; i++) {{
                    if (select.options[i].text.toLowerCase().trim() === size_text.toLowerCase().trim()) return select.options[i].value;
                }}
                return null;
            }}''', size)
            if not option_value: raise Exception(f"Taglia '{size}' non trovata.")
            await page.select('select[data-testid="size-dropdown"]', option_value)

        await page.click('button[data-testid="add-to-cart-button"]')
        print("Prodotto aggiunto al carrello.")

        await page.waitForSelector('div[data-testid="mini-cart"]', {'visible': True})
        await asyncio.sleep(random.uniform(0.3, 0.7))
        await page.evaluate("document.querySelector('a[data-testid=\"mini-cart-checkout-link\"]').click()")

        await page.waitForSelector('#checkout-pay-button', {'timeout': 20000})
        print("Pagina di checkout raggiunta.")

        await fill_checkout_form(page, config)

        print("\nPROCESSO IN ATTESA DEL CLICK FINALE.")
        await page.screenshot({'path': 'final_page_ready.png', 'fullPage': True})

        print("Per completare l'acquisto, decommenta la riga seguente:")
        # await page.click('#checkout-pay-button')

    except Exception as e:
        print(f"\nERRORE: {e}")
        await page.screenshot({'path': 'error_screenshot.png', 'fullPage': True})
    finally:
        print("Chiusura del browser in 10 secondi... (per permettere l'intervento manuale)")
        await asyncio.sleep(10)
        await browser.close()

if __name__ == '__main__':
    print("Questo script è pensato per essere eseguito tramite gui.py")

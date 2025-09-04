# --- ISTRUZIONI DI INSTALLAZIONE ---
# Prima di eseguire, assicurati di installare tutte le librerie necessarie:
# pip install beautifulsoup4 aiohttp
# pip install pyppeteer pyppeteer-extra pyppeteer-extra-plugin-stealth

import asyncio
import json
import random
# Usa pyppeteer-extra per le funzionalità anti-bot
from pyppeteer_extra import launch
from pyppeteer_extra.stealth import stealth
from bs4 import BeautifulSoup

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/115.0"
]

async def get_products_from_html(page):
    """Esegue il parsing dell'HTML per ottenere i prodotti."""
    print("Parsing dell'HTML per trovare i prodotti...")
    await page.goto('https://eu.supreme.com/collections/all', {'waitUntil': 'networkidle2', 'timeout': 30000})
    script_content = await page.evaluate("() => document.getElementById('products-json').innerHTML")
    if not script_content:
        raise Exception("Impossibile trovare il JSON dei prodotti nella pagina HTML.")
    products_data = json.loads(script_content)
    return products_data.get('products', [])

async def fill_checkout_form(page, config):
    """Riempie il modulo di checkout con i dati di configurazione."""
    print("Inizio compilazione del modulo di checkout...")
    addr = config['delivery_address']
    contact = config['contact_details']
    payment = config['payment_details']

    await asyncio.sleep(random.uniform(0.5, 1.0))

    # Utilizzo di ID stabili per i menu a tendina e selettori di placeholder per gli altri campi
    await page.type('input[placeholder="Email"]', contact['email'], {'delay': random.randint(35, 85)})
    await page.select('#Select0', addr['country_code'])
    await asyncio.sleep(0.4)
    await page.type('input[placeholder="Nome"]', addr['first_name'], {'delay': random.randint(35, 85)})
    await page.type('input[placeholder="Cognome"]', addr['last_name'], {'delay': random.randint(35, 85)})
    await page.type('input[placeholder="Indirizzo"]', addr['address'], {'delay': random.randint(35, 85)})
    if addr.get('apt_suite_etc'):
        await page.type('input[placeholder="Appartamento, interno, ecc. (opzionale)"]', addr['apt_suite_etc'], {'delay': random.randint(35, 85)})
    await page.type('input[placeholder="CAP"]', addr['postal_code'], {'delay': random.randint(35, 85)})
    await page.type('input[placeholder="Città"]', addr['city'], {'delay': random.randint(35, 85)})
    await page.select('#Select1', addr['province_code'])
    await page.type('input[placeholder="Telefono"]', addr['phone'], {'delay': random.randint(35, 85)})
    print("Dati di contatto e indirizzo inseriti.")

    print("Inserimento dati di pagamento...")
    async def fill_iframe_field(frame_name, value):
        # La selezione dell'iframe è più stabile tramite il suo nome/id
        iframe = await page.waitForSelector(f'iframe[name="{frame_name}"]')
        frame = await iframe.contentFrame()
        await frame.type('input', value, {'delay': random.randint(50, 100)})

    await fill_iframe_field('card.number', payment['card_number'])
    await fill_iframe_field('card.name', payment['name_on_card'])
    await fill_iframe_field('card.expiry', payment['expiration_date'])
    await fill_iframe_field('card.verification_value', payment['security_code'])
    print("Dati di pagamento inseriti.")

    # Click sulla checkbox dei termini e condizioni
    print("Accettazione termini e condizioni...")
    await page.click('input#checkout_terms_and_conditions')

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
            '--disable-gpu'
        ]
    }
    if proxy:
        print(f"Utilizzo del proxy: {proxy}")
        launch_args['args'].append(f'--proxy-server={proxy}')

    browser = await launch(**launch_args)
    page = await browser.newPage()
    # Applica lo stealth plugin per rendere il browser meno rilevabile
    await stealth(page)
    await page.setUserAgent(random.choice(USER_AGENTS))

    try:
        products = await get_products_from_html(page)

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
                    if (select.options[i].text.toLowerCase().trim() === size_text.toLowerCase().trim()) {{
                        return select.options[i].value;
                    }}
                }}
                return null;
            }}''', size)
            if not option_value: raise Exception(f"Taglia '{size}' non trovata o non disponibile.")
            await page.select('select[data-testid="size-dropdown"]', option_value)

        await page.click('button[data-testid="add-to-cart-button"]')
        print("Prodotto aggiunto al carrello.")

        await page.waitForSelector('div[data-testid="mini-cart"]', {'visible': True})
        await asyncio.sleep(random.uniform(0.4, 0.8))
        await page.evaluate("document.querySelector('a[data-testid=\"mini-cart-checkout-link\"]').click()")

        await page.waitForSelector('#checkout-pay-button', {'timeout': 20000})
        print("Pagina di checkout raggiunta.")

        await fill_checkout_form(page, config)

        print("\nPROCESSO COMPLETATO! Il bot è pronto per il pagamento finale.")
        await page.screenshot({'path': 'final_filled_page.png', 'fullPage': True})
        print("Per completare l'acquisto, decommenta la riga seguente:")
        # await page.click('#checkout-pay-button')

    except Exception as e:
        print(f"\nERRORE: {e}")
        await page.screenshot({'path': 'error_screenshot.png', 'fullPage': True})
    finally:
        print("Chiusura del browser.")
        await browser.close()

if __name__ == '__main__':
    print("Questo script è pensato per essere eseguito tramite gui.py")

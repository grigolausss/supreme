# --- ISTRUZIONI DI INSTALLAZIONE ---
# Esegui: pip install beautifulsoup4 pyppeteer

import asyncio
import json
import random
from pyppeteer import launch
from bs4 import BeautifulSoup

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
]

async def get_products_from_html(page):
    """Esegue il parsing dell'HTML per ottenere i prodotti."""
    print("Parsing dell'HTML per trovare i prodotti...")
    await page.goto('https://eu.supreme.com/collections/all', {'waitUntil': 'networkidle2', 'timeout': 30000})
    script_content = await page.evaluate("() => document.getElementById('products-json').innerHTML")
    if not script_content: raise Exception("Impossibile trovare il JSON dei prodotti.")
    products_data = json.loads(script_content)
    return products_data.get('products', [])

async def fill_checkout_form(page, config):
    """Riempie il modulo di checkout, gestendo l'autocompletamento dell'indirizzo."""
    print("Inizio compilazione del modulo di checkout...")
    addr = config['delivery_address']
    contact = config['contact_details']
    payment = config['payment_details']

    await asyncio.sleep(random.uniform(0.5, 1.0))

    # Usa selettori standard di Shopify, più robusti
    await page.type('#checkout_email', contact['email'], {'delay': random.randint(35, 85)})
    await page.select('#checkout_shipping_address_country', addr['country_code'])
    await asyncio.sleep(0.4)
    await page.type('#checkout_shipping_address_first_name', addr['first_name'], {'delay': random.randint(35, 85)})
    await page.type('#checkout_shipping_address_last_name', addr['last_name'], {'delay': random.randint(35, 85)})

    # --- Logica per l'autocompletamento di Google ---
    print("Inserimento indirizzo e gestione autocompletamento...")
    await page.type('#checkout_shipping_address_address1', addr['address'], {'delay': random.randint(40, 90)})

    # Clicca il pulsante "cerca" (lente di ingrandimento)
    search_button_selector = 'button[aria-label*="Search"]' # Selettore più generico
    await page.waitForSelector(search_button_selector)
    await page.click(search_button_selector)

    # Attendi e clicca il primo suggerimento
    autocomplete_selector = '.pac-item'
    await page.waitForSelector(autocomplete_selector, {'timeout': 5000})
    await asyncio.sleep(0.5)
    await page.click(autocomplete_selector)
    print("Suggerimento indirizzo cliccato. CAP, Città e Provincia dovrebbero essere compilati.")

    # Compila i campi rimanenti
    if addr.get('apt_suite_etc'):
        await page.type('#checkout_shipping_address_address2', addr['apt_suite_etc'], {'delay': random.randint(35, 85)})
    await page.type('#checkout_shipping_address_phone', addr['phone'], {'delay': random.randint(35, 85)})
    print("Dati di contatto e indirizzo inseriti.")

    print("Inserimento dati di pagamento...")
    async def fill_iframe_field(frame_name, value):
        iframe = await page.waitForSelector(f'iframe[name="{frame_name}"]')
        frame = await iframe.contentFrame()
        await frame.type('input', value, {'delay': random.randint(50, 100)})

    await fill_iframe_field('card.number', payment['card_number'])
    await fill_iframe_field('card.name', payment['name_on_card'])
    await fill_iframe_field('card.expiry', payment['expiration_date'])
    await fill_iframe_field('card.verification_value', payment['security_code'])
    print("Dati di pagamento inseriti.")

    print("Accettazione termini e condizioni...")
    # Click forzato tramite JavaScript per massima affidabilità
    await page.evaluate("document.getElementById('checkout_terms_and_conditions').click();")

async def main(product_keywords, color=None, size=None, proxy=None, show_browser=False):
    if not product_keywords: raise ValueError("Parole chiave obbligatorie.")
    try:
        with open('config.json', 'r') as f: config = json.load(f)
    except Exception as e:
        print(f"ERRORE: config.json non trovato o malformato: {e}"); return

    launch_args = {'headless': not show_browser, 'args': ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu']}
    if proxy:
        print(f"Utilizzo del proxy: {proxy}"); launch_args['args'].append(f'--proxy-server={proxy}')

    browser = await launch(**launch_args)
    page = await browser.newPage()
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

        print("\nPROCESSO COMPLETATO! Il bot è pronto per il pagamento finale.")
        await page.screenshot({'path': 'final_filled_page.png', 'fullPage': True})

        print("Per completare l'acquisto, decommenta la riga seguente in supreme_bot.py:")
        # await page.click('#checkout-pay-button')

    except Exception as e:
        print(f"\nERRORE: {e}")
        await page.screenshot({'path': 'error_screenshot.png', 'fullPage': True})
    finally:
        print("Chiusura del browser.")
        await browser.close()

if __name__ == '__main__':
    print("Questo script è pensato per essere eseguito tramite gui.py")

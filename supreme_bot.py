import asyncio
import json
import random
from pyppeteer import launch
from bs4 import BeautifulSoup
import aiohttp

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36"
]

async def get_products_from_api():
    """Tenta di ottenere i prodotti dall'API mobile_stock.json, ignorando gli errori SSL."""
    print("Tentativo di fetch dei prodotti dall'API mobile...")
    # Fix per l'errore SSL: disabilita la verifica del certificato
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        try:
            async with session.get('https://eu.supreme.com/mobile_stock.json') as response:
                response.raise_for_status()
                data = await response.json()
                print("Prodotti ottenuti con successo dall'API.")
                # La struttura dell'API potrebbe cambiare, usiamo .get per sicurezza
                return data.get('products_and_categories', {}).get('new', [])
        except Exception as e:
            print(f"Errore fetch API: {e}. Fallback su HTML.")
            return None

async def get_products_from_html(page):
    """Esegue il parsing dell'HTML per ottenere i prodotti (metodo di fallback)."""
    print("Parsing dell'HTML per trovare i prodotti (metodo di fallback)...")
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

    # L'ordine corretto come da sito
    await page.type('#email', contact['email'], {'delay': random.randint(30, 80)})
    await page.select('#Select0', addr['country_code'])
    await asyncio.sleep(0.3)
    await page.type('#TextField0', addr['first_name'], {'delay': random.randint(30, 80)})
    await page.type('#TextField1', addr['last_name'], {'delay': random.randint(30, 80)})
    await page.type('#shipping-address1', addr['address'], {'delay': random.randint(30, 80)})
    if addr.get('apt_suite_etc'):
        await page.type('#TextField2', addr['apt_suite_etc'], {'delay': random.randint(30, 80)})
    await page.type('#TextField4', addr['postal_code'], {'delay': random.randint(30, 80)})
    await page.type('#TextField3', addr['city'], {'delay': random.randint(30, 80)})
    await page.select('#Select1', addr['province_code'])
    await page.type('#TextField5', addr['phone'], {'delay': random.randint(30, 80)})
    print("Dati di contatto e indirizzo inseriti.")

    print("Inserimento dati di pagamento...")
    async def fill_iframe_field(container_selector, input_selector, value):
        iframe_element = await page.waitForSelector(f'{container_selector} iframe')
        frame = await iframe_element.contentFrame()
        await frame.type(input_selector, value, {'delay': random.randint(40, 90)})

    await fill_iframe_field('#number', '#number', payment['card_number'])
    await fill_iframe_field('#name', '#name', payment['name_on_card'])
    await fill_iframe_field('#expiry', '#expiry', payment['expiration_date'])
    await fill_iframe_field('#verification_value', '#verification_value', payment['security_code'])
    print("Dati di pagamento inseriti.")

async def solve_captcha_placeholder(page):
    if await page.evaluate("() => document.querySelector('.g-recaptcha')"):
        print("CAPTCHA RILEVATO! Avvio del risolutore (simulato)...")
        await asyncio.sleep(3)
        print("CAPTCHA risolto (simulato).")

async def main(product_keywords, color=None, size=None, proxy=None, mode="Normale", show_browser=False):
    if not product_keywords: raise ValueError("Parole chiave obbligatorie.")
    try:
        with open('config.json', 'r') as f: config = json.load(f)
    except Exception as e:
        print(f"ERRORE: config.json non trovato o malformato: {e}"); return

    launch_args = {'headless': not show_browser, 'args': ['--no-sandbox', '--disable-setuid-sandbox']}
    if proxy:
        print(f"Utilizzo del proxy: {proxy}")
        launch_args['args'].append(f'--proxy-server={proxy}')

    browser = await launch(**launch_args)
    page = await browser.newPage()
    await page.setUserAgent(random.choice(USER_AGENTS))

    try:
        products = await get_products_from_api() or await get_products_from_html(page)

        print(f"Ricerca del prodotto: {product_keywords}...")
        # L'API usa 'name' e 'style', l'HTML usa 'title' e 'color'. Unifichiamo.
        target_product = None
        for p in products:
            p_name = p.get('name', p.get('title', '')).lower()
            p_style = p.get('style', p.get('color', '')).lower()

            has_keywords = all(k.lower() in p_name for k in product_keywords)
            has_color = not color or color.lower() in p_style

            if has_keywords and has_color:
                target_product = p
                break

        if not target_product: raise Exception("Prodotto non trovato.")

        print(f"Prodotto trovato: {target_product.get('name', '')} - {target_product.get('style', '')}")

        # L'URL può essere costruito in modi diversi a seconda della fonte (API vs HTML)
        if 'category_name' in target_product:
            product_url = f"https://eu.supreme.com/shop/{target_product['category_name']}/{target_product['id']}"
        else:
            product_url = f"https://eu.supreme.com{target_product['url']}"

        await page.goto(product_url, {'waitUntil': 'networkidle2', 'timeout': 30000})

        if size:
            print(f"Selezione taglia: {size}...")
            await page.waitForSelector('select[data-testid="size-dropdown"]')
            await page.select('select[data-testid="size-dropdown"]', size)

        await page.click('button[data-testid="add-to-cart-button"]')
        print("Prodotto aggiunto al carrello.")

        await page.waitForSelector('div[data-testid="mini-cart"]', {'visible': True})
        await asyncio.sleep(random.uniform(0.4, 0.8) if mode == "Sicura" else random.uniform(0.2, 0.4))
        await page.evaluate("document.querySelector('a[data-testid=\"mini-cart-checkout-link\"]').click()")

        await page.waitForSelector('#checkout-pay-button', {'timeout': 20000})
        print("Pagina di checkout raggiunta.")

        await solve_captcha_placeholder(page)
        await fill_checkout_form(page, config)

        print("\nPROCESSO COMPLETATO! Il bot è pronto per il pagamento finale.")
        await page.screenshot({'path': 'final_filled_page.png', 'fullPage': True})

    except Exception as e:
        print(f"\nERRORE: {e}")
        await page.screenshot({'path': 'error_screenshot.png', 'fullPage': True})
    finally:
        print("Chiusura del browser.")
        await browser.close()

if __name__ == '__main__':
    print("Questo script è pensato per essere eseguito tramite gui.py")

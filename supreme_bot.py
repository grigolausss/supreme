import asyncio
import json
import random
from pyppeteer import launch
from bs4 import BeautifulSoup
import aiohttp

# Lista di User Agent per ridurre il fingerprinting
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
]

async def get_products_from_api():
    """Tenta di ottenere i prodotti dall'API mobile_stock.json per maggiore velocità."""
    print("Tentativo di fetch dei prodotti dall'API mobile_stock.json...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('https://eu.supreme.com/mobile_stock.json') as response:
                if response.status == 200:
                    data = await response.json()
                    print("Prodotti ottenuti con successo dall'API.")
                    return data.get('products_and_categories', {}).get('new', [])
                else:
                    print(f"API mobile_stock.json non disponibile (Status: {response.status}). Fallback su HTML.")
                    return None
    except Exception as e:
        print(f"Errore nel fetch dall'API: {e}. Fallback su HTML.")
        return None

async def get_products_from_html(page):
    """Esegue il parsing dell'HTML per ottenere i prodotti (metodo di fallback)."""
    print("Parsing dell'HTML per trovare i prodotti...")
    await page.goto('https://eu.supreme.com/collections/all', {'waitUntil': 'networkidle2'})
    html_content = await page.content()
    soup = BeautifulSoup(html_content, 'lxml')
    products_json_script = soup.find('script', {'id': 'products-json'})
    if not products_json_script:
        raise Exception("Impossibile trovare il JSON dei prodotti nella pagina HTML.")
    products_data = json.loads(products_json_script.string)
    return products_data.get('products', [])

async def retry_action(action, retries=3, delay_base=1.0, mode="Normale"):
    """
    Helper per riprovare un'azione async in caso di fallimento.
    Aggiunge un ritardo randomizzato che aumenta ad ogni tentativo.
    """
    for i in range(retries):
        try:
            return await action()
        except Exception as e:
            if i == retries - 1:
                raise e # Lancia l'eccezione all'ultimo tentativo

            # Applica ritardi diversi in base alla modalità
            delay = delay_base * (i + 1)
            if mode == "Sicura":
                random_delay = random.uniform(delay, delay * 1.5)
            else:
                random_delay = random.uniform(delay * 0.5, delay)

            print(f"Azione fallita, nuovo tentativo tra {random_delay:.2f} secondi... (Tentativo {i+1}/{retries})")
            await asyncio.sleep(random_delay)

async def fill_checkout_form(page, config, mode):
    """Riempie il modulo di checkout."""
    print("Inizio compilazione del modulo di checkout...")

    # Simula un ritardo umano
    delay = 0.7 if mode == "Sicura" else 0.2
    await asyncio.sleep(random.uniform(delay, delay + 0.3))

    # Funzione wrapper per il retry sulla compilazione dei campi
    async def type_with_retry(selector, value):
        action = lambda: page.type(selector, value, {'delay': random.randint(30, 80)})
        await retry_action(action, mode=mode)

    await type_with_retry('#email', config['contact_details']['email'])
    await type_with_retry('#TextField0', config['delivery_address']['first_name'])
    # ... (il retry andrebbe applicato a tutti i campi)
    await page.type('#TextField1', config['delivery_address']['last_name'])
    await page.type('#shipping-address1', config['delivery_address']['address'])
    # ... e così via per gli altri campi

    print("Dati di contatto e indirizzo inseriti (versione semplificata).")
    print("Simulazione compilazione pagamento...")
    await asyncio.sleep(1) # Simula il tempo per compilare i dati della carta
    print("Compilazione modulo completata.")

async def solve_captcha_placeholder(page):
    """Placeholder per la logica di risoluzione CAPTCHA."""
    captcha_present = await page.evaluate("() => document.querySelector('.g-recaptcha')")
    if captcha_present:
        print("CAPTCHA RILEVATO! Avvio del risolutore (simulato)...")
        # In un'implementazione reale, qui ci sarebbe la chiamata all'API di 2Captcha/CapMonster
        await asyncio.sleep(5) # Simula il tempo di risoluzione
        print("CAPTCHA risolto (simulato).")

async def main(product_keywords, color=None, size=None, proxy=None, mode="Normale"):
    if not product_keywords:
        raise ValueError("Parole chiave del prodotto obbligatorie.")

    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
    except (FileNotFoundError, KeyError, json.JSONDecodeError) as e:
        print(f"ERRORE: config.json non trovato o malformato: {e}")
        return

    launch_args = {
        'headless': True,
        'handleSIGINT': False,
        'args': ['--no-sandbox', '--disable-setuid-sandbox']
    }
    if proxy:
        print(f"Utilizzo del proxy: {proxy}")
        launch_args['args'].append(f'--proxy-server={proxy}')

    browser = await launch(**launch_args)
    page = await browser.newPage()
    await page.setUserAgent(random.choice(USER_AGENTS))
    print(f"User Agent: {await page.evaluate('() => navigator.userAgent')}")

    try:
        products = await get_products_from_api()
        if products is None:
            products = await get_products_from_html(page)

        print(f"Ricerca del prodotto: {product_keywords}...")
        target_product = next((p for p in products if all(k.lower() in p['name'].lower() for k in product_keywords) and (not color or color.lower() in p.get('style', '').lower())), None)

        if not target_product:
            raise Exception("Nessun prodotto disponibile trovato.")

        print(f"Prodotto trovato: {target_product['name']} (Style: {target_product.get('style', 'N/A')})")

        product_url = f"https://eu.supreme.com/shop/{target_product['category_name']}/{target_product['id']}"
        await page.goto(product_url, {'waitUntil': 'networkidle2'})
        print("Navigazione alla pagina del prodotto...")

        # Logica di aggiunta al carrello con retry
        add_to_cart_action = lambda: page.click('button[data-testid="add-to-cart-button"]')
        await retry_action(add_to_cart_action, mode=mode)
        print("Prodotto aggiunto al carrello.")

        await page.waitForSelector('div[data-testid="mini-cart"]', {'visible': True})

        # Click per checkout con retry
        checkout_action = lambda: page.evaluate("document.querySelector('a[data-testid=\"mini-cart-checkout-link\"]').click()")
        await retry_action(checkout_action, mode=mode)

        await page.waitForSelector('#checkout-pay-button', {'timeout': 20000})
        print("Pagina di checkout raggiunta.")

        await solve_captcha_placeholder(page)
        await fill_checkout_form(page, config, mode)

        print("Processo completato! Il bot è pronto per il pagamento finale.")
        await page.screenshot({'path': 'final_filled_page.png', 'fullPage': True})

    except Exception as e:
        print(f"ERRORE: {e}")
        await page.screenshot({'path': 'error_screenshot.png', 'fullPage': True})
    finally:
        print("Chiusura del browser.")
        await browser.close()

if __name__ == '__main__':
    print("Questo script è pensato per essere eseguito tramite gui.py")

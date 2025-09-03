import asyncio
import json
from pyppeteer import launch
from bs4 import BeautifulSoup

async def fill_checkout_form(page, config):
    """Riempie il modulo di checkout con i dati dal file di configurazione."""
    print("Inizio compilazione del modulo di checkout...")
    try:
        # Dettagli di contatto e indirizzo
        await page.type('#email', config['contact_details']['email'])
        await page.type('#TextField0', config['delivery_address']['first_name'])
        await page.type('#TextField1', config['delivery_address']['last_name'])
        await page.type('#shipping-address1', config['delivery_address']['address'])
        if config['delivery_address'].get('apt_suite_etc'):
            await page.type('#TextField2', config['delivery_address']['apt_suite_etc'])
        await page.type('#TextField3', config['delivery_address']['city'])
        await page.type('#TextField4', config['delivery_address']['postal_code'])
        await page.type('#TextField5', config['delivery_address']['phone'])

        await page.select('#Select0', config['delivery_address']['country_code'])
        await asyncio.sleep(0.5)
        await page.select('#Select1', config['delivery_address']['state_code'])

        print("Dati di contatto e indirizzo inseriti.")

        # Gestione campi carta di credito in iframes
        print("Inserimento dati di pagamento...")
        async def fill_iframe_field(container_selector, input_selector, value):
            iframe_element = await page.waitForSelector(f'{container_selector} iframe')
            frame = await iframe_element.contentFrame()
            await frame.waitForSelector(input_selector)
            await frame.type(input_selector, value)

        await fill_iframe_field('#number', '#number', config['payment_details']['card_number'])
        await fill_iframe_field('#name', '#name', config['payment_details']['name_on_card'])
        await fill_iframe_field('#expiry', '#expiry', config['payment_details']['expiration_date'])
        await fill_iframe_field('#verification_value', '#verification_value', config['payment_details']['security_code'])

        print("Dati di pagamento inseriti.")
        print("Compilazione modulo completata.")
    except Exception as e:
        raise Exception(f"Errore durante la compilazione del modulo: {e}")


async def main(product_keywords, color=None, size=None):
    """
    Funzione principale del bot Supreme.
    """
    if not product_keywords:
        raise ValueError("È necessario fornire almeno una parola chiave per la ricerca del prodotto.")

    # Carica la configurazione all'avvio del bot
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print("ERRORE: File 'config.json' non trovato.")
        print("Per favore, usa la GUI per salvare una configurazione prima di avviare il bot.")
        return
    except (KeyError, json.JSONDecodeError) as e:
        print(f"ERRORE: Il file 'config.json' è malformato o mancano delle chiavi: {e}")
        return

    print("Avvio del bot Supreme...")
    browser = await launch(
        headless=True,
        args=['--no-sandbox', '--disable-setuid-sandbox']
    )
    page = await browser.newPage()
    await page.setUserAgent("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36")

    try:
        # 1. Naviga e trova prodotto
        print("Navigazione alla pagina 'shop all'...")
        await page.goto('https://eu.supreme.com/collections/all', {'waitUntil': 'networkidle2'})

        html_content = await page.content()
        soup = BeautifulSoup(html_content, 'lxml')
        products_json_script = soup.find('script', {'id': 'products-json'})
        products_data = json.loads(products_json_script.string)
        products = products_data.get('products', [])

        print(f"Ricerca del prodotto: {product_keywords}, Colore: {color or 'N/A'}, Taglia: {size or 'N/A'}")
        target_product = None
        for product in products:
            title_lower = product['title'].lower()
            has_all_keywords = all(keyword.lower() in title_lower for keyword in product_keywords)
            if has_all_keywords and product.get('available', False):
                if color:
                    if color.lower() in product['color'].lower():
                        target_product = product
                        break
                else:
                    target_product = product
                    break

        if not target_product:
            raise Exception(f"Nessun prodotto disponibile trovato con i criteri specificati.")

        print(f"Prodotto trovato: {target_product['title']} - {target_product['color']}")

        # 2. Naviga alla pagina prodotto e aggiungi al carrello
        product_relative_url = target_product['url']
        product_link_selector = f'a[href^="{product_relative_url}"]'
        await page.click(product_link_selector)
        print("Navigazione alla pagina del prodotto...")

        size_selector = 'select[data-testid="size-dropdown"]'
        add_to_cart_selector = 'button[data-testid="add-to-cart-button"]'
        await page.waitForSelector(size_selector, {'timeout': 10000})

        if size:
            print(f"Cerco la taglia specifica: {size}...")
            option_to_select = await page.evaluate(f'''(size_text) => {{
                const select = document.querySelector('{size_selector}');
                if (!select) return null;
                for (let i = 0; i < select.options.length; i++) {{
                    if (select.options[i].text.toLowerCase().trim() === size_text.toLowerCase().trim() && !select.options[i].disabled) {{
                        return select.options[i].value;
                    }}
                }}
                return null;
            }}''', size)
            if option_to_select:
                await page.select(size_selector, option_to_select)
                print(f"Taglia '{size}' selezionata.")
            else:
                raise Exception(f"Taglia '{size}' non trovata o non disponibile.")

        await page.click(add_to_cart_selector)
        print("Prodotto aggiunto al carrello.")

        await page.waitForSelector('div[data-testid="mini-cart"]', {'visible': True, 'timeout': 10000})

        # 3. Naviga al checkout e compila il modulo
        print("Navigazione alla pagina di checkout...")
        js_click_code = "document.querySelector('a[data-testid=\"mini-cart-checkout-link\"]').click()"
        await page.evaluate(js_click_code)

        await page.waitForSelector('#checkout-pay-button', {'timeout': 20000})
        print("Pagina di checkout raggiunta.")

        # CHIAMA LA FUNZIONE PER COMPILARE IL MODULO
        await fill_checkout_form(page, config)

        print("Processo completato!")
        await page.screenshot({'path': 'final_filled_page.png', 'fullPage': True})
        print("Screenshot finale salvato come 'final_filled_page.png'.")

    except Exception as e:
        print(f"ERRORE: {e}")
        await page.screenshot({'path': 'error_screenshot.png', 'fullPage': True})
        print("Screenshot dell'errore salvato.")

    finally:
        print("Chiusura del browser.")
        await browser.close()

if __name__ == '__main__':
    print("Questo script è pensato per essere eseguito tramite gui.py")
    print("Per un test manuale, decommentare le righe seguenti e configurare i valori.")
    # target_keywords = ["Tee"]
    # target_color = None
    # target_size = "Large"
    # asyncio.run(main(product_keywords=target_keywords, color=target_color, size=target_size))

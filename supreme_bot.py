import asyncio
import json
from pyppeteer import launch
from bs4 import BeautifulSoup

async def main():
    print("Avvio del bot Supreme...")
    browser = await launch(
        headless=True,
        args=['--no-sandbox', '--disable-setuid-sandbox']
    )
    page = await browser.newPage()
    await page.setUserAgent("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36")

    try:
        # 1. Naviga alla pagina principale e trova un prodotto disponibile
        print("Navigazione alla pagina 'shop all' per trovare un prodotto...")
        await page.goto('https://eu.supreme.com/collections/all', {'waitUntil': 'networkidle2'})

        html_content = await page.content()
        soup = BeautifulSoup(html_content, 'lxml')

        # 2. Estrai e parsa il JSON dei prodotti
        products_json_script = soup.find('script', {'id': 'products-json'})
        if not products_json_script:
            raise Exception("Impossibile trovare il JSON dei prodotti sulla pagina.")

        products_data = json.loads(products_json_script.string)
        products = products_data.get('products', [])

        # 3. Trova il primo prodotto disponibile che non sia Hanes/Socks
        print(f"Trovati {len(products)} prodotti. Cerco un articolo disponibile...")
        target_product = None
        for product in products:
            is_base_item = "hanes" in product['title'].lower() or \
                           "socks" in product['title'].lower() or \
                           "boxer" in product['title'].lower()

            if product.get('available', False) and not is_base_item:
                target_product = product
                break

        if not target_product:
            raise Exception("Nessun prodotto disponibile trovato per il test.")

        product_relative_url = target_product['url']
        print(f"Prodotto trovato: {target_product['title']} - {target_product['color']}")
        print(f"URL relativo: {product_relative_url}")

        # 4. Clicca sul link del prodotto invece di navigare direttamente
        product_link_selector = f'a[href^="{product_relative_url}"]'
        print(f"Trovato il selettore del link del prodotto: {product_link_selector}")
        await page.waitForSelector(product_link_selector)
        await page.click(product_link_selector)

        print("Navigazione alla pagina del prodotto tramite click...")
        # Non attendiamo una navigazione completa, ma direttamente un selettore della pagina di destinazione
        # Questo è più robusto per le Single-Page Applications (SPA)

        # 5. Seleziona la taglia e aggiungi al carrello
        size_selector = 'select[data-testid="size-dropdown"]'
        add_to_cart_selector = 'button[data-testid="add-to-cart-button"]'

        print("Attendo che la pagina del prodotto sia completamente caricata...")
        await page.waitForSelector(size_selector, {'timeout': 10000})
        print("Selettore della taglia trovato.")

        # Prova a selezionare una taglia se ci sono più opzioni
        options = await page.querySelectorAll(f'{size_selector} option')
        if len(options) > 1:
            # Seleziona la prima taglia disponibile (non la prima che è spesso un placeholder)
            option_value = await page.evaluate(f'''() => {{
                const select = document.querySelector('{size_selector}');
                if (!select) return null;
                // Cerca la prima opzione selezionabile
                for (let i = 0; i < select.options.length; i++) {{
                    if (!select.options[i].disabled && select.options[i].value) {{
                        return select.options[i].value;
                    }}
                }}
                return null;
            }}''')

            if option_value:
                await page.select(size_selector, option_value)
                print(f"Taglia con valore '{option_value}' selezionata.")
            else:
                print("Nessuna opzione di taglia selezionabile trovata, si procede con quella di default.")
        else:
            print("Trovata una sola opzione per la taglia, si procede con quella di default.")

        await page.waitForSelector(add_to_cart_selector, {'visible': True})
        await page.click(add_to_cart_selector)
        print("Prodotto aggiunto al carrello.")

        # 6. Attendi la comparsa del mini-carrello e clicca su checkout
        print("Attendo la comparsa del mini-carrello...")
        mini_cart_selector = 'div[data-testid="mini-cart"]'
        await page.waitForSelector(mini_cart_selector, {'visible': True, 'timeout': 10000})
        print("Mini-carrello apparso.")

        # Il click sul link del mini-carrello si è dimostrato inaffidabile.
        # Tentativo alternativo: una volta che l'oggetto è nel carrello (confermato dalla
        # comparsa del mini-carrello), navighiamo direttamente all'URL di checkout.
        # Questo dovrebbe funzionare perché lo stato del carrello è salvato nella sessione.
        print("Prodotto nel carrello. Navigazione diretta alla pagina di checkout...")
        checkout_url = 'https://eu.supreme.com/checkout'
        await page.goto(checkout_url, {'waitUntil': 'networkidle2'})

        # 7. Verifica di essere sulla pagina di checkout
        print("Verifico il caricamento della pagina di checkout...")
        # Grazie al debug HTML, abbiamo trovato un selettore affidabile per la pagina di checkout.
        # Attendiamo il pulsante 'process payment' che ha un ID stabile.
        checkout_button_selector = '#checkout-pay-button'
        await page.waitForSelector(checkout_button_selector, {'timeout': 20000})

        print("Pagina di checkout raggiunta con successo!")
        await page.screenshot({'path': 'checkout_page.png', 'fullPage': True})
        print("Screenshot della pagina di checkout salvato come 'checkout_page.png'.")
        print("Fase 1 (Aggiunta al Carrello e Navigazione Checkout) completata con successo!")

    except Exception as e:
        print(f"Si è verificato un errore: {e}")
        await page.screenshot({'path': 'error_screenshot.png', 'fullPage': True})
        print("Screenshot dell'errore salvato come 'error_screenshot.png'.")

    finally:
        print("Chiusura del browser.")
        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())

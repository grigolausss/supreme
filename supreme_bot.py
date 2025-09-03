import asyncio
import json
from pyppeteer import launch
from bs4 import BeautifulSoup

async def main(product_keywords, color=None, size=None):
    """
    Funzione principale del bot Supreme.
    Cerca un prodotto in base a parole chiave, colore e taglia, lo aggiunge al carrello
    e naviga fino alla pagina di checkout.
    """
    if not product_keywords:
        raise ValueError("È necessario fornire almeno una parola chiave per la ricerca del prodotto.")

    print("Avvio del bot Supreme...")
    browser = await launch(
        headless=True,
        args=['--no-sandbox', '--disable-setuid-sandbox']
    )
    page = await browser.newPage()
    await page.setUserAgent("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36")

    try:
        # 1. Naviga alla pagina principale
        print("Navigazione alla pagina 'shop all'...")
        await page.goto('https://eu.supreme.com/collections/all', {'waitUntil': 'networkidle2'})

        html_content = await page.content()
        soup = BeautifulSoup(html_content, 'lxml')

        # 2. Estrai e parsa il JSON dei prodotti
        products_json_script = soup.find('script', {'id': 'products-json'})
        if not products_json_script:
            raise Exception("Impossibile trovare il JSON dei prodotti sulla pagina.")

        products_data = json.loads(products_json_script.string)
        products = products_data.get('products', [])

        # 3. Cerca un prodotto specifico in base ai criteri
        print(f"Ricerca del prodotto con parole chiave: {product_keywords}, colore: {color or 'qualsiasi'}...")
        target_product = None
        for product in products:
            title_lower = product['title'].lower()
            # Controlla che tutte le parole chiave siano nel titolo
            has_all_keywords = all(keyword.lower() in title_lower for keyword in product_keywords)

            if has_all_keywords and product.get('available', False):
                # Se il colore è specificato, controlla anche quello
                if color:
                    if color.lower() in product['color'].lower():
                        target_product = product
                        break  # Trovato prodotto e colore
                else:
                    # Se non è specificato un colore, il primo prodotto che matcha le keyword va bene
                    target_product = product
                    break

        if not target_product:
            raise Exception(f"Nessun prodotto disponibile trovato con i criteri: {product_keywords}, Colore: {color}")

        product_relative_url = target_product['url']
        print(f"Prodotto trovato: {target_product['title']} - {target_product['color']}")
        print(f"URL relativo: {product_relative_url}")

        # 4. Clicca sul link del prodotto
        product_link_selector = f'a[href^="{product_relative_url}"]'
        print(f"Trovato il selettore del link del prodotto: {product_link_selector}")
        await page.waitForSelector(product_link_selector)
        await page.click(product_link_selector)

        print("Navigazione alla pagina del prodotto tramite click...")

        # 5. Seleziona la taglia specifica e aggiungi al carrello
        size_selector = 'select[data-testid="size-dropdown"]'
        add_to_cart_selector = 'button[data-testid="add-to-cart-button"]'

        print("Attendo che la pagina del prodotto sia completamente caricata...")
        await page.waitForSelector(size_selector, {'timeout': 10000})
        print("Selettore della taglia trovato.")

        if size:
            print(f"Cerco la taglia specifica: {size}...")
            # Cerca l'opzione che corrisponde alla taglia richiesta
            option_to_select = await page.evaluate(f'''(size_text) => {{
                const select = document.querySelector('{size_selector}');
                if (!select) return null;
                for (let i = 0; i < select.options.length; i++) {{
                    if (select.options[i].text.toLowerCase().trim() === size_text.toLowerCase().trim() && !select.options[i].disabled) {{
                        return select.options[i].value;
                    }}
                }}
                return null; // Taglia non trovata o non disponibile
            }}''', size)

            if option_to_select:
                await page.select(size_selector, option_to_select)
                print(f"Taglia '{size}' selezionata.")
            else:
                raise Exception(f"Taglia '{size}' non trovata o non disponibile per questo prodotto.")
        else:
            print("Nessuna taglia specifica richiesta, si procede con quella di default o la prima disponibile.")
            # (La logica per selezionare la prima disponibile potrebbe essere aggiunta qui se necessario)

        await page.waitForSelector(add_to_cart_selector, {'visible': True})
        await page.click(add_to_cart_selector)
        print("Prodotto aggiunto al carrello.")

        # 6. Naviga alla pagina di checkout
        print("Attendo la comparsa della conferma nel carrello...")
        mini_cart_selector = 'div[data-testid="mini-cart"]'
        await page.waitForSelector(mini_cart_selector, {'visible': True, 'timeout': 10000})
        print("Conferma carrello apparsa. Navigazione diretta alla pagina di checkout...")
        checkout_url = 'https://eu.supreme.com/checkout'
        await page.goto(checkout_url, {'waitUntil': 'networkidle2'})

        # 7. Verifica di essere sulla pagina di checkout
        print("Verifico il caricamento della pagina di checkout...")
        checkout_button_selector = '#checkout-pay-button'
        await page.waitForSelector(checkout_button_selector, {'timeout': 20000})

        print("Checkout raggiunto con successo!")
        await page.screenshot({'path': 'final_checkout_page.png', 'fullPage': True})
        print("Screenshot salvato come 'final_checkout_page.png'.")
        print("FASE 2 (Ricerca prodotto e taglia) completata con successo!")

    except Exception as e:
        print(f"Si è verificato un errore: {e}")
        await page.screenshot({'path': 'error_screenshot.png', 'fullPage': True})
        print("Screenshot dell'errore salvato come 'error_screenshot.png'.")

    finally:
        print("Chiusura del browser.")
        await browser.close()

if __name__ == '__main__':
    # --- ESEMPIO DI UTILIZZO ---
    # Modifica queste variabili per testare diverse ricerche

    # Esempio 1: Cerca una T-shirt qualsiasi
    # target_keywords = ["Tee"]
    # target_color = None
    # target_size = "Large"

    # Modifica queste variabili per testare diverse ricerche.
    # Il bot cercherà un prodotto che contenga TUTTE le parole chiave nel titolo.
    # Il colore e la taglia sono opzionali, ma se specificati devono corrispondere.

    target_keywords = ["Sleeve Patch Hooded Sweatshirt"]
    target_color = "Black"
    target_size = "Medium"

    print("--- AVVIO BOT CON I SEGUENTI CRITERI ---")
    print(f"Parole Chiave: {target_keywords}")
    print(f"Colore: {target_color or 'Qualsiasi'}")
    print(f"Taglia: {target_size or 'Qualsiasi'}")
    print("------------------------------------")

    asyncio.run(main(product_keywords=target_keywords, color=target_color, size=target_size))

import requests
import pandas as pd
import time
import json
import ast
from bs4 import BeautifulSoup

# --- CONFIGURATION ---
API_URL = "https://aucs34.ksearchnet.com/cs/v2/search" 
TOTAL_PRODUCTS_TO_FETCH = 20000
BATCH_SIZE = 2000 
API_KEY = "klevu-173190000117617559"
OUT_CSV = "briscoes_products_clean.csv"

headers = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# --- 1. ROBUST PARSER ---
def parse_rich_data(raw_data):
    """
    Aggressively tries to turn the string data into a Python list/dict.
    """
    if not raw_data: return []
    
    # Clean up common string issues before parsing
    if isinstance(raw_data, str):
        # Remove escape characters that might confuse the parser if double encoded
        clean_str = raw_data.replace('\\"', '"').replace('\\/', '/')
        if clean_str.startswith('"') and clean_str.endswith('"'):
            clean_str = clean_str[1:-1]
            
        try:
            return json.loads(clean_str)
        except:
            try:
                return ast.literal_eval(clean_str)
            except:
                return []
    return raw_data

# --- 2. HTML CLEANER ---
def clean_html(html_text):
    if not html_text or not isinstance(html_text, str): return ""
    try:
        return BeautifulSoup(html_text, "html.parser").get_text(separator=" ", strip=True)
    except:
        return html_text

# --- 3. THE "FORCE FIX" PRICE EXTRACTOR ---
def extract_true_prices(item, rich_data_list):
    """
    Prioritizes the hidden 'additionalData' for pricing.
    """
    # Default to top-level (The "Bad" Data)
    orig = item.get("price")
    sale = item.get("salePrice")
    
    # Try to find the "Good" Data in the rich list
    if rich_data_list and isinstance(rich_data_list, list):
        # Usually the first item in this list corresponds to the main product
        rich_item = rich_data_list[0]
        
        if isinstance(rich_item, dict):
            # Klevu often stores the REAL original price in 'price' inside this hidden block
            hidden_price = rich_item.get("price")
            hidden_special = rich_item.get("special_price")
            
            # If we found a hidden price that is higher than the sale price, use it!
            if hidden_price:
                # Convert to float to compare safely
                try:
                    hp = float(hidden_price)
                    hs = float(hidden_special) if hidden_special else 0
                    
                    if hp > 0:
                        orig = hidden_price # Found the $199.99!
                    if hs > 0:
                        sale = hidden_special # Found the $49.00!
                        
                except (ValueError, TypeError):
                    pass # Keep defaults if conversion fails

    # Final cleanup: If Sale is same as Orig, and we didn't find a special price, 
    # it might not be on sale, or data is missing.
    return orig, sale

# --- MAIN SCRIPT ---
base_payload = {
    "context": {"apiKeys": [API_KEY]},
    "recordQueries": [{
        "id": "productList",
        "typeOfRequest": "SEARCH",
        "settings": {
            "query": {"term": "*"},
            "limit": BATCH_SIZE,
            "typeOfRecords": ["KLEVU_PRODUCT"],
            "offset": 0,
            "searchPrefs": ["searchCompoundsAsAndQuery", "hideOutOfStockProducts"],
            "sort": "RELEVANCE",
            "fields": [
                "displayTitle", "name", "price", "salePrice", "url", "category", 
                "productplu", "sku", "type_id", "additionalDataToReturn", "stock_status", "desc"
            ]
        }
    }]
}

clean_data = []

print(f"Starting scrape...")

for offset in range(0, TOTAL_PRODUCTS_TO_FETCH, BATCH_SIZE):
    print(f"Fetching records {offset} to {offset + BATCH_SIZE}...")
    base_payload["recordQueries"][0]["settings"]["offset"] = offset
    
    try:
        response = requests.post(API_URL, json=base_payload, headers=headers)
        if response.status_code != 200: break

        data = response.json()
        records = data.get("queryResults", [{}])[0].get("records", [])
        
        if not records: break
        
        for item in records:
            try:
                # 1. Aggressively parse the hidden data
                raw_rich = item.get("additionalDataToReturn")
                rich_data_list = parse_rich_data(raw_rich)
                
                # 2. Get the TRUE prices
                orig_price, sale_price = extract_true_prices(item, rich_data_list)

                # DEBUG PRINT for the specific Air Fryer to prove it works
                if "1116839" in str(item.get("sku")):
                    print(f"!!! DEBUG ZIP AIR FRYER !!! Found Orig: {orig_price}, Sale: {sale_price}")

                # 3. Handle Variants vs Simple
                is_configurable = item.get("type_id") == "configurable"
                
                if is_configurable and rich_data_list:
                    # Explode variants
                    for variant in rich_data_list:
                        if not isinstance(variant, dict): continue
                        
                        # Variant specific prices
                        v_orig = variant.get("price", orig_price)
                        v_sale = variant.get("special_price", sale_price)

                        # Variant Title
                        opts = []
                        if variant.get("color"): opts.append(variant.get("color").strip())
                        if variant.get("size"): opts.append(variant.get("size").strip())
                        suffix = f" - ({', '.join(opts)})" if opts else ""

                        clean_data.append({
                            "Title": item.get("name") + suffix,
                            "Original Price": v_orig,
                            "Sale Price": v_sale,
                            "Category": item.get("category"),
                            "Product ID": variant.get("sku"),
                            "Link": item.get("url"),
                            "Description": clean_html(item.get("desc")),
                            "Stock Status": "In Stock"
                        })
                else:
                    # Simple Product
                    clean_data.append({
                        "Title": item.get("name"),
                        "Original Price": orig_price,
                        "Sale Price": sale_price,
                        "Category": item.get("category"),
                        "Product ID": item.get("sku"),
                        "Link": item.get("url"),
                        "Description": clean_html(item.get("desc")),
                        "Stock Status": item.get("stock_status")
                    })

            except Exception as e:
                continue

    except Exception as e:
        print(f"Error: {e}")
        break
        
    time.sleep(0.5)

# --- SAVE ---
if clean_data:
    df = pd.DataFrame(clean_data)
    # Convert prices to numeric to force proper formatting (optional)
    # df['Original Price'] = pd.to_numeric(df['Original Price'], errors='coerce')
    # df['Sale Price'] = pd.to_numeric(df['Sale Price'], errors='coerce')
    
    df.to_csv(OUT_CSV, index=False)
    print(f"Saved {len(clean_data)} products to {OUT_CSV}")

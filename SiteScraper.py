import requests
import pandas as pd
import time

# --- CONFIGURATION ---
# 1. URL (Briscoes Search API)
API_URL = "https://aucs34.ksearchnet.com/cs/v2/search" 

# 2. Settings
TOTAL_PRODUCTS_TO_FETCH = 14000
BATCH_SIZE = 1000
API_KEY = "klevu-173190000117617559"

headers = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Base Request Payload
base_payload = {
    "context": {"apiKeys": [API_KEY]},
    "recordQueries": [{
        "id": "productList",
        "typeOfRequest": "SEARCH",
        "settings": {
            "query": {"term": "*"},
            "id": "productList",
            "limit": BATCH_SIZE,
            "typeOfRecords": ["KLEVU_PRODUCT"],
            "offset": 0,
            "searchPrefs": ["searchCompoundsAsAndQuery", "hideOutOfStockProducts"],
            "sort": "RELEVANCE",
            # We request fields, but we will filter them in Python below
            "fields": ["displayTitle", "price", "salePrice", "url", "category", "productplu"]
        }
    }]
}

# This list will hold our clean, filtered dictionaries
clean_data = []

print(f"Starting scrape for {TOTAL_PRODUCTS_TO_FETCH} products...")

for offset in range(0, TOTAL_PRODUCTS_TO_FETCH, BATCH_SIZE):
    print(f"Fetching records {offset} to {offset + BATCH_SIZE}...")
    
    base_payload["recordQueries"][0]["settings"]["offset"] = offset
    
    try:
        response = requests.post(API_URL, json=base_payload, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            try:
                results = data.get("queryResults", [])
                if results:
                    records = results[0].get("records", [])
                    if not records:
                        break
                    
                    # --- EXTRACTION LOGIC ---
                    for item in records:
                        # We build a dictionary with ONLY the columns you want
                        product = {
                            "Title": item.get("displayTitle"),
                            "Original Price": item.get("price"),
                            "Sale Price": item.get("salePrice"),
                            "Link": item.get("url"),
                            "Category": item.get("category"),
                            "Product ID": item.get("productplu") 
                        }
                        clean_data.append(product)
                else:
                    break
            except Exception as e:
                print(f"Error parsing JSON: {e}")
                break
        else:
            print(f"Failed request. Status: {response.status_code}")
            break
            
    except Exception as e:
        print(f"Network error: {e}")
        break

    time.sleep(0.5) # Short pause to be polite

# --- SAVE TO CSV ---
print(f"Total products scraped: {len(clean_data)}")

if clean_data:
    df = pd.DataFrame(clean_data)
    # Save to CSV
    df.to_csv("briscoes_products_clean.csv", index=False)
    print("Saved to briscoes_products_clean.csv")
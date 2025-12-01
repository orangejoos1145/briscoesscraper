import pandas as pd
import html
import json
import os
from datetime import datetime
import pytz  # <--- Essential for NZ Time

# ---- Configuration ----
IN_CSV = "briscoes_products_clean.csv"
OUT_HTML = "briscoes_deals.html"
WHATS_NEW_FILE = "whatsnew.txt"

# ---- SUPER CATEGORY MAPPING ----
CATEGORY_MAPPINGS = {
    "Kitchen & Cooking": [
        "fry", "cook", "pan", "pot", "knife", "cutlery", "baking", "kitchen", 
        "toaster", "kettle", "coffee", "blender", "mixer", "food processor", 
        "microwave", "soda", "nespresso", "mug", "glass", "dinner", "plate", 
        "bowl", "serve", "napkin", "tablecloth", "crockpot", "breville", 
        "delonghi", "kenwood", "zip", "russell hobbs", "sunbeam", "ninja"
    ],
    "Bedroom & Bedding": [
        "bed", "sheet", "pillow", "quilt", "duvet", "blanket", "mattress", 
        "protector", "coverlet", "valance", "headboard"
    ],
    "Bathroom & Laundry": [
        "towel", "bath", "mat", "scale", "toilet", "laundry", "iron", 
        "hamper", "basket", "shower", "face cloth", "robe"
    ],
    "Home Decor & Living": [
        "rug", "cushion", "throw", "curtain", "blind", "lamp", "mirror", 
        "vase", "candle", "decor", "clock", "frame", "furniture", "chair", 
        "table", "ottoman", "storage", "bin", "heater", "fan", "dehumidifier"
    ],
    "Electrical & Personal Care": [
        "vacuum", "cleaner", "purifier", "hair", "shaver", "grooming", 
        "massager", "electric blanket", "tooth", "remington", "vs sassoon", 
        "braun", "philips", "oral b"
    ],
    "Travel & Luggage": [
        "suit", "case", "luggage", "bag", "travel", "adapter", "neck", 
        "samsonite", "american tourister"
    ],
    "Outdoor & Leisure": [
        "bbq", "picnic", "outdoor", "camping", "beach", "cooler", "chilly"
    ]
}

def get_super_category(raw_cat):
    if pd.isna(raw_cat): return "Other"
    cat_lower = str(raw_cat).lower()
    for super_cat, keywords in CATEGORY_MAPPINGS.items():
        for keyword in keywords:
            if keyword in cat_lower:
                return super_cat
    return "Other / Brands"

# ---- Utility Functions ----
def esc(x):
    if pd.isna(x): return ""
    return html.escape(str(x)).replace("\n", " ").replace("\r", " ").replace(",", "&#44;")

def to_numeric_price(val):
    try:
        if pd.isna(val) or val == "": return None
        s = str(val).strip().replace("$", "").replace(",", "")
        return float(s)
    except Exception: return None

def fmt_price(val):
    try:
        if pd.isna(val) or val == "": return ""
        v = float(str(val).replace("$", "").replace(",", ""))
        return f"${v:,.2f}"
    except Exception:
        return esc(str(val).strip())

def generate_category_filters_html(cat_list):
    if not cat_list: return ""
    sorted_cats = sorted([c for c in cat_list if c != "Other / Brands"])
    if "Other / Brands" in cat_list:
        sorted_cats.append("Other / Brands")
    html_out = '<div class="controls-promo-filters">'
    html_out += '<span class="small" style="color: var(--muted); font-size: 14px; margin-right: 5px;">Filter By Section:</span>'
    html_out += '<button class="btn toggle active" data-cat="all">All</button>'
    for cat in sorted_cats:
        cat_esc = esc(cat)
        html_out += f'<button class="btn toggle cat-filter-btn" data-cat="{cat_esc.lower()}">{cat_esc}</button>'
    html_out += "</div>"
    return html_out

# ---- Main Processing ----

# Load Data
try:
    df = pd.read_csv(IN_CSV)
    print(f"Loaded {len(df)} rows from {IN_CSV}")
except FileNotFoundError:
    print(f"Warning: {IN_CSV} not found. Using placeholder data.")
    df = pd.DataFrame(columns=["Title","Original Price","Sale Price","Link","Category","Product ID"])

deals_payload = []
unique_categories = set()

for idx, row in df.iterrows():
    pid = str(row.get("Product ID", "") or "")
    display_title = str(row.get("Title", "Unknown Product"))
    link_url = str(row.get("Link", "#"))
    
    orig_raw = row.get("Original Price")
    sale_raw = row.get("Sale Price")
    
    orig_val = to_numeric_price(orig_raw)
    disc_val = to_numeric_price(sale_raw)
    
    pct_val = 0
    if orig_val and disc_val and orig_val > 0:
        pct_val = ((orig_val - disc_val) / orig_val) * 100
    
    if not orig_val and disc_val:
        orig_val = disc_val
        
    raw_cat_str = str(row.get("Category", "Other"))
    if pd.isna(raw_cat_str) or raw_cat_str.lower() == "nan":
        raw_cat_str = "Other"
    
    specific_category = raw_cat_str.split(';;')[0].strip()
    super_category = get_super_category(specific_category)
    unique_categories.add(super_category)

    deals_payload.append({
        "n": display_title,
        "p": pid,
        "l": link_url,
        "o": fmt_price(orig_val),
        "d": fmt_price(disc_val),
        "v": pct_val if pct_val else 0,
        "vp": disc_val if disc_val is not None else (orig_val if orig_val is not None else 0),
        "c": super_category,
        "sc": specific_category
    })

json_data = json.dumps(deals_payload)
category_filters_html = generate_category_filters_html(list(unique_categories))

# ---- TIMEZONE FIX ----
try:
    nz_tz = pytz.timezone('Pacific/Auckland')
    scrape_time_str = datetime.now(nz_tz).strftime("%d/%m/%Y @ %I:%M %p")
except Exception as e:
    print(f"Timezone Error: {e}. Falling back to UTC.")
    scrape_time_str = datetime.now().strftime("%d/%m/%Y @ %I:%M %p UTC")

# ---- WHATS NEW FIX (Safe Read) ----
whats_new_content = "No updates found."
# Check for both lowercase and capitalized filename to be safe
possible_files = ["whatsnew.txt", "WhatsNew.txt", "Whatsnew.txt"]
found_file = None

for f_name in possible_files:
    if os.path.exists(f_name):
        found_file = f_name
        break

if found_file:
    try:
        with open(found_file, "r", encoding="utf-8") as f:
            whats_new_content = f.read()
            # Convert newlines to <br> for HTML display
            whats_new_content = whats_new_content.replace("\n", "<br>")
    except Exception as e:
        print(f"Error reading whatsnew: {e}")
else:
    print("Notice: whatsnew.txt not found. Using default text.")


# ---- HTML Output ----
html_content = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>Briscoes Deal Finder</title>
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=0"/>
<script>
  (function() {{
    const theme = localStorage.getItem('theme');
    if (theme === 'dark') {{
      document.documentElement.classList.add('dark');
    }}
  }})();
</script>
<style>
  :root {{ 
    --accent: #004B8D;        
    --accent-dark: #003366; 
    --highlight: #FFCE00;     
    --highlight-hover: #e6b800;
    --bg: #f4f6f8; 
    --card: #ffffff; 
    --text: #222; 
    --muted: #666; 
    --border: #ddd; 
    --header-bg: #ffffff; 
    --row-even: #f8f9fa; 
    --row-hover: #eef1f5;
    --btn-text: #fff;
    --btn-highlight-text: #222;
  }}
  :root.dark {{ 
    --accent: #4a90e2;        
    --accent-dark: #357abd;
    --highlight: #FFCE00;     
    --highlight-hover: #e6b800;
    --bg: #121212; 
    --card: #1E1E1E; 
    --text: #E0E0E0; 
    --muted: #9E9E9E; 
    --border: #333; 
    --header-bg: #1E1E1E; 
    --row-even: #252525; 
    --row-hover: #303030;
    --btn-text: #fff;
    --btn-highlight-text: #000;
  }}
  html, body {{ width: 100%; margin: 0; padding: 0; }}
  body {{ 
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; 
    background: var(--bg); 
    color: var(--text); 
    padding: 16px; 
  }}
  .container {{ max-width: 1200px; margin: 0 auto; }}
  header {{ 
      background: var(--header-bg); 
      border-radius: 8px; 
      padding: 20px; 
      box-shadow: 0 4px 12px rgba(0,0,0,0.05); 
      border: 1px solid var(--border); 
      display: flex; flex-direction: column; gap: 15px; margin-bottom: 24px;
  }}
  .header-top {{ display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; }}
  .header-titles h1 {{ margin: 0; font-size: 24px; font-weight: 700; color: var(--accent); }}
  :root.dark .header-titles h1 {{ color: var(--text); }}
  .scrape-time {{ font-size: 13px; color: var(--muted); font-family: monospace; margin-top: 4px; }}
  .header-actions {{ display: flex; gap: 8px; align-items: center; }}
  .btn {{ background: var(--accent); color: var(--btn-text); border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: 600; text-decoration: none; display: inline-flex; align-items: center; gap: 6px; transition: all 0.2s; white-space: nowrap; }}
  .btn:hover {{ background: var(--accent-dark); }}
  .btn.action {{ background: var(--highlight); color: var(--btn-highlight-text); }}
  .btn.action:hover {{ background: var(--highlight-hover); }}
  .btn.secondary {{ background: transparent; color: var(--text); border: 1px solid var(--border); }}
  .btn.secondary:hover {{ background: var(--row-hover); }}
  .btn.coffee {{ background: #FF813F; color: #fff; }} 
  .btn.coffee:hover {{ background: #E57339; }}
  .btn.icon-btn {{ padding: 8px; width: 36px; justify-content: center; }}
  .controls-main {{ display: flex; flex-wrap: wrap; gap: 10px; align-items: center; margin-top: 10px; }}
  input, select {{ padding: 10px 12px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg); color: var(--text); font-size: 14px; outline: none; }}
  input:focus {{ border-color: var(--accent); }}
  input[type="search"] {{ min-width: 250px; flex-grow: 1; }}
  .pct-inputs {{ display: flex; align-items: center; gap: 5px; }}
  .pct-inputs input {{ width: 60px; text-align: center; }}
  .checkbox-label {{ display: flex; align-items: center; gap: 6px; font-size: 14px; color: var(--muted); cursor: pointer; user-select: none; font-weight: 500; }}
  .controls-promo-filters {{ display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-top: 15px; border-top: 1px solid var(--border); padding-top:15px; }}
  .btn.toggle {{ background: var(--bg); color: var(--muted); border: 1px solid var(--border); font-size: 13px; padding: 5px 12px; border-radius: 20px; }}
  .btn.toggle:hover {{ background: var(--row-hover); color: var(--text); }}
  .btn.toggle.active {{ background: var(--accent); color: white; border-color: var(--accent); }}
  .table-container {{ overflow-x: auto; border-radius: 8px; border: 1px solid var(--border); background: var(--card); margin-bottom: 20px; }}
  table {{ width: 100%; border-collapse: collapse; min-width: 700px; }}
  thead th {{ text-align: left; padding: 14px 16px; background: var(--header-bg); border-bottom: 1px solid var(--border); cursor: pointer; font-weight: 600; font-size: 13px; text-transform: uppercase; color: var(--muted); user-select: none; }}
  thead th:hover {{ color: var(--text); }}
  tbody td {{ padding: 14px 16px; border-top: 1px solid var(--border); font-size: 14px; vertical-align: middle; }}
  tbody tr:nth-child(even) {{ background: var(--row-even); }}
  tbody tr:hover {{ background: var(--row-hover); }}
  .price {{ font-family: monospace; font-size: 14px; color: var(--text); white-space: nowrap; }}
  .discount {{ color: #D32F2F; font-weight: 700; white-space: nowrap; }}
  :root.dark .discount {{ color: #FF5252; }}
  .google-icon {{ width: 20px; height: 20px; fill: var(--muted); vertical-align: middle; transition: fill 0.2s; }}
  tr:hover .google-icon {{ fill: var(--accent); }}
  a.product-link {{ color: var(--text); text-decoration: none; font-weight: 600; display: block; transition: color 0.15s; }}
  a.product-link:hover {{ color: var(--accent); text-decoration: underline; }}
  .pagination-bar {{ display: flex; justify-content: space-between; align-items: center; padding: 12px; background: var(--header-bg); border: 1px solid var(--border); border-radius: 8px; color: var(--muted); font-size: 14px; }}
  .modal-overlay {{ position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.7); display: none; align-items: center; justify-content: center; z-index: 1000; backdrop-filter: blur(2px); }}
  .modal-content {{ background: var(--card); padding: 25px; border-radius: 12px; width: 90%; max-width: 600px; max-height: 80vh; display: flex; flex-direction: column; box-shadow: 0 10px 25px rgba(0,0,0,0.5); border: 1px solid var(--border); }}
  .modal-header {{ display: flex; justify-content: space-between; border-bottom: 1px solid var(--border); padding-bottom: 15px; margin-bottom: 15px; }}
  .modal-close-btn {{ background: none; border: none; font-size: 24px; cursor: pointer; color: var(--muted); }}
  @media (max-width: 768px) {{
    .header-top {{ flex-direction: column; align-items: flex-start; }}
    .header-actions {{ width: 100%; justify-content: space-between; margin-top: 10px; }}
    .controls-main {{ flex-direction: column; align-items: stretch; }}
    input[type="search"] {{ width: 100%; }}
    .pct-inputs {{ justify-content: space-between; }}
    .pct-inputs input {{ width: 45%; }}
    thead th:nth-child(1), tbody td:nth-child(1) {{ display: none; }}
    thead th:nth-child(3), tbody td:nth-child(3) {{ display: none; }}
    .pagination-bar {{ flex-direction: column; gap: 10px; text-align: center; }}
  }}
</style>
</head>
<body>
<div class="container">
  <header>
    <div class="header-top">
      <div class="header-titles">
        <h1>Briscoes Deal Finder</h1>
        <div class="scrape-time">Last updated: {scrape_time_str}</div>
      </div>
      <div class="header-actions">
        <button class="btn secondary" id="whatsNewBtn">What's New</button>
        <a href="https://www.buymeacoffee.com/polobaggyo" target="_blank" class="btn coffee">☕ Coffee</a>
        <button class="btn icon-btn secondary" id="toggleThemeBtn" title="Toggle Theme">☀️</button>
      </div>
    </div>
    <div class="controls-main">
      <input id="searchInput" type="search" placeholder="Search products..." />
      <button class="btn action" id="searchBtn">Search</button>
      <div class="pct-inputs">
        <span style="font-size:13px; color:var(--muted)">Discount %</span>
        <input id="minPct" type="number" min="0" max="100" placeholder="0" value="0" />
        <input id="maxPct" type="number" min="0" max="100" placeholder="100" value="100" />
      </div>
      <label class="checkbox-label"><input type="checkbox" id="hideZero" checked> Hide 0% Off</label>
      <button class="btn secondary" id="resetBtn">Reset</button>
    </div>
    <div style="display:flex; justify-content:flex-end; margin-top:5px; gap:15px; font-size:13px; color:var(--muted);">
         <span>Found: <strong id="visibleCount" style="color:var(--text)">0</strong></span>
    </div>
    {category_filters_html}
  </header>
  <div class="table-container">
    <table id="dealsTable">
      <thead>
        <tr>
          <th data-sort="p">ID</th>
          <th data-sort="n">Title</th>
          <th data-sort="vp">Original</th>
          <th data-sort="vp">Sale Price</th>
          <th data-sort="v">% Off</th>
          <th data-sort="c">Category</th>
          <th>G</th>
        </tr>
      </thead>
      <tbody id="tableBody"></tbody>
    </table>
  </div>
  <div class="pagination-bar">
    <div>
        Rows: 
        <select id="rowsPerPage">
            <option value="50">50</option>
            <option value="100" selected>100</option>
            <option value="200">200</option>
            <option value="1000">All</option>
        </select>
    </div>
    <div id="pageInfo">Page 1</div>
    <div style="display:flex; gap:5px;">
        <button class="btn secondary" id="btnPrev">Prev</button>
        <button class="btn secondary" id="btnNext">Next</button>
    </div>
  </div>
</div>
<div id="whatsNewModal" class="modal-overlay">
  <div class="modal-content">
    <div class="modal-header">
      <h2 style="color:var(--text)">What's New</h2>
      <button id="closeWhatsNewBtn" class="modal-close-btn">&times;</button>
    </div>
    <div class="modal-body">{whats_new_content}</div>
  </div>
</div>
<script>
const allData = {json_data};
const googleIconSvg = '<svg class="google-icon" viewBox="0 0 24 24"><path d="M12.48 10.92v3.28h7.84c-.24 1.84-.853 3.187-1.787 4.133-1.147 1.147-2.933 2.4-6.053 2.4-4.827 0-8.6-3.893-8.6-8.72s3.773-8.72 8.6-8.72c2.6 0 4.507 1.027 5.907 2.347l2.307-2.307C18.747 1.44 16.133 0 12.48 0 5.867 0 .533 5.333.533 12S5.867 24 12.48 24c3.44 0 6.04-1.133 8.147-3.333 2.147-2.147 2.813-5.013 2.813-7.387 0-.747-.053-1.44-.16-2.107H12.48z"/></svg>';
let state = {{ filtered: [], currentPage: 1, rowsPerPage: 100, sortCol: 'v', sortDir: 'desc', search: '', minPct: 0, maxPct: 100, activeCategory: 'all', hideZero: true }};
const tbody = document.getElementById('tableBody');
const countEl = document.getElementById('visibleCount');
function init() {{ state.filtered = [...allData]; applyFilters(); setupListeners(); renderPage(); }}
function escapeHtml(text) {{ if (!text) return ''; return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;"); }}
function renderPage() {{
    const start = (state.currentPage - 1) * state.rowsPerPage;
    const end = start + state.rowsPerPage;
    const slice = state.filtered.slice(start, end);
    let html = '';
    slice.forEach(d => {{
        const googleLink = `https://www.google.com/search?q=${{encodeURIComponent(d.n)}}`;
        let linkHtml = `<span class="product-link">${{escapeHtml(d.n)}}</span>`;
        if (d.l && d.l !== '#') {{ linkHtml = `<a class="product-link" href="${{d.l}}" target="_blank">${{escapeHtml(d.n)}}</a>`; }}
        let pctDisplay = '';
        if (d.v > 0) {{ pctDisplay = `${{Math.round(d.v)}}%`; }}
        html += `<tr><td style="font-family:monospace; color:var(--muted); font-size:12px;">${{escapeHtml(d.p)}}</td><td>${{linkHtml}}</td><td class="price" style="text-decoration:line-through; color:var(--muted);">${{d.o}}</td><td class="price" style="font-weight:bold;">${{d.d}}</td><td class="discount">${{pctDisplay}}</td><td><span style="background:var(--row-hover); padding:2px 8px; border-radius:4px; font-size:12px; white-space:nowrap;">${{escapeHtml(d.sc)}}</span></td><td style="text-align:center;"><a href="${{googleLink}}" target="_blank">${{googleIconSvg}}</a></td></tr>`;
    }});
    if (slice.length === 0) {{ html = '<tr><td colspan="7" style="text-align:center; padding:20px;">No deals found matching filters.</td></tr>'; }}
    tbody.innerHTML = html;
    const total = state.filtered.length;
    const maxPage = Math.ceil(total / state.rowsPerPage) || 1;
    document.getElementById('pageInfo').innerText = `Page ${{state.currentPage}} of ${{maxPage}}`;
    document.getElementById('btnPrev').disabled = state.currentPage === 1;
    document.getElementById('btnNext').disabled = state.currentPage >= maxPage;
    countEl.innerText = total;
}}
function applyFilters() {{
    const term = state.search.toLowerCase();
    state.filtered = allData.filter(d => {{
        if (state.activeCategory !== 'all' && (!d.c || d.c.toLowerCase() !== state.activeCategory)) return false;
        if (state.hideZero && d.v <= 0) return false;
        if (d.v < state.minPct || d.v > state.maxPct) return false;
        if (term && !(d.n + ' ' + d.sc + ' ' + d.p).toLowerCase().includes(term)) return false;
        return true;
    }});
    state.currentPage = 1; sortData();
}}
function sortData() {{
    const col = state.sortCol; const dir = state.sortDir === 'asc' ? 1 : -1;
    state.filtered.sort((a, b) => {{
        let valA = a[col]; let valB = b[col];
        if (typeof valA === 'string') valA = valA.toLowerCase(); if (typeof valB === 'string') valB = valB.toLowerCase();
        if (col === 'vp') {{ valA = a.vp; valB = b.vp; }}
        if (valA < valB) return -1 * dir; if (valA > valB) return 1 * dir; return 0;
    }});
    renderPage();
}}
function setupListeners() {{
    const debounce = (fn, delay) => {{ let t; return (...args) => {{ clearTimeout(t); t = setTimeout(()=>fn(...args), delay); }}; }};
    const runFilter = debounce(() => {{ applyFilters(); renderPage(); }}, 200);
    document.getElementById('searchInput').addEventListener('input', e => {{ state.search = e.target.value; runFilter(); }});
    document.getElementById('minPct').addEventListener('input', e => {{ state.minPct = parseFloat(e.target.value) || 0; runFilter(); }});
    document.getElementById('maxPct').addEventListener('input', e => {{ state.maxPct = parseFloat(e.target.value) || 100; runFilter(); }});
    document.getElementById('hideZero').addEventListener('change', e => {{ state.hideZero = e.target.checked; applyFilters(); renderPage(); }});
    document.querySelectorAll('.cat-filter-btn, [data-cat="all"]').forEach(btn => {{ btn.addEventListener('click', (e) => {{ document.querySelectorAll('.cat-filter-btn, [data-cat="all"]').forEach(b => b.classList.remove('active')); e.currentTarget.classList.add('active'); state.activeCategory = e.currentTarget.getAttribute('data-cat'); applyFilters(); renderPage(); }}); }});
    document.getElementById('resetBtn').addEventListener('click', () => {{ state.search = ''; state.minPct = 0; state.maxPct = 100; state.activeCategory = 'all'; state.hideZero = true; document.getElementById('searchInput').value = ''; document.getElementById('minPct').value = 0; document.getElementById('maxPct').value = 100; document.getElementById('hideZero').checked = true; document.querySelectorAll('.cat-filter-btn').forEach(b => b.classList.remove('active')); document.querySelector('[data-cat="all"]').classList.add('active'); applyFilters(); renderPage(); }});
    document.querySelectorAll('th[data-sort]').forEach(th => {{ th.addEventListener('click', () => {{ const col = th.dataset.sort; if (state.sortCol === col) {{ state.sortDir = state.sortDir === 'asc' ? 'desc' : 'asc'; }} else {{ state.sortCol = col; state.sortDir = 'desc'; }} sortData(); }}); }});
    document.getElementById('rowsPerPage').addEventListener('change', e => {{ state.rowsPerPage = parseInt(e.target.value); state.currentPage = 1; renderPage(); }});
    document.getElementById('btnPrev').addEventListener('click', () => {{ if(state.currentPage > 1) {{ state.currentPage--; renderPage(); }} }});
    document.getElementById('btnNext').addEventListener('click', () => {{ const max = Math.ceil(state.filtered.length / state.rowsPerPage); if(state.currentPage < max) {{ state.currentPage++; renderPage(); }} }});
    const toggleTheme = document.getElementById('toggleThemeBtn');
    function updateThemeIcon(isDark) {{ toggleTheme.textContent = isDark ? '🌙' : '☀️'; }}
    toggleTheme.addEventListener('click', () => {{ const isDark = document.documentElement.classList.toggle('dark'); localStorage.setItem('theme', isDark ? 'dark' : 'light'); updateThemeIcon(isDark); }});
    updateThemeIcon(document.documentElement.classList.contains('dark'));
    const modal = document.getElementById('whatsNewModal');
    document.getElementById('whatsNewBtn').addEventListener('click', () => modal.style.display = 'flex');
    document.getElementById('closeWhatsNewBtn').addEventListener('click', () => modal.style.display = 'none');
    modal.addEventListener('click', (e) => {{ if (e.target === modal) modal.style.display = 'none'; }});
}}
init();
</script>
</body>
</html>
"""

with open(OUT_HTML, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"✅ Generated {OUT_HTML} successfully.")

from flask import Flask, request, render_template, send_file, flash
import io
import csv
import json
import requests
from bs4 import BeautifulSoup
import re
from html import unescape

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Required for flashing messages

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
}

def extract_needed_data(json_data):
    if isinstance(json_data, str):
        json_data = json.loads(json_data)

    resId = str(json_data.get("pages", {}).get('current', {}).get("resId"))
    menus = json_data.get("pages", {}).get('restaurant', {}).get(resId, {}).get("order", {}).get("menuList", {}).get("menus", [])
    name = json_data.get("pages", {}).get('restaurant', {}).get(resId, {}).get("sections", {}).get("SECTION_BASIC_INFO", {}).get('name', 'Restaurant')

    filtered_data = []
    for menu in menus:
        category_name = menu.get("menu", {}).get("name", "")
        for category in menu.get("menu", {}).get("categories", []):
            sub_category_name = category.get("category", {}).get("name", "")
            for item in category.get("category", {}).get("items", []):
                item_data = item["item"]
                filtered_data.append({
                    "Restaurant": name,
                    "Category": category_name,
                    "Sub-category": sub_category_name,
                    "Veg/NonVeg": ','.join(item_data.get("dietary_slugs", [])) or "N/A",
                    "Item Name": item_data.get("name", ""),
                    "Price": item_data.get("display_price", ""),
                    "Description": item_data.get("desc", "")
                })
    return filtered_data

def scrape_menu(url):
    if not url.endswith('/order'):
        url += '/order'

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except requests.RequestException as e:
        return None, f"Error fetching the page: {e}"

    soup = BeautifulSoup(response.text, 'html.parser')
    scripts = soup.find_all('script')
    preloaded_state = None
    for script in scripts:
        if 'window.__PRELOADED_STATE__' in script.text:
            match = re.search(r'window\.__PRELOADED_STATE__ = JSON\.parse\((.+?)\);', script.text)
            if match:
                try:
                    escaped_json = match.group(1)
                    decoded_json_str = unescape(escaped_json)
                    parsed_json = json.loads(decoded_json_str)
                    preloaded_state = json.loads(parsed_json)
                    break
                except Exception as e:
                    return None, f"Error parsing embedded JSON data: {e}"
    if preloaded_state is None:
        return None, "No embedded menu data found on the page."

    data = extract_needed_data(preloaded_state)
    if not data:
        return None, "No menu data extracted."
    return data, None

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form.get('url', '').strip()
        if not url:
            flash("Please enter a valid Zomato restaurant URL.", "error")
            return render_template('index.html', menu=None)

        data, error = scrape_menu(url)
        if error:
            flash(error, "error")
            return render_template('index.html', menu=None)

        # Create CSV in memory
        si = io.StringIO()
        fieldnames = ["Restaurant", "Category", "Sub-category", "Veg/NonVeg", "Item Name", "Price", "Description"]
        writer = csv.DictWriter(si, fieldnames=fieldnames)
        writer.writeheader()
        for row in data:
            writer.writerow(row)

        # Prepare the CSV for download
        mem = io.BytesIO()
        mem.write(si.getvalue().encode('utf-8'))
        mem.seek(0)
        filename = "zomato_menu.csv"

        return send_file(
            mem,
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )

    return render_template('index.html', menu=None)

if __name__ == '__main__':
    app.run(debug=True)


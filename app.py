from flask import Flask, request, jsonify
import os
import json
import requests
import pandas as pd
import csv
from bs4 import BeautifulSoup
import re
from html import unescape

app = Flask(__name__)

# User-agent header to mimic a web browser's request
headers = {
    'User -Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
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
                    "restaurant": name,
                    "category": category_name,
                    "sub_category": sub_category_name,
                    "dietary_slugs": ','.join(item_data.get("dietary_slugs", [])),
                    "item_name": item_data.get("name", ""),
                    "price": item_data.get("display_price", ""),
                    "desc": item_data.get("desc", "")
                })

    return filtered_data, name

@app.route('/get_menu', methods=['POST'])
def get_menu():
    url = request.json.get('url')
    if not url.endswith('/order'):
        url += '/order'

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 400

    soup = BeautifulSoup(response.text, 'html.parser')
    scripts = soup.find_all('script')
    for script in scripts:
        if 'window.__PRELOADED_STATE__' in script.text:
            match = re.search(r'window\.__PRELOADED_STATE__ = JSON\.parse\((.+?)\);', script.text)
            if match:
                try:
                    escaped_json = match.group(1)
                    decoded_json_str = unescape(escaped_json)
                    parsed_json = json.loads(decoded_json_str)
                    preloaded_state = json.loads(parsed_json)

                    flat_data, restaurant_name = extract_needed_data(preloaded_state)
                    return jsonify(flat_data)

                except Exception as e:
                    return jsonify({"error": "Error parsing embedded JSON: " + str(e)}), 400

    return jsonify({"error": "No embedded menu data found on this page."}), 404

if __name__ == "__main__":
    app.run(debug=True)

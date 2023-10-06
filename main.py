import requests
from bs4 import BeautifulSoup
import csv
import os
from urllib.parse import urlparse
import time

def get_categories(base_url):
    response = requests.get(base_url)
    categories = []
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        nav_container = soup.find('ul', class_='nav navbar-nav')
        if nav_container:
            links = nav_container.find_all('a', attrs={'data-toggle': 'dropdown'})
            categories = [(link.string, link['href']) for link in links]
    return categories

def get_info_from_page(page_url):
    products = []
    try:
        response = requests.get(page_url)
        response.raise_for_status()

        if response.status_code == 403:
            print("Доступ запрещен. Возможно, ваш IP был временно заблокирован.")
            return [], None
        elif response.status_code == 404:
            print("Страница не найдена.")
            return [], None

        soup = BeautifulSoup(response.content, 'html.parser')
        product_thumbs = soup.find_all('div', class_='product-thumb')
        for thumb in product_thumbs:
            caption = thumb.find('div', class_='caption')
            if caption:
                h4_element = caption.find('h4')
                if h4_element and h4_element.a:
                    product_name = h4_element.a.string
                    product_link = h4_element.a['href']
                    
                    product_path = urlparse(product_link).path
                    product_id = product_path.split('/')[-1]
                    
                    stock_status_rows = caption.find_all('div', style="width:100%;display: table-row;")
                    rostov_stock_total = 0

                    for row in stock_status_rows:
                        stock_info = row.find('div', style="display: table-cell;width:85%;text-align: left;").get_text(strip=True)
                        if "Ростов" in stock_info:
                            img_element = row.find('img')
                            if img_element:
                                img_src = img_element['src']
                                if img_src == "/catalog/view/theme/default/image/max-min.png":
                                    rostov_stock_total += 20
                                elif img_src == "/catalog/view/theme/default/image/1-5-min.png":
                                    rostov_stock_total += 1
                                elif img_src == "/catalog/view/theme/default/image/5-20-min.png":
                                    rostov_stock_total += 5

                    products.append((product_name, product_link, product_id, rostov_stock_total))
        return products, soup

    except requests.RequestException as e:
        print(f"Произошла ошибка при запросе к {page_url}: {e}")
        return [], None

def get_info_from_category(category_url):
    all_products = []
    page_idx = 1
    while category_url:
        products, soup = get_info_from_page(category_url)
        all_products.extend(products)
        print(f"\nPage {page_idx}:")
        for product_name, product_link, product_id, stock_total in products:
            print(f"  Product: {product_name} - {product_link} | Stock Total: {stock_total}")

        pagination = soup.find('ul', class_='pagination')
        next_page_elem = pagination.find('li', class_='active').find_next_sibling('li') if pagination else None
        category_url = next_page_elem.a['href'] if next_page_elem else None
        page_idx += 1

    return all_products

def write_to_csv(data, filename="products.csv"):
    file_exists = os.path.isfile(filename)
    with open(filename, "a", newline='', encoding="utf-8") as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(["Category", "Name", "ID", "Link", "Stock Total"])
        writer.writerows(data)

base_url = 'https://b2b.zip161.ru/'
categories = get_categories(base_url)
for category_name, category_link in categories:
    print(f"\nCategory: {category_name}")
    products = get_info_from_category(category_link)
    write_to_csv([(category_name, product[0], product[2], product[1], product[3]) for product in products])

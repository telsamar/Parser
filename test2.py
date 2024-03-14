import requests
from bs4 import BeautifulSoup
import csv
import os
from urllib.parse import urljoin
import time

def get_categories(session, base_url):
    categories = {}
    response = session.get(base_url)
    soup = BeautifulSoup(response.text, 'html.parser')

    category_links = soup.select('.categories-v__link--with-subs')

    for link in category_links:
        category_name = link.find(class_='categories-v__title').text.strip()
        category_url = link.get('href')
        full_url = base_url + category_url if base_url not in category_url else category_url
        categories[category_name] = full_url

    return categories

def get_info_from_page(session, page_url):
    products = []
    try:
        response = session.get(page_url)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        product_cards = soup.find_all('div', class_='card-body items-center px-[15px] py-[12px] min-[600px]:!px-5 xl:flex')

        for card in product_cards:
            product_link_tag = card.find('a', href=True)
            product_link = product_link_tag['href'] if product_link_tag else None

            product_name_tag = card.find('a', class_='text-[#151528]')
            product_name = product_name_tag.text.strip() if product_name_tag else None

            product_id = product_link_tag['href'].split('/')[-2] if product_link_tag else None
            
            stock_info_divs = card.find_all('div', class_='flex-col !gap-2 hidden xl:flex w-1/4') 
 
            rostov_stock_total = 0
            stock_info_blocks = card.find_all('div', class_='flex items-center !gap-2')
            
            for block in stock_info_blocks:
                stock_text = block.find('span', class_='text-sm leading-[17px] whitespace-nowrap text-ellipsis overflow-hidden xl:w-[130px] min-[1300px]:w-auto').text.strip()
                stock_count = 0
                if "Основной склад" in stock_text or stock_text.startswith("РНД"):
                    stock_indicators = block.find_all('div', class_='flex items-center gap-[5px]')

                    for indicator_container in stock_indicators:
                        indicators = indicator_container.find_all('div', class_=lambda value: value and 'text-[11px] opacity-100' in value and ('bg-green' in value or 'bg-pastel-red' in value or 'bg-[#FFB25B]' in value))
                        stock_count = len(indicators)

                if stock_count == 1:
                    rostov_stock_total += 1
                elif stock_count == 2:
                    rostov_stock_total += 5
                elif stock_count == 3:
                    rostov_stock_total += 20

            if product_name and product_link and product_id:
                products.append((product_name, product_link, product_id, rostov_stock_total))

    except requests.RequestException as e:
        print(f"Произошла ошибка при запросе к {page_url}: {e}")

    return products, soup

def get_info_from_category(base_url, session, category_url):
    all_products = []
    page_idx = 1
    while category_url:
        products, soup = get_info_from_page(session, category_url)
        all_products.extend(products)
        print(f"\nPage {page_idx}:")
        for product_name, product_link, product_id, stock_total in products:
            print(f"  Product: {product_name} - {product_link} | Stock Total: {stock_total}")

        pagination = soup.find('ul', class_='js-pagination pagination js-pagination-ajax')
        if pagination:
            next_page_link = pagination.find('a', string='→')
            if next_page_link and 'href' in next_page_link.attrs:
                category_url = urljoin(base_url, next_page_link['href'])
                page_idx += 1
            else:
                category_url = None

    return all_products

def write_to_csv(data, filename="products.csv"):
    file_exists = os.path.isfile(filename)
    with open(filename, "a", newline='', encoding="utf-8") as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(["Category", "Name", "ID", "Link", "Stock Total"])
        writer.writerows(data)

def authenticate(session, login_url, email, password):
    response = session.get(login_url)
    soup = BeautifulSoup(response.text, 'html.parser')

    csrf_token = soup.find('input', {'name': '_csrf'})['value'] if soup.find('input', {'name': '_csrf'}) else None
    
    login_data = {
        'login': email,
        'password': password,
        '_csrf': csrf_token
    }
    
    login_response = session.post(login_url, data=login_data)
    login_soup = BeautifulSoup(login_response.text, 'html.parser')

    user_name = login_soup.find('span', class_="text-base font-medium text-[#555555] mb-2")
    if user_name:
        print(f"Авторизация прошла успешно под пользователем: {user_name.text.strip()}")
        return True
    else:
        print("Ошибка авторизации")
        return False

def main():
    print("Бот начал работу")
    session = requests.Session()
    login_url = 'https://b2b.zip161.ru/login/'
    email = 'SisfinityMarket@gmail.com'
    password = 'bactoh-7'
    authenticate(session, login_url, email, password)
    
    base_url = 'https://b2b.zip161.ru'
    categories = get_categories(session,base_url)

    for category_name, category_link in categories.items():
        print(f"{category_name}: {category_link}")
        products = get_info_from_category(base_url, session, category_link)
        write_to_csv([(category_name, product[0], product[2], urljoin(base_url, product[1]), product[3]) for product in products])
    print("Бот закончил работу")

main()
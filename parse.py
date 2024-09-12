import csv
from dataclasses import dataclass, astuple
from typing import List
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By

BASE_URL = "https://webscraper.io/"
HOME_URL = urljoin(BASE_URL, "test-sites/e-commerce/static/computers/laptops")


@dataclass
class Product:
    title: str
    description: str
    price: float
    rating: int
    num_of_reviews: int
    additional_info: dict


_driver: WebDriver | None = None


def get_driver() -> WebDriver:
    return _driver


def set_driver() -> None:
    global _driver
    _driver = webdriver.Chrome()


def close_driver() -> None:
    global _driver
    _driver.close()


def parse_hdd_block_prices(product_soup: BeautifulSoup) -> dict:
    detail_url = urljoin(BASE_URL, product_soup.select_one(".title")["href"])
    driver = get_driver()
    driver.get(detail_url)
    swatches = driver.find_element(By.CLASS_NAME, "swatches")
    buttons = swatches.find_elements(By.TAG_NAME, "button")

    prices = {}

    for button in buttons:
        if not button.get_property("disabled"):
            button.click()
            prices[button.get_property("value")] = driver.find_element(By.CLASS_NAME, "price").text.replace("$", "")

    return prices


def parse_single_product(product_soup: BeautifulSoup) -> Product:
    hdd_prices = parse_hdd_block_prices(product_soup)
    return Product(
        title=product_soup.select_one(".title")["title"],
        description=product_soup.select_one(".description").text,
        price=float(product_soup.select_one(".price").text.replace("$", "")),
        rating=int(product_soup.select_one("p[data-rating]")["data-rating"]),
        num_of_reviews=int(product_soup.select_one(".ratings > p.review-count.float-end").text.split()[0]),
        additional_info={"hdd_prices": hdd_prices},
    )


def get_num_pages(page_soup: BeautifulSoup) -> int:
    pagination = page_soup.select_one(".pagination")

    if pagination is None:
        return 1

    return int(pagination.select("li")[-2].text)


def get_single_page_products(page_soup: BeautifulSoup) -> [Product]:
    products = page_soup.select(".thumbnail")

    return [parse_single_product(product_soup=product_soup) for product_soup in products]


def write_products_to_csv(products: list[Product], name_page: str) -> None:
    with open(f"{name_page}.csv", "w", newline="", encoding="utf-8") as file:
        write = csv.writer(file)
        write.writerow([
            "title",
            "description",
            "price",
            "rating",
            "num_of_reviews"
        ])
        write.writerows([astuple(product) for product in products])


def get_home_products() -> [Product]:
    page = requests.get(HOME_URL).content
    soup = BeautifulSoup(page, "html.parser")

    # get nums of page
    num_pages = get_num_pages(soup)

    all_products = get_single_page_products(soup)

    for page_num in range(2, num_pages + 1):
        page = requests.get(HOME_URL, {"page": page_num}).content
        soup = BeautifulSoup(page, "html.parser")
        all_products.extend(get_single_page_products(soup))

    return all_products


def main():
    set_driver()
    products = get_home_products()
    write_products_to_csv(products, "laptops")
    close_driver()


if __name__ == "__main__":
    main()

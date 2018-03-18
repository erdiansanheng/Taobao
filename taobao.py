from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pyquery import PyQuery as pq
from config import *
import re
import pymongo

browser = webdriver.PhantomJS(service_args=SERVICE_ARGS)
browser.set_window_size(1400, 900)
wait = WebDriverWait(browser, 10)

client = pymongo.MongoClient(MONGO_URL)
db = client[MONGO_DB]

def search():
    print('正在搜索')
    try:
        browser.get('http://www.taobao.com')
        input = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '#q'))
        )
        submit = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '#J_TSearchForm > div.search-button > button')))
        input.send_keys(KEYWORD)
        submit.click()
        total_pages = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#mainsrp-pager > div > div > div > div.total')))
        get_products()
        return total_pages.text
    except TimeoutException:
        return search()

def next_page(page_number):
    print('正在前往第%d页' % page_number)
    try:
        input = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '#mainsrp-pager > div > div > div > div.form > input'))
        )
        submit = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '#mainsrp-pager > div > div > div > div.form > span.btn.J_Submit')))
        input.clear()
        input.send_keys(page_number)
        submit.click()
        wait.until(EC.text_to_be_present_in_element((By.CSS_SELECTOR, '#mainsrp-pager > div > div > div > ul > li.item.active > span'), str(page_number)))
        get_products()
    except TimeoutException:
        next_page(page_number)

def get_products():
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#mainsrp-itemlist .items .item')))
    html = browser.page_source
    doc = pq(html)
    items = doc('#mainsrp-itemlist .items .item').items()
    for item in items:
        product = {
            'image': item.find('.pic .img').attr('src'),
            'price': item.find('.price').text().replace('\n', ''),
            'deal': item.find('.deal-cnt').text()[:-3],
            'title': item.find('.title').text(),
            'shop': item.find('.shop').text(),
            'location': item.find('.location').text()
        }
        save_to_mongo(product)

def save_to_mongo(result):
    try:
        db_datas = db[MONGO_TABLE].find({'title': {'$regex': '.*?'}})
        for db_data in db_datas:
            title = db_data['title']
            if not hasattr(result, 'get'):
                return False
            elif title == result.get('title'):
                print('数据库已有该数据，不反复存储')
                return False
        db[MONGO_TABLE].insert(result)
        print('存储到MongoDB成功', result)
        return True
    except Exception:
        print('存储到MongoDB失败', result)

def main():
    try:
        page_num = search()
        page_num = int(re.compile('(\d+)').search(page_num).group(1))
        for i in range(2, page_num + 1):
            next_page(i)
    except Exception:
        print('出错了')
    finally:
        browser.close()

if __name__ == '__main__':
    main()

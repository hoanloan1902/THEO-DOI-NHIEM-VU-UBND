import time
import os
import logging
import requests
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

URL_DANG_NHAP = "https://cddh.dienbien.gov.vn/qlvb/vbcddh.nsf"
URL_BANG_DU_LIEU = "https://cddh.dienbien.gov.vn/qlvb/vbcddh.nsf/Default?OpenForm&tab=subMenuTheodoi&donvi="

USER_NAME        = os.environ.get("SKHCN_USER", "")
PASS_WORD        = os.environ.get("SKHCN_PASS", "")
TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

def gui_anh_telegram(photo_path: str, caption_text: str):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID: return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
        with open(photo_path, 'rb') as photo:
            files = {'photo': photo}
            data = {'chat_id': TELEGRAM_CHAT_ID, 'caption': caption_text, 'parse_mode': 'HTML'}
            resp = requests.post(url, files=files, data=data, timeout=40)
        return resp.status_code == 200
    except Exception as e:
        log.error(f"Lỗi gửi ảnh Telegram: {e}")
        return False

def chay_robot_chup_man_hinh():
    log.info("--- BẮT ĐẦU CHẠY ROBOT V4.4 (KÉO DÀI CỬA SỔ CHỤP HẾT VIỆC) ---")
    driver = None
    ngay_hom_nay = datetime.now() + timedelta(hours=7)
    thoi_gian_hien_tai = ngay_hom_nay.strftime('%H:%M %d/%m/%Y')

    try:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1400,1300") # 🎯 NÂNG CHIỀU CAO LÊN 1300 ĐỂ CHỤP HẾT CÁC VĂN BẢN PHÍA DƯỚI
        options.add_argument('--ignore-certificate-errors')
        
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

        driver.get(URL_DANG_NHAP)
        time.sleep(10)

        inputs = driver.find_elements(By.TAG_NAME, "input")
        for inp in inputs:
            try:
                type_attr = inp.get_attribute("type")
                if type_attr == "text" and inp.is_displayed():
                    driver.execute_script("arguments[0].value = arguments[1];", inp, USER_NAME)
                elif type_attr == "password" and inp.is_displayed():
                    driver.execute_script("arguments[0].value = arguments[1];", inp, PASS_WORD)
            except:
                continue
        time.sleep(2)

        try:
            nut_login = driver.find_element(By.XPATH, "//input[@type='submit' or @value='Đăng nhập']")
            driver.execute_script("arguments[0].click();", nut_login)
        except:
            driver.execute_script("document.forms[0].submit()")
        
        time.sleep(15)

        driver.get(URL_BANG_DU_LIEU)
        time.sleep(25) 

        ten_anh = "man_hinh_nhiem_vu.png"
        driver.save_screenshot(ten_anh)

        caption = f"📸 <b>BẢN TIN CHỤP TAB THEO DÕI NHIỆM VỤ</b>\n📅 <i>Cập nhật: {thoi_gian_hien_tai}</i>"
        thanh_cong = gui_anh_telegram(ten_anh, caption)

        if os.path.exists(ten_anh):
            os.remove(ten_anh)

    except Exception as e:
        log.error(f"❌ Lỗi: {e}")
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    chay_robot_chup_man_hinh()

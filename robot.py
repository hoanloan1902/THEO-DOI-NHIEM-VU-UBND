import time
import os
import logging
import requests
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

URL_HE_THONG = "https://cddh.dienbien.gov.vn/qlvb/vbcddh.nsf"

USER_NAME        = os.environ.get("SKHCN_USER", "")
PASS_WORD        = os.environ.get("SKHCN_PASS", "")
TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

def gui_telegram(msg: str) -> bool:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID: return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        resp = requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"}, timeout=15)
        return resp.status_code == 200
    except Exception:
        return False

def chay_robot_nhac_viec():
    log.info("--- BẮT ĐẦU CHẠY ROBOT NHẮC VIỆC V3.4 ---")
    driver = None
    ngay_hom_nay = datetime.now() + timedelta(hours=7)

    try:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument('--ignore-certificate-errors')
        options.add_argument("--disable-blink-features=AutomationControlled")
        
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        wait = WebDriverWait(driver, 30)

        driver.get(URL_HE_THONG)
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

        driver.get(URL_HE_THONG)
        time.sleep(15)

        driver.switch_to.default_content()
        frames = driver.find_elements(By.TAG_NAME, "frame") or driver.find_elements(By.TAG_NAME, "iframe")
        if frames:
            for frame in frames:
                frame_name = frame.get_attribute("name")
                if frame_name and frame_name.lower() in ["main", "right"]:
                    driver.switch_to.frame(frame)
                    break

        wait.until(EC.presence_of_element_located((By.TAG_NAME, "tr")))
        rows = driver.find_elements(By.TAG_NAME, "tr")

        log.info(f"📋 Đang quét bảng theo dõi nhiệm vụ...")
        
        noi_dung_bao_cao = f"⏰ <b>BẢN TIN GIÁM SÁT NHIỆM VỤ</b>\n📅 <i>Cập nhật: {ngay_hom_nay.strftime('%H:%M %d/%m/%Y')}</i>\n\n"
        co_nhiem_vu_ton = False

        for row in rows:
            cells = row.find_elements(By.TAG_NAME, "td")
            
            # Khớp chính xác số cột của bảng Sở Điện Biên
            if len(cells) < 10: 
                continue

            # 🎯 Căn chỉnh tọa độ cột chuẩn xác theo ảnh image_7e6c00.png:
            noi_dung_nhiem_vu = cells[4].text.strip() # Cột 5 (Nội dung chỉ đạo)
            thoi_han = cells[7].text.strip()          # Cột 8 (Thời hạn xử lý)
            trang_thai = cells[8].text.strip()        # Cột 9 (Trạng thái)

            # Robot lọc những việc chưa làm
            if ("chưa thực hiện" in trang_thai.lower()) and noi_dung_nhiem_vu:
                co_nhiem_vu_ton = True
                
                # Cắt ngắn nội dung nếu quá dài để Telegram không bị lỗi
                nhiem_vu_rut_gon = noi_dung_nhiem_vu.split('\n')[0][:120] 
                
                noi_dung_bao_cao += (
                    f"📌 <b>Việc:</b> {nhiem_vu_rut_gon}...\n"
                    f"⏳ <b>Hạn:</b> 🔴 {thoi_han}\n"
                    f"🚦 <b>TT:</b> {trang_thai}\n"
                    f"─────────────────\n"
                )

        if co_nhiem_vu_ton:
            gui_telegram(noi_dung_bao_cao)
            log.info("✅ Đã gửi danh sách việc tồn đọng qua Telegram!")
        else:
            gui_telegram(f"⏰ <b>BẢN TIN GIÁM SÁT NHIỆM VỤ</b>\n📅 {ngay_hom_nay.strftime('%H:%M %d/%m/%Y')}\n\n🎉 Hiện tại không có nhiệm vụ tồn đọng.")

    except Exception as e:
        log.error(f"❌ Lỗi: {e}")
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    chay_robot_nhac_viec()

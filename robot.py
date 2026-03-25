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

# ============================================================
# CẤU HÌNH HỆ THỐNG THEO DÕI NHIỆM VỤ MỚI
# ============================================================
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
    log.info("--- BẮT ĐẦU CHẠY ROBOT NHẮC VIỆC V3.3 (NÂNG CẤP ĐĂNG NHẬP) ---")
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

        # 🚀 Bước 1: Đăng nhập
        driver.get(URL_HE_THONG)
        time.sleep(10) # Cho web 10 giây để tải xong hoàn toàn bảng đăng nhập

        # Tìm chính xác ô input kiểu text và kiểu password để điền
        inputs = driver.find_elements(By.TAG_NAME, "input")
        
        for inp in inputs:
            try:
                type_attr = inp.get_attribute("type")
                if type_attr == "text" and inp.is_displayed():
                    # Dùng JavaScript điền thẳng vào để tránh lỗi che khuất
                    driver.execute_script("arguments[0].value = arguments[1];", inp, USER_NAME)
                elif type_attr == "password" and inp.is_displayed():
                    driver.execute_script("arguments[0].value = arguments[1];", inp, PASS_WORD)
            except:
                continue

        time.sleep(2)

        # Bấm nút đăng nhập bằng JavaScript (bao đâm thủng mọi rào cản che khuất)
        try:
            nut_login = driver.find_element(By.XPATH, "//input[@type='submit' or @value='Đăng nhập']")
            driver.execute_script("arguments[0].click();", nut_login)
        except:
            driver.execute_script("document.forms[0].submit()")
            
        time.sleep(15) # Đợi hệ thống xử lý đăng nhập và chuyển trang

        # 🚀 Bước 2: Quét bảng dữ liệu theo dõi
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
            if len(cells) < 8:
                continue

            # Đoán cột dựa trên giao diện chuẩn
            noi_dung_nhiem_vu = cells[max(0, min(len(cells)-1, 4))].text.strip()
            thoi_han = cells[max(0, min(len(cells)-1, 7))].text.strip()
            trang_thai = cells[max(0, min(len(cells)-1, 8))].text.strip()

            if "chưa thực hiện" in trang_thai.lower() and noi_dung_nhiem_vu:
                co_nhiem_vu_ton = True
                noi_dung_bao_cao += (
                    f"📌 <b>Nhiệm vụ:</b> {noi_dung_nhiem_vu[:150]}...\n"
                    f"⏳ <b>Hạn:</b> 🔴 {thoi_han}\n"
                    f"─────────────────\n"
                )

        if co_nhiem_vu_ton:
            gui_telegram(noi_dung_bao_cao)
            log.info("✅ Đã gửi báo cáo danh sách nhiệm vụ tồn đọng qua Telegram!")
        else:
            gui_telegram(f"⏰ <b>BẢN TIN GIÁM SÁT NHIỆM VỤ</b>\n📅 {ngay_hom_nay.strftime('%H:%M %d/%m/%Y')} \n\n🎉 Tuyệt vời! Hiện tại không có nhiệm vụ nào tồn đọng.")
            log.info("✅ Không có nhiệm vụ tồn đọng.")

    except Exception as e:
        log.error(f"❌ Lỗi hệ thống: {e}")
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    chay_robot_nhac_viec()

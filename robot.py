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
URL_BANG_DU_LIEU = "https://cddh.dienbien.gov.vn/qlvb/vbcddh.nsf/Default?OpenForm&tab=subMenuTheoDoi"

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
    log.info("--- BẮT ĐẦU CHẠY ROBOT NHẮC VIỆC V3.7 ---")
    driver = None
    ngay_hom_nay = datetime.now() + timedelta(hours=7)

    try:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument('--ignore-certificate-errors')
        
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

        # 🚀 Bước 1: Đăng nhập
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

        # 🚀 Bước 2: Nhảy thẳng vào URL chứa bảng dữ liệu
        driver.get(URL_BANG_DU_LIEU)
        time.sleep(20) # Thả lỏng cho mạng tỉnh load tẹt ga 20 giây

        driver.switch_to.default_content()
        frames = driver.find_elements(By.TAG_NAME, "frame") or driver.find_elements(By.TAG_NAME, "iframe")
        
        if frames:
            for frame in frames:
                f_name = frame.get_attribute("name") or ""
                if f_name.lower() in ["main", "right", "body"]:
                    driver.switch_to.frame(frame)
                    log.info(f"Đã nhảy vào frame: {f_name}")
                    break

        # 💥 CHIÊU MỚI: Quét tất cả thẻ <tr> chứa chữ "chưa thực hiện" (không đợi Selenium đếm nữa!)
        hàng_tìm_được = driver.find_elements(By.XPATH, "//tr[contains(translate(., 'CHƯA THỰC HIỆN', 'chưa thực hiện'), 'chưa thực hiện')]")

        log.info(f"📋 Quét nhanh phát hiện thấy {len(hàng_tìm_được)} việc có trạng thái Chưa thực hiện!")

        co_viec_ton = False
        noi_dung_bao_cao = f"⏰ <b>BẢN TIN GIÁM SÁT NHIỆM VỤ</b>\n📅 <i>Cập nhật: {ngay_hom_nay.strftime('%H:%M %d/%m/%Y')}</i>\n\n"

        for row in hàng_tìm_được:
            try:
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) < 5:
                    continue

                noi_dung = cells[4].text.strip() # Nội dung (Cột 5)
                
                # Tìm thời hạn ở cột 8 (Nếu không bốc được thì lấy tạm chuỗi rỗng)
                thoi_han = "Không rõ"
                if len(cells) >= 8:
                    thoi_han = cells[7].text.strip()

                if noi_dung:
                    co_viec_ton = True
                    rut_gon = noi_dung.split('\n')[0][:150]
                    noi_dung_bao_cao += (
                        f"📌 <b>Việc:</b> {rut_gon}...\n"
                        f"⏳ <b>Hạn:</b> 🔴 {thoi_han}\n"
                        f"─────────────────\n"
                    )
            except:
                continue

        if co_viec_ton:
            gui_telegram(noi_dung_bao_cao)
            log.info("✅ Bắn báo cáo thành công lên Telegram!")
        else:
            # Gửi thử một tin Debug nhẹ nếu nó bảo không có gì
            mau_html = driver.page_source[:200]
            gui_telegram(f"🤖 Robot V3.7 hoàn tất quét. Không bốc được việc. (Dấu vết web: <code>{mau_html}</code>)")

    except Exception as e:
        log.error(f"❌ Lỗi: {e}")
        gui_telegram(f"❌ Robot V3.7 báo lỗi: {e}")
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    chay_robot_nhac_viec()

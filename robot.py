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
from google import genai
from google.genai import types

# 🎯 Cấu hình hệ thống
URL_DANG_NHAP = "https://cddh.dienbien.gov.vn/qlvb/vbcddh.nsf"
URL_BANG_DU_LIEU = "https://cddh.dienbien.gov.vn/qlvb/vbcddh.nsf/Default?OpenForm&tab=subMenuTheodoi&donvi="

USER_NAME        = os.environ.get("SKHCN_USER", "")
PASS_WORD        = os.environ.get("SKHCN_PASS", "")
TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
GEMINI_API_KEY   = os.environ.get("GEMINI_API_KEY", "")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# --- 🤖 HÀM 1: DÙNG GEMINI AI ĐỂ ĐỌC HIỂU ẢNH ---
def phan_tich_anh_bang_ai(image_path: str) -> str:
    if not GEMINI_API_KEY:
        return "⚠️ Chưa cấu hình GEMINI_API_KEY trên GitHub Secrets!"
    
    try:
        log.info("🤖 Đang gửi ảnh sang Google Gemini AI để đọc chữ...")
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        prompt = """
        Bạn là trợ lý hành chính Việt Nam chuyên nghiệp. Hãy nhìn vào ảnh chụp bảng theo dõi nhiệm vụ này và bóc tách dữ liệu ra text.
        Hãy quét từng hàng của bảng và liệt kê lại các nhiệm vụ theo mẫu sau một cách ngắn gọn, súc tích (chỉ lấy những việc 'Chưa thực hiện' hoặc 'Đang thực hiện'):

        📌 Việc: [Tên nhiệm vụ ngắn gọn]
        ⏳ Hạn: [Thời hạn xử lý]
        🚦 Trạng thái: [Trạng thái hiện tại]
        ─────────────────
        
        Nếu không có việc nào quá hạn hoặc cần làm, hãy thông báo 'Tuyệt vời! Không có nhiệm vụ tồn đọng'. Trả lời bằng tiếng Việt chuẩn xác.
        """

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
                types.Part.from_bytes(
                    data=image_bytes,
                    mime_type='image/png',
                ),
                prompt
            ]
        )
        return response.text
    except Exception as e:
        log.error(f"Lỗi AI: {e}")
        return f"⚠️ Robot không bóc tách được chữ do lỗi AI: {e}"

# --- 📱 HÀM 2: GỬI TIN NHẮN VÀ ẢNH LÊN TELEGRAM ---
def gui_tin_kem_anh_telegram(photo_path: str, caption_text: str):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID: return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
        with open(photo_path, 'rb') as photo:
            files = {'photo': photo}
            # Cắt bớt caption nếu Gemini viết dài quá 1024 kí tự (Giới hạn của Telegram)
            truncated_caption = caption_text[:1020]
            data = {'chat_id': TELEGRAM_CHAT_ID, 'caption': truncated_caption, 'parse_mode': 'HTML'}
            resp = requests.post(url, files=files, data=data, timeout=40)
        return resp.status_code == 200
    except Exception as e:
        log.error(f"Lỗi gửi Telegram: {e}")
        return False

# --- 🏎️ HÀM CHÍNH ---
def chay_robot_ai():
    log.info("--- BẮT ĐẦU CHẠY ROBOT V5.0 (AI OCR) ---")
    driver = None
    ngay_hom_nay = datetime.now() + timedelta(hours=7)
    thoi_gian_hien_tai = ngay_hom_nay.strftime('%H:%M %d/%m/%Y')

    try:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1400,1300") 
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

        # 📸 Chụp màn hình
        ten_anh = "man_hinh_nhiem_vu.png"
        driver.save_screenshot(ten_anh)
        log.info("✅ Đã chụp màn hình!")

        # 🤖 Nhờ AI bóc tách chữ
        van_ban_boc_tach = phan_tich_anh_bang_ai(ten_anh)

        # 📱 Gửi Telegram
        caption = f"📊 <b>BÁO CÁO NHIỆM VỤ TỰ ĐỘNG (AI)</b>\n📅 {thoi_gian_hien_tai}\n\n{van_ban_boc_tach}"
        gui_tin_kem_anh_telegram(ten_anh, caption)

        if os.path.exists(ten_anh):
            os.remove(ten_anh)

    except Exception as e:
        log.error(f"❌ Lỗi: {e}")
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    chay_robot_ai()

import time
import requests
import json
import urllib.parse
from bs4 import BeautifulSoup
from datetime import datetime

# --- 설정 파일 관리 ---
CONFIG_FILE = 'config.json'

def load_config():
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # 기본 설정 생성
        default_config = {
            "is_active": True,
            "interval_seconds": 60,
            "discord_url": "YOUR_DISCORD_WEBHOOK_URL",
            "regions": ["서울", "경기"],
            "keywords": ["사범"],
            "last_id": 0
        }
        save_config(default_config)
        return default_config

def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

# --- 디스코드 알림 ---
def send_discord_alert(webhook_url, msg):
    if not webhook_url or "YOUR" in webhook_url:
        print("디스코드 URL이 설정되지 않았습니다.")
        return

    data = {"content": msg}
    requests.post(webhook_url, json=data)

# --- 크롤러 핵심 ---
def crawl_job_board():
    config = load_config()
    current_max_id = config['last_id']
    found_max_id = current_max_id

    base_url = "https://www.taekwonstory.com/bbs/board.php"

    print(f"[{datetime.now()}] 크롤링 시작... (대상: {config['regions']})")

    for region in config['regions']:
        try:
            # URL 인코딩 및 요청
            encoded_region = urllib.parse.quote(region)
            url = f"{base_url}?bo_table=guin&wr_1={encoded_region}"
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')

            # 게시글 목록 파싱 (실제 CSS 선택자는 개발자 도구 확인 필요)
            # 예시: tr 태그 안에 있는 리스트라고 가정
            rows = soup.select('form[name="fboardlist"] tbody tr')

            for row in rows:
                # 공지사항은 건너뛰기 로직 필요할 수 있음
                subject_div = row.select_one('.td_subject a')
                if not subject_div: continue

                link = subject_div['href']
                title = subject_div.text.strip()

                # wr_id 추출 로직
                try:
                    wr_id = int(link.split('wr_id=')[1].split('&')[0])
                except:
                    continue

                # ID 갱신용 (가장 높은 번호 기억)
                if wr_id > found_max_id:
                    found_max_id = wr_id

                # 신규 글이면서, 키워드가 포함된 경우
                if wr_id > current_max_id:
                    for keyword in config['keywords']:
                        if keyword in title:
                            msg = f"🔔 **[{region}] 키워드 '{keyword}' 발견!**\n{title}\n{link}"
                            send_discord_alert(config['discord_url'], msg)
                            print(f"알림 발송: {title}")
                            break # 키워드 중복 알림 방지

        except Exception as e:
            print(f"에러 발생 ({region}): {e}")

    # 마지막 ID 업데이트 및 저장
    if found_max_id > current_max_id:
        config['last_id'] = found_max_id
        save_config(config)

# --- 메인 실행 ---
if __name__ == "__main__":
    while True:
        config = load_config()

        if config['is_active']:
            crawl_job_board()
        else:
            print("🚫 기능이 꺼져있습니다. (Off)")

        time.sleep(config['interval_seconds'])

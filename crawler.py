import os
import requests
import urllib.parse
from bs4 import BeautifulSoup
from supabase import create_client
from datetime import datetime, timedelta, timezone

# --- Supabase 설정 ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 한국 시간 구하기 ---
KST = timezone(timedelta(hours=9))

def send_discord(webhook_url, msg):
    if webhook_url and "http" in webhook_url:
        try:
            requests.post(webhook_url, json={"content": msg})
        except: pass

def main():
    # 1. 내 설정 가져오기 (ID가 'admin'인 행)
    response = supabase.table('my_config').select("*").eq('uid', 'admin').execute()
    if not response.data:
        print("DB에 계정이 없습니다.")
        return

    user = response.data[0]

    # 2. ON/OFF 체크
    if not user['is_active']:
        print("⛔ 크롤링이 꺼져 있습니다. (OFF)")
        return

    # 3. 시간 간격 체크 (쿨타임)
    last_run = datetime.fromisoformat(user['last_run_at'].replace('Z', '+00:00'))
    now = datetime.now(timezone.utc)
    # 설정된 분(min)보다 적게 지났으면 스킵
    if (now - last_run).total_seconds() < (user['check_interval_min'] * 60):
        print(f"⏳ 아직 쿨타임입니다. (설정: {user['check_interval_min']}분 간격)")
        return

    print(f"🚀 크롤링 시작! (타겟: {user['regions']})")

    # --- 크롤링 로직 시작 ---
    base_url = "https://www.taekwonstory.com/bbs/board.php"
    found_max_id = user['last_id']
    new_posts_count = 0

    for region in user['regions']:
        try:
            encoded_region = urllib.parse.quote(region) if region != "전체" else ""
            url = f"{base_url}?bo_table=guin&wr_1={encoded_region}"

            resp = requests.get(url)
            soup = BeautifulSoup(resp.text, 'html.parser')
            rows = soup.select('form[name="fboardlist"] tbody tr')

            for row in rows:
                subject_div = row.select_one('.td_subject a')
                if not subject_div: continue

                title = subject_div.text.strip()
                link = subject_div['href']

                try:
                    wr_id = int(link.split('wr_id=')[1].split('&')[0])
                except: continue

                # 전체 중 가장 최신 ID 기록
                if wr_id > found_max_id:
                    found_max_id = wr_id

                # 진짜 신규 글 & 키워드 매칭
                if wr_id > user['last_id']:
                    for keyword in user['keywords']:
                        if keyword in title:
                            msg = f"🥋 **[{region}] 새 공고 알림**\n제목: {title}\n바로가기: {link}"
                            send_discord(user['discord_url'], msg)
                            new_posts_count += 1
                            break
        except Exception as e:
            print(f"에러 ({region}): {e}")

    # 4. 상태 업데이트 (마지막 실행시간, 마지막 ID)
    supabase.table('my_config').update({
        'last_run_at': datetime.now(timezone.utc).isoformat(),
        'last_id': found_max_id
    }).eq('uid', 'admin').execute()

    print(f"✅ 완료. 신규 알림: {new_posts_count}건, 갱신된 ID: {found_max_id}")

if __name__ == "__main__":
    main()

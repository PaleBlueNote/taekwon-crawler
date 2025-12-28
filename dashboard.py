import streamlit as st
import json
import requests
from bs4 import BeautifulSoup
import urllib.parse
import os

# --- 설정 파일 경로 ---
CONFIG_FILE = 'config.json'

# --- 설정 불러오기/저장하기 함수 ---
def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

# --- 실시간 검색 기능 (태권스토리 크롤링) ---
def search_taekwon(region, keyword):
    base_url = "https://www.taekwonstory.com/bbs/board.php"
    encoded_region = urllib.parse.quote(region) if region != "전체" else ""
    encoded_keyword = urllib.parse.quote(keyword)

    # 검색 쿼리 조합
    url = f"{base_url}?bo_table=guin&wr_1={encoded_region}&stx={encoded_keyword}"

    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        rows = soup.select('form[name="fboardlist"] tbody tr')

        results = []
        for row in rows:
            subject_div = row.select_one('.td_subject a')
            if not subject_div: continue

            title = subject_div.text.strip()
            link = subject_div['href']
            date = row.select_one('.td_datetime').text.strip() if row.select_one('.td_datetime') else "-"

            results.append({"제목": title, "날짜": date, "링크": link})
        return results, url
    except Exception as e:
        return [], str(e)

# --- UI 레이아웃 시작 ---
st.set_page_config(page_title="태권스토리 알림 센터", layout="wide")

st.title("🥋 태권스토리 구인 알림 제어판")

# 탭 메뉴 구성
tab1, tab2 = st.tabs(["⚙️ 설정 관리", "🔍 실시간 검색"])

# === [탭 1] 설정 관리 ===
with tab1:
    config = load_config()

    if not config:
        st.error("config.json 파일이 없습니다. app.py를 먼저 한 번 실행해주세요.")
    else:
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("🤖 크롤러 상태")

            # On/Off 스위치
            is_active = st.toggle("크롤링 작동 (On/Off)", value=config.get('is_active', True))

            # 시간 간격 설정
            interval = st.number_input("검사 간격 (초 단위)", min_value=10, value=config.get('interval_seconds', 60))

            if st.button("설정 저장하기"):
                config['is_active'] = is_active
                config['interval_seconds'] = interval
                save_config(config)
                st.success("상태가 저장되었습니다! 크롤러가 다음 주기부터 반영합니다.")

        with col2:
            st.subheader("🎯 타겟 설정")

            # 지역 다중 선택
            all_regions = ["서울", "경기", "인천", "강원", "충북", "충남", "경북", "경남", "전북", "전남", "제주", "부산", "대구", "대전", "광주", "울산", "세종"]
            selected_regions = st.multiselect("감시할 지역", all_regions, default=config.get('regions', []))

            # 키워드 입력
            current_keywords = ", ".join(config.get('keywords', []))
            new_keywords_str = st.text_area("감시 키워드 (쉼표로 구분)", value=current_keywords)

            if st.button("타겟 업데이트"):
                # 키워드 리스트로 변환
                keyword_list = [k.strip() for k in new_keywords_str.split(',') if k.strip()]
                config['regions'] = selected_regions
                config['keywords'] = keyword_list
                save_config(config)
                st.success("타겟 설정이 업데이트 되었습니다.")

        st.divider()
        st.caption(f"현재 디스코드 웹훅: `{config.get('discord_url', '')[:30]}...`")
        st.caption(f"마지막 크롤링 ID: `{config.get('last_id', 0)}`")

# === [탭 2] 실시간 검색 ===
with tab2:
    st.header("게시판 검색")

    c1, c2 = st.columns([1, 3])
    with c1:
        search_region = st.selectbox("지역 선택", ["전체"] + ["서울", "경기", "인천", "부산", "대구", "광주", "대전", "울산"])
    with c2:
        search_keyword = st.text_input("검색어 (제목+내용)", placeholder="예: 사범, 오후")

    if st.button("검색 시작"):
        with st.spinner('태권스토리에서 검색 중...'):
            results, search_url = search_taekwon(search_region, search_keyword)

            if isinstance(results, str): # 에러 발생 시
                st.error(f"에러 발생: {results}")
            elif not results:
                st.warning("검색 결과가 없습니다.")
            else:
                st.success(f"총 {len(results)}건이 검색되었습니다.")
                st.markdown(f"[🔗 실제 검색 페이지 바로가기]({search_url})")

                # 결과 카드 형태로 보여주기
                for item in results:
                    with st.expander(f"{item['제목']} ({item['날짜']})"):
                        st.write(f"링크: {item['링크']}")
                        st.markdown(f"[게시글 보러가기]({item['링크']})")

import streamlit as st
from supabase import create_client
import time
import requests
import urllib.parse
from bs4 import BeautifulSoup

# --- Supabase 연결 (Secrets 사용) ---
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
except:
    st.error("Secrets 설정이 안 되어 있습니다!")
    st.stop()

supabase = create_client(url, key)

st.set_page_config(page_title="태권 알림봇 설정", layout="centered")

# --- 실시간 검색 함수 (태권스토리 크롤링) ---
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
            date_elm = row.select_one('.td_datetime')
            date = date_elm.text.strip() if date_elm else "-"

            results.append({"제목": title, "날짜": date, "링크": link})
        return results, url
    except Exception as e:
        return [], str(e)

# --- 세션 상태 초기화 (로그인 유지용) ---
if 'is_logged_in' not in st.session_state:
    st.session_state['is_logged_in'] = False
if 'user_id' not in st.session_state:
    st.session_state['user_id'] = None

# ==========================================
# 1. 로그인 화면
# ==========================================
if not st.session_state['is_logged_in']:
    st.title("🔒 관리자 로그인")
    with st.form("login_form"):
        input_id = st.text_input("아이디")
        input_pw = st.text_input("비밀번호", type="password")
        submitted = st.form_submit_button("로그인")

        if submitted:
            # DB에서 ID/PW 확인
            res = supabase.table('my_config').select("*").eq('uid', input_id).execute()
            if res.data and res.data[0]['password'] == input_pw:
                st.session_state['is_logged_in'] = True
                st.session_state['user_id'] = input_id
                st.success("로그인 성공!")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("아이디 또는 비밀번호가 틀렸습니다.")

# ==========================================
# 2. 메인 화면 (로그인 후)
# ==========================================
else:
    st.title("🥋 태권스토리 봇 제어판")

    # 상단 탭 메뉴 생성
    tab1, tab2 = st.tabs(["⚙️ 설정 관리", "🔍 실시간 검색"])

    # --- [탭 1] 설정 관리 ---
    with tab1:
        my_id = st.session_state['user_id']
        res = supabase.table('my_config').select("*").eq('uid', my_id).execute()

        if not res.data:
            st.error(f"DB 데이터 오류: '{my_id}' 계정 정보를 찾을 수 없습니다.")
            st.stop()

        user_data = res.data[0]

        with st.form("config_form"):
            st.subheader(f"설정 관리 ({user_data['uid']}님)")

            c1, c2 = st.columns(2)
            with c1:
                new_is_active = st.toggle("봇 작동 (ON/OFF)", value=user_data['is_active'])
            with c2:
                new_interval = st.number_input("크롤링 주기 (분 단위)", min_value=5, value=user_data['check_interval_min'])
                st.caption("※ 너무 짧으면 서버 과부하 위험이 있습니다.")

            st.divider()
            st.subheader("2. 감시 타겟")

            region_list = ["서울", "경기", "인천", "부산", "대구", "광주", "대전", "울산", "세종", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주", "전체"]
            current_regions = [r for r in user_data['regions'] if r in region_list]
            new_regions = st.multiselect("지역 선택", region_list, default=current_regions)

            kwd_str = ", ".join(user_data['keywords'])
            new_keywords_str = st.text_area("키워드 (쉼표 , 로 구분)", value=kwd_str)

            st.divider()
            st.subheader("3. 연결 정보")
            new_discord = st.text_input("디스코드 웹훅 URL", value=user_data['discord_url'])

            if st.form_submit_button("설정 저장하기"):
                new_kwd_list = [k.strip() for k in new_keywords_str.split(',') if k.strip()]

                update_data = {
                    "is_active": new_is_active,
                    "check_interval_min": new_interval,
                    "regions": new_regions,
                    "keywords": new_kwd_list,
                    "discord_url": new_discord
                }

                supabase.table('my_config').update(update_data).eq('uid', my_id).execute()
                st.success("✅ 설정이 저장되었습니다! 다음 크롤링부터 적용됩니다.")
                time.sleep(1)
                st.rerun()

        if st.button("로그아웃"):
            st.session_state['is_logged_in'] = False
            st.session_state['user_id'] = None
            st.rerun()

    # --- [탭 2] 실시간 검색 ---
    with tab2:
        st.header("게시판 실시간 검색")
        st.caption("봇 설정과 상관없이, 지금 바로 태권스토리 게시판을 검색합니다.")

        col_s1, col_s2 = st.columns([1, 2])
        with col_s1:
            search_region = st.selectbox("지역 선택", ["전체"] + ["서울", "경기", "인천", "부산", "대구", "광주", "대전", "울산"])
        with col_s2:
            search_keyword = st.text_input("검색어 (제목+내용)", placeholder="예: 사범, 오후")

        if st.button("검색 시작", type="primary"):
            with st.spinner('태권스토리에서 데이터를 가져오는 중...'):
                results, search_url = search_taekwon(search_region, search_keyword)

                if isinstance(results, str):
                    st.error(f"에러 발생: {results}")
                elif not results:
                    st.warning("검색 결과가 없습니다.")
                else:
                    st.success(f"총 {len(results)}건이 검색되었습니다.")
                    st.markdown(f"[🔗 실제 게시판 페이지로 이동]({search_url})")

                    for item in results:
                        with st.expander(f"{item['제목']} ({item['날짜']})"):
                            st.write(f"링크: {item['링크']}")
                            st.markdown(f"[게시글 바로가기]({item['링크']})")

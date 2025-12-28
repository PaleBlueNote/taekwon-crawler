import streamlit as st
from supabase import create_client
import time

# --- Supabase 연결 (Secrets 사용) ---
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
except:
    st.error("Secrets 설정이 안 되어 있습니다!")
    st.stop()

supabase = create_client(url, key)

st.set_page_config(page_title="태권 알림봇 설정", layout="centered")

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
                st.session_state['user_id'] = input_id  # <--- 핵심 수정: 로그인한 ID 기억하기
                st.success("로그인 성공!")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("아이디 또는 비밀번호가 틀렸습니다.")

# ==========================================
# 2. 메인 설정 화면 (로그인 후 보임)
# ==========================================
else:
    st.title("🥋 태권스토리 봇 제어판")

    # 기억해둔 ID로 내 설정 가져오기
    my_id = st.session_state['user_id']
    res = supabase.table('my_config').select("*").eq('uid', my_id).execute() # <--- 수정됨 ('admin' 삭제)

    if not res.data:
        st.error(f"DB 데이터 오류: '{my_id}' 계정 정보를 찾을 수 없습니다.")
        if st.button("재로그인"):
            st.session_state['is_logged_in'] = False
            st.rerun()
        st.stop()

    user_data = res.data[0]

    # --- 설정 폼 ---
    with st.form("config_form"):
        st.subheader(f"설정 관리 ({user_data['uid']}님)") # 누구 설정인지 표시

        c1, c2 = st.columns(2)
        with c1:
            # ON/OFF 스위치
            new_is_active = st.toggle("봇 작동 (ON/OFF)", value=user_data['is_active'])
        with c2:
            # 시간 간격 설정
            new_interval = st.number_input("크롤링 주기 (분 단위)", min_value=5, value=user_data['check_interval_min'])
            st.caption("※ 너무 짧으면 서버에 무리가 갈 수 있습니다.")

        st.divider()
        st.subheader("2. 감시 타겟")

        # 지역 선택
        region_list = ["서울", "경기", "인천", "부산", "대구", "광주", "대전", "울산", "세종", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주", "전체"]

        # 저장된 지역 불러오기 (없는 지역이 있을 경우 에러 방지)
        current_regions = [r for r in user_data['regions'] if r in region_list]
        new_regions = st.multiselect("지역 선택", region_list, default=current_regions)

        # 키워드 입력
        kwd_str = ", ".join(user_data['keywords'])
        new_keywords_str = st.text_area("키워드 (쉼표 , 로 구분)", value=kwd_str)

        st.divider()
        st.subheader("3. 연결 정보")
        new_discord = st.text_input("디스코드 웹훅 URL", value=user_data['discord_url'])

        # 저장 버튼
        if st.form_submit_button("설정 저장하기"):
            new_kwd_list = [k.strip() for k in new_keywords_str.split(',') if k.strip()]

            update_data = {
                "is_active": new_is_active,
                "check_interval_min": new_interval,
                "regions": new_regions,
                "keywords": new_kwd_list,
                "discord_url": new_discord
            }

            # 내 ID로 업데이트
            supabase.table('my_config').update(update_data).eq('uid', my_id).execute()
            st.success("✅ 설정이 저장되었습니다! 다음 크롤링부터 적용됩니다.")
            time.sleep(1)
            st.rerun()

    # 로그아웃 버튼
    if st.button("로그아웃"):
        st.session_state['is_logged_in'] = False
        st.session_state['user_id'] = None
        st.rerun()

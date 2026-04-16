import streamlit as st
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from io import BytesIO
import datetime
import os
import requests

# 1. 기본 설정
st.set_page_config(page_title="AE History Visualizer v6.3", layout="wide")

# 폰트 자동 로드 (구글 나눔고딕)
@st.cache_data
def load_font():
    try:
        font_url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Bold.ttf"
        font_res = requests.get(font_url)
        with open("nanum_font.ttf", "wb") as f:
            f.write(font_res.content)
        return "nanum_font.ttf"
    except:
        return None

FONT_PATH = load_font()

# 세션 상태 초기화
if 'client_db' not in st.session_state: st.session_state.client_db = pd.DataFrame()
if 'history_db' not in st.session_state: st.session_state.history_db = pd.DataFrame(columns=['날짜', '광고주명', '소통내용', '핵심키워드'])

# 2. UI 디자인
st.markdown("""
    <style>
    header[data-testid="stHeader"] { visibility: hidden; }
    .stButton>button { width: 100%; border-radius: 8px; background-color: #FFB300; color: white; font-weight: bold; border: none; height: 3em; }
    div[data-testid="stTextInput"] input { border: 2px solid #FFB300 !important; }
    .keyword-hint { font-size: 0.8em; color: #666; margin-top: -10px; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

st.title("📝 AE History Visualizer v6.3")

# 사이드바 메뉴
menu = st.sidebar.radio("📋 메뉴 이동", ["광고주 DB 관리", "관리 이력 입력", "디지털 리포트 생성"])

# --- 1. 광고주 DB 관리 ---
if menu == "광고주 DB 관리":
    st.header("📂 데이터 로드 및 백업")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🏢 광고주 리스트 업로드")
        uploaded_clients = st.file_uploader("광고주 엑셀/CSV", type=['xlsx', 'xls', 'csv'], key="clients")
    with col2:
        st.subheader("💾 히스토리 백업 로드")
        uploaded_history = st.file_uploader("이전 히스토리 엑셀", type=['xlsx'], key="history")
    
    if uploaded_clients:
        try:
            df = pd.read_csv(uploaded_clients) if uploaded_clients.name.endswith('.csv') else pd.read_excel(uploaded_clients)
            df.rename(columns={df.columns[0]: '광고주명'}, inplace=True)
            st.session_state.client_db = df
            st.success("✅ 광고주 리스트 로드 완료!")
        except Exception as e: st.error(f"파일 오류: {e}")

    if uploaded_history:
        try:
            h_df = pd.read_excel(uploaded_history)
            st.session_state.history_db = h_df
            st.success("✅ 이전 히스토리 복구 완료!")
        except Exception as e: st.error(f"백업 파일 오류: {e}")

    st.divider()
    if not st.session_state.client_db.empty:
        st.dataframe(st.session_state.client_db, use_container_width=True, hide_index=True)

# --- 2. 관리 이력 입력 ---
elif menu == "관리 이력 입력":
    st.header("✍️ 소통 및 관리 이력 기록")
    if st.session_state.client_db.empty:
        st.warning("먼저 '광고주 DB 관리' 메뉴에서 리스트를 등록해주세요.")
    else:
        # 업체 검색 기능
        search_query = st.text_input("🔍 업체명 검색", placeholder="예: 삼다 또는 water")
        all_clients = sorted(st.session_state.client_db['광고주명'].dropna().unique())
        filtered_clients = [c for c in all_clients if search_query.lower() in str(c).lower()]
        
        if not filtered_clients:
            st.error("검색 결과가 없습니다.")
        else:
            # 🌟 키워드 추천을 위한 이전 데이터 분석
            existing_keywords = []
            if not st.session_state.history_db.empty:
                # '핵심키워드' 컬럼에서 쉼표로 분리하여 고유한 키워드 리스트 생성
                all_tags = st.session_state.history_db['핵심키워드'].dropna().str.split(',').explode().str.strip()
                existing_keywords = sorted(all_tags.unique())
                existing_keywords = [k for k in existing_keywords if k] # 빈값 제거

            with st.form("history_input_form", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    client = st.selectbox(f"광고주 선택 ({len(filtered_clients)}건 검색됨)", filtered_clients)
                    log_date = st.date_input("기록 날짜", datetime.date.today())
                with c2:
                    # 🌟 키워드 추천 멀티셀렉트 도입
                    selected_hints = st.multiselect("🏷️ 자주 쓰는 키워드 선택", options=existing_keywords)
                    manual_tags = st.text_input("➕ 직접 입력 (쉼표로 구분)", placeholder="새로운 키워드는 여기에 입력")
                
                content = st.text_area("상세 관리 내용 (워드클라우드 분석용)", height=150)
                submitted = st.form_submit_button("히스토리 저장하기")
                
                if submitted:
                    if content.strip() == "":
                        st.error("내용을 입력해주세요!")
                    else:
                        # 🌟 선택된 힌트와 직접 입력한 태그 합치기
                        combined_tags = list

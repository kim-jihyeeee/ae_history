import streamlit as st
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from io import BytesIO
import datetime
import os
import requests

# 1. 기본 설정
st.set_page_config(page_title="AE History Visualizer v6.9", layout="wide")

# 폰트 자동 로드 (나눔고딕)
@st.cache_data
def load_font():
    try:
        font_url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Bold.ttf"
        font_res = requests.get(font_url)
        with open("nanum_font.ttf", "wb") as f: f.write(font_res.content)
        return "nanum_font.ttf"
    except: return None

FONT_PATH = load_font()

# 세션 상태 초기화
if 'client_db' not in st.session_state: st.session_state.client_db = pd.DataFrame()
if 'history_db' not in st.session_state: st.session_state.history_db = pd.DataFrame(columns=['날짜', '광고주명', '소통내용', '핵심키워드'])

# 2. UI 디자인
st.markdown("""
    <style>
    header[data-testid="stHeader"] { visibility: hidden; }
    .stButton>button { width: 100%; border-radius: 8px; background-color: #FFB300; color: white; font-weight: bold; height: 3em; }
    .stDataEditor { border: 2px solid #FFB300; border-radius: 8px; }
    /* 슬라이더 라벨 가독성 강화 */
    div[data-testid="stSliderTickBar"] { font-weight: bold; color: #FFB300; }
    </style>
""", unsafe_allow_html=True)

st.title("📝 AE History Visualizer v6.9")

# 사이드바 메뉴
menu = st.sidebar.radio("📋 메뉴 이동", ["광고주 DB 관리", "관리 이력 입력", "디지털 리포트 생성"])

# --- 1. 광고주 DB 관리 ---
if menu == "광고주 DB 관리":
    st.header("📂 데이터 로드 및 관리")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🏢 광고주 리스트 업로드")
        uploaded_clients = st.file_uploader("광고주 리스트 (엑셀/CSV)", type=['xlsx', 'csv'], key="clients")
    with col2:
        st.subheader("💾 히스토리 백업 로드")
        uploaded_history = st.file_uploader("백업 엑셀 파일", type=['xlsx'], key="history")
    
    if uploaded_clients:
        try:
            df = pd.read_csv(uploaded_clients) if uploaded_clients.name.endswith('.csv') else pd.read_excel(uploaded_clients)
            df.rename(columns={df.columns[0]: '광고주명'}, inplace=True)
            st.session_state.client_db = df
            st.success("✅ 광고주 리스트 로드 완료!")
        except: st.error("파일 확인 필요")

    if uploaded_history:
        try:
            h_df = pd.read_excel(uploaded_history)
            if '날짜' in h_df.columns: h_df['날짜'] = pd.to_datetime(h_df['날짜']).dt.date
            st.session_state.history_db = h_df
            st.success("✅ 히스토리 복구 완료!")
        except: st.error("백업 파일 로드 실패")

# --- 2. 관리 이력 입력 ---
elif menu == "관리 이력 입력":
    st.header("✍️ 소통 이력 기록 및 실시간 수정")
    if st.session_state.client_db.empty:
        st.warning("먼저 '광고주 DB 관리' 메뉴에서 리스트를 등록해주세요.")
    else:
        search_query = st.text_input("🔍 업체명 검색", placeholder="일부만 입력해도 필터링됩니다.")
        all_clients = sorted(st.session_state.client_db['광고주명'].dropna().unique())
        filtered_clients = [c for c in all_clients if search_query.lower() in str(c).lower()]
        
        existing_keywords = []
        if not st.session_state.history_db.empty:
            all_tags = st.session_state.history_db['핵심키워드'].dropna().str.split(',').explode().str.strip()
            existing_keywords = sorted(all_tags.unique())

        with st.form("history_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                client = st.selectbox(f"광고주 선택 ({len(filtered_clients)}건)", filtered_clients)
                log_date = st.date_input("날짜", datetime.date.today())
            with c2:
                selected_hints = st.multiselect("🏷️ 자주 쓰는 키워드", options=existing_keywords)
                manual_tags = st.text_input("➕ 직접 입력 (쉼표 구분)")
            content = st.text_area("상세 내용

import streamlit as st
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from io import BytesIO
import datetime
import os
import requests
from bs4 import BeautifulSoup
from pptx import Presentation
from pptx.util import Inches
from fpdf import FPDF

# 1. 기본 설정 및 폰트 로드
st.set_page_config(page_title="AE Total Solution v8.2", layout="wide")

@st.cache_data
def load_font():
    try:
        font_url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Bold.ttf"
        font_res = requests.get(font_url)
        with open("nanum_font.ttf", "wb") as f: f.write(font_res.content)
        return "nanum_font.ttf"
    except: return None

FONT_PATH = load_font()

# 세션 초기화
if 'client_db' not in st.session_state: st.session_state.client_db = pd.DataFrame()
if 'history_db' not in st.session_state: st.session_state.history_db = pd.DataFrame(columns=['날짜', '광고주명', '소통내용', '핵심키워드'])

# 2. UI 디자인 (메뉴 간격 및 슬라이더 개선)
st.markdown("""
    <style>
    header[data-testid="stHeader"] { visibility: hidden; }
    .stButton>button { width: 100%; border-radius: 8px; background-color: #FFB300; color: white; font-weight: bold; height: 3em; }
    .menu-header { font-size: 1.1em; font-weight: bold; color: #FFB300; margin-top: 30px; margin-bottom: 10px; border-bottom: 2px solid #eee; padding-bottom: 5px; }
    .spacer { margin-bottom: 40px; }
    div[role="slider"] { background-color: #FF4B4B !important; }
    </style>
""", unsafe_allow_html=True)

# 3. 사이드바 메뉴 디자인 (여백 확실히 추가)
st.sidebar.title("🚀 AE Total Tool v8.2")

st.sidebar.markdown('<p class="menu-header">📋 내부 히스토리 관리</p>', unsafe_allow_html=True)
menu_internal = st.sidebar.radio("항목 선택", ["광고주 DB 관리", "관리 이력 입력", "디지털 리포트(내부)"], label_visibility="collapsed")

st.sidebar.markdown('<div class="spacer"></div>', unsafe_allow_html=True) # 여백 추가

st.sidebar.markdown('<p class="menu-header">📊 외부 시장 분석</p>', unsafe_allow_html=True)
menu_external = st.sidebar.checkbox("📊 Trend Radar(외부)")

# 메뉴 결정
menu = "📊 Trend Radar(외부)" if menu_external else menu_internal

# --- [메뉴별 로직] ---

if menu == "광고주 DB 관리":
    st.header("📂 데이터 로드 및 관리")
    col1, col2 = st.columns(2)
    with col1: uploaded_clients = st.file_uploader("광고주 리스트", type=['xlsx', 'csv'], key="c_up")
    with col2: uploaded_history = st.file_uploader("백업 엑셀", type=['xlsx'], key="h_up")
    
    if uploaded_clients:
        df = pd.read_csv(uploaded_clients) if uploaded_clients.name.endswith('.csv') else pd.read_excel(uploaded_clients)
        df.rename(columns={df.columns[0]: '광고주명'}, inplace=True)
        st.session_state.client_db = df
        st.success("✅ 로드 완료")
    if uploaded_history:
        st.session_state.history_db = pd.read_excel(uploaded_history)
        st.success("✅ 복구 완료")

elif menu == "관리 이력 입력":
    st.header("✍️ 소통 이력 기록 및 수정")
    if st.session_state.client_db.empty: st.warning("먼저 광고주 리스트를 등록해주세요.")
    else:
        search_q = st.text_input("🔍 업체명 검색")
        all_c = sorted(st.session_state.client_db['광고주명'].dropna().unique())
        filtered_c = [c for c in all_c if search_q.lower() in str(c).lower()]
        with st.form("history_form"):
            c1, c2 = st.columns(2)
            with c1:
                client = st.selectbox(f"광고주 ({len(filtered_c)}건)", filtered_c)
                log_date = st.date_input("날짜", datetime.date.today())
            with c2: manual_tags = st.text_input("키워드 (쉼표 구분)")
            content = st.text_area("상세 내용")
            if st.form_submit_button("저장"):
                new_data = pd.DataFrame([[log_date, client, content, manual_tags]], columns=['날짜', '광고주명', '소통내용', '핵심키워드'])
                st.session_state.history_db = pd.concat([st.session_state.history_db, new_data], ignore_index=True)
                st.rerun()
        st.dataframe(st.session_state.history_db, use_container_width=True)

elif menu == "디지털 리포트(내부)":
    st.header("📊 내부 관리 리포트")
    if not st.session_state.history_db.empty:
        target = st.selectbox("광고주 선택", sorted(st.session_state.history_db['광고주명'].unique()))
        period_opt = st.select_slider("기간", options=["7일", "15일", "한달", "분기"], value="한달")
        filtered = st.session_state.history_db[st.session_state.history_db['광고주명'] == target]
        if not filtered.empty:
            text = (filtered['핵심키워드'].fillna('').str.cat(sep=' ') + " ") * 3 + filtered['소통내용'].fillna('').str.cat(sep=' ')
            wc = WordCloud(font_path=FONT_PATH, width=800, height=400, background_color='white').generate(text)
            fig, ax = plt.subplots(); ax.imshow(wc); ax.axis('off'); st.pyplot(fig)

# --- [Trend Radar: 구글 뉴스 기반 수집 강화] ---
elif menu == "📊 Trend Radar(외부)":
    st.header("🌐 실시간 트렌드 레이더 (Multi-Channel)")
    st.info("💡 구글 및 네이트 뉴스를 분석하여 시장 트렌드를 수집합니다.")
    
    col_input, col_period = st.columns([3, 1])
    with col_input: trend_keyword = st.text_input("분석 키워드", placeholder="예: 도라지정과, 비건 뷰티")
    with col_period: period_val = st.selectbox("수집 범위", ["최근 7일", "최근 30일"])

    if st.button("🔍 트렌드 데이터 분석 시작"):
        if not trend_keyword: st.warning("키워드를 입력해 주세요.")
        else:
            with st.spinner("다채널 뉴스 데이터를 수집 중입니다..."):
                headers = {"User-Agent": "Mozilla/5.0"}
                # 🌟 구글 뉴스(RSS/Search) 방식 채택 (네이버보다 차단이 덜함)
                google_url = f"https://www.google.com/search?q={trend_keyword}&tbm=nws"
                
                try:
                    res = requests.get(google_url, headers=headers, timeout=10)
                    soup = BeautifulSoup(res.text, 'html.parser')
                    # 구글 뉴스의 제목과 요약 텍스트 추출
                    titles = soup.find_all(['h3', '

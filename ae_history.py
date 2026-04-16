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
st.set_page_config(page_title="AE Total Solution v8.1", layout="wide")

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

# 2. UI 디자인
st.markdown("""
    <style>
    header[data-testid="stHeader"] { visibility: hidden; }
    .stButton>button { width: 100%; border-radius: 8px; background-color: #FFB300; color: white; font-weight: bold; height: 3em; }
    /* 사이드바 여백 조절 */
    [data-testid="stSidebarNav"] { padding-top: 20px; }
    .menu-header { font-size: 1.1em; font-weight: bold; color: #FFB300; margin-top: 25px; margin-bottom: 10px; border-bottom: 2px solid #eee; padding-bottom: 5px; }
    </style>
""", unsafe_allow_html=True)

# 3. 사이드바 메뉴 디자인 (구분 및 여백 추가)
st.sidebar.title("🚀 AE Total Tool v8.1")

st.sidebar.markdown('<p class="menu-header">📋 내부 히스토리 관리</p>', unsafe_allow_html=True)
menu_internal = st.sidebar.radio("항목 선택", ["광고주 DB 관리", "관리 이력 입력", "디지털 리포트(내부)"], label_visibility="collapsed")

# 메뉴 간 간격을 위해 여백 추가
st.sidebar.markdown("<br><br>", unsafe_allow_html=True)

st.sidebar.markdown('<p class="menu-header">📊 외부 시장 분석</p>', unsafe_allow_html=True)
menu_external = st.sidebar.checkbox("📊 Trend Radar(외부)")

# 메뉴 결정 로직
if menu_external:
    menu = "📊 Trend Radar(외부)"
else:
    menu = menu_internal

# --- [기존 기능 로직] --- (지혜님이 쓰시던 기존 코드를 이 조건문에 맞춰 유지합니다)
if menu == "광고주 DB 관리":
    st.header("📂 데이터 로드 및 관리")
    # ... (기존 광고주 DB 관리 코드 생략, 지혜님 버전 유지)
    col1, col2 = st.columns(2)
    with col1:
        uploaded_clients = st.file_uploader("광고주 리스트", type=['xlsx', 'csv'], key="clients_v8")
    with col2:
        uploaded_history = st.file_uploader("백업 엑셀 파일", type=['xlsx'], key="history_v8")
    
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
        except: st.error("백업 로드 실패")

elif menu == "관리 이력 입력":
    st.header("✍️ 소통 이력 기록 및 수정")
    # ... (기존 관리 이력 입력 및 수정 코드 유지)
    if st.session_state.client_db.empty:
        st.warning("먼저 '광고주 DB 관리' 메뉴에서 리스트를 등록해주세요.")
    else:
        search_q = st.text_input("🔍 업체명 검색")
        all_c = sorted(st.session_state.client_db['광고주명'].dropna().unique())
        filtered_c = [c for c in all_c if search_q.lower() in str(c).lower()]
        
        with st.form("history_form_v8"):
            c1, c2 = st.columns(2)
            with c1:
                client = st.selectbox(f"광고주 ({len(filtered_c)}건)", filtered_c)
                log_date = st.date_input("날짜", datetime.date.today())
            with c2:
                manual_tags = st.text_input("키워드 (쉼표 구분)")
            content = st.text_area("상세 내용", height=150)
            if st.form_submit_button("저장"):
                new_data = pd.DataFrame([[log_date, client, content, manual_tags]], columns=['날짜', '광고주명', '소통내용', '핵심키워드'])
                st.session_state.history_db = pd.concat([st.session_state.history_db, new_data], ignore_index=True)
                st.rerun()

elif menu == "디지털 리포트(내부)":
    st.header("📊 내부 관리 리포트")
    # ... (기존 내부 워드클라우드 로직 유지)
    if not st.session_state.history_db.empty:
        target = st.selectbox("광고주 선택", sorted(st.session_state.history_db['광고주명'].unique()))
        filtered = st.session_state.history_db[st.session_state.history_db['광고주명'] == target]
        text = (filtered['핵심키워드'].fillna('').str.cat(sep=' ') + " ") * 3 + filtered['소통내용'].fillna('').str.cat(sep=' ')
        wc = WordCloud(font_path=FONT_PATH, width=800, height=400, background_color='white').generate(text)
        fig, ax = plt.subplots(); ax.imshow(wc); ax.axis('off'); st.pyplot(fig)

# --- [신규 기능: Trend Radar 수집 강화] ---
elif menu == "📊 Trend Radar(외부)":
    st.header("🌐 실시간 트렌드 레이더")
    st.info("💡 실시간 네이버 뉴스를 분석하여 가장 많이 언급되는 키워드를 보여줍니다.")
    
    col_input, col_period = st.columns([3, 1])
    with col_input:
        trend_keyword = st.text_input("분석 키워드 (예: 도라지정과)", placeholder="시장 분석을 위한 단어를 입력하세요")
    with col_period:
        # 기간 선택 시뮬레이션
        period_val = st.selectbox("수집 범위", ["최근 3일", "최근 7일", "최근 한달"])

    if st.button("🔍 트렌드 데이터 수집 시작"):
        if not trend_keyword:
            st.warning("키워드를 먼저 입력해 주세요.")
        else:
            with st.spinner("네이버 뉴스 데이터를 정밀 수집 중입니다..."):
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
                # 수집 신뢰성을 위해 검색 결과 주소 보강
                search_url = f"https://search.naver.com/search.naver?where=news&query={trend_keyword}&sort=0"
                
                try:
                    res = requests.get(search_url, headers=headers, timeout=10)
                    soup = BeautifulSoup(res.text, 'html.parser')
                    
                    # 뉴스 제목과 요약문 모두 수집하여 데이터 확보
                    titles = soup.select('.news_tit')
                    descriptions = soup.select('.news_dsc')
                    
                    all_news_text = " ".join([t.text for t in titles]) + " " + " ".join([d.text for d in descriptions])
                    
                    if len(all_news_text.strip()) < 10:
                        st.error("뉴스 데이터를 충분히 가져오지 못했습니다. 키워드가 너무 생소하거나 네이버 차단이 발생했을 수

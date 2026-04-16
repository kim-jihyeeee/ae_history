import streamlit as st
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from io import BytesIO
import datetime, os, requests, re
from bs4 import BeautifulSoup
from pptx import Presentation
from pptx.util import Inches

# 1. 페이지 설정 (메뉴 강제 확장 상태로 시작)
st.set_page_config(
    page_title="AE Total Solution v9.6", 
    layout="wide",
    initial_sidebar_state="expanded" 
)

@st.cache_data
def load_font():
    try:
        url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Bold.ttf"
        res = requests.get(url)
        with open("nanum_font.ttf", "wb") as f: f.write(res.content)
        return "nanum_font.ttf"
    except: return None

FONT_PATH = load_font()

# 세션 초기화
if 'client_db' not in st.session_state: st.session_state.client_db = pd.DataFrame()
if 'history_db' not in st.session_state: st.session_state.history_db = pd.DataFrame(columns=['날짜', '광고주명', '소통내용', '핵심키워드'])

# 2. UI 스타일 (🌟 사이드바 강제 노출 CSS 추가)
st.markdown("""
    <style>
    /* 닫힌 사이드바를 강제로 열거나 화살표를 보이게 함 */
    [data-testid="stSidebarNav"] { display: block !important; }
    [data-testid="collapsedControl"] { display: block !important; color: #FFB300 !important; }
    
    .stButton>button { width: 100%; border-radius: 8px; background-color: #FFB300; color: white; font-weight: bold; height: 3em; }
    .menu-header { font-size: 1.1em; font-weight: bold; color: #FFB300; margin-top: 35px; border-bottom: 2px solid #eee; padding-bottom: 5px; }
    .spacer { margin-bottom: 50px; }
    
    .restore-box {
        padding: 15px;
        background-color: #fff4e5;
        border: 1px solid #FFB300;
        border-radius: 8px;
        text-align: center;
        margin-bottom: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# 3. 사이드바 구성
st.sidebar.title("🚀 AE Total Tool v9.6")
st.sidebar.markdown('<p class="menu-header">📋 내부 히스토리 관리</p>', unsafe_allow_html=True)
m_int = st.sidebar.radio("항목", ["광고주 DB 관리", "관리 이력 입력", "디지털 리포트(내부)"], label_visibility="collapsed")
st.sidebar.markdown('<div class="spacer"></div>', unsafe_allow_html=True)
st.sidebar.markdown('<p class="menu-header">📊 외부 시장 분석</p>', unsafe_allow_html=True)
m_ext = st.sidebar.checkbox("📊 Trend Radar(듀얼 모드)")

menu = "📊 Trend Radar(외부)" if m_ext else m_int

# 안내 박스
st.markdown("""
    <div class="restore-box">
        💡 왼쪽 메뉴가 보이지 않으면 <b>새로고침(F5)</b>을 한 번 더 해주시거나, 화면 왼쪽 끝에 마우스를 가져가 보세요!
    </div>
""", unsafe_allow_html=True)

# --- [이후 로직 통합본] ---

if menu == "광고주 DB 관리":
    st.header("📂 데이터 로드 및 관리")
    c1, c2 = st.columns(2)
    with c1: 
        up_c = st.file_uploader("🏢 광고주 리스트 업로드", type=['xlsx', 'csv'], key="c_up")
        if up_c:
            df = pd.read_csv(up_c) if up_c.name.endswith('.csv') else pd.read_excel(up_c)
            df.rename(columns={df.columns[0]: '광고주명'}, inplace=True)
            st.session_state.client_db = df
            st.success("로드 완료!")
    with c2:
        up_h = st.file_uploader("💾 히스토리 백업 로드", type=['xlsx'], key="h_up")
        if up_h:
            h_df = pd.read_excel(up_h)
            if '날짜' in h_df.columns: h_df['날짜'] = pd.to_datetime(h_df['날짜']).dt.date
            st.session_state.history_db = h_df
            st.success("복구 완료!")

elif menu == "관리 이력 입력":
    st.header("✍️ 소통 이력 기록 및 수정")
    if st.session_state.client_db.empty:
        st.warning("먼저 '광고주 DB 관리' 메뉴에서 리스트를 등록해주세요.")
    else:
        search_q = st.text_input("🔍 업체명 검색")
        all_clients = sorted(st.session_state.client_db['광고주명'].dropna().unique())
        filtered_clients = [c for c in all_clients if search_q.lower() in str(c).lower()]
        with st.form("history_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                client = st.selectbox(f"광고주 선택 ({len(filtered_clients)}건)", filtered_clients)
                log_date = st.date_input("날짜", datetime.date.today())
            with c2: tags = st.text_input("🏷️ 핵심 키워드 (쉼표 구분)")
            content = st.text_area("상세 소통 내용", height=150)
            if st.form_submit_button("히스토리 저장"):
                new_data = pd.DataFrame([[log_date, client, content, tags]], columns=['날짜', '광고주명', '소통내용', '핵심키워드'])
                st.session_state.history_db = pd.concat([st.session_state.history_db, new_data], ignore_index=True)
                st.rerun()
        if not st.session_state.history_db.empty:
            st.divider()
            st.data_editor(st.session_state.history_db, use_container_width=True)

elif menu == "디지털 리포트(내부)":
    st.header("📊 내부 소통 키워드 분석")
    if not st.session_state.history_db.empty:
        target_client = st.selectbox("광고주 선택", sorted(st.session_state.history_db['광고주명'].unique()))
        period_opt = st.select_slider("📍 기간", options=["7일", "15일", "한달", "분기"], value="한달")
        days_delta = {"7일": 7, "15일": 15, "한달": 30, "분기": 90}[period_opt]
        start_date = datetime.date.today() - datetime.timedelta(days=days_delta)
        f_df = st.session_state.history_db[(st.session_state.history_db['광고주명'] == target_client) & (pd.to_datetime(st.session_state.history_db['날짜']).dt.date >= start_date)]
        if not f_df.empty:
            words = (f_df['핵심키워드'].fillna('').str.cat(sep=' ') + " ") * 3 + f_df['소통내용'].fillna('').str.cat(sep=' ')
            wc = WordCloud(font_path=FONT_PATH, width=900, height=500, background_color='white').generate(words)
            fig, ax = plt.subplots(); ax.imshow(wc); ax.axis('off'); st.pyplot(fig)

elif menu == "📊 Trend Radar(외부)":
    st.header("🌐 Trend Radar 듀얼 모드")
    t1, t2 = st.tabs(["📰 뉴스 에디션", "🔍 검색 에디션"])
    with t1:
        kw_n = st.text_input("뉴스 키워드")
        if st.button("🔍 뉴스 분석 시작"):
            rss = f"https://news.google.com/rss/search?q={kw_n}&hl=ko&gl=KR&ceid=KR:ko"
            res = requests.get(rss)
            items = BeautifulSoup(res.text, 'xml').find_all('item')
            txt = " ".join([re.split(r' - | \| ', i.title.get_text())[0] for i in items])
            if txt:
                wc = WordCloud(font_path=FONT_PATH, width=900, height=500, background_color='white', colormap='cool').generate(txt)
                fig, ax = plt.subplots(); ax.imshow(wc); ax.axis('off'); st.pyplot(fig)
    with t2:
        kw_s = st.text_input("검색 키워드")
        if st.button("🔍 검색 분석 시작"):
            rss = f"https://news.google.com/rss/search?q={kw_s}&hl=ko&gl=KR&ceid=KR:ko"
            res = requests.get(rss)
            soup = BeautifulSoup(res.text, 'xml')
            titles = [i.title.get_text() for i in soup.find_all('item')]
            clean = " ".join(re.findall(r'[가-힣]+', " ".join(titles)))
            for t in ["뉴스", "네이버", "구글", "다음"]: clean = clean.replace(t, "")
            if clean:
                wc_s = WordCloud(font_path=FONT_PATH, width=900, height=500, background_color='white', colormap='YlOrRd').generate(clean)
                fig_s, ax_s = plt.subplots(); ax_s.imshow(wc_s); ax_s.axis('off'); st.pyplot(fig_s)

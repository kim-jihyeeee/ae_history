import streamlit as st
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from io import BytesIO
import datetime, os, requests, re
from bs4 import BeautifulSoup
import google.generativeai as genai

# 1. 페이지 설정
st.set_page_config(
    page_title="AE Total Solution v10.4", 
    layout="wide",
    initial_sidebar_state="expanded" 
)

# 🌟 Gemini API 설정 (지혜님의 API 키를 넣어주세요)
API_KEY = "AQ.Ab8RN6Lc9LYyyyi-oE7eVOZfjfe8AKJIQ8u3SnPmUce-LjoZRw" 

if API_KEY != "AQ.Ab8RN6Lc9LYyyyi-oE7eVOZfjfe8AKJIQ8u3SnPmUce-LjoZRw":
    genai.configure(api_key=API_KEY)

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

# 2. UI 스타일
st.markdown("""
    <style>
    header[data-testid="stHeader"] { visibility: hidden; }
    .stButton>button { width: 100%; border-radius: 8px; background-color: #FFB300; color: white; font-weight: bold; height: 3em; }
    .ai-box { padding: 20px; background-color: #f8f9fa; border-radius: 10px; border-left: 5px solid #4285F4; margin-bottom: 20px; line-height: 1.6; }
    .menu-header { font-size: 1.1em; font-weight: bold; color: #FFB300; margin-top: 35px; border-bottom: 2px solid #eee; padding-bottom: 5px; }
    </style>
""", unsafe_allow_html=True)

# 3. 사이드바
st.sidebar.title("🚀 AE Total Tool v10.4")
st.sidebar.markdown('<p class="menu-header">📋 내부 히스토리 관리</p>', unsafe_allow_html=True)
m_int = st.sidebar.radio("항목", ["광고주 DB 관리", "관리 이력 입력", "디지털 리포트(내부)"], label_visibility="collapsed")
st.sidebar.markdown('<p class="menu-header">📊 외부 시장 분석</p>', unsafe_allow_html=True)
m_ext = st.sidebar.checkbox("📊 Trend Radar (AI)")

menu = "📊 Trend Radar(외부)" if m_ext else m_int

# [내부 관리 로직]
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
            st.session_state.history_db = h_df
            # 🌟 에러 수정된 부분: 따옴표와 괄호를 정확히 닫았습니다.
            st.success("복구 완료!")

elif menu == "관리 이력 입력":
    st.header("✍️ 소통 이력 기록")
    if st.session_state.client_db.empty: st.warning("먼저 리스트를 등록하세요.")
    else:
        q = st.text_input("🔍 업체명 검색")
        all_c = sorted(st.session_state.client_db['광고주명'].dropna().unique())
        filtered_c = [c for c in all_c if q.lower() in str(c).lower()]
        with st.form("history_form"):
            c1, c2 = st.columns(2)
            with c1:
                client = st.selectbox("광고주 선택", filtered_c)
                log_date = st.date_input("날짜", datetime.date.today())
            with c2: tags = st.text_input("🏷️ 핵심 키워드")
            content = st.text_area("내용")
            if st.form_submit_button("저장"):
                row = pd.DataFrame([[log_date, client, content, tags]], columns=['날짜', '광고주명', '소통내용', '핵심키워드'])
                st.session_state.history_db = pd.concat([st.session_state.history_db, row], ignore_index=True)
                st.rerun()

elif menu == "디지털 리포트(내부)":
    st.header("📊 내부 소통 키워드 분석")
    if not st.session_state.history_db.empty:
        target = st.selectbox("광고주 선택", sorted(st.session_state.history_db['광고주명'].unique()))
        f_df = st.session_state.history_db[st.session_state.history_db['광고주명'] == target]
        if not f_df.empty:
            words = (f_df['핵심키워드'].fillna('').str.cat(sep=' ') + " ") * 3 + f_df['소통내용'].fillna('').str.cat(sep=' ')
            wc = WordCloud(font_path=FONT_PATH, width=900, height=500, background_color='white').generate(words)
            fig, ax = plt.subplots(); ax.imshow(wc); ax.axis('off'); st.pyplot(fig)

elif menu == "📊 Trend Radar(외부)":
    st.header("🌐 AI Trend Radar 듀얼 모드")
    tab_n, tab_s = st.tabs(["📰 뉴스 에디션 (AI)", "🔍 검색 에디션 (AI)"])
    
    with tab_n:
        kw_n = st.text_input("뉴스 분석 키워드", key="kw_n")
        if st.button("🔍 뉴스 AI 분석 시작"):
            rss = f"https://news.google.com/rss/search?q={kw_n}&hl=ko&gl=KR&ceid=KR:ko"
            res = requests.get(rss)
            items = BeautifulSoup(res.text, 'xml').find_all('item')[:25]
            titles = [re.split(r' - | \| ', i.title.get_text())[0] for i in items]
            if titles:
                model = genai.GenerativeModel('gemini-1.5-flash')
                response = model.generate_content(f"'{kw_n}' 뉴스 요약 및 AE 전략 수립:\n" + "\n".join(titles))
                st.markdown(f'<div class="ai-box">{response.text}</div>', unsafe_allow_html=True)
                wc = WordCloud(font_path=FONT_PATH, width=900, height=400, background_color='white').generate(" ".join(titles))
                fig, ax = plt.subplots(); ax.imshow(wc); ax.axis('off'); st.pyplot(fig)
    
    with tab_s:
        kw_s = st.text_input("검색 분석 키워드", key="kw_s")
        if st.button("🔍 검색 AI 분석 시작"):
            rss = f"https://news.google.com/rss/search?q={kw_s}&hl=ko&gl=KR&ceid=KR:ko"
            res = requests.get(rss)
            titles = [i.title.get_text() for i in BeautifulSoup(res.text, 'xml').find_all('item')]
            if titles:
                clean_txt = " ".join(re.findall(r'[가-힣]+', " ".join(titles)))
                model = genai.GenerativeModel('gemini-1.5-flash')
                response = model.generate_content(f"'{kw_s}' 유저 관심사 분석:\n" + clean_txt)
                st.markdown(f'<div class="ai-box">{response.text}</div>', unsafe_allow_html=True)
                wc_s = WordCloud(font_path=FONT_PATH, width=900, height=400, background_color='white', colormap='YlOrRd').generate(clean_txt)
                fig_s, ax_s = plt.subplots(); ax_s.imshow(wc_s); ax_s.axis('off'); st.pyplot(fig_s)

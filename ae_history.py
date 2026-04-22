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
    page_title="AE Total Solution v10.8", 
    layout="wide",
    initial_sidebar_state="expanded" 
)

# 🌟 Gemini API 설정 (지혜님의 API 키 - 공백 제거 처리)
RAW_KEY = "AQ.Ab8RN6Lc9LYyyyi-oE7eVOZfjfe8AKJIQ8u3SnPmUce-LjoZRw"
API_KEY = RAW_KEY.strip()

# AI 모델 초기화 (에러 방어형)
@st.cache_resource
def load_ai_model():
    if not API_KEY: return None
    try:
        genai.configure(api_key=API_KEY)
        # 🌟 가장 최신이자 안정적인 모델명으로 고정
        return genai.GenerativeModel('gemini-1.5-flash')
    except: return None

model = load_ai_model()

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
    .ai-box { padding: 20px; background-color: #f8f9fa; border-radius: 10px; border-left: 5px solid #4285F4; margin-bottom: 20px; line-height: 1.8; }
    .menu-header { font-size: 1.1em; font-weight: bold; color: #FFB300; margin-top: 35px; border-bottom: 2px solid #eee; padding-bottom: 5px; }
    </style>
""", unsafe_allow_html=True)

# 3. 사이드바
st.sidebar.title("🚀 AE Total Tool v10.8")
st.sidebar.markdown('<p class="menu-header">📋 내부 히스토리 관리</p>', unsafe_allow_html=True)
m_int = st.sidebar.radio("항목", ["광고주 DB 관리", "관리 이력 입력", "디지털 리포트(내부)"], label_visibility="collapsed")
st.sidebar.markdown('<p class="menu-header">📊 외부 시장 분석</p>', unsafe_allow_html=True)
m_ext = st.sidebar.checkbox("📊 Trend Radar (AI)")

menu = "📊 Trend Radar(외부)" if m_ext else m_int

# [내부 로직 시작]
if menu == "광고주 DB 관리":
    st.header("📂 데이터 로드 및 관리")
    c1, c2 = st.columns(2)
    with c1: 
        up_c = st.file_uploader("🏢 광고주 리스트", type=['xlsx', 'csv'], key="c_up")
        if up_c:
            df = pd.read_csv(up_c) if up_c.name.endswith('.csv') else pd.read_excel(up_c)
            df.rename(columns={df.columns[0]: '광고주명'}, inplace=True)
            st.session_state.client_db = df
            st.success("로드 완료!")
    with c2:
        up_h = st.file_uploader("💾 히스토리 백업", type=['xlsx'], key="h_up")
        if up_h:
            st.session_state.history_db = pd.read_excel(up_h)
            st.success("복구 완료!")

elif menu == "관리 이력 입력":
    st.header("✍️ 소통 이력 기록")
    if st.session_state.client_db.empty: st.warning("리스트를 먼저 등록하세요.")
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

# --- [외부 로직: AI Trend Radar - 에러 완전 방어] ---
elif menu == "📊 Trend Radar(외부)":
    st.header("🌐 AI Trend Radar 듀얼 모드")
    tab_n, tab_s = st.tabs(["📰 뉴스 AI 분석", "🔍 검색 AI 분석"])
    
    with tab_n:
        kw_n = st.text_input("뉴스 분석 키워드", key="kw_n")
        if st.button("🔍 뉴스 AI 분석 시작"):
            with st.spinner("AI 분석 중..."):
                rss = f"https://news.google.com/rss/search?q={kw_n}&hl=ko&gl=KR&ceid=KR:ko"
                res = requests.get(rss)
                items = BeautifulSoup(res.text, 'xml').find_all('item')[:15]
                titles = [re.split(r' - | \| ', i.title.get_text())[0] for i in items]
                
                if titles:
                    # AI 분석 (오류 시 워드클라우드만 출력)
                    try:
                        prompt = f"키워드 '{kw_n}' 관련 뉴스 제목들을 분석해 3줄 트렌드 요약과 광고 소구점을 알려줘:\n\n" + "\n".join(titles)
                        response = model.generate_content(prompt)
                        st.markdown(f'<div class="ai-box"><b>🤖 AI 리포트</b><br><br>{response.text}</div>', unsafe_allow_html=True)
                    except Exception as e:
                        st.error("AI 엔진 연결에 일시적인 문제가 있어 워드클라우드만 표시합니다.")
                    
                    wc = WordCloud(font_path=FONT_PATH, width=900, height=400, background_color='white').generate(" ".join(titles))
                    fig, ax = plt.subplots(); ax.imshow(wc); ax.axis('off'); st.pyplot(fig)

    with tab_s:
        kw_s = st.text_input("검색 분석 키워드", key="kw_s")
        if st.button("🔍 검색 AI 분석 시작"):
            with st.spinner("관심사 분석 중..."):
                rss = f"https://news.google.com/rss/search?q={kw_s}&hl=ko&gl=KR&ceid=KR:ko"
                res = requests.get(rss)
                titles = [i.title.get_text() for i in BeautifulSoup(res.text, 'xml').find_all('item')[:15]]
                
                if titles:
                    clean_txt = " ".join(re.findall(r'[가-힣]+', " ".join(titles)))
                    try:
                        response_s = model.generate_content(f"'{kw_s}' 유저 관심사 분석:\n" + clean_txt)
                        st.markdown(f'<div class="ai-box">{response_s.text}</div>', unsafe_allow_html=True)
                    except Exception:
                        pass
                    
                    wc_s = WordCloud(font_path=FONT_PATH, width=900, height=400, background_color='white', colormap='YlOrRd').generate(clean_txt)
                    fig_s, ax_s = plt.subplots(); ax_s.imshow(wc_s); ax_s.axis('off'); st.pyplot(fig_s)

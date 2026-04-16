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
    page_title="AE Total Solution v10.1", 
    layout="wide",
    initial_sidebar_state="expanded" 
)

# 🌟 Gemini API 설정 (복사한 키를 여기에 붙여넣으세요!)
API_KEY = "여기에_복사한_키를_붙여넣으세요" 

if API_KEY != "여기에_복사한_키를_붙여넣으세요":
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
    .ai-box { padding: 20px; background-color: #f8f9fa; border-radius: 10px; border-left: 5px solid #4285F4; margin-bottom: 20px; line-height: 1.6; font-size: 1.1em; }
    .menu-header { font-size: 1.1em; font-weight: bold; color: #FFB300; margin-top: 35px; border-bottom: 2px solid #eee; padding-bottom: 5px; }
    </style>
""", unsafe_allow_html=True)

# 3. 사이드바
st.sidebar.title("🚀 AE Total Tool v10.1")
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
            st.session_state.history_db = pd.read_excel(up_h)
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

# --- [외부 로직: Gemini AI Trend Radar] ---
elif menu == "📊 Trend Radar(외부)":
    st.header("🌐 AI Trend Radar (Gemini 분석)")
    kw = st.text_input("분석 키워드 입력", placeholder="예: 혈당 다이어트 트렌드")
    
    if st.button("🔍 AI 심층 분석 시작"):
        if not kw: st.warning("키워드를 입력하세요.")
        elif API_KEY == "AQ.Ab8RN6Lc9LYyyyi-oE7eVOZfjfe8AKJIQ8u3SnPmUce-LjoZRw": st.error("API 키를 코드에 먼저 넣어주세요!")
        else:
            with st.spinner("AI가 최신 트렌드를 읽고 전략을 짜는 중입니다..."):
                rss_url = f"https://news.google.com/rss/search?q={kw}&hl=ko&gl=KR&ceid=KR:ko"
                res = requests.get(rss_url)
                items = BeautifulSoup(res.text, 'xml').find_all('item')[:25]
                titles = [i.title.get_text() for i in items]
                context_text = "\n".join(titles)

                model = genai.GenerativeModel('gemini-1.5-flash')
                prompt = f"다음 '{kw}' 관련 뉴스들을 분석해 AE 관점에서 3줄 요약하고, 소비자 관심사 3개와 광고 컨셉 2개를 추천해줘:\n\n{context_text}"
                response = model.generate_content(prompt)
                
                st.markdown(f'<div class="ai-box"><b>🤖 AI 트렌드 전략 브리핑</b><br><br>{response.text}</div>', unsafe_allow_html=True)
                
                clean_data = " ".join(re.findall(r'[가-힣]+', context_text))
                wc = WordCloud(font_path=FONT_PATH, width=900, height=400, background_color='white', colormap='cool').generate(clean_data)
                fig, ax = plt.subplots(); ax.imshow(wc); ax.axis('off'); st.pyplot(fig)

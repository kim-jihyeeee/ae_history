import streamlit as st
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from io import BytesIO
import datetime, os, requests, re
from bs4 import BeautifulSoup
import google.generativeai as genai

# 1. 페이지 설정 및 사이드바 강제 고정
st.set_page_config(
    page_title="AE Total Tool v11.0", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# 🌟 Gemini API 설정 (지혜님 키 고정)
API_KEY = "AQ.Ab8RN6Lc9LYyyyi-oE7eVOZfjfe8AKJIQ8u3SnPmUce-LjoZRw"
if API_KEY:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')

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

# 2. UI 스타일 (AI 리포트 박스 및 디자인 최적화)
st.markdown("""
    <style>
    header[data-testid="stHeader"] { visibility: hidden; }
    .stButton>button { width: 100%; border-radius: 8px; background-color: #FFB300; color: white; font-weight: bold; height: 3.5em; }
    .ai-report-card { 
        padding: 25px; background-color: #F0F7FF; border-radius: 12px; border-left: 10px solid #007BFF; 
        margin-bottom: 30px; font-size: 1.1em; line-height: 1.8; color: #333;
    }
    .menu-header { font-size: 1.1em; font-weight: bold; color: #FFB300; margin-top: 35px; border-bottom: 2px solid #eee; padding-bottom: 5px; }
    .spacer { margin-bottom: 50px; }
    </style>
""", unsafe_allow_html=True)

# 3. 사이드바 메뉴 구성
st.sidebar.title("🚀 AE Total Tool v11.0")
st.sidebar.markdown('<p class="menu-header">📋 내부 히스토리 관리</p>', unsafe_allow_html=True)
m_int = st.sidebar.radio("항목", ["광고주 DB 관리", "관리 이력 입력", "디지털 리포트(내부)"], label_visibility="collapsed")
st.sidebar.markdown('<div class="spacer"></div>', unsafe_allow_html=True)
st.sidebar.markdown('<p class="menu-header">📊 외부 시장 분석</p>', unsafe_allow_html=True)
m_ext = st.sidebar.checkbox("📊 Trend Radar (AI)", value=True)

menu = "📊 Trend Radar(외부)" if m_ext else m_int

# --- [내부 로직 1: 광고주 DB 관리] ---
if menu == "광고주 DB 관리":
    st.header("📂 데이터 로드 및 관리")
    c1, c2 = st.columns(2)
    with c1: 
        up_c = st.file_uploader("🏢 광고주 리스트 (xlsx/csv)", type=['xlsx', 'csv'])
        if up_c:
            df = pd.read_csv(up_c) if up_c.name.endswith('.csv') else pd.read_excel(up_c)
            df.rename(columns={df.columns[0]: '광고주명'}, inplace=True)
            st.session_state.client_db = df
            st.success("✅ 광고주 리스트 로드 완료")
    with c2:
        up_h = st.file_uploader("💾 히스토리 백업 로드 (xlsx)", type=['xlsx'])
        if up_h:
            h_df = pd.read_excel(up_h)
            h_df['날짜'] = pd.to_datetime(h_df['날짜']).dt.date
            st.session_state.history_db = h_df
            st.success(f"✅ {len(h_df)}건의 이력 복구 완료")

# --- [내부 로직 2: 관리 이력 입력] ---
elif menu == "관리 이력 입력":
    st.header("✍️ 소통 이력 기록")
    if st.session_state.client_db.empty:
        st.warning("광고주 리스트를 먼저 등록하세요.")
    else:
        q = st.text_input("🔍 업체명 검색")
        all_c = sorted(st.session_state.client_db['광고주명'].dropna().unique())
        filtered_c = [c for c in all_c if q.lower() in str(c).lower()]
        with st.form("history_form"):
            c1, c2 = st.columns(2)
            with c1:
                sel_c = st.selectbox(f"광고주 선택", filtered_c)
                dt = st.date_input("날짜", datetime.date.today())
            with c2: tags = st.text_input("🏷️ 핵심 키워드")
            txt = st.text_area("📄 소통 내용", height=150)
            if st.form_submit_button("저장"):
                row = pd.DataFrame([[dt, sel_c, txt, tags]], columns=['날짜', '광고주명', '소통내용', '핵심키워드'])
                st.session_state.history_db = pd.concat([st.session_state.history_db, row], ignore_index=True)
                st.rerun()
        st.divider()
        st.data_editor(st.session_state.history_db, use_container_width=True)

# --- [내부 로직 3: 디지털 리포트(내부)] ---
elif menu == "디지털 리포트(내부)":
    st.header("📊 내부 소통 키워드 분석")
    if st.session_state.history_db.empty:
        st.info("기록된 데이터가 없습니다.")
    else:
        target = st.selectbox("광고주 선택", sorted(st.session_state.history_db['광고주명'].unique()))
        period = st.select_slider("📅 분석 기간 설정", options=["7일", "15일", "한달", "분기"], value="한달")
        days_map = {"7일": 7, "15일": 15, "한달": 30, "분기": 90}
        limit_dt = datetime.date.today() - datetime.timedelta(days=days_map[period])
        f_df = st.session_state.history_db[(st.session_state.history_db['광고주명'] == target) & (st.session_state.history_db['날짜'] >= limit_dt)]
        if not f_df.empty:
            words = (f_df['핵심키워드'].fillna('').str.cat(sep=' ') + " ") * 3 + f_df['소통내용'].fillna('').str.cat(sep=' ')
            wc = WordCloud(font_path=FONT_PATH, width=900, height=500, background_color='white').generate(words)
            fig, ax = plt.subplots(figsize=(10, 5)); ax.imshow(wc); ax.axis('off'); st.pyplot(fig)

# --- [외부 로직: Trend Radar AI - 모든 기능 통합] ---
elif menu == "📊 Trend Radar(외부)":
    st.header("🌐 AI Trend Radar 듀얼 모드 v11.0")
    t_news, t_srch = st.tabs(["📰 뉴스 AI 분석", "🔍 검색 AI 분석"])
    
    with t_news:
        c1, c2 = st.columns([3, 1])
        with c1: kw_n = st.text_input("뉴스 분석 키워드", key="kw_n")
        with c2: prd_n = st.selectbox("수집 기간", ["최근 3일", "최근 7일", "최근 30일", "최근 90일"], key="pn")
        if st.button("📰 뉴스 AI 심층 분석 시작"):
            with st.spinner("AI 분석 중..."):
                days = int(re.findall(r'\d+', prd_n)[0])
                limit = datetime.datetime.now() - datetime.timedelta(days=days)
                rss = f"https://news.google.com/rss/search?q={kw_n}&hl=ko&gl=KR&ceid=KR:ko"
                res = requests.get(rss)
                items = BeautifulSoup(res.text, 'xml').find_all('item')[:25]
                titles = [re.split(r' - | \| ', i.title.get_text())[0] for i in items if datetime.datetime.strptime(i.pubDate.get_text(), '%a, %d %b %Y %H:%M:%S %Z') >= limit]
                if titles:
                    try:
                        prompt = f"'{kw_n}' 관련 뉴스 제목들 분석해 3줄 요약, 타겟 추천, 광고 소구점 2개 제안해줘:\n\n" + "\n".join(titles)
                        response = model.generate_content(prompt)
                        st.markdown(f'<div class="ai-report-card"><b>🤖 AI 트렌드 리포트</b><br><br>{response.text}</div>', unsafe_allow_html=True)
                    except: st.error("AI 연결 실패")
                    wc = WordCloud(font_path=FONT_PATH, width=900, height=450, background_color='white', colormap='cool').generate(" ".join(titles))
                    fig, ax = plt.subplots(figsize=(10, 5)); ax.imshow(wc); ax.axis('off'); st.pyplot(fig)

    with t_srch:
        cs1, cs2 = st.columns([3, 1])
        with cs1: kw_s = st.text_input("검색 분석 키워드", key="kw_s")
        with cs2: prd_s = st.selectbox("수집 기간", ["최근 3일", "최근 7일", "최근 30일", "최근 90일"], key="ps")
        if st.button("🔍 검색 소비자 니즈 AI 분석 시작"):
            with st.spinner("소비자 분석 중..."):
                days_s = int(re.findall(r'\d+', prd_s)[0])
                limit_s = datetime.datetime.now() - datetime.timedelta(days=days_s)
                rss_s = f"https://news.google.com/rss/search?q={kw_s}&hl=ko&gl=KR&ceid=KR:ko"
                items_s = BeautifulSoup(requests.get(rss_s).text, 'xml').find_all('item')[:25]
                titles_s = [i.title.get_text() for i in items_s if datetime.datetime.strptime(i.pubDate.get_text(), '%a, %d %b %Y %H:%M:%S %Z') >= limit_s]
                if titles_s:
                    clean_txt = " ".join(re.findall(r'[가-힣]+', " ".join(titles_s)))
                    try:
                        prompt_s = f"'{kw_s}' 검색어 분석해 유저 니즈 3가지와 전략 제안해줘:\n\n" + clean_txt
                        response_s = model.generate_content(prompt_s)
                        st.markdown(f'<div class="ai-report-card"><b>🤖 소비자 니즈 분석 AI 리포트</b><br><br>{response_s.text}</div>', unsafe_allow_html=True)
                    except: st.error("AI 연결 실패")
                    wc_s = WordCloud(font_path=FONT_PATH, width=900, height=450, background_color='white', colormap='YlOrRd').generate(clean_txt)
                    fig_s, ax_s = plt.subplots(figsize=(10, 5)); ax_s.imshow(wc_s); ax_s.axis('off'); st.pyplot(fig_s)

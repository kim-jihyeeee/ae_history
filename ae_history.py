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
    page_title="AE Total Solution v10.6", 
    layout="wide",
    initial_sidebar_state="expanded" 
)

# 🌟 Gemini API 설정 (지혜님의 API 키 적용 완료)
API_KEY = "AQ.Ab8RN6Lc9LYyyyi-oE7eVOZfjfe8AKJIQ8u3SnPmUce-LjoZRw" 

# [수정] API 키가 있으면 즉시 설정되도록 변경
if API_KEY:
    try:
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        st.error(f"API 설정 중 오류 발생: {e}")

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
    .ai-box { padding: 20px; background-color: #f8f9fa; border-radius: 10px; border-left: 5px solid #4285F4; margin-bottom: 20px; line-height: 1.8; font-size: 1.05em; }
    .menu-header { font-size: 1.1em; font-weight: bold; color: #FFB300; margin-top: 35px; border-bottom: 2px solid #eee; padding-bottom: 5px; }
    </style>
""", unsafe_allow_html=True)

# 3. 사이드바
st.sidebar.title("🚀 AE Total Tool v10.6")
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

# --- [외부 로직: Trend Radar AI 분석] ---
elif menu == "📊 Trend Radar(외부)":
    st.header("🌐 AI Trend Radar 듀얼 모드")
    tab_n, tab_s = st.tabs(["📰 뉴스 에디션 (AI)", "🔍 검색 에디션 (AI)"])
    
    with tab_n:
        kw_n = st.text_input("뉴스 분석 키워드", key="kw_n", placeholder="예: 콘드로이친 효능")
        if st.button("🔍 뉴스 AI 분석 시작"):
            with st.spinner("AI가 최신 뉴스를 분석 중입니다..."):
                rss = f"https://news.google.com/rss/search?q={kw_n}&hl=ko&gl=KR&ceid=KR:ko"
                res = requests.get(rss)
                items = BeautifulSoup(res.text, 'xml').find_all('item')[:20]
                titles = [re.split(r' - | \| ', i.title.get_text())[0] for i in items]
                
                if titles:
                    # AI 분석 실행
                    prompt = f"다음 '{kw_n}' 관련 뉴스 제목들을 분석해 1)현재 트렌드 3줄 요약 2)소비자 니즈 3가지 3)광고 카피 제안을 해줘:\n\n" + "\n".join(titles)
                    response = model.generate_content(prompt)
                    st.markdown(f'<div class="ai-box"><b>🤖 뉴스 트렌드 리포트</b><br><br>{response.text}</div>', unsafe_allow_html=True)
                    
                    # 워드클라우드
                    wc = WordCloud(font_path=FONT_PATH, width=900, height=400, background_color='white', colormap='cool').generate(" ".join(titles))
                    fig, ax = plt.subplots(); ax.imshow(wc); ax.axis('off'); st.pyplot(fig)
                else:
                    st.error("데이터를 가져오지 못했습니다. 키워드를 변경해 보세요.")

    with tab_s:
        kw_s = st.text_input("검색 분석 키워드", key="kw_s", placeholder="예: 무라벨 생수 추천")
        if st.button("🔍 검색 AI 분석 시작"):
            with st.spinner("AI가 소비자 검색 관심사를 분석 중입니다..."):
                rss = f"https://news.google.com/rss/search?q={kw_s}&hl=ko&gl=KR&ceid=KR:ko"
                res = requests.get(rss)
                soup = BeautifulSoup(res.text, 'xml')
                titles = [i.title.get_text() for i in soup.find_all('item')]
                
                if titles:
                    clean_txt = " ".join(re.findall(r'[가-힣]+', " ".join(titles)))
                    # AI 분석 실행
                    prompt_s = f"다음은 '{kw_s}'에 대한 소비자 검색 데이터 요약이다. 유저들의 진짜 고민과 소구점을 마케팅 관점에서 분석해줘:\n\n" + clean_txt
                    response_s = model.generate_content(prompt_s)
                    st.markdown(f'<div class="ai-box"><b>🤖 검색 데이터 심층 분석</b><br><br>{response_s.text}</div>', unsafe_allow_html=True)
                    
                    # 워드클라우드
                    wc_s = WordCloud(font_path=FONT_PATH, width=900, height=400, background_color='white', colormap='YlOrRd').generate(clean_txt)
                    fig_s, ax_s = plt.subplots(); ax_s.imshow(wc_s); ax_s.axis('off'); st.pyplot(fig_s)
                else:
                    st.error("데이터를 가져오지 못했습니다. 키워드를 변경해 보세요.")

import streamlit as st
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from io import BytesIO
import datetime, requests, re
from bs4 import BeautifulSoup
import google.generativeai as genai

# 1. 페이지 설정
st.set_page_config(page_title="AE Total Tool v12.0", layout="wide", initial_sidebar_state="expanded")

# 🌟 Gemini API 설정 (모델 자동 탐색 로직 도입)
API_KEY = "AQ.Ab8RN6Lc9LYyyyi-oE7eVOZfjfe8AKJIQ8u3SnPmUce-LjoZRw"

@st.cache_resource
def init_ai_engine():
    if not API_KEY: return None
    try:
        genai.configure(api_key=API_KEY)
        # 🌟 지혜님 계정에서 사용 가능한 모델 리스트를 탐색하여 가장 적합한 것을 자동 선택합니다.
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # 1.5-flash -> 1.0-pro -> gemini-pro 순으로 우선순위 탐색
        target_model = 'models/gemini-1.5-flash'
        if target_model not in available_models:
            target_model = next((m for m in available_models if 'gemini-1.5' in m), 
                           next((m for m in available_models if 'gemini-pro' in m), available_models[0]))
        
        return genai.GenerativeModel(target_model)
    except Exception as e:
        return None

ai_engine = init_ai_engine()

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
    .stButton>button { width: 100%; border-radius: 8px; background-color: #FFB300; color: white; font-weight: bold; height: 3.5em; }
    .ai-report-card { padding: 25px; background-color: #F0F7FF; border-radius: 12px; border-left: 10px solid #007BFF; margin-bottom: 25px; line-height: 1.8; color: #333; }
    .menu-header { font-size: 1.1em; font-weight: bold; color: #FFB300; margin-top: 35px; border-bottom: 2px solid #eee; padding-bottom: 5px; }
    </style>
""", unsafe_allow_html=True)

# 3. 사이드바
st.sidebar.title("🚀 AE Total Tool v12.0")
st.sidebar.markdown('<p class="menu-header">📋 내부 히스토리 관리</p>', unsafe_allow_html=True)
m_int = st.sidebar.radio("항목", ["광고주 DB 관리", "관리 이력 입력", "디지털 리포트(내부)"], label_visibility="collapsed")
st.sidebar.markdown('<div style="margin-bottom: 50px;"></div>', unsafe_allow_html=True)
st.sidebar.markdown('<p class="menu-header">📊 외부 시장 분석</p>', unsafe_allow_html=True)
m_ext = st.sidebar.checkbox("📊 Trend Radar (AI)", value=True)

menu = "📊 Trend Radar(외부)" if m_ext else m_int

# [내부 데이터 관리 로직]
if menu == "광고주 DB 관리":
    st.header("📂 데이터 로드 및 관리")
    c1, c2 = st.columns(2)
    with c1: 
        up_c = st.file_uploader("🏢 광고주 리스트", type=['xlsx', 'csv'])
        if up_c:
            df = pd.read_csv(up_c) if up_c.name.endswith('.csv') else pd.read_excel(up_c)
            df.rename(columns={df.columns[0]: '광고주명'}, inplace=True)
            st.session_state.client_db = df
            st.success("✅ 로드 완료")
    with c2:
        up_h = st.file_uploader("💾 히스토리 백업 로드", type=['xlsx'])
        if up_h:
            h_df = pd.read_excel(up_h)
            h_df['날짜'] = pd.to_datetime(h_df['날짜'])
            st.session_state.history_db = h_df
            st.success(f"✅ {len(h_df)}건 복구 완료")

elif menu == "관리 이력 입력":
    st.header("✍️ 소통 이력 기록")
    if st.session_state.client_db.empty: st.warning("광고주 리스트를 먼저 등록하세요.")
    else:
        all_c = sorted(st.session_state.client_db['광고주명'].dropna().unique())
        with st.form("history_form"):
            c1, c2 = st.columns(2)
            with c1:
                sel_c = st.selectbox("광고주 선택", all_c)
                dt = st.date_input("날짜", datetime.date.today())
            with c2: tags = st.text_input("🏷️ 핵심 키워드")
            txt = st.text_area("📄 소통 내용")
            if st.form_submit_button("저장"):
                row = pd.DataFrame([[pd.to_datetime(dt), sel_c, txt, tags]], columns=['날짜', '광고주명', '소통내용', '핵심키워드'])
                st.session_state.history_db = pd.concat([st.session_state.history_db, row], ignore_index=True)
                st.rerun()
        st.divider()
        st.data_editor(st.session_state.history_db, use_container_width=True)

elif menu == "디지털 리포트(내부)":
    st.header("📊 내부 소통 키워드 분석")
    if st.session_state.history_db.empty: st.info("기록된 데이터가 없습니다.")
    else:
        target = st.selectbox("광고주 선택", sorted(st.session_state.history_db['광고주명'].unique()))
        period = st.select_slider("📅 기간 설정", options=["7일", "15일", "30일", "90일"], value="30일")
        days = int(re.findall(r'\d+', period)[0])
        limit_dt = pd.Timestamp(datetime.date.today() - datetime.timedelta(days=days))
        f_df = st.session_state.history_db[(st.session_state.history_db['광고주명'] == target) & (pd.to_datetime(st.session_state.history_db['날짜']) >= limit_dt)]
        if not f_df.empty:
            words = (f_df['핵심키워드'].fillna('').str.cat(sep=' ') + " ") * 3 + f_df['소통내용'].fillna('').str.cat(sep=' ')
            wc = WordCloud(font_path=FONT_PATH, width=900, height=500, background_color='white').generate(words)
            fig, ax = plt.subplots(); ax.imshow(wc); ax.axis('off'); st.pyplot(fig)

# --- [외부 Trend Radar - 자동 탐색 AI 엔진 적용] ---
elif menu == "📊 Trend Radar(외부)":
    st.header("🌐 AI Trend Radar v12.0")
    t_news, t_srch = st.tabs(["📰 뉴스 AI 분석", "🔍 검색 AI 분석"])
    
    with t_news:
        c1, c2 = st.columns([3, 1])
        with c1: kw_n = st.text_input("뉴스 키워드", key="kn_v12")
        with c2: prd_n = st.selectbox("수집 기간", ["3일", "7일", "30일", "90일"], key="pn_v12")
        if st.button("📰 뉴스 AI 분석 시작"):
            with st.spinner("최적의 모델을 찾아 트렌드 분석 중..."):
                rss = f"https://news.google.com/rss/search?q={kw_n}&hl=ko&gl=KR&ceid=KR:ko"
                items = BeautifulSoup(requests.get(rss).text, 'xml').find_all('item')[:15]
                titles = [re.split(r' - | \| ', i.title.get_text())[0] for i in items]
                if titles:
                    if ai_engine:
                        try:
                            resp = ai_engine.generate_content(f"키워드 '{kw_n}' 관련 뉴스 제목들 분석. AE 전략 3줄 요약:\n\n" + "\n".join(titles))
                            st.markdown(f'<div class="ai-report-card"><b>🤖 AI 트렌드 리포트</b><br><br>{resp.text}</div>', unsafe_allow_html=True)
                        except Exception as e: st.error(f"AI 호출 오류: {e}")
                    else: st.warning("사용 가능한 AI 모델을 찾지 못했습니다.")
                    wc = WordCloud(font_path=FONT_PATH, width=900, height=450, background_color='white').generate(" ".join(titles))
                    fig, ax = plt.subplots(); ax.imshow(wc); ax.axis('off'); st.pyplot(fig)

    with t_srch:
        cs1, cs2 = st.columns([3, 1])
        with cs1: kw_s = st.text_input("검색 키워드", key="ks_v12")
        with cs2: prd_s = st.selectbox("수집 기간", ["3일", "7일", "30일", "90일"], key="ps_v12")
        if st.button("🔍 검색 AI 분석 시작"):
            with st.spinner("소비자 고민 분석 중..."):
                rss_s = f"https://news.google.com/rss/search?q={kw_s}&hl=ko&gl=KR&ceid=KR:ko"
                items_s = BeautifulSoup(requests.get(rss_s).text, 'xml').find_all('item')[:15]
                titles_s = [i.title.get_text() for i in items_s]
                if titles_s:
                    clean = " ".join(re.findall(r'[가-힣]+', " ".join(titles_s)))
                    if ai_engine:
                        try:
                            resp_s = ai_engine.generate_content(f"'{kw_s}' 검색어 기반 유저 고민과 니즈 분석:\n\n" + clean)
                            st.markdown(f'<div class="ai-report-card"><b>🤖 소비자 관심 분석 AI 리포트</b><br><br>{resp_s.text}</div>', unsafe_allow_html=True)
                        except Exception as e: st.error(f"AI 호출 오류: {e}")
                    wc_s = WordCloud(font_path=FONT_PATH, width=900, height=450, background_color='white', colormap='YlOrRd').generate(clean)
                    fig_s, ax_s = plt.subplots(); ax_s.imshow(wc_s); ax_s.axis('off'); st.pyplot(fig_s)

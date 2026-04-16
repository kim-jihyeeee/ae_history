import streamlit as st
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from io import BytesIO
import datetime, os, requests, re
from bs4 import BeautifulSoup
from pptx import Presentation
from pptx.util import Inches

# 1. 기본 설정 및 폰트 로드
st.set_page_config(page_title="AE Total Solution v8.9", layout="wide")

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
    .menu-header { font-size: 1.1em; font-weight: bold; color: #FFB300; margin-top: 35px; border-bottom: 2px solid #eee; padding-bottom: 5px; }
    .spacer { margin-bottom: 50px; }
    </style>
""", unsafe_allow_html=True)

# 3. 사이드바 메뉴
st.sidebar.title("🚀 AE Total Tool v8.9")
st.sidebar.markdown('<p class="menu-header">📋 내부 히스토리 관리</p>', unsafe_allow_html=True)
m_int = st.sidebar.radio("항목", ["광고주 DB 관리", "관리 이력 입력", "디지털 리포트(내부)"], label_visibility="collapsed")
st.sidebar.markdown('<div class="spacer"></div>', unsafe_allow_html=True)
st.sidebar.markdown('<p class="menu-header">📊 외부 시장 분석</p>', unsafe_allow_html=True)
m_ext = st.sidebar.checkbox("📊 Trend Radar(듀얼 모드)")

menu = "📊 Trend Radar(외부)" if m_ext else m_int

# --- [내부 로직 생략 (v8.8과 동일)] ---
if menu == "광고주 DB 관리":
    st.header("📂 데이터 로드 및 관리")
    c1, c2 = st.columns(2)
    with c1: 
        up_c = st.file_uploader("광고주 리스트", type=['xlsx', 'csv'], key="c_up")
        if up_c:
            df = pd.read_csv(up_c) if up_c.name.endswith('.csv') else pd.read_excel(up_c)
            df.rename(columns={df.columns[0]: '광고주명'}, inplace=True)
            st.session_state.client_db = df
            st.success("로드 완료")
    with c2:
        up_h = st.file_uploader("백업 엑셀", type=['xlsx'], key="h_up")
        if up_h:
            st.session_state.history_db = pd.read_excel(up_h)
            st.success("복구 완료")

elif menu == "관리 이력 입력":
    st.header("✍️ 소통 이력 기록 및 수정")
    if st.session_state.client_db.empty: st.warning("먼저 광고주 리스트를 등록하세요.")
    else:
        q = st.text_input("🔍 업체명 검색")
        all_c = sorted(st.session_state.client_db['광고주명'].dropna().unique())
        filtered_c = [c for c in all_c if q.lower() in str(c).lower()]
        with st.form("history_form"):
            c1, c2 = st.columns(2)
            with c1:
                sel_c = st.selectbox(f"광고주 ({len(filtered_c)}건)", filtered_c)
                dt = st.date_input("날짜", datetime.date.today())
            with c2: tags = st.text_input("키워드 (쉼표 구분)")
            txt = st.text_area("상세 내용")
            if st.form_submit_button("저장"):
                row = pd.DataFrame([[dt, sel_c, txt, tags]], columns=['날짜', '광고주명', '소통내용', '핵심키워드'])
                st.session_state.history_db = pd.concat([st.session_state.history_db, row], ignore_index=True)
                st.rerun()
        st.dataframe(st.session_state.history_db, use_container_width=True)

elif menu == "디지털 리포트(내부)":
    st.header("📊 내부 관리 리포트")
    if not st.session_state.history_db.empty:
        target = st.selectbox("광고주 선택", sorted(st.session_state.history_db['광고주명'].unique()))
        f = st.session_state.history_db[st.session_state.history_db['광고주명'] == target]
        if not f.empty:
            words = (f['핵심키워드'].fillna('').str.cat(sep=' ') + " ") * 3 + f['소통내용'].fillna('').str.cat(sep=' ')
            wc = WordCloud(font_path=FONT_PATH, width=800, height=400, background_color='white').generate(words)
            fig, ax = plt.subplots(); ax.imshow(wc); ax.axis('off'); st.pyplot(fig)

# --- 🌟 Trend Radar 듀얼 모드 (뉴스 vs 검색) ---
elif menu == "📊 Trend Radar(외부)":
    st.header("🌐 Trend Radar 듀얼 모드")
    
    # 모드 선택 탭
    tab_news, tab_search = st.tabs(["📰 뉴스 에디션 (공급자 트렌드)", "🔍 검색 에디션 (소비자 관심도)"])

    with tab_news:
        st.subheader("최신 뉴스 기반 키워드 분석")
        c1, c2 = st.columns([3, 1])
        with c1: kw_n = st.text_input("뉴스 분석 키워드", placeholder="예: 비건 뷰티, 강아지 관절")
        with c2: prd_n = st.selectbox("수집 기간", ["최근 7일", "최근 30일", "최근 60일"], key="prd_n")
        
        if st.button("🔍 뉴스 트렌드 분석 시작"):
            with st.spinner("뉴스를 분석 중입니다..."):
                days = int(re.findall(r'\d+', prd_n)[0])
                limit_date = datetime.datetime.now() - datetime.timedelta(days=days)
                rss_url = f"https://news.google.com/rss/search?q={kw_n}&hl=ko&gl=KR&ceid=KR:ko"
                res = requests.get(rss_url)
                items = BeautifulSoup(res.text, 'xml').find_all('item')
                
                filtered = [re.split(r' - | \| ', i.title.get_text())[0] for i in items if datetime.datetime.strptime(i.pubDate.get_text(), '%a, %d %b %Y %H:%M:%S %Z') >= limit_date]
                
                if not filtered: st.error("해당 기간 뉴스 없음")
                else:
                    news_txt = " ".join(filtered)
                    # 매체명 제거
                    for m in ["동아일보", "서울경제", "헬스조선", "하이닥", "연합뉴스", "매일경제", "한국경제", "조선일보", "네이버", "뉴스"]: news_txt = news_txt.replace(m, "")
                    
                    wc = WordCloud(font_path=FONT_PATH, width=900, height=500, background_color='white', colormap='cool', regexp=r"[\w\xA1-\xFE]+").generate(news_txt)
                    fig, ax = plt.subplots(figsize=(10, 6)); ax.imshow(wc); ax.axis('off'); st.pyplot(fig)
                    
                    # 다운로드 버튼
                    buf = BytesIO(); fig.savefig(buf, format="png", dpi=300)
                    st.download_button("📥 뉴스 이미지 저장", data=buf.getvalue(), file_name=f"News_{kw_n}.png")

    with tab_search:
        st.subheader("포털 검색 결과 기반 키워드 분석")
        c1, c2 = st.columns([3, 1])
        with c1: kw_s = st.text_input("검색 분석 키워드", placeholder="예: 단백질 쉐이크 추천, 캠핑장 예약")
        with c2: engine = st.multiselect("검색 매체", ["네이버", "구글", "빙"], default=["네이버", "구글"])
        
        if st.button("🔍 다채널 검색 분석 시작"):
            with st.spinner("다양한 검색 매체에서 데이터를 긁어오는 중입니다..."):
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
                search_data = ""
                
                # 네이버 검색 결과 본문 수집
                if "네이버" in engine:
                    res_n = requests.get(f"https://search.naver.com/search.naver?query={kw_s}", headers=headers)
                    soup_n = BeautifulSoup(res_n.text, 'html.parser')
                    search_data += " ".join([v.get_text() for v in soup_n.select('.lnk_tit, .dsc_txt, .api_txt_lines')])

                # 구글 검색 결과 본문 수집
                if "구글" in engine:
                    res_g = requests.get(f"https://www.google.com/search?q={kw_s}", headers=headers)
                    soup_g = BeautifulSoup(res_g.text, 'html.parser')
                    search_data += " ".join([g.get_text() for g in soup_g.find_all(['h3', 'div']) if len(g.get_text()) > 10])

                if len(search_data.strip()) < 50:
                    st.error("검색 데이터를 가져오지 못했습니다. 키워드를 확인해 주세요.")
                else:
                    # 검색 결과용 워드클라우드 (Warm 테마로 차별화)
                    wc_s = WordCloud(font_path=FONT_PATH, width=900, height=500, background_color='white', colormap='YlOrRd', regexp=r"[\w\xA1-\xFE]+").generate(search_data)
                    fig_s, ax_s = plt.subplots(figsize=(10, 6)); ax_s.imshow(wc_s); ax_s.axis('off'); st.pyplot(fig_s)
                    
                    buf_s = BytesIO(); fig_s.savefig(buf_s, format="png", dpi=300)
                    st.download_button("📥 검색 이미지 저장", data=buf_s.getvalue(), file_name=f"Search_{kw_s}.png")

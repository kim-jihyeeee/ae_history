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
st.set_page_config(page_title="AE Total Solution v9.1", layout="wide")

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
st.sidebar.title("🚀 AE Total Tool v9.1")
st.sidebar.markdown('<p class="menu-header">📋 내부 히스토리 관리</p>', unsafe_allow_html=True)
m_int = st.sidebar.radio("항목", ["광고주 DB 관리", "관리 이력 입력", "디지털 리포트(내부)"], label_visibility="collapsed")
st.sidebar.markdown('<div class="spacer"></div>', unsafe_allow_html=True)
st.sidebar.markdown('<p class="menu-header">📊 외부 시장 분석</p>', unsafe_allow_html=True)
m_ext = st.sidebar.checkbox("📊 Trend Radar(듀얼 모드)")

menu = "📊 Trend Radar(외부)" if m_ext else m_int

# --- [내부 로직 생략 (기존과 동일)] ---
if menu == "광고주 DB 관리":
    st.header("📂 데이터 로드 및 관리")
    c1, c2 = st.columns(2)
    with c1: 
        up_c = st.file_uploader("광고주 리스트", type=['xlsx', 'csv'], key="c_up")
        if up_c:
            df = pd.read_csv(up_c) if up_c.name.endswith('.csv') else pd.read_excel(up_c)
            df.rename(columns={df.columns[0]: '광고주명'}, inplace=True)
            st.session_state.client_db = df
            st.success("✅ 로드 완료")
    with c2:
        up_h = st.file_uploader("히스토리 백업", type=['xlsx'], key="h_up")
        if up_h:
            st.session_state.history_db = pd.read_excel(up_h)
            st.success("✅ 복구 완료")

elif menu == "관리 이력 입력":
    st.header("✍️ 소통 이력 기록 및 수정")
    if st.session_state.client_db.empty: st.warning("광고주 리스트를 먼저 등록하세요.")
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
            txt = st.text_area("상세 소통 내용")
            if st.form_submit_button("히스토리 저장"):
                new_row = pd.DataFrame([[dt, sel_c, txt, tags]], columns=['날짜', '광고주명', '소통내용', '핵심키워드'])
                st.session_state.history_db = pd.concat([st.session_state.history_db, new_row], ignore_index=True)
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

# --- 🌟 v9.1 Trend Radar 다채널 엔진 (네이버/구글/네이트/다음/티스토리 통합) ---
elif menu == "📊 Trend Radar(외부)":
    st.header("🌐 Trend Radar 듀얼 모드 v9.1")
    tab_news, tab_search = st.tabs(["📰 뉴스 에디션", "🔍 검색 에디션 (포털/커뮤니티 통합)"])

    with tab_news:
        st.subheader("매체사 뉴스 트렌드")
        cn1, cn2 = st.columns([3, 1])
        with cn1: kw_n = st.text_input("뉴스 키워드", placeholder="예: 무라벨 생수")
        with cn2: prd_n = st.selectbox("뉴스 기간", ["최근 7일", "최근 30일", "최근 60일"], key="n_prd")
        
        if st.button("🔍 뉴스 분석 시작"):
            with st.spinner("데이터를 수집 중입니다..."):
                days = int(re.findall(r'\d+', prd_n)[0])
                limit = datetime.datetime.now() - datetime.timedelta(days=days)
                rss_url = f"https://news.google.com/rss/search?q={kw_n}&hl=ko&gl=KR&ceid=KR:ko"
                res = requests.get(rss_url)
                items = BeautifulSoup(res.text, 'xml').find_all('item')
                filtered = [re.split(r' - | \| ', i.title.get_text())[0] for i in items if datetime.datetime.strptime(i.pubDate.get_text(), '%a, %d %b %Y %H:%M:%S %Z') >= limit]
                if not filtered: st.error("기사 없음")
                else:
                    txt = " ".join(filtered)
                    wc_n = WordCloud(font_path=FONT_PATH, width=900, height=500, background_color='white', colormap='cool', regexp=r"[\w\xA1-\xFE]+").generate(txt)
                    fig, ax = plt.subplots(figsize=(10, 6)); ax.imshow(wc_n); ax.axis('off'); st.pyplot(fig)

    with tab_search:
        st.subheader("포털/블로그/카페/광고 영역 통합 분석")
        cs1, cs2 = st.columns([3, 1])
        with cs1: kw_s = st.text_input("검색 분석 키워드", placeholder="예: 혈당 낮추는 법, 슬개골 영양제")
        with cs2: prd_s = st.selectbox("검색 기간", ["최근 7일", "최근 30일", "최근 60일"], key="s_prd")
        
        if st.button("🔍 소비자 통합 데이터 분석 시작"):
            with st.spinner("네이버/구글/다음/네이트 데이터를 동시 수집 중입니다..."):
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
                all_data = ""
                
                # 1. 네이버 통합 검색 (블로그/카페/밴드/광고 요약)
                try:
                    res_n = requests.get(f"https://search.naver.com/search.naver?query={kw_s}", headers=headers, timeout=10)
                    soup_n = BeautifulSoup(res_n.text, 'html.parser')
                    all_data += " ".join([v.get_text() for v in soup_n.select('.lnk_tit, .dsc_txt, .total_tit, .api_txt_lines, .ad_section')])
                except: pass

                # 2. 다음/네이트/티스토리 통합 수집
                try:
                    res_d = requests.get(f"https://search.daum.net/search?q={kw_s}", headers=headers, timeout=10)
                    soup_d = BeautifulSoup(res_d.text, 'html.parser')
                    all_data += " ".join([d.get_text() for d in soup_d.select('.tit_main, .desc_txt, .f_link_b, .txt_dot')])
                except: pass

                # 3. 구글 검색 요약 (보안 우회형 수집)
                try:
                    google_rss = f"https://www.google.com/search?q={kw_s}&tbs=qdr:m" # 최근 한달 필터
                    res_g = requests.get(google_rss, headers=headers, timeout=10)
                    soup_g = BeautifulSoup(res_g.text, 'html.parser')
                    all_data += " ".join([g.get_text() for g in soup_g.find_all(['h3', 'div']) if len(g.get_text()) > 15])
                except: pass

                # 데이터 정화 (시스템 문구 및 언어사 매체명 필터 강화)
                trash = ["내용", "보기", "이동", "클릭", "Search", "Google", "Please", "accessing", "redirected", "seconds", "동아일보", "서울경제", "머니투데이", "매일경제"]
                for t in trash: all_data = re.sub(t, "", all_data, flags=re.I)

                if len(all_data.strip()) < 50:
                    st.error("데이터 수집 실패. 키워드를 조금 더 구체적으로(예: '혈당 관리') 입력해 보세요.")
                else:
                    wc_s = WordCloud(font_path=FONT_PATH, width=900, height=500, background_color='white', colormap='YlOrRd', regexp=r"[\w\xA1-\xFE]+").generate(all_data)
                    fig_s, ax_s = plt.subplots(figsize=(10, 6)); ax_s.imshow(wc_s, interpolation='bilinear'); ax_s.axis('off'); st.pyplot(fig_s)
                    
                    buf_s = BytesIO(); fig_s.savefig(buf_s, format="png", dpi=300)
                    st.download_button("📥 통합 검색 분석 결과 저장", data=buf_s.getvalue(), file_name=f"Total_Search_{kw_s}.png")

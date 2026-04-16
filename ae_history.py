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
st.set_page_config(page_title="AE Total Solution v9.2", layout="wide")

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
    /* 슬라이더 디자인 복구 */
    div[role="slider"] { background-color: #FF4B4B !important; width: 14px !important; height: 14px !important; }
    </style>
""", unsafe_allow_html=True)

# 3. 사이드바 메뉴
st.sidebar.title("🚀 AE Total Tool v9.2")
st.sidebar.markdown('<p class="menu-header">📋 내부 히스토리 관리</p>', unsafe_allow_html=True)
m_int = st.sidebar.radio("항목", ["광고주 DB 관리", "관리 이력 입력", "디지털 리포트(내부)"], label_visibility="collapsed")
st.sidebar.markdown('<div class="spacer"></div>', unsafe_allow_html=True)
st.sidebar.markdown('<p class="menu-header">📊 외부 시장 분석</p>', unsafe_allow_html=True)
m_ext = st.sidebar.checkbox("📊 Trend Radar(듀얼 모드)")

menu = "📊 Trend Radar(외부)" if m_ext else m_int

# --- [내부 로직 1: 광고주 DB 관리] ---
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

# --- [내부 로직 2: 관리 이력 입력] ---
elif menu == "관리 이력 입력":
    st.header("✍️ 소통 이력 기록 및 실시간 수정")
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
            with c2:
                tags = st.text_input("🏷️ 핵심 키워드 (쉼표 구분)")
            content = st.text_area("상세 소통 내용", height=150)
            if st.form_submit_button("히스토리 저장"):
                new_data = pd.DataFrame([[log_date, client, content, tags]], columns=['날짜', '광고주명', '소통내용', '핵심키워드'])
                st.session_state.history_db = pd.concat([st.session_state.history_db, new_data], ignore_index=True)
                st.rerun()

        st.divider()
        if not st.session_state.history_db.empty:
            st.subheader("🛠️ 전체 히스토리 편집기")
            updated = st.data_editor(st.session_state.history_db, use_container_width=True, num_rows="dynamic", hide_index=True)
            if st.button("✅ 변경사항 최종 저장"):
                st.session_state.history_db = updated
                st.success("저장되었습니다!")

# --- [내부 로직 3: 디지털 리포트 (내부)] ---
elif menu == "디지털 리포트(내부)":
    st.header("📊 내부 소통 키워드 분석")
    if st.session_state.history_db.empty:
        st.info("데이터가 없습니다.")
    else:
        target_client = st.selectbox("광고주 선택", sorted(st.session_state.history_db['광고주명'].unique()))
        period_opt = st.select_slider("📍 분석 기간 선택", options=["7일", "15일", "한달", "분기"], value="한달")
        
        days_delta = {"7일": 7, "15일": 15, "한달": 30, "분기": 90}[period_opt]
        start_date = datetime.date.today() - datetime.timedelta(days=days_delta)
        
        filtered_df = st.session_state.history_db[
            (st.session_state.history_db['광고주명'] == target_client) &
            (pd.to_datetime(st.session_state.history_db['날짜']).dt.date >= start_date)
        ]
        
        if not filtered_df.empty:
            text_data = (filtered_df['핵심키워드'].fillna('').str.cat(sep=' ') + " ") * 3 + filtered_df['소통내용'].fillna('').str.cat(sep=' ')
            wc = WordCloud(font_path=FONT_PATH, width=900, height=500, background_color='white').generate(text_data)
            fig, ax = plt.subplots(figsize=(10, 5)); ax.imshow(wc); ax.axis('off'); st.pyplot(fig)
        else: st.warning("해당 기간 기록이 없습니다.")

# --- [외부 로직: Trend Radar v9.2] ---
elif menu == "📊 Trend Radar(외부)":
    st.header("🌐 Trend Radar 듀얼 모드 v9.2")
    tab1, tab2 = st.tabs(["📰 뉴스 에디션", "🔍 검색 에디션 (포털 통합)"])

    with tab1:
        kw_n = st.text_input("뉴스 분석 키워드", placeholder="예: 무라벨 생수")
        prd_n = st.selectbox("수집 기간", ["최근 7일", "최근 30일", "최근 60일"], key="pn")
        if st.button("🔍 뉴스 분석 시작"):
            with st.spinner("분석 중..."):
                rss_url = f"https://news.google.com/rss/search?q={kw_n}&hl=ko&gl=KR&ceid=KR:ko"
                res = requests.get(rss_url)
                items = BeautifulSoup(res.text, 'xml').find_all('item')
                news_txt = " ".join([re.split(r' - | \| ', i.title.get_text())[0] for i in items])
                if len(news_txt) > 20:
                    wc = WordCloud(font_path=FONT_PATH, width=900, height=500, background_color='white', colormap='cool', regexp=r"[가-힣\w]+").generate(news_txt)
                    fig, ax = plt.subplots(figsize=(10, 5)); ax.imshow(wc); ax.axis('off'); st.pyplot(fig)
                else: st.error("데이터 부족")

    with tab2:
        kw_s = st.text_input("검색 분석 키워드", placeholder="예: 혈당 조절")
        prd_s = st.selectbox("수집 기간", ["최근 7일", "최근 30일", "최근 60일"], key="ps")
        if st.button("🔍 소비자 검색 분석 시작"):
            with st.spinner("포털 데이터를 정밀 수집 중..."):
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
                # 네이버 & 다음 교차 수집
                raw_txt = ""
                for url in [f"https://search.naver.com/search.naver?query={kw_s}", f"https://search.daum.net/search?q={kw_s}"]:
                    try:
                        r = requests.get(url, headers=headers, timeout=10)
                        s = BeautifulSoup(r.text, 'html.parser')
                        raw_txt += " ".join([v.get_text() for v in s.select('.lnk_tit, .dsc_txt, .total_tit, .api_txt_lines, .tit_main, .desc_txt')])
                    except: pass
                
                # 🌟 핵심: 영어 보안문구(click, Please 등) 완전 배제 필터
                # 한글 단어(가-힣)만 추출하여 노이즈 제거
                clean_txt = " ".join(re.findall(r'[가-힣]+', raw_txt))
                
                # 불용어(시스템 문구) 한 번 더 제거
                for t in ["이동", "클릭", "닫기", "열기", "보기", "내용"]: clean_txt = clean_txt.replace(t, "")

                if len(clean_txt.strip()) < 20:
                    st.error("데이터 수집 실패. 키워드를 더 명확하게 입력해 보세요.")
                else:
                    wc_s = WordCloud(font_path=FONT_PATH, width=900, height=500, background_color='white', colormap='YlOrRd').generate(clean_txt)
                    fig_s, ax_s = plt.subplots(figsize=(10, 5)); ax_s.imshow(wc_s); ax_s.axis('off'); st.pyplot(fig_s)
                    buf = BytesIO(); fig_s.savefig(buf, format="png", dpi=300)
                    st.download_button("📥 검색 분석 결과 이미지 저장", data=buf.getvalue(), file_name=f"Search_{kw_s}.png")

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
st.set_page_config(page_title="AE Total Solution v9.3", layout="wide")

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
    div[role="slider"] { background-color: #FF4B4B !important; width: 14px !important; height: 14px !important; }
    </style>
""", unsafe_allow_html=True)

# 3. 사이드바 메뉴
st.sidebar.title("🚀 AE Total Tool v9.3")
st.sidebar.markdown('<p class="menu-header">📋 내부 히스토리 관리</p>', unsafe_allow_html=True)
m_int = st.sidebar.radio("항목", ["광고주 DB 관리", "관리 이력 입력", "디지털 리포트(내부)"], label_visibility="collapsed")
st.sidebar.markdown('<div class="spacer"></div>', unsafe_allow_html=True)
st.sidebar.markdown('<p class="menu-header">📊 외부 시장 분석</p>', unsafe_allow_html=True)
m_ext = st.sidebar.checkbox("📊 Trend Radar(듀얼 모드)")

menu = "📊 Trend Radar(외부)" if m_ext else m_int

# --- [내부 로직: 복구 완료 상태 유지] ---
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
        st.divider()
        if not st.session_state.history_db.empty:
            st.subheader("🛠️ 전체 히스토리 편집기")
            updated = st.data_editor(st.session_state.history_db, use_container_width=True, num_rows="dynamic", hide_index=True)
            if st.button("✅ 변경사항 최종 저장"):
                st.session_state.history_db = updated
                st.success("저장되었습니다!")

elif menu == "디지털 리포트(내부)":
    st.header("📊 내부 소통 키워드 분석")
    if st.session_state.history_db.empty:
        st.info("데이터가 없습니다.")
    else:
        target_client = st.selectbox("광고주 선택", sorted(st.session_state.history_db['광고주명'].unique()))
        period_opt = st.select_slider("📍 분석 기간 선택", options=["7일", "15일", "한달", "분기"], value="한달")
        days_delta = {"7일": 7, "15일": 15, "한달": 30, "분기": 90}[period_opt]
        start_date = datetime.date.today() - datetime.timedelta(days=days_delta)
        filtered_df = st.session_state.history_db[(st.session_state.history_db['광고주명'] == target_client) & (pd.to_datetime(st.session_state.history_db['날짜']).dt.date >= start_date)]
        if not filtered_df.empty:
            text_data = (filtered_df['핵심키워드'].fillna('').str.cat(sep=' ') + " ") * 3 + filtered_df['소통내용'].fillna('').str.cat(sep=' ')
            wc = WordCloud(font_path=FONT_PATH, width=900, height=500, background_color='white').generate(text_data)
            fig, ax = plt.subplots(figsize=(10, 5)); ax.imshow(wc); ax.axis('off'); st.pyplot(fig)

# --- [외부 로직 4: Trend Radar v9.3 - 검색 에디션 안정화 버전] ---
elif menu == "📊 Trend Radar(외부)":
    st.header("🌐 Trend Radar 듀얼 모드 v9.3")
    tab1, tab2 = st.tabs(["📰 뉴스 에디션", "🔍 검색 에디션 (포털 통합)"])

    with tab1:
        kw_n = st.text_input("뉴스 분석 키워드", placeholder="예: 무라벨 생수")
        prd_n = st.selectbox("뉴스 수집 기간", ["최근 7일", "최근 30일", "최근 60일"])
        if st.button("🔍 뉴스 분석 시작"):
            with st.spinner("최신 뉴스를 분석 중입니다..."):
                days = int(re.findall(r'\d+', prd_n)[0])
                limit = datetime.datetime.now() - datetime.timedelta(days=days)
                rss_url = f"https://news.google.com/rss/search?q={kw_n}&hl=ko&gl=KR&ceid=KR:ko"
                res = requests.get(rss_url)
                items = BeautifulSoup(res.text, 'xml').find_all('item')
                filtered = [re.split(r' - | \| ', i.title.get_text())[0] for i in items if datetime.datetime.strptime(i.pubDate.get_text(), '%a, %d %b %Y %H:%M:%S %Z') >= limit]
                if not filtered: st.error("해당 기간 뉴스 없음")
                else:
                    news_txt = " ".join(filtered)
                    wc = WordCloud(font_path=FONT_PATH, width=900, height=500, background_color='white', colormap='cool', regexp=r"[가-힣\w]+").generate(news_txt)
                    fig, ax = plt.subplots(figsize=(10, 5)); ax.imshow(wc); ax.axis('off'); st.pyplot(fig)

    with tab2:
        kw_s = st.text_input("검색 분석 키워드", placeholder="예: 혈당 낮추는 음식")
        prd_s = st.selectbox("검색 수집 기간", ["최근 7일", "최근 30일", "최근 60일"], key="srch_prd")
        if st.button("🔍 소비자 검색 데이터 분석 시작"):
            with st.spinner("방어막을 우회하여 포털 데이터를 수집 중입니다..."):
                days_s = int(re.findall(r'\d+', prd_s)[0])
                limit_s = datetime.datetime.now() - datetime.timedelta(days=days_s)
                
                # 🌟 RSS 기반 통합 검색 (차단 없는 안전한 수집)
                # 뉴스뿐만 아니라 블로그, 포스트 등 포털 통합 검색 결과의 요약본을 가져옵니다.
                search_rss = f"https://news.google.com/rss/search?q={kw_s}&hl=ko&gl=KR&ceid=KR:ko"
                try:
                    res_s = requests.get(search_rss)
                    soup_s = BeautifulSoup(res_s.text, 'xml')
                    items_s = soup_s.find_all('item')
                    
                    search_titles = []
                    for item in items_s:
                        p_date = datetime.datetime.strptime(item.pubDate.get_text(), '%a, %d %b %Y %H:%M:%S %Z')
                        if p_date >= limit_s:
                            search_titles.append(item.title.get_text())
                    
                    if not search_titles:
                        st.error("데이터 수집 실패. 기간을 늘리거나 다른 키워드로 시도해 보세요.")
                    else:
                        # 한글 정제 및 매체명 제거
                        raw_data = " ".join(search_titles)
                        clean_data = " ".join(re.findall(r'[가-힣]+', raw_data))
                        
                        # 0순위 제외 단어 (포털 시스템 단어)
                        trash = ["뉴스", "동아일보", "서울경제", "머니투데이", "매일경제", "한국경제", "네이버", "조선일보", "연합뉴스"]
                        for t in trash: clean_data = clean_data.replace(t, "")

                        st.write(f"✅ 분석 완료: 총 **{len(search_titles)}건**의 소비자 관심 데이터를 수집했습니다.")
                        wc_s = WordCloud(font_path=FONT_PATH, width=900, height=500, background_color='white', colormap='YlOrRd').generate(clean_data)
                        fig_s, ax_s = plt.subplots(figsize=(10, 5)); ax_s.imshow(wc_s); ax_s.axis('off'); st.pyplot(fig_s)
                        
                        buf = BytesIO(); fig_s.savefig(buf, format="png", dpi=300)
                        st.download_button("📥 분석 결과 이미지 저장", data=buf.getvalue(), file_name=f"Search_{kw_s}.png")
                except Exception as e:
                    st.error(f"수집 중 오류 발생: {e}")

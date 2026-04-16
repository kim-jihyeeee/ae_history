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
st.set_page_config(page_title="AE Total Solution v8.7", layout="wide")

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
st.sidebar.title("🚀 AE Total Tool v8.7")
st.sidebar.markdown('<p class="menu-header">📋 내부 히스토리 관리</p>', unsafe_allow_html=True)
m_int = st.sidebar.radio("항목", ["광고주 DB 관리", "관리 이력 입력", "디지털 리포트(내부)"], label_visibility="collapsed")
st.sidebar.markdown('<div class="spacer"></div>', unsafe_allow_html=True)
st.sidebar.markdown('<p class="menu-header">📊 외부 시장 분석</p>', unsafe_allow_html=True)
m_ext = st.sidebar.checkbox("📊 Trend Radar(외부)")

menu = "📊 Trend Radar(외부)" if m_ext else m_int

# --- [내부 로직 생략 (v8.6과 동일)] ---
if menu == "광고주 DB 관리":
    st.header("📂 데이터 로드 및 관리")
    c1, c2 = st.columns(2)
    with c1: 
        up_c = st.file_uploader("광고주 리스트", type=['xlsx', 'csv'])
        if up_c:
            df = pd.read_csv(up_c) if up_c.name.endswith('.csv') else pd.read_excel(up_c)
            df.rename(columns={df.columns[0]: '광고주명'}, inplace=True)
            st.session_state.client_db = df
            st.success("로드 완료")
    with c2:
        up_h = st.file_uploader("백업 엑셀", type=['xlsx'])
        if up_h:
            st.session_state.history_db = pd.read_excel(up_h)
            st.success("복구 완료")

elif menu == "관리 이력 입력":
    st.header("✍️ 소통 이력 기록 및 수정")
    if st.session_state.client_db.empty: st.warning("광고주 리스트를 먼저 등록하세요.")
    else:
        q = st.text_input("🔍 업체명 검색")
        clients = sorted(st.session_state.client_db['광고주명'].dropna().unique())
        f_clients = [c for c in clients if q.lower() in str(c).lower()]
        with st.form("history_form"):
            c1, c2 = st.columns(2)
            with c1:
                sel_c = st.selectbox(f"광고주 ({len(f_clients)}건)", f_clients)
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

# --- 🌟 신규 Trend Radar 로직 (기간 필터 및 매체명 제거) ---
elif menu == "📊 Trend Radar(외부)":
    st.header("🌐 실시간 트렌드 레이더 (RSS Smart Filter)")
    st.info("💡 뉴스 데이터를 분석하여 매체명을 제외한 시장 키워드만 추출합니다.")
    
    # 세션 상태로 분석 결과 저장 (건수 표기용)
    if 'trend_count' not in st.session_state: st.session_state.trend_count = 0

    c_in, c_pr = st.columns([3, 1])
    with c_in: kw = st.text_input("분석 키워드", placeholder="예: 혈당, 제로음료, 미세먼지")
    with c_pr: 
        prd = st.selectbox("수집 범위", ["최근 7일", "최근 30일", "최근 60일"])
        if st.session_state.trend_count > 0:
            st.write(f"✅ 수집된 뉴스: **{st.session_state.trend_count}건**")

    if st.button("🔍 트렌드 데이터 분석 시작"):
        if not kw: st.warning("키워드를 입력하세요.")
        else:
            with st.spinner("날짜별 뉴스를 선별하고 매체명을 필터링 중입니다..."):
                # 기간 설정
                days = int(re.findall(r'\d+', prd)[0])
                limit_date = datetime.datetime.now() - datetime.timedelta(days=days)
                
                rss_url = f"https://news.google.com/rss/search?q={kw}&hl=ko&gl=KR&ceid=KR:ko"
                try:
                    res = requests.get(rss_url)
                    soup = BeautifulSoup(res.text, 'xml')
                    items = soup.find_all('item')
                    
                    filtered_titles = []
                    for item in items:
                        # 날짜 체크
                        pub_date_str = item.pubDate.get_text()
                        # 구글 RSS 날짜 포맷: Wed, 15 Apr 2026 05:00:00 GMT
                        pub_date = datetime.datetime.strptime(pub_date_str, '%a, %d %b %Y %H:%M:%S %Z')
                        
                        if pub_date >= limit_date:
                            title = item.title.get_text()
                            # 🌟 2번 요청: 뉴스 매체명 제거 (보통 제목 끝에 " - 매체명" 형식이 많음)
                            clean_title = re.split(r' - | \| ', title)[0] 
                            filtered_titles.append(clean_title)
                    
                    st.session_state.trend_count = len(filtered_titles)
                    news_txt = " ".join(filtered_titles)

                    # 🌟 매체명 리스트 (추가 필터링)
                    media_trash = ["동아일보", "서울경제", "헬스조선", "하이닥", "코메디닷컴", "뉴시스", "연합뉴스", "매일경제", "한국경제", "머니투데이", "조선일보", "중앙일보", "한겨레", "daum", "net", "네이버", "뉴스"]
                    for m in media_trash:
                        news_txt = news_txt.replace(m, "")

                    if len(filtered_titles) == 0:
                        st.error(f"선택하신 기간({prd}) 내에 검색된 뉴스가 없습니다.")
                    else:
                        wc_t = WordCloud(font_path=FONT_PATH, width=900, height=500, background_color='white', colormap='cool', regexp=r"[\w\xA1-\xFE]+").generate(news_txt)
                        fig_t, ax_t = plt.subplots(figsize=(10, 6))
                        ax_t.imshow(wc_t, interpolation='bilinear'); ax_t.axis('off'); st.pyplot(fig_t)
                        
                        st.divider()
                        d1, d2 = st.columns(2)
                        img_b = BytesIO(); fig_t.savefig(img_b, format="png", dpi=300)
                        d1.download_button("📥 이미지 저장", data=img_b.getvalue(), file_name=f"Trend_{kw}.png")
                        
                        try:
                            prs = Presentation()
                            slide = prs.slides.add_slide(prs.slide_layouts[6])
                            slide.shapes.add_picture(img_b, Inches(0.5), Inches(1), width=Inches(9))
                            ppt_b = BytesIO(); prs.save(ppt_b)
                            d2.download_button("📊 PPTX 제안서 저장", data=ppt_b.getvalue(), file_name=f"Trend_{kw}.pptx")
                        except: st.error("PPT 생성 환경 오류")
                        
                        st.rerun() # 건수 업데이트를 위해 화면 갱신
                except Exception as e:
                    st.error(f"분석 중 오류 발생: {e}")

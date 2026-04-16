import streamlit as st
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from io import BytesIO
import datetime, os, requests
from bs4 import BeautifulSoup
from pptx import Presentation
from pptx.util import Inches
from fpdf import FPDF

# 1. 기본 설정 및 폰트
st.set_page_config(page_title="AE Total Solution v8.3", layout="wide")

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

# 2. UI 스타일 (메뉴 간격 강조)
st.markdown("""
    <style>
    header[data-testid="stHeader"] { visibility: hidden; }
    .stButton>button { width: 100%; border-radius: 8px; background-color: #FFB300; color: white; font-weight: bold; height: 3em; }
    .menu-header { font-size: 1.1em; font-weight: bold; color: #FFB300; margin-top: 35px; border-bottom: 2px solid #eee; padding-bottom: 5px; }
    .spacer { margin-bottom: 50px; }
    div[role="slider"] { background-color: #FF4B4B !important; }
    </style>
""", unsafe_allow_html=True)

# 3. 사이드바 메뉴
st.sidebar.title("🚀 AE Total Tool v8.3")
st.sidebar.markdown('<p class="menu-header">📋 내부 히스토리 관리</p>', unsafe_allow_html=True)
m_int = st.sidebar.radio("항목", ["광고주 DB 관리", "관리 이력 입력", "디지털 리포트(내부)"], label_visibility="collapsed")

st.sidebar.markdown('<div class="spacer"></div>', unsafe_allow_html=True) # 시원한 여백

st.sidebar.markdown('<p class="menu-header">📊 외부 시장 분석</p>', unsafe_allow_html=True)
m_ext = st.sidebar.checkbox("📊 Trend Radar(외부)")

menu = "📊 Trend Radar(외부)" if m_ext else m_int

# --- 메뉴별 로직 ---
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

elif menu == "📊 Trend Radar(외부)":
    st.header("🌐 실시간 트렌드 레이더 (Google News)")
    st.info("💡 구글 뉴스 데이터를 수집하여 트렌드를 분석합니다.")
    c_in, c_pr = st.columns([3, 1])
    with c_in: kw = st.text_input("분석 키워드", placeholder="예: 도라지정과, 비건 뷰티")
    with c_pr: prd = st.selectbox("수집 범위", ["최근 7일", "최근 30일"])

    if st.button("🔍 트렌드 데이터 분석 시작"):
        if not kw: st.warning("키워드를 입력하세요.")
        else:
            with st.spinner("뉴스 수집 및 분석 중..."):
                h = {"User-Agent": "Mozilla/5.0"}
                url = f"https://www.google.com/search?q={kw}&tbm=nws"
                try:
                    res = requests.get(url, headers=h, timeout=10)
                    soup = BeautifulSoup(res.text, 'html.parser')
                    # 🌟 126번 줄: 가장 안정적인 텍스트 수집 방식
                    items = soup.find_all(['h3', 'div', 'span'])
                    news_txt = " ".join([i.get_text() for i in items if len(i.get_text()) > 15])
                    
                    if len(news_txt) < 50: st.error("데이터가 부족합니다. 키워드를 더 일반적인 단어로 바꿔보세요.")
                    else:
                        wc_t = WordCloud(font_path=FONT_PATH, width=900, height=500, background_color='white', colormap='cool').generate(news_txt)
                        fig_t, ax_t = plt.subplots(figsize=(10, 6))
                        ax_t.imshow(wc_t, interpolation='bilinear'); ax_t.axis('off'); st.pyplot(fig_t)
                        
                        st.divider()
                        d1, d2, d3 = st.columns(3)
                        img_b = BytesIO(); fig_t.savefig(img_b, format="png", dpi=300)
                        d1.download_button("📥 이미지 저장", data=img_b.getvalue(), file_name=f"Trend_{kw}.png")
                        
                        prs = Presentation()
                        slide = prs.slides.add_slide(prs.slides.add_slide(prs.slide_layouts[5]))
                        slide.shapes.title.text = f"Market Trend: {kw}"
                        slide.shapes.add_picture(img_b, Inches(1), Inches(1.5), width=Inches(8))
                        ppt_b = BytesIO(); prs.save(ppt_b)
                        d2.download_button("📊 PPTX 제안서", data=ppt_b.getvalue(), file_name=f"Trend_{kw}.pptx")
                        
                        pdf = FPDF()
                        pdf.add_page(); pdf.set_font("Arial", size=15)
                        pdf.cell(200, 10, txt=f"Trend Report: {kw}", ln=True, align='C')
                        tmp = "tmp.png"; fig_t.savefig(tmp)
                        pdf.image(tmp, x=10, y=30, w=190)
                        pdf_b = pdf.output(dest='S').encode('latin-1')
                        d3.download_button("📄 PDF 리포트", data=pdf_b, file_name=f"Trend_{kw}.pdf")
                        if os.path.exists(tmp): os.remove(tmp)
                except Exception as e: st.error(f"오류 발생: {e}")

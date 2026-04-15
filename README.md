import streamlit as st
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from io import BytesIO
import datetime
import os

# 1. 기본 설정
st.set_page_config(page_title="AE History Visualizer v5.2", layout="wide")

# 🌟 폰트 설정 (공백이 있으면 인식이 안 될 수 있으니 주의하세요!)
# 업로드하신 파일명이 "Hakgyoansim Badasseugi TTF L.ttf"라면 아래도 똑같이 맞춰야 합니다.
FONT_NAME = "Hakgyoansim Badasseugi TTF L.ttf"

# 세션 상태 초기화
if 'client_db' not in st.session_state: st.session_state.client_db = pd.DataFrame(columns=['광고주명', '담당자', '업종'])
if 'history_db' not in st.session_state: st.session_state.history_db = pd.DataFrame(columns=['날짜', '광고주명', '소통내용', '핵심키워드'])

# 2. UI 디자인
st.markdown("""
    <style>
    header[data-testid="stHeader"] { visibility: hidden; }
    .stButton>button { width: 100%; border-radius: 8px; background-color: #FFB300; color: white; font-weight: bold; border: none; }
    div[data-testid="stExpander"] { border: 1px solid #FFB300; border-radius: 8px; }
    </style>
""", unsafe_allow_html=True)

st.title("📝 AE History Visualizer v5.2")
st.caption("광고주 히스토리 시각화 및 한글 워드클라우드 리포트")

# 사이드바 메뉴
menu = st.sidebar.radio("📋 메뉴 이동", ["광고주 DB 관리", "관리 이력 입력", "디지털 리포트 생성"])

# --- 1. 광고주 DB 관리 ---
if menu == "광고주 DB 관리":
    st.header("📂 광고주 리스트 등록")
    uploaded_file = st.file_uploader("Excel/CSV 파일을 업로드하세요", type=['xlsx', 'csv'])
    
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            st.session_state.client_db = df
            st.success("✅ 광고주 리스트 로드 완료!")
        except Exception as e:
            st.error(f"오류 발생: {e}")
    st.dataframe(st.session_state.client_db, use_container_width=True, hide_index=True)

# --- 2. 관리 이력 입력 ---
elif menu == "관리 이력 입력":
    st.header("✍️ 소통 이력 기록")
    if st.session_state.client_db.empty:
        st.warning("먼저 광고주 리스트를 등록해주세요.")
    else:
        with st.form("log_form"):
            c1, c2 = st.columns(2)
            with c1:
                client = st.selectbox("광고주 선택", st.session_state.client_db['광고주명'].unique())
                date = st.date_input("날짜", datetime.date.today())
            with c2:
                tags = st.text_input("핵심 키워드 (쉼표 구분)", placeholder="효율개선, 소재교체")
            content = st.text_area("상세 관리 내용")
            
            if st.form_submit_button("히스토리 저장"):
                new_data = pd.DataFrame([[date, client, content, tags]], columns=['날짜', '광고주명', '소통내용', '핵심키워드'])
                st.session_state.history_db = pd.concat([st.session_state.history_db, new_data], ignore_index=True)
                st.success("✅ 저장 완료!")
        st.dataframe(st.session_state.history_db.sort_values(by='날짜', ascending=False), use_container_width=True)

# --- 3. 디지털 리포트 생성 ---
elif menu == "디지털 리포트 생성":
    st.header("📊 한글 워드클라우드 리포트")
    if st.session_state.history_db.empty:
        st.info("데이터가 없습니다.")
    else:
        target = st.selectbox("대상 광고주", st.session_state.history_db['광고주명'].unique())
        period = st.select_slider("기간", options=["7일", "15일", "한달", "분기"])
        
        days = {"7일": 7, "15일": 15, "한달": 30, "분기": 90}[period]
        cutoff = datetime.date.today() - datetime.timedelta(days=days)
        
        filtered = st.session_state.history_db[
            (st.session_state.history_db['광고주명'] == target) &
            (pd.to_datetime(st.session_state.history_db['날짜']).dt.date >= cutoff)
        ]
        
        if not filtered.empty:
            # 🌟 한글 폰트 적용 및 워드클라우드 생성 🌟
            # 핵심키워드에 가중치를 주기 위해 5번 반복해서 합칩니다.
            text = (filtered['핵심키워드'].str.cat(sep=' ') + " ") * 5 + filtered['소통내용'].str.cat(sep=' ')
            
            if os.path.exists(FONT_NAME):
                wc = WordCloud(
                    font_path=FONT_NAME,
                    width=800, height=500,
                    background_color='white',
                    colormap='viridis',
                    regexp=r"[\w\xA1-\xFE]+" # 한글 정규식 추가 (깨짐 방지 보조)
                ).generate(text)
                
                fig, ax = plt.subplots(figsize=(10, 6))
                ax.imshow(wc, interpolation='bilinear')
                ax.axis('off')
                st.pyplot(fig)
                
                # 이미지 저장 버튼
                buf = BytesIO()
                fig.savefig(buf, format="png", dpi=300)
                st.download_button("📥 리포트 이미지 저장", buf.getvalue(), f"{target}_리포트.png", "image/png")
            else:
                st.error(f"⚠️ '{FONT_NAME}' 폰트 파일을 찾을 수 없습니다. 파일명을 확인해주세요.")
        else:
            st.warning("기간 내 데이터가 없습니다.")

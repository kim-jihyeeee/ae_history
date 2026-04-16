import streamlit as st
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from io import BytesIO
import datetime
import os

# 1. 기본 설정
st.set_page_config(page_title="AE History Visualizer v5.3", layout="wide")

# 🌟 폰트 파일명을 font.ttf로 고정했습니다.
FONT_NAME = "font.ttf"

# 세션 상태 초기화
if 'client_db' not in st.session_state: st.session_state.client_db = pd.DataFrame(columns=['광고주명', '담당자', '업종'])
if 'history_db' not in st.session_state: st.session_state.history_db = pd.DataFrame(columns=['날짜', '광고주명', '소통내용', '핵심키워드'])

# 2. UI 디자인
st.markdown("""
    <style>
    header[data-testid="stHeader"] { visibility: hidden; }
    .stButton>button { width: 100%; border-radius: 8px; background-color: #FFB300; color: white; font-weight: bold; border: none; height: 3em; }
    div[data-testid="stExpander"] { border: 1px solid #FFB300; border-radius: 8px; }
    </style>
""", unsafe_allow_html=True)

st.title("📝 AE History Visualizer v5.3")
st.caption("광고주 히스토리 데이터 시각화 리포트 시스템")

# 사이드바 메뉴
menu = st.sidebar.radio("📋 메뉴 이동", ["광고주 DB 관리", "관리 이력 입력", "디지털 리포트 생성"])

# --- 1. 광고주 DB 관리 ---
if menu == "광고주 DB 관리":
    st.header("📂 광고주 리스트 등록")
    uploaded_file = st.file_uploader("Excel 또는 CSV 파일을 업로드하세요", type=['xlsx', 'csv'])
    
    if uploaded_file:
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            st.session_state.client_db = df
            st.success("✅ 광고주 리스트 로드 완료!")
        except Exception as e:
            st.error(f"오류 발생: {e}")
    st.dataframe(st.session_state.client_db, use_container_width=True, hide_index=True)

# --- 2. 관리 이력 입력 ---
elif menu == "관리 이력 입력":
    st.header("✍️ 소통 및 관리 이력 기록")
    if st.session_state.client_db.empty:
        st.warning("먼저 '광고주 DB 관리' 메뉴에서 리스트를 등록해주세요.")
    else:
        with st.form("log_entry_form"):
            c1, c2 = st.columns(2)
            with c1:
                client = st.selectbox("광고주 선택", st.session_state.client_db['광고주명'].unique())
                date = st.date_input("기록 날짜", datetime.date.today())
            with c2:
                tags = st.text_input("핵심 키워드 (쉼표로 구분)", placeholder="효율개선, ROAS상승, GFA세팅")
            content = st.text_area("상세 관리 내용 (워드클라우드 분석용)", height=150)
            
            if st.form_submit_button("히스토리 저장하기"):
                new_data = pd.DataFrame([[date, client, content, tags]], columns=['날짜', '광고주명', '소통내용', '핵심키워드'])
                st.session_state.history_db = pd.concat([st.session_state.history_db, new_data], ignore_index=True)
                st.success(f"✅ {client}의 이력이 저장되었습니다.")
        st.dataframe(st.session_state.history_db.sort_values(by='날짜', ascending=False), use_container_width=True)

# --- 3. 디지털 리포트 생성 ---
elif menu == "디지털 리포트 생성":
    st.header("📊 워드클라우드 분석 리포트")
    if st.session_state.history_db.empty:
        st.info("기록된 데이터가 없습니다. 먼저 관리 이력을 입력해주세요.")
    else:
        target_client = st.selectbox("리포트 대상 광고주", st.session_state.history_db['광고주명'].unique())
        period_opt = st.select_slider("분석 기간", options=["7일", "15일", "한달", "분기"])
        
        days_delta = {"7일": 7, "15일": 15, "한달": 30, "분기": 90}[period_opt]
        start_date = datetime.date.today() - datetime.timedelta(days=days_delta)
        
        filtered_df = st.session_state.history_db[
            (st.session_state.history_db['광고주명'] == target_client) &
            (pd.to_datetime(st.session_state.history_db['날짜']).dt.date >= start_date)
        ]
        
        if not filtered_df.empty:
            text_data = (filtered_df['핵심키워드'].fillna('').str.cat(sep=' ') + " ") * 3 + filtered_df['소통내용'].fillna('').str.cat(sep=' ')
            
            if os.path.exists(FONT_NAME):
                wc = WordCloud(
                    font_path=FONT_NAME,
                    width=900, height=500,
                    background_color='white',
                    colormap='Dark2',
                    regexp=r"[\w\xA1-\xFE]+"
                ).generate(text_data)
                
                fig, ax = plt.subplots(figsize=(10, 6))
                ax.imshow(wc, interpolation='bilinear')
                ax.axis('off')
                st.pyplot(fig)
                
                img_buf = BytesIO()
                fig.savefig(img_buf, format="png", dpi=300, bbox_inches='tight')
                st.download_button(label="📥 리포트 이미지 저장", data=img_buf.getvalue(), file_name=f"Report_{target_client}.png", mime="image/png")
            else:
                st.error(f"⚠️ '{FONT_NAME}' 파일을 찾을 수 없습니다. 깃허브 파일명을 다시 확인해주세요.")
        else:
            st.warning("선택한 기간 동안의 데이터가 없습니다.")

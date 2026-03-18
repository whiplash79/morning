import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# 1. 구글 시트 연결 설정
def get_gspread_client():
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    # Secrets에 저장한 JSON 열쇠를 사용합니다.
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    return gspread.authorize(creds)

# 2. 데이터 불러오기 및 저장하기
def load_data():
    client = get_gspread_client()
    # 선생님의 시트 ID (주소창의 d/ 뒤쪽 문자열)
    sheet_id = "1718siWh7O-He8KQ3Ae2lHhpRsNaENzGFk0i2pu8398Q" 
    doc = client.open_by_key(sheet_id)
    
    # '학생현황' 탭에서 명단 읽기
    sheet = doc.worksheet("학생현황")
    return pd.DataFrame(sheet.get_all_records()), doc

st.title("☀️ 실시간 지각 체크")

try:
    df, doc = load_data()
    
    # 주소창에서 반 정보 읽기 (예: ?grade=3&room=1)
    qp = st.query_params
    target_grade = int(qp.get("grade", 3))
    target_room = int(qp.get("room", 1))

    st.subheader(f"📍 {target_grade}학년 {target_room}반")
    
    # 해당 반 학생만 필터링
    class_df = df[(df['학년'] == target_grade) & (df['반'] == target_room)]
    
    if class_df.empty:
        st.warning("해당 반의 학생 데이터가 시트에 없습니다.")
    else:
        # 체크박스 리스트 생성
        late_list = []
        for index, row in class_df.iterrows():
            if st.checkbox(f"👤 {row['성명']}", key=index):
                late_list.append(row)

        # 전송 및 저장 버튼
        if st.button(f"🚀 {len(late_list)}명 지각 보고 및 저장", use_container_width=True):
            if not late_list:
                st.success("오늘 지각생이 없습니다! 모두 출석 완료.")
            else:
                # '지각기록' 탭에 데이터 추가
                log_sheet = doc.worksheet("지각기록") # 시트에 '지각기록' 탭이 있어야 합니다!
                now = datetime.now().strftime("%Y-%m-%d %H:%M")
                
                for s in late_list:
                    # [날짜, 학년, 반, 성명, 학부모번호] 순서로 한 줄씩 추가
                    log_sheet.append_row([now, s['학년'], s['반'], s['성명'], s['학부모폰']])
                
                st.balloons() # 축하 풍선!
                st.success(f"{[s['성명'] for s in late_list]} 기록 완료!")

except Exception as e:
    st.error(f"⚠️ 연결 오류: {e}")
    st.info("시트에 '로봇 이메일'이 공유되어 있는지, 탭 이름이 맞는지 확인해 주세요.")

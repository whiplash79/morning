import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# 1. 구글 시트 연결 설정
def get_gspread_client():
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    return gspread.authorize(creds)

# 2. [수정됨] 데이터 불러오기 함수
def load_data():
    client = get_gspread_client()
    sheet_id = "1718siWh7O-He8KQ3Ae2lHhpRsNaENzGFk0i2pu8398Q" 
    doc = client.open_by_key(sheet_id)
    sheet = doc.worksheet("학생현황")
    
    # 깐깐한 get_all_records 대신 모든 값을 일단 가져옵니다.
    all_values = sheet.get_all_values()
    
    # '학년'과 '성명'이라는 글자가 들어있는 진짜 '제목 줄'을 찾습니다.
    header_idx = 0
    for i, row in enumerate(all_values):
        if '학년' in row and '성명' in row:
            header_idx = i
            break
    
    # 찾은 제목 줄을 기준으로 데이터를 표(DataFrame)로 만듭니다.
    header = all_values[header_idx]
    data = all_values[header_idx + 1:]
    
    # 중복된 제목이 있으면 뒤에 숫자를 붙여서 충돌을 피합니다.
    seen = {}
    new_header = []
    for h in header:
        if h in seen:
            seen[h] += 1
            new_header.append(f"{h}_{seen[h]}")
        else:
            seen[h] = 0
            new_header.append(h)
            
    return pd.DataFrame(data, columns=new_header), doc

st.title("☀️ 실시간 지각 체크")

# 이후 로직은 이전과 동일합니다.
try:
    df, doc = load_data()
    qp = st.query_params
    target_grade = qp.get("grade", "3") # 문자로 읽어온 뒤 비교
    target_room = qp.get("room", "1")

    st.subheader(f"📍 {target_grade}학년 {target_room}반")
    
    # 숫자/문자 섞임을 방지하기 위해 모두 문자로 바꾸어 비교합니다.
    df['학년'] = df['학년'].astype(str)
    df['반'] = df['반'].astype(str)
    
    class_df = df[(df['학년'] == target_grade) & (df['반'] == target_room)]
    
    if class_df.empty:
        st.warning(f"{target_grade}학년 {target_room}반 학생 데이터가 없습니다. 시트의 내용을 확인해주세요.")
    else:
        late_list = []
        for index, row in class_df.iterrows():
            if st.checkbox(f"👤 {row['성명']}", key=index):
                late_list.append(row)

        if st.button(f"🚀 {len(late_list)}명 지각 보고 및 저장", use_container_width=True):
            if not late_list:
                st.success("오늘 지각생이 없습니다!")
            else:
                log_sheet = doc.worksheet("지각기록")
                now = datetime.now().strftime("%Y-%m-%d %H:%M")
                for s in late_list:
                    log_sheet.append_row([now, s['학년'], s['반'], s['성명'], s.get('학부모폰', '')])
                st.balloons()
                st.success("기록 완료!")

except Exception as e:
    st.error(f"⚠️ 연결 오류: {e}")

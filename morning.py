import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- 1. 앱 설정 ---
st.set_page_config(page_title="지각생 체크 시스템", layout="centered")

# --- 2. 구글 시트 연결 (캐시 적용) ---
@st.cache_resource
def get_gspread_client():
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    return gspread.authorize(creds)

# --- 3. 데이터 로드 (10분 동안 기억하기) ---
@st.cache_data(ttl=600) # 600초(10분) 동안은 시트를 다시 읽지 않음
def load_student_data(sheet_id):
    client = get_gspread_client()
    doc = client.open_by_key(sheet_id)
    sheet = doc.worksheet("학생현황")
    all_values = sheet.get_all_values()
    
    header_idx = 0
    for i, row in enumerate(all_values):
        if '학년' in row and '성명' in row:
            header_idx = i
            break
    
    header = all_values[header_idx]
    data = all_values[header_idx + 1:]
    
    seen = {}
    new_header = []
    for h in header:
        if h in seen:
            seen[h] += 1
            new_header.append(f"{h}_{seen[h]}")
        else:
            seen[h] = 0
            new_header.append(h)
            
    return pd.DataFrame(data, columns=new_header)

# --- 메인 로직 시작 ---
st.title("☀️ 실시간 지각 체크 시스템")

# 명단 새로고침 기능
if st.sidebar.button("♻️ 명단 새로고침"):
    st.cache_data.clear()
    st.rerun()

try:
    sheet_id = "1718siWh7O-He8KQ3Ae2lHhpRsNaENzGFk0i2pu8398Q"
    df = load_student_data(sheet_id)
    
    # 지각기록 시트는 저장을 위해 캐시 없이 연결
    client = get_gspread_client()
    doc = client.open_by_key(sheet_id)
    log_sheet = doc.worksheet("지각기록")
    
    qp = st.query_params
    target_grade = qp.get("grade", "3") 
    target_room = qp.get("room", "1")

    st.subheader(f"📍 {target_grade}학년 {target_room}반")
    
    df['학년'] = df['학년'].astype(str)
    df['반'] = df['반'].astype(str)
    class_df = df[(df['학년'] == target_grade) & (df['반'] == target_room)]
    
    if class_df.empty:
        st.warning(f"{target_grade}학년 {target_room}반 데이터가 없습니다.")
    else:
        # 1. 체크박스 영역
        late_list = []
        for index, row in class_df.iterrows():
            s_phone = row.get('학생 전화번호', '')
            p_phone = row.get('학부모 전화번호', '')
            
            label = f"👤 **{row['성명']}**"
            if p_phone: label += f" (P: {p_phone[-4:]})"
            
            if st.checkbox(label, key=f"chk_{row['성명']}"):
                late_list.append({
                    '학년': row['학년'], '반': row['반'], '성명': row['성명'],
                    '학생 전화번호': s_phone, '학부모 전화번호': p_phone
                })

        st.divider()

        # 2. 저장 버튼 (중복 체크 포함)
        if st.button(f"🚀 {len(late_list)}명 지각 보고 및 저장", use_container_width=True):
            if not late_list:
                st.info("선택된 학생이 없습니다.")
            else:
                # 저장할 때만 시트를 읽어서 중복 체크
                all_logs = log_sheet.get_all_values()
                if not all_logs:
                    log_sheet.append_row(["날짜", "학년", "반", "성명", "학생 전화번호", "학부모 전화번호"])
                    all_logs = [["날짜", "학년", "반", "성명", "학생 전화번호", "학부모 전화번호"]]
                
                log_df = pd.DataFrame(all_logs[1:], columns=all_logs[0])
                today_str = datetime.now().strftime("%Y-%m-%d")
                now_full = datetime.now().strftime("%Y-%m-%d %H:%M")
                
                newly_added = []
                for s in late_list:
                    is_dup = False
                    if not log_df.empty:
                        match = log_df[(log_df['날짜'].str.contains(today_str)) & (log_df['성명'] == s['성명'])]
                        if not match.empty:
                            is_dup = True
                    
                    if not is_dup:
                        log_sheet.append_row([now_full, s['학년'], s['반'], s['성명'], s['학생 전화번호'], s['학부모 전화번호']])
                        newly_added.append(s['성명'])

                if newly_added:
                    st.toast(f"{len(newly_added)}명 기록 성공!", icon="✅")
                    st.success(f"저장 완료: {', '.join(newly_added)}")
                else:
                    st.info("추가할 인원이 없습니다. (이미 기록됨)")

        st.divider()

        # 3. 오늘의 기록 확인 및 삭제
        with st.expander("📝 오늘의 기록 확인 및 삭제", expanded=True):
            fresh_logs = log_sheet.get_all_values()
            if len(fresh_logs) > 1:
                display_df = pd.DataFrame(fresh_logs[1:], columns=fresh_logs[0])
                today_str = datetime.now().strftime("%Y-%m-%d")
                mine = display_df[
                    (display_df['날짜'].str.contains(today_str)) & 
                    (display_df['학년'] == str(target_grade)) & 
                    (display_df['반'] == str(target_room))
                ]

                if not mine.empty:
                    for idx, row in mine.iterrows():
                        c1, c2 = st.columns([4, 1])
                        c1.write(f"· **{row['성명']}** (부: {row.get('학부모 전화번호', '-')})")
                        if c2.button("삭제", key=f"del_{idx}"):
                            log_sheet.delete_rows(int(idx) + 2)
                            st.rerun()
                else:
                    st.write("오늘 기록된 학생이 없습니다.")
            else:
                st.write("장부가 비어있습니다.")

except Exception as e:
    # 쿼터 에러 발생 시 안내
    if "429" in str(e):
        st.error("⚠️ 구글 시트 접속량이 너무 많습니다. 1분만 기다렸다가 새로고침 해주세요.")
    else:
        st.error(f"⚠️ 오류 발생: {e}")

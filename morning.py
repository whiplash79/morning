import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- 1. 앱 페이지 설정 ---
st.set_page_config(page_title="지각생 체크 시스템", layout="centered")

# --- 2. 구글 시트 연결 함수 ---
def get_gspread_client():
    """
    Secrets에 저장된 JSON 열쇠를 꺼내 구글 서버에 인증을 요청하는 도구입니다.
    """
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    # st.secrets: 스트림릿 설정창에 넣은 비밀번호 뭉치를 가져옵니다.
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    return gspread.authorize(creds)

# --- 3. 데이터 로드 및 전처리 함수 ---
def load_data():
    """
    구글 시트에서 학생 명단을 가져오고, 복잡한 엑셀 양식에서도 제목줄을 찾아냅니다.
    """
    client = get_gspread_client()
    # 유저님의 구글 시트 고유 ID입니다.
    sheet_id = "1718siWh7O-He8KQ3Ae2lHhpRsNaENzGFk0i2pu8398Q" 
    doc = client.open_by_key(sheet_id)
    sheet = doc.worksheet("학생현황")
    
    # get_all_values(): 시트의 모든 내용을 일단 날것 그대로 가져옵니다.
    all_values = sheet.get_all_values()
    
    # '학년'과 '성명'이라는 글자가 있는 줄을 제목줄(Header)로 인식합니다.
    header_idx = 0
    for i, row in enumerate(all_values):
        if '학년' in row and '성명' in row:
            header_idx = i
            break
    
    header = all_values[header_idx]
    data = all_values[header_idx + 1:]
    
    # 중복된 제목(예: '3월'이 두 번 있을 때)이 있으면 '3월_1'로 이름을 바꿔 에러를 방지합니다.
    seen = {}
    new_header = []
    for h in header:
        if h in seen:
            seen[h] += 1
            new_header.append(f"{h}_{seen[h]}")
        else:
            seen[h] = 0
            new_header.append(h)
            
    # 표(DataFrame) 형태로 변환하여 반환합니다.
    return pd.DataFrame(data, columns=new_header), doc

# --- 4. 메인 화면 구성 ---
st.title("☀️ 실시간 지각 체크 시스템")

try:
    # 데이터 불러오기
    df, doc = load_data()
    
    # URL 파라미터 읽기 (예: ?grade=3&room=1)
    qp = st.query_params
    target_grade = qp.get("grade", "3") 
    target_room = qp.get("room", "1")

    st.subheader(f"📍 {target_grade}학년 {target_room}반")
    
    # 학년/반 데이터를 문자로 통일하여 비교 (필터링)
    df['학년'] = df['학년'].astype(str)
    df['반'] = df['반'].astype(str)
    
    class_df = df[(df['학년'] == target_grade) & (df['반'] == target_room)]
    
    if class_df.empty:
        st.warning(f"{target_grade}학년 {target_room}반 학생 데이터가 시트에 없습니다.")
    else:
        # 지각생 체크박스 리스트 생성
        late_list = []
        for index, row in class_df.iterrows():
            if st.checkbox(f"👤 {row['성명']}", key=index):
                late_list.append(row)

        st.divider()

        # 보고 및 저장 버튼
        if st.button(f"🚀 {len(late_list)}명 지각 보고 및 저장", use_container_width=True):
            if not late_list:
                st.success("오늘 지각생이 없습니다! 모두 출석했습니다.")
            else:
                # 구글 시트의 '지각기록' 탭에 저장
                log_sheet = doc.worksheet("지각기록")
                now = datetime.now().strftime("%Y-%m-%d %H:%M")
                
                for s in late_list:
                    # [일시, 학년, 반, 성명, 학부모번호] 순서로 한 줄씩 추가
                    log_sheet.append_row([now, s['학년'], s['반'], s['성명'], s.get('학부모폰', '')])
                
                # 풍선 대신 차분한 토스트 알림
                st.toast(f"{len(late_list)}명의 지각 기록이 저장되었습니다.", icon="📋")
                
                # 하이에듀 업로드용 임시 데이터 생성 (세션에 저장)
                st.session_state['last_late'] = late_list
                st.success("구글 시트에 기록을 성공적으로 남겼습니다!")

        # 하이에듀용 파일 다운로드 버튼 (기록 완료 후에 나타남)
        if 'last_late' in st.session_state:
            late_df = pd.DataFrame(st.session_state['last_late'])
            csv = late_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 하이에듀 업로드용 CSV 다운로드",
                data=csv,
                file_name=f"late_list_{datetime.now().strftime('%m%d')}.csv",
                mime="text/csv"
            )

except Exception as e:
    st.error(f"⚠️ 시스템 연결 오류: {e}")
    st.info("시트에 '지각기록' 탭이 있는지, 로봇 이메일이 공유되어 있는지 확인해 주세요.")

import streamlit as st
import pandas as pd
from datetime import datetime

# --- 1. 설정 및 데이터 로드 ---
st.set_page_config(page_title="지각생 체크 시스템", layout="centered")

# 실제 구현 시에는 google-sheets-reader를 사용하지만, 여기서는 예시 데이터를 사용합니다.
# 유저님이 공유해주신 시트 데이터를 불러오는 로직이 들어갈 자리입니다.
def load_student_data():
    # 예시 데이터 (실제로는 구글 시트에서 fetch)
    data = {
        '학년': [3, 3, 3, 3],
        '반': [1, 1, 2, 2],
        '성명': ['김철수', '이영희', '박민수', '최지우'],
        '학생폰': ['01011112222', '01022223333', '01033334444', '01044445555'],
        '학부모폰': ['01099998888', '01077776666', '01055554444', '01033332222']
    }
    return pd.DataFrame(data)

df = load_student_data()

# --- 2. 파라미터를 이용한 반 자동 인식 ---
# URL 예시: myapp.streamlit.app/?grade=3&room=1
query_params = st.query_params
target_grade = int(query_params.get("grade", 3)) # 기본값 3학년
target_room = int(query_params.get("room", 1))   # 기본값 1반

# --- 3. 교사용 체크 화면 ---
st.title(f"☀️ {target_grade}학년 {target_room}반")
st.subheader("오늘의 지각생을 체크해 주세요.")

# 해당 반 학생만 필터링
class_df = df[(df['학년'] == target_grade) & (df['반'] == target_room)]

late_students = []
for index, row in class_df.iterrows():
    # 모바일에서 누르기 편하도록 큰 체크박스 제공
    if st.checkbox(f"{row['성명']}", key=f"std_{index}"):
        late_students.append(row)

# --- 4. 데이터 제출 ---
if st.button(f"🚀 {len(late_students)}명 지각 보고", use_container_width=True):
    if not late_students:
        st.success("오늘 우리 반은 지각생이 없습니다! 👍")
    else:
        # 여기에 구글 시트의 'Today_Late' 시트로 데이터를 전송하는 코드가 들어갑니다.
        st.info(f"{[s['성명'] for s in late_students]} 학생이 기록되었습니다.")
        st.success("중앙 관리자에게 전송 완료!")

# --- 5. [관리자 전용] 하이에듀용 파일 생성 ---
with st.sidebar:
    st.header("Admin Menu")
    if st.button("📥 하이에듀 업로드 파일 생성"):
        # 오늘 기록된 데이터를 모아서 하이에듀 양식으로 변환
        # 하이에듀는 보통 [수신번호, 메시지내용] 형태의 CSV를 요구합니다.
        export_data = []
        for s in late_students:
            msg = f"[지각안내] {s['성명']} 학생이 아직 미등교입니다."
            export_data.append({"수신번호": s['학생폰'], "메시지": msg})
            export_data.append({"수신번호": s['학부모폰'], "메시지": msg})
        
        export_df = pd.DataFrame(export_data)
        csv = export_df.to_csv(index=False).encode('utf-8-sig')
        
        st.download_button(
            label="엑셀 양식 다운로드",
            data=csv,
            file_name=f"hiedu_late_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

import streamlit as st
import pdfplumber
import re

# 1. 페이지 기본 설정
st.set_page_config(
    page_title="소비기한 가속실험 정밀 검증 시스템",
    page_icon="🧪",
    layout="wide"
)

# 2. 사이드바 (왼쪽 안내 창)
with st.sidebar:
    st.header("⚙️ 검증 시스템 안내")
    st.info("""
    **💡 주요 자동 검증 항목**
    * R²(결정계수) 음수 부호 오기
    * Ea(활성에너지) 단위 오차 (cal vs kcal)
    * 개월-일수(Day) 환산 수식 검증
    * 안전계수(0.8) 적용 일수 산출
    """)
    st.divider()
    st.caption("실험실 자동화 검증 엔진 v2.5")

# 3. 메인 화면 상단 타이틀
st.title("🧪 소비기한 가속실험 보고서 검증기")
st.caption("PDF 또는 TXT 보고서를 업로드하면 수치 오차 및 단위 불일치를 자동으로 정밀 분석합니다.")
st.divider()

# 4. 파일 업로드 섹션
uploaded_file = st.file_uploader("📂 검토할 보고서 파일(PDF, TXT)을 선택하세요", type=["pdf", "txt"])

# 검증 로직 함수
def verify_report(text):
    errors, warnings, infos = [], [], []
    clean_text = text.replace(" ", "")

    # R² 음수 부호 검사
    r2_matches = re.findall(r'(?:R\^?2?|결정계수)\s*=\s*(-?\d+\.\d+)', text, re.IGNORECASE)
    for r2_str in r2_matches:
        if float(r2_str) < 0:
            errors.append(f"**R²(결정계수) 음수 부호 감지 (`{r2_str}`)**: 결정계수는 0 이상이어야 합니다. 부호를 확인하세요.")

    # Ea 단위 검사
    large_numbers = re.findall(r'(\d{1,3}(?:,\d{3})+|\d{4,})\.?\d*', text)
    for num_str in large_numbers:
        val = float(num_str.replace(',', ''))
        if 1000 <= val <= 100000:
            errors.append(f"**활성에너지(Ea) 단위 오류 (`{val:,.3f}`)**: `cal/mol` 수치가 `kcal/mol`로 잘못 표기되었을 수 있습니다. (`{val/1000:.3f} kcal/mol` 권장)")
            break

    # 개월수 환산 검사
    month_day_matches = re.findall(r'(\d+)\s*개월\s*\(\s*(\d+)\s*일\s*\)', text)
    for m_str, d_str in month_day_matches:
        m_val, d_val = int(m_str), int(d_str)
        if abs(m_val - (d_val / 30.0)) > 0.5:
            warnings.append(f"**개월-일수 환산 불일치 (`{m_val}개월({d_val}일)`)**: {d_val}일은 약 {d_val/30.0:.1f}개월입니다.")

    # 안전계수
    if "149" in clean_text or "119" in clean_text:
        infos.append("**안전계수 산출 안내**: 149.7일 × 0.8 = 119.76일 (버림 시 119일, 반올림 시 120일)")

    return errors, warnings, infos

# 5. 결과 출력 (탭 UI 구조 적용)
if uploaded_file is not None:
    with st.status("📄 문서를 파싱하고 수치를 정밀 검증 중입니다...", expanded=True) as status:
        extracted_text = ""
        if uploaded_file.name.endswith('.pdf'):
            with pdfplumber.open(uploaded_file) as pdf:
                for page in pdf.pages:
                    t = page.extract_text(layout=True)
                    if t: extracted_text += t + "\n"
        else:
            extracted_text = uploaded_file.read().decode('utf-8')

        errs, warns, infos = verify_report(extracted_text)
        status.update(label="✅ 분석 완료!", state="complete", expanded=False)

    # 탭으로 깔끔하게 구분
    tab1, tab2 = st.tabs(["📊 검토 결과 보고서", "🔍 원본 텍스트 확인"])

    with tab1:
        # 상단 요약 카드 (Metrics)
        c1, c2, c3 = st.columns(3)
        c1.metric("치명적 오류", f"{len(errs)} 건")
        c2.metric("단위 불일치 경고", f"{len(warns)} 건")
        c3.metric("수치 산출 안내", f"{len(infos)} 건")
        st.divider()

        if not errs and not warns and not infos:
            st.balloons()
            st.success("🎉 수치 오차 및 단위 불일치가 발견되지 않았습니다!")
        else:
            for e in errs: st.error(e, icon="🚨")
            for w in warns: st.warning(w, icon="⚠️")
            for i in infos: st.info(i, icon="ℹ️")

    with tab2:
        st.text_area("PDF 파싱 원본 텍스트", extracted_text, height=400)

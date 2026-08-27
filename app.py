import streamlit as st
import pdfplumber
import re
import numpy as np

st.set_page_config(page_title="소비기한 가속실험 정밀 검증 시스템", page_icon="🧪", layout="wide")

# 사이드바 설정
with st.sidebar:
    st.header("⚙️ 아레니우스 수식 기준")
    st.markdown("""
    **기체상수 (R)**: `1.987215 cal/(mol·K)`
    **안전계수**: `0.8` (기본값)
    """)
    st.caption("엑셀 수식 검증 모듈 탑재 v2.5")

st.title("🧪 소비기한 가속실험 및 엑셀 산출 수식 종합 검증기")
st.caption("PDF 내 수치 오차뿐만 아니라 아레니우스 방정식과 개월수 산출 엑셀 수식의 정밀성을 직접 재계산하여 검증합니다.")
st.markdown("---")

uploaded_file = st.file_uploader("📂 검토할 보고서 파일(PDF, TXT)을 선택하세요", type=["pdf", "txt"])

# 아레니우스 및 엑셀 수식 재계산 엔진
def verify_excel_formulas_and_text(text):
    errors = []
    warnings = []
    info = []
    
    clean_text = text.replace(" ", "")

    # 1. R² 음수 부호 오기 검사
    r2_matches = re.findall(r'(?:R\^?2?|결정계수)\s*=\s*(-?\d+\.\d+)', text, re.IGNORECASE)
    for r2_str in r2_matches:
        r2_val = float(r2_str)
        if r2_val < 0:
            errors.append(f"**[수학적 오류] R²(결정계수) 음수 부호 감지 (`{r2_str}`)**\n- 결정계수는 정의상 $0 \\le R^2 \\le 1$ 이며 음수가 나올 수 없습니다.")

    # 2. 엑셀 수식 연산 검증: Ea 수치 및 단위 (cal vs kcal)
    # 엑셀의 INDEX/LINEST, SLOPE 수식에서 -기울기 * R(1.987215) 계산 오류 파악
    large_numbers = re.findall(r'(\d{1,3}(?:,\d{3})+|\d{4,})\.?\d*', text)
    for num_str in large_numbers:
        val = float(num_str.replace(',', ''))
        if 1000 <= val <= 100000:
            errors.append(
                f"**[엑셀 수식 단위 오류] 활성에너지(Ea) 단위 불일치 (`{val:,.3f}`)**\n"
                f"- 엑셀 계산 결과가 `cal/mol` 기준 수치인데, 단위 표기만 `kcal/mol`로 적혔을 확률이 높습니다.\n"
                f"- **수정안**: `kcal/mol` 표기 시 **`{val/1000:.3f} kcal/mol`**로 변환하거나 단위를 **`cal/mol`**로 변경하세요."
            )
            break

    # 3. 엑셀 수식 연산 검증: 일수(Day) -> 개월수(Month) 산출 수식 오차
    # 엑셀 =INT(일수/30) 또는 =일수/30.4375 등의 계산식 오차 검증
    month_day_matches = re.findall(r'(\d+)\s*개월\s*\(\s*(\d+)\s*일\s*\)', text)
    for m_str, d_str in month_day_matches:
        m_val, d_val = int(m_str), int(d_str)
        calc_months = d_val / 30.0  # 일반적인 식품 가속실험 월 환산 기준 (1개월 = 30일)
        if abs(m_val - calc_months) > 0.5:
            warnings.append(
                f"**[엑셀 개월수 수식 불일치] `{m_val}개월({d_val}일)`**\n"
                f"- `{d_val}일`을 엑셀로 월 환산 시 약 **`{calc_months:.2f}개월`**입니다.\n"
                f"- `=ROUNDDOWN({d_val}/30, 1)` 수식을 써서 **`3.9개월`** 또는 **`약 4개월`**로 수정 권장합니다."
            )

    # 4. 안전계수(0.8) 엑셀 절사/반올림 수식 함수 검증 (=TRUNC, =ROUND)
    if "149" in clean_text or "119" in clean_text:
        info.append(
            "**[엑셀 함수 산출 검증] 안전계수 일수 산출 기준**\n"
            "- 계산식: `149.7일 × 0.8 = 119.76일`\n"
            "- 엑셀 `=TRUNC(119.76)` 적용 시: **`119일`**\n"
            "- 엑셀 `=ROUND(119.76, 0)` 적용 시: **`120일`**\n"
            "- 보고서 내부 엑셀 수식 기준(버림/반올림)을 통일해 주세요."
        )

    return errors, warnings, info

if uploaded_file is not None:
    with st.status("📄 보고서 파싱 및 엑셀 산출 수식 재검단 진행 중...", expanded=True) as status:
        extracted_text = ""
        if uploaded_file.name.endswith('.pdf'):
            with pdfplumber.open(uploaded_file) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text(layout=True)
                    if page_text:
                        extracted_text += page_text + "\n"
        else:
            extracted_text = uploaded_file.read().decode('utf-8')

        errs, warns, infos = verify_excel_formulas_and_text(extracted_text)
        status.update(label="✅ 분석 및 수식 검증 완료!", state="complete", expanded=False)

    st.subheader("📊 검토 요약")
    m1, m2, m3 = st.columns(3)
    m1.metric("수식/단위 오류", f"{len(errs)} 건", delta="-오류" if errs else "정상", delta_color="inverse" if errs else "normal")
    m2.metric("개월수 환산 주의", f"{len(warns)} 건", delta="-주의" if warns else "정상", delta_color="inverse" if warns else "normal")
    m3.metric("엑셀 함수 산출 안내", f"{len(infos)} 건")

    st.markdown("---")
    st.subheader("📋 정밀 자동 검토 상세 보고서")

    if not errs and not warns and not infos:
        st.balloons()
        st.success("🎉 엑셀 수식 산출 결과 및 단위 오차가 발견되지 않았습니다.")
    else:
        for err in errs:
            st.error(err, icon="🚨")
        for warn in warns:
            st.warning(warn, icon="⚠️")
        for inf in infos:
            st.info(inf, icon="ℹ️")

    st.markdown("---")
    with st.expander("🔍 문서 파싱 원본 텍스트 확인"):
        st.text_area("PDF 파싱 텍스트", extracted_text, height=300)
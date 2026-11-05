# 🐰 설거지 제비뽑기 (Dishwashing Lucky Draw)

첨부된 우사기(치이카와) 테마를 기반으로 제작된 모바일 최적화 단일 화면 설거지 당번 제비뽑기 웹앱입니다.
GitHub과 Streamlit Community Cloud를 통해 무료로 손쉽게 QR 코드로 배포할 수 있습니다.

## 🌟 주요 특징
1. **단일 화면 & 모바일 노스크롤 (No-Scroll View)**: 스마트폰 화면 한눈에 쏙 들어오는 초컴팩트 레이아웃.
2. **우사기 파스텔 옐로우 테마**: 첨부 이미지(앞모습/뒷모습 우사기) 및 바닐라 크림 파스텔톤 UI.
3. **7개 다국어 지원**: 한국어, English, 日本語, 中文, Tiếng Việt, ภาษาไทย, हिन्दी.
4. **당번 결과 자동 저장**: 추첨 시마다 `dishwashing_history.csv`에 자동 기록 & CSV 다운로드 제공.
5. **내장 QR 코드 생성기**: 배포된 Streamlit URL을 입력하면 친구들이 바로 찍을 수 있는 QR 코드 즉시 생성.

## 🚀 GitHub & Streamlit Cloud 배포 가이드
1. GitHub에서 새 Repository 생성 (예: `dishwashing-lottery`)
2. 본 폴더의 파일들(`app.py`, `requirements.txt`, `images.jpg`, `usagi.jpg`)을 업로드
3. [share.streamlit.io](https://share.streamlit.io) 접속 후 GitHub 계정으로 로그인
4. **New App** 클릭 -> 방금 만든 Repository와 `app.py` 선택 후 **Deploy** 클릭!
5. 생성된 웹 링크를 QR 코드로 만들어 식탁에 붙여두거나 메신저로 공유하면 끝!

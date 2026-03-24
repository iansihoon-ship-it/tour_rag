# 서울 맞춤형 관광지 추천 대시보드 배포 가이드

이 문서는 완성된 Streamlit 대시보드를 외부(웹)에 무료로 배포하는 가장 빠른 방법인 **Streamlit Community Cloud** 배포 프로세스를 안내합니다.

## 배포 전 준비사항

현재 `tour_rag` 폴더 내에 배포에 필요한 필수 파일 2개가 모두 준비되어 있습니다.
1. `app.py`: 대시보드 실행 파이썬 코드
2. `requirements.txt`: 배포 서버에서 필요한 파이썬 라이브러리 목록

## 배포 순서 (Streamlit Cloud 기준)

### 1단계: GitHub에 코드 업로드 (Push)
1. 본인의 [GitHub(깃허브)](https://github.com/) 계정에 로그인하여 새로운 퍼블릭(Public) 저장소(Repository)를 생성합니다. (예: `seoul-tour-dashboard`)
2. 생성한 저장소에 현재 폴더에 있는 **`app.py`** 와 **`requirements.txt`** 두 개의 파일을 업로드(Push)합니다.
   * `data` 폴더 등 다른 파일들은 선택사항이지만, 위 두 파일은 반드시 최상위 경로나 특정 폴더 내에 함께 있어야 합니다.

### 2단계: Streamlit Cloud 연결 및 배포
1. [Streamlit Community Cloud](https://share.streamlit.io/) 홈페이지에 접속하여 GitHub 계정으로 로그인 (Continue with GitHub) 합니다.
2. 우측 상단의 **`New app`** 버튼을 클릭합니다.
3. 팝업 창에서 아래 정보를 입력합니다:
   - **Repository**: 방금 만든 GitHub 저장소 선택 (예: `your-username/seoul-tour-dashboard`)
   - **Branch**: `main` (또는 `master`) 등 코드가 올라간 브랜치 선택
   - **Main file path**: `app.py` (폴더 안에 넣었다면 `tour_rag/app.py` 와 같이 경로 지정)
   - **App URL**: 원하는 나만의 고유 웹 주소를 설정할 수 있습니다.
4. **`Deploy`** 버튼을 클릭합니다.

### 3단계: 배포 완료 및 확인
* Deploy 버튼을 누르면 화면에 로딩 애니메이션(오븐이 구워지는 그래픽)이 나타나며, 약 1~3분 정도 `requirements.txt`의 패키지들을 설치하는 과정이 진행됩니다.
* 설치가 완료되면 전 세계 누구나 접속할 수 있는 여러분만의 URL로 대시보드가 자동 실행됩니다! 🎉

---
> 💡 Github 업로드나 배포 과정에서 `requirements.txt` 오류 등 문제가 발생한다면 언제든 에러 메시지를 알려주세요!

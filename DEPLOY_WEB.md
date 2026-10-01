# Stock AI Pro 웹사이트 배포

이 프로젝트는 Streamlit 기반이라 서버에 올리면 `https://...` 주소로 접속할 수 있습니다.

## 중요한 점
- 현재 기본 AI는 Ollama 로컬 AI입니다.
- **내 PC에서 실행할 때** Ollama를 그대로 사용할 수 있습니다.
- 외부 서버에 배포하면 그 서버에 Ollama가 없으므로, 공개 웹사이트에서 AI 기능을 쓰려면 서버에 Ollama를 설치하거나 선택적으로 OpenAI API 같은 원격 AI를 설정해야 합니다.
- 계정 DB는 현재 SQLite 기반의 로컬/단일 서버 구조입니다. 공개 서비스 규모가 커지면 PostgreSQL 등의 서버 DB로 교체하는 것을 권장합니다.

## 가장 간단한 주소
PC에서 실행 후:

`http://localhost:8501`

같은 공유기 안의 다른 기기에서는 PC의 사설 IP와 8501 포트를 사용합니다.

## Docker

```bash
docker build -t stock-ai-pro .
docker run --rm -p 8501:8501 --env-file .env stock-ai-pro
```

그 다음 브라우저에서 `http://localhost:8501`로 접속합니다.

## 공개 HTTPS 주소
Docker를 지원하는 호스팅 서비스나 Streamlit 계열 호스팅에 이 폴더를 배포하면 공개 URL을 받을 수 있습니다. 배포 후 환경변수에 `.env`의 필요한 값들을 설정하세요.

공개 배포 전에 `data/stock_ai_accounts.db` 같은 로컬 DB를 그대로 공유하지 않도록 주의하세요.

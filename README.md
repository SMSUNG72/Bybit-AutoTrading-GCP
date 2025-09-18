# CGT (Cobweb Grid Trader) - Multi-user Web App

- Flask + Gunicorn + Systemd
- 유저별 .env는 `~/Bybit-AutoTrading-GCP-run/user_N/.env` (Git 추적 금지)

## Quick Start (로컬/테스트)
1) `.env.example`를 참고해 `~/Bybit-AutoTrading-GCP-run/user_1/.env` 작성
2) `systemctl start legacy@1` 로 서비스 기동 (서버 기준)
3) 브라우저: `http://<serverip>:7001/`

## 환경변수 (.env)
- BYBIT_API_KEY / BYBIT_API_SECRET
- SMTP_SERVER / SMTP_PORT / SMTP_SENDER / SMTP_RECEIVER / SMTP_USER / SMTP_PASSWORD

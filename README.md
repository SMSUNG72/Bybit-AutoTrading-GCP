# Bybit 자동매매 봇 (Web GUI on GCP)

## 1. 프로젝트 개요

이 프로젝트는 Bybit 거래소의 BTCUSDT 무기한 선물을 대상으로 하는 자동매매 봇입니다.
**Flask를 기반으로 제작된 웹 GUI**를 통해 모든 설정을 제어할 수 있으며, 실제 매매 로직은 Google Cloud Platform(GCP) 서버에서 24시간 안정적으로 실행됩니다.

## 2. 주요 기능

- 그리드(물타기) 매매 전략 기반
- Long/Short 양방향 독립적인 포지션 운영 가능 (헤지 모드)
- 웹 브라우저를 통한 실시간 상태 모니터링
- 주요 매매 이벤트 발생 시 이메일 알림

## 3. 서버 실행 방법

이 서비스는 systemd를 통해 관리됩니다.

- **상태 확인:** `sudo systemctl status bybit-bot`
- **서비스 시작:** `sudo systemctl start bybit-bot`
- **서비스 종료:** `sudo systemctl stop bybit-bot`
- **실시간 로그 확인:** `sudo journalctl -u bybit-bot -f`

## 4. 참고 사항

- 모든 API 키와 비밀 정보는 `.env` 파일에 안전하게 보관됩니다.
- 이 설명서는 2025년 8월 23일에 최종 업데이트되었습니다.

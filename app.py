from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import os

# 다음 단계에서 만들 trading_bot.py 파일에서 TradingBot 클래스를 가져옵니다.
# 아직 파일이 없어서 오류처럼 보일 수 있지만, 정상입니다.
from trading_bot import TradingBot

# .env 파일에서 환경 변수를 로드합니다.
load_dotenv()

# Flask 웹 애플리케이션 생성
app = Flask(__name__)

# .env 파일에서 Bybit API 키를 가져옵니다.
api_key = os.getenv("BYBIT_API_KEY")
api_secret = os.getenv("BYBIT_API_SECRET")

# API 키가 .env 파일에 설정되지 않은 경우, 오류를 발생시켜 문제를 알려줍니다.
if not api_key or not api_secret:
    raise ValueError("오류: .env 파일에 BYBIT_API_KEY와 BYBIT_API_SECRET을 설정해야 합니다.")

# 자동매매 봇 객체를 단 하나만 생성하여 전역 변수로 관리합니다.
# 이렇게 하면 서버가 실행되는 동안 봇의 상태(실행 여부 등)가 계속 유지됩니다.
bot = TradingBot(api_key=api_key, api_secret=api_secret)


# --- 웹 페이지 주소(URL)와 파이썬 함수를 연결하는 부분 ---

@app.route('/')
def index():
    """
    사용자가 웹 브라우저에서 우리 서버의 기본 주소로 접속했을 때,
    templates 폴더에 있는 index.html 파일을 화면에 보여주는 함수입니다.
    """
    return render_template('index.html')

@app.route('/start', methods=['POST'])
def start_bot():
    """
    웹 UI의 '봇 시작하기' 버튼을 누르면, scripts.js가 이곳으로 요청을 보냅니다.
    웹에서 받은 설정값(JSON)으로 봇을 시작시키는 함수입니다.
    """
    if not bot.is_running:
        params = request.json  # 웹에서 보낸 모든 설정값을 딕셔너리(params)로 받습니다.
        bot.start(params)      # 받은 설정값으로 trading_bot.py의 봇을 시작시킵니다.
        return jsonify({'status': 'success', 'message': '봇이 성공적으로 시작되었습니다.'})
    else:
        return jsonify({'status': 'already_running', 'message': '봇이 이미 실행 중입니다.'})

@app.route('/stop', methods=['POST'])
def stop_bot():
    """
    '봇 종료' 버튼을 누르면 이곳으로 요청이 옵니다.
    실행 중인 봇을 중지시키는 함수입니다.
    """
    if bot.is_running:
        bot.stop()
        return jsonify({'status': 'success', 'message': '봇이 성공적으로 중지되었습니다.'})
    else:
        return jsonify({'status': 'not_running', 'message': '봇이 이미 중지 상태입니다.'})

@app.route('/status')
def get_status():
    """
    웹 UI가 주기적으로 봇의 현재 상태를 물어볼 때 이곳으로 요청이 옵니다.
    봇의 현재 상태(실행 여부, 로그 등)를 JSON 형태로 웹에 전달하는 함수입니다.
    """
    return jsonify(bot.get_status())


# --- 웹 서버 실행 ---

if __name__ == '__main__':
    """
    터미널에서 'python app.py' 명령어로 이 파일을 직접 실행했을 때만
    아래의 웹 서버 실행 코드가 동작합니다.
    """
    # host='0.0.0.0'은 내 PC뿐만 아니라, 같은 네트워크의 다른 기기에서도 접속할 수 있게 합니다.
    # debug=True는 코드 수정 시 서버가 자동으로 재시작되어 개발에 편리합니다.
    app.run(host='0.0.0.0', port=5001, debug=True)

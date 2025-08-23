from pybit.unified_trading import HTTP
import time
import logging
from threading import Thread, Event
import math
import smtplib
from email.mime.text import MIMEText
import random
import string

# 로그 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TradingBot:
    def __init__(self, api_key, api_secret):
        try:
            self.session = HTTP(testnet=False, api_key=api_key, api_secret=api_secret)
            logging.info("Bybit API 세션이 성공적으로 초기화되었습니다.")
        except Exception as e:
            logging.error(f"API 세션 초기화 실패: {e}")
            raise

        self.params = {}
        self.is_running = False
        self.stop_event = Event()
        self.thread = None
        self.logs = []
        self.instrument_info = {}
        self.last_position_state = {"size": None, "avg_price": None}
        self.tp_order_link_id = None # 익절 주문 ID를 저장할 변수

        # --- 이메일 설정 (원본 코드와 동일) ---
        self.email_config = {
            "smtp_server": "smtp.naver.com",
            "port": 465,
            "sender_email": "smsung2@naver.com",
            "receiver_email": "smsung2@naver.com",
            "user_id": "smsung2",
            "password": "SBDV8PZYKC4X" # 원본 코드의 비밀번호
        }

    def log(self, message):
        logging.info(message)
        log_entry = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}"
        self.logs.insert(0, log_entry)
        self.logs = self.logs[:100]

    def _send_email(self, subject, text):
        try:
            cfg = self.email_config
            msg = MIMEText(text)
            msg['Subject'] = subject
            msg['From'] = cfg['sender_email']
            msg['To'] = cfg['receiver_email']

            with smtplib.SMTP_SSL(cfg['smtp_server'], cfg['port']) as server:
                server.login(cfg['user_id'], cfg['password'])
                server.sendmail(cfg['sender_email'], cfg['receiver_email'], msg.as_string())
            self.log(f"이메일 알림 발송 성공: {subject}")
        except Exception as e:
            self.log(f"오류: 이메일 발송 실패 - {e}")

    def get_status(self):
        return {'is_running': self.is_running, 'logs': self.logs}

    def start(self, params):
        if self.is_running:
            self.log("경고: 봇이 이미 실행 중입니다.")
            return
        self.params = params
        self.is_running = True
        self.stop_event.clear()
        self.thread = Thread(target=self._run)
        self.thread.start()
        self.log("봇 스레드를 시작합니다.")

    def stop(self):
        if not self.is_running:
            self.log("경고: 봇이 이미 중지 상태입니다.")
            return
        self.is_running = False
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=10)
        try:
            symbol = self.params.get('symbol', 'BTCUSDT')
            self.session.cancel_all_orders(category="linear", symbol=symbol)
            self.log(f"{symbol}의 모든 대기 주문을 취소했습니다.")
        except Exception as e:
            self.log(f"오류: 주문 취소 실패 - {e}")
        self.log("봇 스레드를 중지했습니다.")

    def _get_instrument_info(self, symbol):
        try:
            res = self.session.get_instruments_info(category="linear", symbol=symbol)
            info = res['result']['list'][0]
            self.instrument_info = {
                'qty_step': float(info['lotSizeFilter']['qtyStep']),
                'tick_size': float(info['priceFilter']['tickSize']),
                'min_order_qty': float(info['lotSizeFilter']['minOrderQty'])
            }
            self.instrument_info['qty_precision'] = int(abs(math.log10(self.instrument_info['qty_step']))) if self.instrument_info['qty_step'] > 0 else 0
            self.instrument_info['price_precision'] = int(abs(math.log10(self.instrument_info['tick_size']))) if self.instrument_info['tick_size'] > 0 else 0
            self.log(f"{symbol} 정보 로드 완료: {self.instrument_info}")
        except Exception as e:
            self.log(f"오류: {symbol} 정보 로드 실패 - {e}")
            raise

    def _place_order(self, order_params):
        try:
            order_params['qty'] = str(round(float(order_params['qty']), self.instrument_info['qty_precision']))
            if 'price' in order_params:
                order_params['price'] = str(round(float(order_params['price']), self.instrument_info['price_precision']))

            if float(order_params['qty']) < self.instrument_info['min_order_qty']:
                self.log(f"경고: 계산된 주문 수량({order_params['qty']})이 최소 주문 수량({self.instrument_info['min_order_qty']})보다 작아 주문을 실행하지 않습니다.")
                return None
            
            self.log(f"주문 시도: {order_params}")
            response = self.session.place_order(**order_params)
            self.log(f"주문 응답: {response.get('retMsg')}")
            if response.get('retCode') != 0:
                self.log(f"주문 실패! 응답: {response}")
                return None
            return response
        except Exception as e:
            self.log(f"오류: 주문 실패 - {e}")
            return None

    def _run(self):
        self.log(f"자동매매 로직을 시작합니다. 설정: {self.params}")
        
        try:
            symbol = self.params['symbol']
            leverage = self.params['leverage']
            
            self._get_instrument_info(symbol)
            
            try:
                self.session.switch_position_mode(category="linear", symbol=symbol, mode=3)
                self.log("계정을 헤지 모드로 설정했습니다.")
            except Exception as e:
                if "110025" in str(e) or "110021" in str(e):
                    self.log("정보: 계정이 이미 헤지 모드로 설정되어 있습니다.")
                else:
                    self.log(f"경고: 포지션 모드 설정 실패 - {e}")

            try:
                self.session.set_leverage(category="linear", symbol=symbol, buyLeverage=str(leverage), sellLeverage=str(leverage))
                self.log(f"레버리지를 {leverage}x로 설정했습니다.")
            except Exception as e:
                if "110043" in str(e): self.log(f"정보: 레버리지가 이미 {leverage}x로 설정되어 있어 건너뜁니다.")
                else: raise e

            self.session.cancel_all_orders(category="linear", symbol=symbol)
            self.log("시작 전 모든 대기 주문을 취소했습니다.")
            self.last_position_state = {"size": None, "avg_price": None}
            self.tp_order_link_id = None

        except Exception as e:
            self.log(f"오류: 초기 설정에 실패했습니다 - {e}")
            self.is_running = False
            return

        is_first_run = True # 최초 실행 여부를 판단하기 위한 변수

        while self.is_running and not self.stop_event.is_set():
            try:
                side_param = self.params['side']
                position_idx_param = 1 if side_param == 'Buy' else 2

                pos_res = self.session.get_positions(category="linear", symbol=symbol, positionIdx=position_idx_param)
                position = pos_res['result']['list'][0]
                
                current_size = float(position['size'])
                avg_price = float(position['avgPrice']) if current_size > 0 else 0
                orders_res = self.session.get_open_orders(category="linear", symbol=symbol)
                open_orders = orders_res['result']['list']

                if current_size == 0:
                    # --- 최종 수정: 익절 후 와 최초 실행을 구분하는 로직 ---
                    if not is_first_run: # 최초 실행이 아닐 경우 (즉, 익절 후)
                        self.log("포지션이 익절로 종료되었습니다.")
                        self._send_email("포지션 익절", f"{symbol} 포지션이 성공적으로 종료되었습니다.")
                        
                        if len(open_orders) > 0:
                            self.log("남은 주문을 취소합니다.")
                            self.session.cancel_all_orders(category="linear", symbol=symbol)
                        
                        if self.params.get('loop', 'Yes') == 'No':
                            self.log("반복 실행이 꺼져있어 봇을 중지합니다."); self.stop(); return
                        
                        self.log("60초 후 새로운 사이클을 시작합니다.")
                        self.stop_event.wait(60)
                        if not self.is_running: break
                    
                    self.last_position_state = {"size": None, "avg_price": None}
                    self.tp_order_link_id = None
                    is_first_run = False # 다음부터는 최초 실행이 아님

                    self.log("포지션 없음. 신규 진입 및 그리드 주문을 설정합니다.")
                    steps = self.params['steps']
                    price_res = self.session.get_tickers(category="linear", symbol=symbol)
                    last_price = float(price_res['result']['list'][0]['lastPrice'])
                    
                    if self.params.get('startmarketprice', 'Yes') == 'Yes':
                        qty1 = (steps[0]['usdt'] * leverage) / last_price
                        self._place_order({"category": "linear", "symbol": symbol, "side": side_param, "orderType": "Market", "qty": qty1, "positionIdx": position_idx_param})
                        self._send_email("1차 주문 체결", f"{symbol} 포지션에 시장가로 진입했습니다.")
                        self.stop_event.wait(3)
                        pos_res = self.session.get_positions(category="linear", symbol=symbol, positionIdx=position_idx_param)
                        base_price = float(pos_res['result']['list'][0]['avgPrice']) if float(pos_res['result']['list'][0]['size']) > 0 else last_price
                    else:
                        base_price = last_price
                        qty1 = (steps[0]['usdt'] * leverage) / base_price
                        self._place_order({"category": "linear", "symbol": symbol, "side": side_param, "orderType": "Limit", "qty": qty1, "price": base_price, "positionIdx": position_idx_param})

                    current_calc_price = base_price
                    for step in steps[1:]:
                        gap_pct, money = step['gap'], step['usdt']
                        price = current_calc_price * (1 - gap_pct / 100) if side_param == 'Buy' else current_calc_price * (1 + gap_pct / 100)
                        qty = (money * leverage) / price
                        self._place_order({"category": "linear", "symbol": symbol, "side": side_param, "orderType": "Limit", "qty": qty, "price": price, "positionIdx": position_idx_param})
                        current_calc_price = price
                
                else: # 포지션이 있는 경우
                    self.log(f"포지션 보유 중 (크기: {current_size}, 평단: {avg_price}). 익절 주문을 관리합니다.")
                    position_side = position['side']
                    tp_side = 'Sell' if position_side == 'Buy' else 'Buy'
                    
                    tp_rate = self.params['profittake']
                    leverage_in_pos = float(position['leverage'])
                    
                    if position_side == 'Buy':
                        tp_price = avg_price * (1 + (tp_rate / 100 / leverage_in_pos))
                    else:
                        tp_price = avg_price * (1 - (tp_rate / 100 / leverage_in_pos))
                    
                    existing_tp_order = None
                    if self.tp_order_link_id:
                        for o in open_orders:
                            if o.get('orderLinkId') == self.tp_order_link_id:
                                existing_tp_order = o
                                break
                    
                    position_changed = (current_size != self.last_position_state.get('size')) or \
                                       (avg_price != self.last_position_state.get('avg_price'))

                    if position_changed and self.last_position_state.get("size") is not None:
                         self.log("물타기 주문 체결 감지! 포지션이 변경되었습니다.")
                         self._send_email("물타기 주문 체결", f"{symbol} 포지션 크기가 {self.last_position_state.get('size')} -> {current_size}로 변경되었습니다.")

                    if not existing_tp_order or position_changed:
                        if existing_tp_order:
                            self.log("포지션 변경 감지. 기존 익절 주문을 취소합니다.")
                            self.session.cancel_order(category="linear", symbol=symbol, orderLinkId=self.tp_order_link_id)
                        
                        self.log(f"새로운 익절 주문을 설정합니다. 가격: {tp_price}, 수량: {current_size}")
                        new_tp_id = "tp_" + ''.join(random.choices(string.ascii_letters + string.digits, k=8))
                        response = self._place_order({
                            "category": "linear", "symbol": symbol, "side": tp_side,
                            "orderType": "Limit", "qty": current_size, "price": tp_price,
                            "reduceOnly": True, "positionIdx": position_idx_param,
                            "orderLinkId": new_tp_id
                        })
                        if response:
                            self.tp_order_link_id = new_tp_id
                        
                        self.last_position_state = {"size": current_size, "avg_price": avg_price}
                    else:
                        self.log("익절 주문이 이미 올바르게 설정되어 있습니다.")

                self.stop_event.wait(15)

            except Exception as e:
                self.log(f"오류: 매매 로직 실행 중 문제 발생 - {e}")
                self.stop_event.wait(30)


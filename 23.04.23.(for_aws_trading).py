access = "EzQNayHa9KMNwl50xyD3FLw2GZZHj1vsCKLYQf3b"
secret = "J1dFjOMOi2tqp9xHeEYwC8xXxxEJ4GK2FqI5L3tt"
import time
import pyupbit
import pandas as pd
import numpy as np
from datetime import datetime # datetime 모듈에서 datetime 클래스를 임포트
import openpyxl
start_money = 500000
#23.04.22.로부터 성공실패를 기록해 투자 비율에 적용케. 완전 처음부터 시작할거면 trdaing()과 맨 마지막 예산 쪽 성패를 각각 수식 자체 수정해야!
#시작 자금을 1/2로 하려면 01로, 시작 자금을 1로 하려면 00으로 하자.
sucess = 0
fail = 1
No = 1 #엑셀 작성 연번


sf_betting_rate = (1+sucess)/(1+fail)
if sf_betting_rate >= 1:
    sf_betting_rate = 0.99


# 로그인
upbit = pyupbit.Upbit(access, secret)


cash = upbit.get_balance("KRW")
budget = cash* sf_betting_rate

signal_time = datetime.now() # 현재 시간을 변수에 할당
print(signal_time, " 보유 현금: ",cash,"  예산: ",budget, "누적 수익금: ",start_money-cash, "누적 수익률: ",(cash-start_money)/start_money*100,"%", "성공 횟수: ",sucess, "실패 횟수: ",fail,"성공률: ",sucess/fail)

traded_coin = None
strategy = None
hour_result=[] #초기화
day_result=[]
day_coin = None
hour_coin = None
avg_buy_price = None
df_hour = None
df_day = None
balance = None

def find_hour_coin():
    # 원화 마켓에 있는 모든 코인의 티커를 가져옵니다.
    tickers = pyupbit.get_tickers(fiat="KRW")
    # 결과를 저장할 빈 리스트를 만듭니다.
    #global hour_result
    hour_result = []
    # 각 코인에 대해 반복합니다.
    for ticker in tickers:
        # 코인의 10일간의 시간봉 데이터를 가져옵니다.
        #################################################################
        time.sleep(0.1)
        df = pyupbit.get_ohlcv(ticker,"month",200,None,0.1)
        if df is not None:

            low_min = df["low"].rolling(window=5).min()
            high_max = df["high"].rolling(window=5).max()

            df["%k_fast"] = 100 * (df["close"] - low_min) / (high_max - low_min)
            df["%d_fast"] = df["%k_fast"].rolling(window=3).mean()

            df["%k_slow"] = df["%d_fast"]
            df["%d_slow"] = df["%k_slow"].rolling(window=3).mean()
            # alow 열(12열)을 추가하고, %d_slow 값이 한칸 위 행의 값보다 크면 True, 아니면 False를 할당합니다.
            df['allow'] = np.where(df['%d_slow'].shift(+1) < df['%d_slow'], True, False)
            # alow열이 True이거나, 월봉 스토 slow가 존재하지 않거나.
            if df.iloc[-1].loc['allow'] == True or np.isnan(df.iloc[-1].loc["%d_slow"]) == True:
                               
                    #일봉 일목균형표 선행스팬보다 종가가 높은 코인 찾기
                df_day = pyupbit.get_ohlcv(ticker,"day",200,None,0.1)
                if df_day is not None:
                    
                    df_day['high_low'] = (df_day['high'] + df_day['low']) / 2
                    df_day['tenkan_sen'] = (df_day['high'].rolling(window=9).max() + df_day['low'].rolling(window=9).min()) / 2
                    df_day['kijun_sen'] = (df_day['high'].rolling(window=26).max() + df_day['low'].rolling(window=26).min()) / 2
                    df_day['senkou_span_a'] = ((df_day['tenkan_sen'] + df_day['kijun_sen']) / 2).shift(26)
                    df_day['senkou_span_b'] = ((df_day['high'].rolling(window=52).max() + df_day['low'].rolling(window=52).min()) / 2).shift(26)
                    df_day['chikou_span'] = df_day['close'].shift(-26)
            #구름떼 위거나 선행스팬이 존재하지 않거나.
                    if df_day.iloc[-1]['low'] > max(df_day.iloc[-1]['senkou_span_a'], df_day.iloc[-1]['senkou_span_b']) or np.isnan(df_day.iloc[-1]['senkou_span_a']) == True:
            
                        ################이하는 시봉으로 df_hour를 다시 설정함. 위는 월봉df
                # 시간별 OHLCV 데이터를 가져오는 코드
                        df_hour = pyupbit.get_ohlcv(ticker,"minute60",200,None,0.1)
                        # 전일 일봉 CCI가 0 이상인 경우만 작동하도록 하자. 일봉 기준 최소한의 상승 추세에 관한 보장이다.
                        if df_hour is not None:
                            
                    # 볼린저 밴드 계산
                            df_hour["MA20"] = df_hour["close"].rolling(20).mean()
                            df_hour["stddev"] = df_hour["close"].rolling(20).std()
                            df_hour["upper"] = df_hour["MA20"] + (df_hour["stddev"] * 2)
                            df_hour["lower"] = df_hour["MA20"] - (df_hour["stddev"] * 2)
                            df_hour["bandwidth"] = (df_hour["upper"] - df_hour["lower"]) / df_hour["MA20"]

                    

                    #각종 조건 순차 계산. 밴드폭이 이거보다 크다면 15분봉 매매로 가야한다.
                            if df_hour.iloc[-2]["bandwidth"] <= 1.5:
                                
                                #print(df_hour.iloc[-2]["bandwidth"])
                                # 시봉 구름떼 위어야 한다.
                                df_hour['high_low'] = (df_hour['high'] + df_hour['low']) / 2
                                df_hour['tenkan_sen'] = (df_hour['high'].rolling(window=9).max() + df_hour['low'].rolling(window=9).min()) / 2
                                df_hour['kijun_sen'] = (df_hour['high'].rolling(window=26).max() + df_hour['low'].rolling(window=26).min()) / 2
                                df_hour['senkou_span_a'] = ((df_hour['tenkan_sen'] + df_hour['kijun_sen']) / 2).shift(26)
                                df_hour['senkou_span_b'] = ((df_hour['high'].rolling(window=52).max() + df_hour['low'].rolling(window=52).min()) / 2).shift(26)
                                df_hour['chikou_span'] = df_hour['close'].shift(-26)
                                if df_hour.iloc[-1]['low'] > min(df_hour.iloc[-1]['senkou_span_a'], df_hour.iloc[-1]['senkou_span_b']):
                                    #print(ticker,": 1시간봉 매매, 구름떼 위")

                                    if df_hour.iloc[-1]["close"] + df_hour.iloc[-1]["upper"] > 0:
                                        # 밴드 상단 돌파 조건 해제
                                        # 시봉 CCI 계산
                                        tp = df_hour["close"]
                                        ma = tp.rolling(9).mean()
                                        md = tp.rolling(9).apply(lambda x: np.fabs(x - x.mean()).mean())
                                        df_hour["CCI"] = (tp - ma) / (0.015 * md)
                                        
                                        
                                        if df_hour.iloc[-1]["CCI"] >= 100 and df_hour.iloc[-1]["close"] > df_hour.iloc[-1]["open"]:
                                           
                                           
                                            # 10일 평균 거래량을 계산합니다.
                                           vol10 = df_hour["volume"].rolling(10).mean()
                                            # 현재 거래량을 가져옵니다.
                                           volume = df_hour.iloc[-1]["volume"]
                                            # 현재 거래량이 10일 평균 거래량보다 높은지 확인합니다.         # df -1행의 alow열 값이 True인지 확인합니다.
                                            
                                            
                                           tp_day = df_day["close"]
                                           ma_day = tp_day.rolling(9).mean()
                                           md_day = tp_day.rolling(9).apply(lambda x: np.fabs(x - x.mean()).mean())
                                           df_day["CCI"] = (tp_day - ma_day) / (0.015 * md_day)
                                            
                                           if volume > vol10.iloc[-2]*2 and df_day.iloc[-2]["CCI"] >= 0  and df_hour.iloc[-2]["CCI"] <= 100: #파동 중간 진입 방지용: #여기다 일봉 cci0이상 걸자
                                               # 10 거래량이평의 4배는 되어야 횡보, 3파, 5파를 거를 수 있다.
                                                                                            
                                               hour_result.append(ticker)
                                           else:
                                                continue
                                                                                            
                                        else:
                                            continue
                                        
                                    else:
                                        continue
                                        
                                else:
                                    continue
                            else:
                                continue
                        else:
                            continue
                    else:
                    # 에러 처리
                    #print("3번 if에서 에러 발생")    
                        continue
                else:
                    # 에러 처리
                    #print("df_hour nonetype 에러 발생")
                    continue
            
            else:
                # 에러 처리
                #print("df nonetype 에러 발생")
                continue
        else:
            continue
            
            
        # 결과 리스트를 반환합니다.
        return hour_result


             
def find_day_coin():
    # 원화 마켓에 있는 모든 코인의 티커를 가져옵니다.
    tickers = pyupbit.get_tickers(fiat="KRW")
    # 결과를 저장할 빈 리스트를 만듭니다.
    #global day_result
    day_result = []
    # 각 코인에 대해 반복합니다.
    for ticker in tickers:
        # 코인의 10일간의 시간봉 데이터를 가져옵니다.
        #################################################################
        time.sleep(0.1)
        df = pyupbit.get_ohlcv(ticker,"month",200,None,0.1)
        if df is not None:

            low_min = df["low"].rolling(window=5).min()
            high_max = df["high"].rolling(window=5).max()

            df["%k_fast"] = 100 * (df["close"] - low_min) / (high_max - low_min)
            df["%d_fast"] = df["%k_fast"].rolling(window=3).mean()

            df["%k_slow"] = df["%d_fast"]
            df["%d_slow"] = df["%k_slow"].rolling(window=3).mean()
            # alow 열(12열)을 추가하고, %d_slow 값이 한칸 위 행의 값보다 크면 True, 아니면 False를 할당합니다.
            df['allow'] = np.where(df['%d_slow'].shift(+1) < df['%d_slow'], True, False)
            # alow열이 True이거나, 월봉 스토 slow가 존재하지 않거나.
            if df.iloc[-1].loc['allow'] == True or np.isnan(df.iloc[-1].loc["%d_slow"]) == True:
                               
                    #주봉 일목균형표 선행스팬보다 종가가 높은 코인 찾기
                df_week = pyupbit.get_ohlcv(ticker,"week",200,None,0.1)
                if df_week is not None:
                    
                    df_week['high_low'] = (df_week['high'] + df_week['low']) / 2
                    df_week['tenkan_sen'] = (df_week['high'].rolling(window=9).max() + df_week['low'].rolling(window=9).min()) / 2
                    df_week['kijun_sen'] = (df_week['high'].rolling(window=26).max() + df_week['low'].rolling(window=26).min()) / 2
                    df_week['senkou_span_a'] = ((df_week['tenkan_sen'] + df_week['kijun_sen']) / 2).shift(26)
                    df_week['senkou_span_b'] = ((df_week['high'].rolling(window=52).max() + df_week['low'].rolling(window=52).min()) / 2).shift(26)
                    df_week['chikou_span'] = df_week['close'].shift(-26)
            # 주봉 구름떼 위거나 선행스팬이 존재하지 않거나.
                    if df_week.iloc[-1]['low'] > max(df_week.iloc[-1]['senkou_span_a'], df_week.iloc[-1]['senkou_span_b']) or np.isnan(df_week.iloc[-1]['senkou_span_a']) == True:
            
                        ################이하는 일봉으로 df_day를 다시 설정함. 위는 주봉df
                
                        df_day = pyupbit.get_ohlcv(ticker,"day",200,None,0.1)
                        
                        if df_day is not None:
                            
                    # 볼린저 밴드 계산
                            df_day["MA20"] = df_day["close"].rolling(20).mean()
                            df_day["stddev"] = df_day["close"].rolling(20).std()
                            df_day["upper"] = df_day["MA20"] + (df_day["stddev"] * 2)
                            df_day["lower"] = df_day["MA20"] - (df_day["stddev"] * 2)
                            df_day["bandwidth"] = (df_day["upper"] - df_day["lower"]) / df_day["MA20"]

                    

                    # 조건 순차 계산. 밴드폭이 이거보다 크다면 매매 접는다.
                            if df_day.iloc[-2]["bandwidth"] <= 1.5:
                                
                                #print(df_day.iloc[-2]["bandwidth"])
                                # 시봉 구름떼 위어야 한다.
                                df_day['high_low'] = (df_day['high'] + df_day['low']) / 2
                                df_day['tenkan_sen'] = (df_day['high'].rolling(window=9).max() + df_day['low'].rolling(window=9).min()) / 2
                                df_day['kijun_sen'] = (df_day['high'].rolling(window=26).max() + df_day['low'].rolling(window=26).min()) / 2
                                df_day['senkou_span_a'] = ((df_day['tenkan_sen'] + df_day['kijun_sen']) / 2).shift(26)
                                df_day['senkou_span_b'] = ((df_day['high'].rolling(window=52).max() + df_day['low'].rolling(window=52).min()) / 2).shift(26)
                                df_day['chikou_span'] = df_day['close'].shift(-26)
                                if df_day.iloc[-1]['low'] > min(df_day.iloc[-1]['senkou_span_a'], df_day.iloc[-1]['senkou_span_b']):
                                    #print(ticker,": 1시간봉 매매, 구름떼 위")

                                    if df_day.iloc[-1]["close"] + df_day.iloc[-1]["upper"] > 0:
                                        # 밴드 상단 돌파 조건 해제.
                                        # 시봉 CCI 계산
                                        tp = df_day["close"]
                                        ma = tp.rolling(9).mean()
                                        md = tp.rolling(9).apply(lambda x: np.fabs(x - x.mean()).mean())
                                        df_day["CCI"] = (tp - ma) / (0.015 * md)
                                        if df_day.iloc[-1]["CCI"] >= 100 and df_day.iloc[-1]["close"] > df_day.iloc[-1]["open"]:  
                                           
                                            
                                            # 10일 평균 거래량을 계산합니다.
                                           vol10 = df_day["volume"].rolling(10).mean()
                                            # 현재 거래량을 가져옵니다.
                                           volume = df_day.iloc[-1]["volume"]
                                            # 현재 거래량이 10일 평균 거래량보다 높은지 확인합니다.         # df -1행의 alow열 값이 True인지 확인합니다.
                                            
                                            #여기다 전 주봉 cci>0이상 걸자. 최소한의 추세 확인용이다.
                                           tp_week = df_week["close"]
                                           ma_week = tp_week.rolling(9).mean()
                                           md_week = tp_week.rolling(9).apply(lambda x: np.fabs(x - x.mean()).mean())
                                           df_week["CCI"] = (tp_week - ma_week) / (0.015 * md_week)
                                            
                                           if volume > vol10.iloc[-2]*2 and df_week.iloc[-2]["CCI"] >= 0  and df_day.iloc[-2]["CCI"] <= 100: #파동 중간 진입 방지용:
                                               # 10 거래량이평의 4배는 되어야 횡보, 3파, 5파를 거를 수 있다.
                                                                                            
                                               day_result.append(ticker)
                                           else:
                                                continue
                                                                                            
                                        else:
                                            continue
                                        
                                    else:
                                        continue
                                        
                                else:
                                    continue
                            else:
                                continue
                        else:
                            continue
                    else:
                    # 에러 처리
                    #print("3번 if에서 에러 발생")    
                        continue
                else:
                    # 에러 처리
                    #print("df_hour nonetype 에러 발생")
                    continue
            
            else:
                # 에러 처리
                #print("df nonetype 에러 발생")
                continue
        else:
            continue
            
            
        # 결과 리스트를 반환합니다.
        return day_result



def day_trading(): # 시봉 매매 함수
    signal_time = datetime.now() # 현재 시간을 변수에 할당
    day_coin = day_result[0]     
    
    df_day = pyupbit.get_ohlcv(day_coin,"day",200,None,0.1)
                        
    while df_day is None:
        df_day = pyupbit.get_ohlcv(day_coin,"day",200,None,0.1)
                            
                    # 볼린저 밴드 계산
    df_day["MA20"] = df_day["close"].rolling(20).mean()
    df_day["stddev"] = df_day["close"].rolling(20).std()
    df_day["upper"] = df_day["MA20"] + (df_day["stddev"] * 2)
    df_day["lower"] = df_day["MA20"] - (df_day["stddev"] * 2)
    df_day["bandwidth"] = (df_day["upper"] - df_day["lower"]) / df_day["MA20"]
    
    budget = cash * 0.1 / df_day.iloc[-2]["bandwidth"]  * sf_betting_rate  #변동성(밴드폭)에 반비례해서 예산을 투입. 거기에 성공률 보정
    if budget >= cash:
        budget = cash * sf_betting_rate 
    
    print(budget)

    order = upbit.buy_market_order(day_coin, budget) # 시장가 매수 주문 (예산을 코인 개수로 나눠서 균등하게 투자)
    print(signal_time, order, day_coin," 매수 완료") # 주문 결과 출력
    
    balance = upbit.get_balance(day_coin) # 보유 코인 개수
    while balance is None  or balance <= 0.00008 : #이오스 보유수량 에러 필터용.
        balance = upbit.get_balance(day_coin) #평단가 받을 때까지 계속
        time.sleep(0.1)
    
    avg_buy_price = budget / balance # 평단가

        
    # Get the candle data for a ticker
    df_day = pyupbit.get_ohlcv(day_coin,"day",200,None,0.1)
    while df_day is None:
        df_day = pyupbit.get_ohlcv(day_coin,"day",200,None,0.1) # df_day 받을 때까지
        time.sleep(0.1)
    # Calculate the 20-day SMA
    df_day['SMA'] = df_day['close'].rolling(20).mean()

    # Calculate the standard deviation of the closing prices
    df_day['std'] = df_day['close'].rolling(20).std()

    # Calculate the upper and lower bands
    df_day['upper'] = df_day['SMA'] + 2 * df_day['std']
    df_day['lower'] = df_day['SMA'] - 2 * df_day['std']

    # Calculate the BBW
    df_day['BBW'] = (df_day['upper'] - df_day['lower']) / df_day['SMA']

    stop_loss = df_day.iloc[-2]["BBW"]*0.5 # 직전 봉의 BBW를 구해서, 손절폭으로 정하자.
    
    stop_loss_price = avg_buy_price * (1-stop_loss) # stop_loss를 튜플로 안하더라도 df 갱신 시 바뀌지 않는다. 걱정 ㄴㄴ
    
 
    #stop_loss_price = 27400
    print("평단가: ",avg_buy_price,"손절가: ",stop_loss_price,"손절률: ",stop_loss, "직전봉 BBW: ",df_day.iloc[-2]["BBW"])
    
    # KRW-BTC 종목의 현재가와 평단가 조회
    
    time.sleep(0.1)
    # 현재가가 평단가의 -5% 이하인지 비교
    if df_day.iloc[-1]["close"] <= stop_loss_price:
    # 시장가 매도 주문
        
       
        order = upbit.sell_market_order(day_coin, balance) # 시장가 매도 주문
        time.sleep(0.1)
        signal_time = datetime.now() # 현재 시간을 변수에 할당
           
        print(signal_time,"   ",day_coin," 손절",order) # 주문 결과 출력
           
       
    else:
        #초기 와일 시동용 조건(매수 직후 현 파동 CCI 상승기)
        #아래 와일이 돌아가는 동안에도 스탑로스 이하로 오는지는 계속 점검해야 한다!-------------------------
        
        df_day = pyupbit.get_ohlcv(day_coin,"day",200,None,0.1)
        
        while df_day is None:
            df_day = pyupbit.get_ohlcv(day_coin,"day",200,None,0.1) # df_day 받을 때까지
            time.sleep(0.1)
        tp = df_day["close"]
        ma = tp.rolling(9).mean()
        md = tp.rolling(9).apply(lambda x: np.fabs(x - x.mean()).mean())
        df_day["CCI"] = (tp - ma) / (0.015 * md)
        
        print("현 파동 CCI 상승중")
        
        #첫 파동의 전봉에서 CCI감소하는 경우를 대비해 이 와일을 넣는다.
        while df_day.iloc[-1]["CCI"]>=df_day.iloc[-2]["CCI"] and balance >= 0.00008:    #검출 시점에서 CCI가 계속 상승하는지 점검
                                
               
            df_day = pyupbit.get_ohlcv(day_coin,"day",200,None,0.1)
            time.sleep(0.1)
            
            while df_day is None:
                df_day = pyupbit.get_ohlcv(day_coin,"day",200,None,0.1) # df_day 받을 때까지
                time.sleep(0.1)
            tp = df_day["close"]
            ma = tp.rolling(9).mean()
            md = tp.rolling(9).apply(lambda x: np.fabs(x - x.mean()).mean())
            df_day["CCI"] = (tp - ma) / (0.015 * md)
            
            # while 돌아가는 동안 손절 감시
            if df_day.iloc[-1]["close"] <= stop_loss_price:
            # 시장가 매도 주문
               order = upbit.sell_market_order(day_coin, balance) # 시장가 매도 주문
               
               signal_time = datetime.now() # 현재 시간을 변수에 할당
               
               print(signal_time,"   ",day_coin," 손절",order) # 주문 결과 출력
               
               break
               
            elif df_day.iloc[-2]["CCI"] < 0: #봉 종결 시 추세가 꺾였다면 언제든 시장가 매도해야 한다.
            # 시장가 매도 주문
               order = upbit.sell_market_order(hour_coin, balance) # 시장가 매도 주문
               
               signal_time = datetime.now() # 현재 시간을 변수에 할당
               
               print(signal_time,"   ",hour_coin," - 추세 꺾임. 포지션 정리",order) # 주문 결과 출력
               
               break
               
               
            else:
                continue       
        
        
                
        
        
        while df_day.iloc[-2]["CCI"]>=df_day.iloc[-3]["CCI"] and balance >= 0.00008:    #봉 종료 후에 지켜봐야       
                #CCI가 상승하는지 계속 감시
                
               
            df_day = pyupbit.get_ohlcv(day_coin,"day",200,None,0.1)
            time.sleep(0.1)
            
            while df_day is None:
                df_day = pyupbit.get_ohlcv(day_coin,"day",200,None,0.1) # df_day 받을 때까지
                time.sleep(0.1)
            tp = df_day["close"]
            ma = tp.rolling(9).mean()
            md = tp.rolling(9).apply(lambda x: np.fabs(x - x.mean()).mean())
            df_day["CCI"] = (tp - ma) / (0.015 * md)
            
            # while 돌아가는 동안 손절 감시
            if df_day.iloc[-1]["close"] <= stop_loss_price:
            # 시장가 매도 주문
               order = upbit.sell_market_order(day_coin, balance) # 시장가 매도 주문
               
               signal_time = datetime.now() # 현재 시간을 변수에 할당
               
               print(signal_time,"   ",day_coin," 손절",order) # 주문 결과 출력
               
               break
               
            elif df_day.iloc[-2]["CCI"] < 0: #봉 종결 시 추세가 꺾였다면 언제든 시장가 매도해야 한다.
            # 시장가 매도 주문
               order = upbit.sell_market_order(hour_coin, balance) # 시장가 매도 주문
               
               signal_time = datetime.now() # 현재 시간을 변수에 할당
               
               print(signal_time,"   ",hour_coin," - 추세 꺾임. 포지션 정리",order) # 주문 결과 출력   

               break               
               
               
            else:
                continue
            

        
        print("현 파동 CCI 하강 시작")
        #이 이하는 전 봉의 CCI가 전전봉의 CCI보다 작다는 뜻. 즉 CCI가 꺾여 하강중임을 뜻함.
        
        while df_day.iloc[-2]["CCI"]<=df_day.iloc[-3]["CCI"] and balance >= 0.00008:    #봉 종료 후에 지켜봐야       
                #CCI가 하강하는 동안 지속
            df_day = pyupbit.get_ohlcv(day_coin,"day",200,None,0.1)
            time.sleep(0.1)
            
            while df_day is None:
                df_day = pyupbit.get_ohlcv(day_coin,"day",200,None,0.1) # df_day 받을 때까지
                time.sleep(0.1)
            tp = df_day["close"]
            ma = tp.rolling(9).mean()
            md = tp.rolling(9).apply(lambda x: np.fabs(x - x.mean()).mean())
            df_day["CCI"] = (tp - ma) / (0.015 * md)
            
            # while 돌아가는 동안 손절 감시
            if df_day.iloc[-1]["close"] <= stop_loss_price:
            # 시장가 매도 주문
               order = upbit.sell_market_order(day_coin, balance) # 시장가 매도 주문
               
               signal_time = datetime.now() # 현재 시간을 변수에 할당
               
               print(signal_time,"   ",day_coin," 손절",order) # 주문 결과 출력
               
               break
               
            elif df_day.iloc[-2]["CCI"] < 0: #봉 종결 시 추세가 꺾였다면 언제든 시장가 매도해야 한다.
            # 시장가 매도 주문
               order = upbit.sell_market_order(hour_coin, balance) # 시장가 매도 주문
               
               signal_time = datetime.now() # 현재 시간을 변수에 할당
               
               print(signal_time,"   ",hour_coin," - 추세 꺾임. 포지션 정리",order) # 주문 결과 출력     
               
               break
        
               
            else:
                continue
            #-----------------------------------------------------------------------------------------------


        
        
        print("다음 파동 CCI 상승 시작, 회광반조 감시중")
            
            #이제 다시 CCI가 상승하는 동안 while 돌리자
        while df_day.iloc[-2]["CCI"]>=df_day.iloc[-3]["CCI"] and balance >= 0.00008:    #봉 종료 후에 지켜봐야       
                #CCI가 상승하는 동안 지속
            df_day = pyupbit.get_ohlcv(day_coin,"day",200,None,0.1)
            time.sleep(0.1)
            
            while df_day is None:
                df_day = pyupbit.get_ohlcv(day_coin,"day",200,None,0.1) # df_day 받을 때까지
                time.sleep(0.1)
            tp = df_day["close"]
            ma = tp.rolling(9).mean()
            md = tp.rolling(9).apply(lambda x: np.fabs(x - x.mean()).mean())
            df_day["CCI"] = (tp - ma) / (0.015 * md)
            
            # while 돌아가는 동안 손절 감시
            if df_day.iloc[-1]["close"] <= stop_loss_price:
            # 시장가 매도 주문
               order = upbit.sell_market_order(day_coin, balance) # 시장가 매도 주문
               
               signal_time = datetime.now() # 현재 시간을 변수에 할당
               
               print(signal_time,"   ",day_coin," 손절",order) # 주문 결과 출력
               
               break
            
            elif df_day.iloc[-2]["CCI"] < 0: #봉 종결 시 추세가 꺾였다면 언제든 시장가 매도해야 한다.
            # 시장가 매도 주문
               order = upbit.sell_market_order(hour_coin, balance) # 시장가 매도 주문
               
               signal_time = datetime.now() # 현재 시간을 변수에 할당
               
               print(signal_time,"   ",hour_coin," - 추세 꺾임. 포지션 정리",order) # 주문 결과 출력   
               
               break

                        
            # 이하 CCI 200 급등 시 매도 코드. 현 시간+1이면서 분은 0인 때 매도. 다만 실시간으로 손절가 이하 시 손절해야
            
            
            elif df_day.iloc[-1]["CCI"] >= 200: # 2차 파동에서 CCI200 이상의 급등(회광반조)이 오면 정각에 시장가 매도
            
                time.sleep(0.1)
                now = datetime.now()
                # 현재 시각의 분과 초를 구합니다.
                starting_hour = now.hour
                hour = now.hour
                while starting_hour == hour: # 시간 단위가 동일할 동안에만 와일 가동. 시간 단위가 달라지면 와일 탈출 후 익절!
                    now = datetime.now()
                    hour = now.hour
                    time.sleep(0.1)
                    
                    df_day = pyupbit.get_ohlcv(day_coin,"day",200,None,0.1) # 이하 손절 감시를 위한 df 최신화
                    time.sleep(0.1)
                    
                    while df_day is None:
                        df_day = pyupbit.get_ohlcv(day_coin,"day",200,None,0.1) # df_day 받을 때까지
                        time.sleep(0.1)
                    tp = df_day["close"]
                    ma = tp.rolling(9).mean()
                    md = tp.rolling(9).apply(lambda x: np.fabs(x - x.mean()).mean())
                    df_day["CCI"] = (tp - ma) / (0.015 * md)
                    
                    
                    # while 돌아가는 동안 손절 감시
                    if df_day.iloc[-1]["close"] <= stop_loss_price:
                    # 시장가 매도 주문
                       order = upbit.sell_market_order(day_coin, balance) # 시장가 매도 주문
                       
                       signal_time = datetime.now() # 현재 시간을 변수에 할당
                       
                       print(signal_time,"   ",day_coin," 손절",order) # 주문 결과 출력
                       
                       break
                
                       
                    else:
                       continue
                
                order = upbit.sell_market_order(day_coin, balance) # 시장가 매도 주문
                
                signal_time = datetime.now() # 현재 시간을 변수에 할당
                
                print(signal_time,"   ",day_coin," 2차 파동 CCI100 이상 익절",order) # 주문 결과 출력
               
               
            else:
                continue
            #-----------------------------------------------------------------------------------------------


        
        print("CCI 꺾임, 회광반조 감시중")

        
        #이제 음봉이 뜨는지 체크하자. 양봉일 때만 while이 돈다. 음봉이 뜨면 while 탈출
        while df_day.iloc[-2]["close"] >= df_day.iloc[-2]["open"] and balance >= 0.00008:
            df_day = pyupbit.get_ohlcv(day_coin,"day",200,None,0.1)
            time.sleep(0.1)
            
            while df_day is None:
                df_day = pyupbit.get_ohlcv(day_coin,"day",200,None,0.1) # df_day 받을 때까지
                time.sleep(0.1)
        
            tp = df_day["close"]
            ma = tp.rolling(9).mean()
            md = tp.rolling(9).apply(lambda x: np.fabs(x - x.mean()).mean())
            df_day["CCI"] = (tp - ma) / (0.015 * md)
        
            # while 돌아가는 동안 손절 감시
            if df_day.iloc[-1]["close"] <= stop_loss_price:
            # 시장가 매도 주문
               order = upbit.sell_market_order(day_coin, balance) # 시장가 매도 주문
               
               signal_time = datetime.now() # 현재 시간을 변수에 할당
               
               print(signal_time,"   ",day_coin," 손절",order) # 주문 결과 출력
               
               break
            
            elif df_day.iloc[-2]["CCI"] < 0: #봉 종결 시 추세가 꺾였다면 언제든 시장가 매도해야 한다.
            # 시장가 매도 주문
               order = upbit.sell_market_order(hour_coin, balance) # 시장가 매도 주문
               
               signal_time = datetime.now() # 현재 시간을 변수에 할당
               
               print(signal_time,"   ",hour_coin," - 추세 꺾임. 포지션 정리",order) # 주문 결과 출력
               
               break
            
           
            
            # 이하 CCI 200 급등 시 매도 코드. 현 시간+1이면서 분은 0인 때 매도. 다만 실시간으로 손절가 이하 시 손절해야
            
            
            elif df_day.iloc[-1]["CCI"] >= 100: # 2차 파동에서 CCI100 이상의 급등(회광반조)이 오면 정각에 시장가 매도
            
                time.sleep(0.1)
                now = datetime.now()
                # 현재 시각의 분과 초를 구합니다.
                starting_hour = now.hour
                hour = now.hour
                while starting_hour == hour: # 시간 단위가 동일할 동안에만 와일 가동. 시간 단위가 달라지면 와일 탈출 후 익절!
                    now = datetime.now()
                    hour = now.hour
                    time.sleep(0.1)
                    
                    df_day = pyupbit.get_ohlcv(day_coin,"day",200,None,0.1) # 이하 손절 감시를 위한 df 최신화
                    time.sleep(0.1)
                    
                    while df_day is None:
                        df_day = pyupbit.get_ohlcv(day_coin,"day",200,None,0.1) # df_day 받을 때까지
                        time.sleep(0.1)
                    tp = df_day["close"]
                    ma = tp.rolling(9).mean()
                    md = tp.rolling(9).apply(lambda x: np.fabs(x - x.mean()).mean())
                    df_day["CCI"] = (tp - ma) / (0.015 * md)
                    
                    
                    # while 돌아가는 동안 손절 감시
                    if df_day.iloc[-1]["close"] <= stop_loss_price:
                    # 시장가 매도 주문
                       order = upbit.sell_market_order(day_coin, balance) # 시장가 매도 주문
                       
                       signal_time = datetime.now() # 현재 시간을 변수에 할당
                       
                       print(signal_time,"   ",day_coin," 손절",order) # 주문 결과 출력
                       
                       break
                       
                       
                    else:
                       continue
                
                order = upbit.sell_market_order(day_coin, balance) # 시장가 매도 주문
                
                signal_time = datetime.now() # 현재 시간을 변수에 할당
                
                print(signal_time,"   ",day_coin," 2차 파동 CCI100 이상 익절",order) # 주문 결과 출력
               

               
               
            else:
                continue            
        
        print("음봉, 익절")

       
        
        # 모든 익절 조건 만족하였기 때문에 시장가 익절
        order = upbit.sell_market_order(day_coin, balance) # 시장가 매도 주문
        
        signal_time = datetime.now() # 현재 시간을 변수에 할당
        
        print(signal_time,"   ",day_coin," 익절",order) # 주문 결과 출력
        
        
 


def hour_trading(): # 시봉 매매 함수
    signal_time = datetime.now() # 현재 시간을 변수에 할당
    
    hour_coin = hour_result[0] 
    
    df_hour = pyupbit.get_ohlcv(hour_coin,"minute60",200,None,0.1)
                        
    while df_hour is None:
        df_hour = pyupbit.get_ohlcv(hour_coin,"minute60",200,None,0.1)
                            
                    # 볼린저 밴드 계산
    df_hour["MA20"] = df_hour["close"].rolling(20).mean()
    df_hour["stddev"] = df_hour["close"].rolling(20).std()
    df_hour["upper"] = df_hour["MA20"] + (df_hour["stddev"] * 2)
    df_hour["lower"] = df_hour["MA20"] - (df_hour["stddev"] * 2)
    df_hour["bandwidth"] = (df_hour["upper"] - df_hour["lower"]) / df_hour["MA20"]
    
    budget = cash * 0.1 / df_hour.iloc[-2]["bandwidth"] * sf_betting_rate
    if budget >= cash:
        budget = cash * sf_betting_rate
    
    print(budget)
    
    order = upbit.buy_market_order(hour_coin, budget) # 시장가 매수 주문 (예산을 코인 개수로 나눠서 균등하게 투자)
    print(signal_time, order, hour_coin," 매수 완료") # 주문 결과 출력
    
    balance = upbit.get_balance(hour_coin) # 보유 코인 개수
    while balance is None  or balance <= 0.00008 : #이오스 보유수량 에러 필터용.
        balance = upbit.get_balance(hour_coin) #평단가 받을 때까지 계속
        time.sleep(0.1)
    
    avg_buy_price = budget / balance # 평단가
    
        
    # Get the candle data for a ticker
    df_hour = pyupbit.get_ohlcv(hour_coin,"minute60",200,None,0.1)
    while df_hour is None:
        df_hour = pyupbit.get_ohlcv(hour_coin,"minute60",200,None,0.1) # df_hour 받을 때까지
        time.sleep(0.1)
    # Calculate the 20-day SMA
    df_hour['SMA'] = df_hour['close'].rolling(20).mean()

    # Calculate the standard deviation of the closing prices
    df_hour['std'] = df_hour['close'].rolling(20).std()

    # Calculate the upper and lower bands
    df_hour['upper'] = df_hour['SMA'] + 2 * df_hour['std']
    df_hour['lower'] = df_hour['SMA'] - 2 * df_hour['std']

    # Calculate the BBW
    df_hour['BBW'] = (df_hour['upper'] - df_hour['lower']) / df_hour['SMA']

    stop_loss = df_hour.iloc[-2]["BBW"]*0.5 # 직전 봉의 BBW를 구해서, 손절폭으로 정하자.
    
    stop_loss_price = avg_buy_price * (1-stop_loss) # stop_loss를 튜플로 안하더라도 df 갱신 시 바뀌지 않는다. 걱정 ㄴㄴ
    
    
    #stop_loss_price = 27400
    print("평단가: ",avg_buy_price,"손절가: ",stop_loss_price,"손절률: ",stop_loss, "직전봉 BBW: ",df_hour.iloc[-2]["BBW"])
    
    # KRW-BTC 종목의 현재가와 평단가 조회

    time.sleep(0.1)
    # 현재가가 평단가의 -5% 이하인지 비교
    
    if df_hour.iloc[-1]["close"] <= stop_loss_price:
    # 시장가 매도 주문
       
       
       order = upbit.sell_market_order(hour_coin, balance) # 시장가 매도 주문
       time.sleep(0.1)
       signal_time = datetime.now() # 현재 시간을 변수에 할당
           
       print(signal_time,"   ",hour_coin," 손절",order) # 주문 결과 출력
       
                 
       
       
    else:
        #초기 와일 시동용 조건(매수 직후 현 파동 CCI 상승기)
        #아래 와일이 돌아가는 동안에도 스탑로스 이하로 오는지는 계속 점검해야 한다!-------------------------
        
        df_hour = pyupbit.get_ohlcv(hour_coin,"minute60",200,None,0.1)
        
        while df_hour is None:
            df_hour = pyupbit.get_ohlcv(hour_coin,"minute60",200,None,0.1) # df_hour 받을 때까지
            time.sleep(0.1)
        tp = df_hour["close"]
        ma = tp.rolling(9).mean()
        md = tp.rolling(9).apply(lambda x: np.fabs(x - x.mean()).mean())
        df_hour["CCI"] = (tp - ma) / (0.015 * md)
        
        print("현 파동 CCI 상승중")
        
        #첫 파동의 전봉에서 CCI감소하는 경우를 대비해 이 와일을 넣는다.
        while df_hour.iloc[-1]["CCI"] >= df_hour.iloc[-2]["CCI"] and balance >= 0.00008:    #검출 시점에서 CCI가 계속 상승하는지 점검
                                
            
            df_hour = pyupbit.get_ohlcv(hour_coin,"minute60",200,None,0.1)
            time.sleep(0.1)
            
            while df_hour is None:
                df_hour = pyupbit.get_ohlcv(hour_coin,"minute60",200,None,0.1) # df_hour 받을 때까지
                time.sleep(0.1)
            tp = df_hour["close"]
            ma = tp.rolling(9).mean()
            md = tp.rolling(9).apply(lambda x: np.fabs(x - x.mean()).mean())
            df_hour["CCI"] = (tp - ma) / (0.015 * md)
            
            # while 돌아가는 동안 손절 감시
            if df_hour.iloc[-1]["close"] <= stop_loss_price:
            # 시장가 매도 주문
               order = upbit.sell_market_order(hour_coin, balance) # 시장가 매도 주문
               
               signal_time = datetime.now() # 현재 시간을 변수에 할당
               
               print(signal_time,"   ",hour_coin," 손절",order) # 주문 결과 출력
               
               break
            
            elif df_hour.iloc[-2]["CCI"] < 0: #봉 종결 시 추세가 꺾였다면 언제든 시장가 매도해야 한다.
            # 시장가 매도 주문
               order = upbit.sell_market_order(hour_coin, balance) # 시장가 매도 주문
               
               signal_time = datetime.now() # 현재 시간을 변수에 할당
               
               print(signal_time,"   ",hour_coin," - 추세 꺾임. 포지션 정리",order) # 주문 결과 출력
               
               break
               
                              
               
            else:
                continue








        while df_hour.iloc[-2]["CCI"]>=df_hour.iloc[-3]["CCI"] and balance >= 0.00008:    #봉 종료 후에 지켜봐야       
                #CCI가 상승하는지 계속 감시
                
            
            df_hour = pyupbit.get_ohlcv(hour_coin,"minute60",200,None,0.1)
            time.sleep(0.1)
            
            while df_hour is None:
                df_hour = pyupbit.get_ohlcv(hour_coin,"minute60",200,None,0.1) # df_hour 받을 때까지
                time.sleep(0.1)
            tp = df_hour["close"]
            ma = tp.rolling(9).mean()
            md = tp.rolling(9).apply(lambda x: np.fabs(x - x.mean()).mean())
            df_hour["CCI"] = (tp - ma) / (0.015 * md)
            
            # while 돌아가는 동안 손절 감시
            if df_hour.iloc[-1]["close"] <= stop_loss_price:
            # 시장가 매도 주문
               order = upbit.sell_market_order(hour_coin, balance) # 시장가 매도 주문
               
               signal_time = datetime.now() # 현재 시간을 변수에 할당
               
               print(signal_time,"   ",hour_coin," 손절",order) # 주문 결과 출력
               
               break
               
            elif df_hour.iloc[-2]["CCI"] < 0: #봉 종결 시 추세가 꺾였다면 언제든 시장가 매도해야 한다.
            # 시장가 매도 주문
               order = upbit.sell_market_order(hour_coin, balance) # 시장가 매도 주문
               
               signal_time = datetime.now() # 현재 시간을 변수에 할당
               
               print(signal_time,"   ",hour_coin," - 추세 꺾임. 포지션 정리",order) # 주문 결과 출력
               
               break
               
               
            else:
                continue
            
            
        print("현 파동 CCI 하강 시작")
        #이 이하는 전 봉의 CCI가 전전봉의 CCI보다 작다는 뜻. 즉 CCI가 꺾여 하강중임을 뜻함.
        
        while df_hour.iloc[-2]["CCI"]<=df_hour.iloc[-3]["CCI"] and balance >= 0.00008:    #봉 종료 후에 지켜봐야       
                #CCI가 하강하는 동안 지속
            df_hour = pyupbit.get_ohlcv(hour_coin,"minute60",200,None,0.1)
            time.sleep(0.1)
            
            while df_hour is None:
                df_hour = pyupbit.get_ohlcv(hour_coin,"minute60",200,None,0.1) # df_hour 받을 때까지
                time.sleep(0.1)
            tp = df_hour["close"]
            ma = tp.rolling(9).mean()
            md = tp.rolling(9).apply(lambda x: np.fabs(x - x.mean()).mean())
            df_hour["CCI"] = (tp - ma) / (0.015 * md)
            
            # while 돌아가는 동안 손절 감시
            if df_hour.iloc[-1]["close"] <= stop_loss_price:
            # 시장가 매도 주문
               order = upbit.sell_market_order(hour_coin, balance) # 시장가 매도 주문
               
               signal_time = datetime.now() # 현재 시간을 변수에 할당
               
               print(signal_time,"   ",hour_coin," 손절",order) # 주문 결과 출력
               
               break
           
               
            
            elif df_hour.iloc[-2]["CCI"] < 0: #봉 종결 시 추세가 꺾였다면 언제든 시장가 매도해야 한다.
            # 시장가 매도 주문
               order = upbit.sell_market_order(hour_coin, balance) # 시장가 매도 주문
               
               signal_time = datetime.now() # 현재 시간을 변수에 할당
               
               print(signal_time,"   ",hour_coin," - 추세 꺾임. 포지션 정리",order) # 주문 결과 출력   
            
               break
             
            else:
                continue
            #-----------------------------------------------------------------------------------------------


    




        print("다음 파동 CCI 상승 시작, 회광반조 감시중")
            
            #이제 다시 CCI가 상승하는 동안 while 돌리자
        while df_hour.iloc[-2]["CCI"]>=df_hour.iloc[-3]["CCI"] and balance >= 0.00008:    #봉 종료 후에 지켜봐야       
                #CCI가 상승하는 동안 지속
            df_hour = pyupbit.get_ohlcv(hour_coin,"minute60",200,None,0.1)
            time.sleep(0.1)
            
            while df_hour is None:
                df_hour = pyupbit.get_ohlcv(hour_coin,"minute60",200,None,0.1) # df_hour 받을 때까지
                time.sleep(0.1)
            tp = df_hour["close"]
            ma = tp.rolling(9).mean()
            md = tp.rolling(9).apply(lambda x: np.fabs(x - x.mean()).mean())
            df_hour["CCI"] = (tp - ma) / (0.015 * md)
            
            # while 돌아가는 동안 손절 감시
            if df_hour.iloc[-1]["close"] <= stop_loss_price:
            # 시장가 매도 주문
               
               
               signal_time = datetime.now() # 현재 시간을 변수에 할당
               
               print(signal_time,"   ",hour_coin," 손절",order) # 주문 결과 출력
               
               break
               
            elif df_hour.iloc[-2]["CCI"] < 0: #봉 종결 시 추세가 꺾였다면 언제든 시장가 매도해야 한다.
            # 시장가 매도 주문
               order = upbit.sell_market_order(hour_coin, balance) # 시장가 매도 주문
               
               signal_time = datetime.now() # 현재 시간을 변수에 할당
               
               print(signal_time,"   ",hour_coin," - 추세 꺾임. 포지션 정리",order) # 주문 결과 출력
               
               break
               
            
                        
            # 이하 CCI 200 급등 시 매도 코드. 현 시간+1이면서 분은 0인 때 매도. 다만 실시간으로 손절가 이하 시 손절해야
            
            
            elif df_hour.iloc[-1]["CCI"] >= 200: # 2차 파동에서 CCI200 이상의 급등(회광반조)이 오면 정각에 시장가 매도
            
                time.sleep(0.1)
                now = datetime.now()
                # 현재 시각의 분과 초를 구합니다.
                starting_hour = now.hour
                hour = now.hour
                while starting_hour == hour: # 시간 단위가 동일할 동안에만 와일 가동. 시간 단위가 달라지면 와일 탈출 후 익절!
                    now = datetime.now()
                    hour = now.hour
                    time.sleep(0.1)
                    
                    df_hour = pyupbit.get_ohlcv(day_coin,"day",200,None,0.1) # 이하 손절 감시를 위한 df 최신화
                    time.sleep(0.1)
                    
                    while df_hour is None:
                        df_hour = pyupbit.get_ohlcv(day_coin,"day",200,None,0.1) # df_hour 받을 때까지
                        time.sleep(0.1)
                    tp = df_hour["close"]
                    ma = tp.rolling(9).mean()
                    md = tp.rolling(9).apply(lambda x: np.fabs(x - x.mean()).mean())
                    df_hour["CCI"] = (tp - ma) / (0.015 * md)
                    
                    
                    # while 돌아가는 동안 손절 감시
                    if df_hour.iloc[-1]["close"] <= stop_loss_price:
                    # 시장가 매도 주문
                       order = upbit.sell_market_order(day_coin, balance) # 시장가 매도 주문
                       
                       signal_time = datetime.now() # 현재 시간을 변수에 할당
                       
                       print(signal_time,"   ",day_coin," 손절",order) # 주문 결과 출력
                       
                       break
                       
                   
                    elif df_hour.iloc[-2]["CCI"] < 0: #봉 종결 시 추세가 꺾였다면 언제든 시장가 매도해야 한다.
                    # 시장가 매도 주문
                       order = upbit.sell_market_order(hour_coin, balance) # 시장가 매도 주문
                       
                       signal_time = datetime.now() # 현재 시간을 변수에 할당
                       
                       print(signal_time,"   ",hour_coin," - 추세 꺾임. 포지션 정리",order) # 주문 결과 출력 
                       
                       break
                   
                       
                    else:
                       continue
                
                order = upbit.sell_market_order(day_coin, balance) # 시장가 매도 주문
                
                signal_time = datetime.now() # 현재 시간을 변수에 할당
                
                print(signal_time,"   ",day_coin," 2차 파동 CCI100 이상 익절",order) # 주문 결과 출력
               
               
            else:
                continue
            #-----------------------------------------------------------------------------------------------
 
               
            
        
        print("CCI 꺾임, 회광반조 감시중")
        
        #이제 음봉이 뜨는지 체크하자. 양봉일 때만 while이 돈다. 음봉이 뜨면 while 탈출
        while df_hour.iloc[-2]["close"] >= df_hour.iloc[-2]["open"] and balance >= 0.00008:
            df_hour = pyupbit.get_ohlcv(hour_coin,"minute60",200,None,0.1)
            time.sleep(0.1)
            
            while df_hour is None:
                df_hour = pyupbit.get_ohlcv(hour_coin,"minute60",200,None,0.1) # df_hour 받을 때까지
                time.sleep(0.1)

            tp = df_hour["close"]
            ma = tp.rolling(9).mean()
            md = tp.rolling(9).apply(lambda x: np.fabs(x - x.mean()).mean())
            df_hour["CCI"] = (tp - ma) / (0.015 * md)
            
            # while 돌아가는 동안 손절 감시
            if df_hour.iloc[-1]["close"] <= stop_loss_price:
            # 시장가 매도 주문
               order = upbit.sell_market_order(hour_coin, balance) # 시장가 매도 주문
               
               signal_time = datetime.now() # 현재 시간을 변수에 할당
               
               print(signal_time,"   ",hour_coin," 손절",order) # 주문 결과 출력
               
               break
            
            elif df_hour.iloc[-2]["CCI"] < 0: #봉 종결 시 추세가 꺾였다면 언제든 시장가 매도해야 한다.
            # 시장가 매도 주문
               order = upbit.sell_market_order(hour_coin, balance) # 시장가 매도 주문
               
               signal_time = datetime.now() # 현재 시간을 변수에 할당
               
               print(signal_time,"   ",hour_coin," - 추세 꺾임. 포지션 정리",order) # 주문 결과 출력   
               
               break
            
            
            # 이하 CCI 200 급등 시 매도 코드. 현 시간+1이면서 분은 0인 때 매도. 다만 실시간으로 손절가 이하 시 손절해야
            
            
            elif df_hour.iloc[-1]["CCI"] >= 100: # 2차 파동에서 CCI100 이상의 급등(회광반조)이 오면 정각에 시장가 매도
            
                time.sleep(0.1)
                now = datetime.now()
                # 현재 시각의 분과 초를 구합니다.
                starting_hour = now.hour
                hour = now.hour
                while starting_hour == hour: # 시간 단위가 동일할 동안에만 와일 가동. 시간 단위가 달라지면 와일 탈출 후 익절!
                    now = datetime.now()
                    hour = now.hour
                    time.sleep(0.1)
                    
                    df_hour = pyupbit.get_ohlcv(day_coin,"day",200,None,0.1) # 이하 손절 감시를 위한 df 최신화
                    time.sleep(0.1)
                    
                    while df_hour is None:
                        df_hour = pyupbit.get_ohlcv(day_coin,"day",200,None,0.1) # df_hour 받을 때까지
                        time.sleep(0.1)
                    tp = df_hour["close"]
                    ma = tp.rolling(9).mean()
                    md = tp.rolling(9).apply(lambda x: np.fabs(x - x.mean()).mean())
                    df_hour["CCI"] = (tp - ma) / (0.015 * md)
                    
                    
                    # while 돌아가는 동안 손절 감시
                    if df_hour.iloc[-1]["close"] <= stop_loss_price:
                    # 시장가 매도 주문
                       order = upbit.sell_market_order(day_coin, balance) # 시장가 매도 주문
                       
                       signal_time = datetime.now() # 현재 시간을 변수에 할당
                       
                       print(signal_time,"   ",day_coin," 손절",order) # 주문 결과 출력
                       
                       break
                    
                    else:
                       continue
                
                order = upbit.sell_market_order(day_coin, balance) # 시장가 매도 주문
                
                signal_time = datetime.now() # 현재 시간을 변수에 할당
                
                print(signal_time,"   ",day_coin," 2차 파동 CCI100 이상 익절",order) # 주문 결과 출력
               
               
               
            else:
               
                continue            
        
        print("음봉, 익절")

          
        
        # 모든 익절 조건 만족하였기 때문에 시장가 익절
        order = upbit.sell_market_order(hour_coin, balance) # 시장가 매도 주문
        
        signal_time = datetime.now() # 현재 시간을 변수에 할당
        
        print(signal_time,"   ",hour_coin," 익절",order) # 주문 결과 출력
        
 

while not hour_result and not day_result and day_coin is None and hour_coin is None and avg_buy_price is None and df_hour is None and df_day is None and balance is None: #영원히 돌아가게 한다. 왜냐면 hour_trading()이 최종적으로 hour_result=[]을 넣기 때문.
    while not hour_result and not day_result:
        
        day_result = find_day_coin() # 전역 변수로 day_result 제작
        if not day_result:
            hour_result = find_hour_coin() #일봉 코인 없을 경우만 전역 변수로 hour_result 제작
        
        time.sleep(0.1)
        signal_time = datetime.now() # 현재 시간을 변수에 할당
        
    # day_result나 hour_result가 구성되면 와일 탈출
                
    print("day_result: ",day_result,"day_coin: ",day_coin)
    print("hour_result: ",hour_result,"hour_coin: ",hour_coin)
    
    if day_result:
        day_trading()
        
    elif hour_result:
        hour_trading() # 시봉 코인 매매
        
    #-------------------------------------------이 이하는 매매 후 뒷처리
    ori_cash = cash # 매매 전 원금을 저장
    
    cash = upbit.get_balance("KRW") # 원화 갱신
    if ori_cash <= cash:
        sucess = sucess+1
    else:
        fail = fail+1
    sf_betting_rate = (1+sucess)/(1+fail)
    if sf_betting_rate >= 1:
        sf_betting_rate = 0.99 # 아무리 성공률이 높아도 0.99배 이하로 배팅하게.
    budget = cash* sf_betting_rate # 예산 갱신
    signal_time = datetime.now() # 현재 시간을 변수에 할당
    
 
    
    
    
    
    day_result=[]   # 대상 코인 목록들 초기화
    hour_result=[] # 대상 코인 목록들 초기화
    day_coin = None
    hour_coin= None
    avg_buy_price = None
    df_hour = None
    df_day = None
    balance = None
    

    print(signal_time, " 보유 현금: ",cash,"  예산: ",budget, "누적 수익금: ", cash-start_money, "누적 수익률: ",(cash-start_money)/start_money*100,"%", "성공 횟수: ",sucess, "실패 횟수: ",fail,"성공률: ",sucess/fail)
    print("day_result: ",day_result,"hour_result: ",hour_result,"day_coin: ",day_coin,"hour_coin: ",hour_coin,"avg_buy_price: ",avg_buy_price, "balance: ",balance)
    
    

#v3 대비
    #검출식에 나온 첫 코인에 몰빵 투자
    #CCI 100 달성 후 꺾임 구현
    #일봉 매매와 시봉 매매 구현
    #상위 매매 단위에서 전일 CCI가 0 이상이어야 매매 대상이 되도록 필터 추가.(상승추세 확인용)
#v4_day+hour 대비 
    #예산을 밴드폭에 반비례토록 수정. 밴드폭 10%에서 예산 최대
    #balance>0 일 때의 와일 제거
    #find_coin의 밴드 폭 조건 50%로 완화
    #2차 파동에서 CCI200 이상 급등 시 다음 정각에 시장가 매도
    #각종 변수들 와일 돌기 전후에 초기화([]이나 None으로) 설정
    
#23.04.17.
    #회광반조 코드 시점 한 칸씩 뒤로 적용(cci200 이상)
    #find 함수 내부에서 global 제거. 
    #맨 밑에서 find 함수 결과값을 result에 바인딩으로 대체
    #회광반조 코드 적용 전 CCI 갱신 적용.
    #전 봉의 시가나 고가 중 큰 값이 밴드 상단 이하도록 find_coin() 수정 - 고점에 물리는 것을 방지하기 위함.
    
#23. 04. 18.
    #회광반조 코드 내 datetime.datetime.now() 에러 해결
    #매수 직전봉에서 CCI 감소 추세였을 경우 곧바로 다음 파동으로 넘어가던 문제 해결
    #balance를 서버로부터 수령을 하지 않은 경우(0)에도 다음 코드로 넘어가는 에러 해결

#23.04.19.
    #마지막 ADMS 음수 조건 해제. 우리는 CCI100꺾 음봉에서 익절한다.
    #CCI[-2]<0일 때 무조건 손절 추가 : 추세를 이탈했다는 증거니까.
#23.04.19.2.
    #2차 파동이 CCI100이상에서 꺾이는 조건을 빼기. 2차 파동의 CCi가 100이상이든 아니든 2차 파동 꺾인 후 음봉이면 매도해야 한다.
    #엘리엇 5파 진입 방지를 위해 직전봉 10거래이평의 400%여야 진입토록 수정 
        # 10 거래량이평의 4배는 되어야 횡보, 3파, 5파를 거를 수 있다.
    #전봉의 시가나 종가가 밴드 상단 이하여야 한다는 조건 삭제. 10거래이평의 400% 돌파면 횡보, 3파, 5파 거를 수 있다.
    #가격 손절이나 추세 꺾임에 의한 손절 시 break 설정
    #find_coin()에서 양봉이어야만 하도록 조건 추가
#23.04.20.
    #손절이나 회광반조 발동 후 즉시 와일 탈출하여 find_coin()으로 바로 갈 수 있게, 각 첫 와일마다  and balance >= 0.00008 조건 추가
#23.04.21.
    #볼밴 상단 .01퍼 이하일 때 매수 조건을 취소. 일단 돌파했다면 안내려오는 게 강한 상승이니까.
    #거래량은 10이평의 300%로 바꾸자. 기회가 많아야 한다.
#23.04.22.
    # budget = cash * sf_betting_rate 로 해서 변동성을 통계에 기반하여 예산 편성케.
#23.04.23.
    #직전봉 CCI 100 이상이면 안들어가기 - 중간에 진입 막기위해
    #직전 10이평 거래량 2배로 수정 - 기회가 많아야. 너무 고가 진입 예방
    #회광반조 코드 cci100으로 수정. - 짧게 먹자.
    #밴드 상단 돌파 조건 해제(너무 꼭지에 물린다.)
    #회광반조 2차 파동 상승 중일 때만 CCI200에 정리. 2차 파동 하방에서는 CCI100으로도 정리되게.

    
#사용법
    #맨 위에 이런저런 변수 수동 입력
    
    
#개발 방향
    #추후 회광반조 코드가 cci100이냐 200이냐를 성공률에 연동되게
    #성공률 및 손익률을 얻어서 켈리 베팅 공식을 적용하자.
    #일단은 올인 투자로.
    #폰(노트10+)에서 자동으로 데이터쉐어링 통해 돌아갈 수 있도록 시스템 구축
    #AWS 사용?
    #10이평 거래량의 현재 2배인데 적정 거래량 배수를 찾아봐야겠다.
    #가급적 일봉 거래를 해보자.

#검토 후 폐기(안)


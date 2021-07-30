from datetime import datetime, timezone,date
import numpy as np
import datetime as dt
import requests
import pandas as pd
from pandas_datareader import data as pdr
from tkinter import Tk
from tkinter.filedialog import askopenfilename
import time
import pytz
import matplotlib.pyplot as plt
import talib
from config import client_id



'''Start date & end date as milliseconds since epoch. 
If startDate and endDate are provided, period should not be provided.'''

startyear = 2021
startmonth = 2
startday = 22
startDate = dt.date(startyear, startmonth, startday)
startDate = startDate.strftime('%Y-%m-%d %H:%M:%S+00:00')
startDate = dt.datetime.strptime(startDate, '%Y-%m-%d %H:%M:%S+00:00')
startDate = startDate.replace(tzinfo=pytz.utc)

epochTS=0
epoch=dt.datetime.fromtimestamp(epochTS, tz=timezone.utc)
#start date as milliseconds since epoch:
epochStart=(startDate - epoch).total_seconds()*1000 

#Current date in milliseconds since epoch
now=int(time.time()*1000)


root=Tk()
ftypes=[(".xlsm", ".xlsx", ".xls")]
ttl="Title"
dir1='~/Desktop'

filepath = askopenfilename(filetypes=ftypes, initialdir=dir1, title=ttl)
#filepath=open(os.path.expanduser("~/Desktop/candlestickscreenerpython/holdings-daily-us-en-spy.xlsx"))
#filepath=open(r"~/Desktop/candlestickscreenerpython/holdings-daily-us-en-spy.xlsx")

stocklist = pd.read_excel(filepath)
stocklist = stocklist.head(1)   #reads only 5 symbols from the top

def get_price_history(**kwargs):
    url=r'https://api.tdameritrade.com/v1/marketdata/{}/pricehistory'.format(kwargs.get('symbol'))
    key=client_id
    params={}
    params.update({'apikey':key})

    for arg in kwargs:
        parameter={arg: kwargs.get(arg)}
        params.update(parameter)
    
    return requests.get(url, params=params).json()

    '''Need to provide the following information
    symbol=stock, 
    periodType - Valid values are day, month, year, or ytd (year to date). Default is day.
    period - Valid periods by periodType (defaults marked with an asterisk): 
            day: 1, 2, 3, 4, 5, 10*; month: 1*, 2, 3, 6; year: 1*, 2, 3, 5, 10, 15, 20; ytd: 1*
    frequencyType - minute, daily, weekly or monthly
    frequency - 1 for daily, weekly and monthly frequencyType and '1, 5, 10, 15 & 30' for minute frequencyType
    endDate -  as milliseconds since epoch. If startDate and endDate are provided, period should not be provided.
    startDate - as milliseconds since epoch. If startDate and endDate are provided, period should not be provided.
    needExtendedHoursData - 'true' if required or 'false' if not required
    '''

# Function to create ATR
def wwma(values, n):
    """
     J. Welles Wilder's EMA: (alpha=1/n)
     Exponential moving average: (alpha=2/(1+n))
    """
    return values.ewm(alpha=2/(1+n), min_periods=n, adjust=False).mean()

def atr(Dframe, n):
    data = Dframe.copy()
    high = data['High']
    low = data['Low']
    close = data['Close']
    data['tr0'] = abs(high - low)
    data['tr1'] = abs(high - close.shift())
    data['tr2'] = abs(low - close.shift())
    tr = data[['tr0', 'tr1', 'tr2']].max(axis=1)
    atr = wwma(tr, n)
    return atr

# Function to calculate historical volatility
def HistVol(Dframe, ndays):
    window=ndays
    Data=Dframe.copy()
    close=Data['Close']
    log_ret = np.log(close).diff() 
    HistVolatility = log_ret.rolling(window).std()*(252**0.5) #Annualized
    return HistVolatility

#function to calculate expected move from Historic volatility
 
def HistVolExpMove(Dframe, ndays):
    Data=Dframe.copy()
    close=Data['Close']
    HV_ExpMove=(close.iloc[-1]*HistVol(Data, ndays))/(252**0.5)
    return HV_ExpMove

# Function to count nos of days from pivots
def periodCounter(dframe,col):
    counter=1
    nPeriod=[]
    dateloc=[]
    for i in range(len(dframe)-1):
        if np.isnan(dframe[col][i])==True:
            counter+=1
            if not np.isnan(dframe[col][i+1])==True:
                nPeriod.append(counter)
                dateloc.append(dframe['Date'][i+1])
                counter=1
    prdCounter=pd.DataFrame({'Date':dateloc,'NosPeriod':nPeriod})
    return prdCounter
    # print(nPeriodPH, datelocPH)

# Function to count nos of days from pivot low to pivot high
def periodCounter1(dframe,col1,col2):
    # col1 is pivot highs col and col2 is pivotlows col
    counterLH=1
    nPeriodLH=[]
    datelocLH=[]
    
    for i in range(len(dframe)-1):
        if np.isnan(dframe[col2][i])==True:
            counterLH+=1
            if np.isnan(dframe[col1][i+1])==False:
                nPeriodLH.append(counterLH)
                datelocLH.append(dframe['Date'][i+1])
                counterLH=1
    LHprd=pd.DataFrame({'Date':datelocLH,'L-HPrds':nPeriodLH})
    return LHprd

# Function to count nos of days from pivot low to pivot high
def periodCounter2(dframe,col1,col2):
    # col1 is pivot highs col and col2 is pivotlows col
    counterHL=1
    nPeriodHL=[]
    datelocHL=[]
    for i in range(len(dframe)-1):
        if np.isnan(dframe[col1][i])==True:
            counterHL+=1
            if np.isnan(dframe[col2][i+1])==False:
                nPeriodHL.append(counterHL)
                datelocHL.append(dframe['Date'][i+1])
                counterHL=1
    
    HLprd=pd.DataFrame({'Date':datelocHL,'H-LPrds':nPeriodHL})
    return HLprd

for i in stocklist.index:
    stock=stocklist["Ticker"][i]
    
    ph=get_price_history(symbol=stock, periodType='year', period='3', frequencyType='daily', frequency='1', endDate=now, needExtendedHoursData='false')
    df=pd.DataFrame(ph['candles'], columns=['datetime', 'open', 'high', 'low', 'close', 'volume'])
    df=df.rename(columns={'datetime':'Date','open':'Open','high':'High','low':'Low','close':'Close','volume':'Volume'})
    df.Date=pd.to_datetime(df.Date, unit='ms').dt.date
    # calculate and insert 9 EMA, 20, 50 & 200SMA column
    ema_9=df.Close.ewm(span=9, adjust=False).mean()
    sma_20=df.Close.rolling(20,win_type=None).mean()
    sma_50=df.Close.rolling(50,win_type=None).mean()
    sma_200=df.Close.rolling(200,win_type=None).mean()

    df.insert(6,'EMA_9',ema_9,False)
    df.insert(7,'SMA_20',sma_20,False)
    df.insert(8,'SMA_50',sma_50,False)
    df.insert(9,'SMA_200',sma_200,False)

    # calucate and insert RSI

    # identify supports & resistance pivot points

    pivotsHigh=[]
    pivotsLow=[]
    datesPH=[]
    datesPL=[]
    counterPH=0
    counterPL=0
    lastpivotHigh=0
    lastPivotLow=0
    RangePH = [0,0,0,0,0,0,0,0,0,0]
    daterangePH = [0,0,0,0,0,0,0,0,0,0]
    RangePL = [0,0,0,0,0,0,0,0,0,0]
    daterangePL = [0,0,0,0,0,0,0,0,0,0]
    #For Pivot Highs
    for i in df.index:
        currentMax = max(RangePH , default=0)
        valuePH=round(df["High"][i],2)
        RangePH=RangePH[1:9]
        RangePH.append(valuePH)
        daterangePH=daterangePH[1:9]
        daterangePH.append(df["Date"][i])
        if currentMax == max(RangePH , default=0):
            counterPH+=1
        else:
            counterPH = 0
        if counterPH ==  5:
            lastPivotHigh=currentMax
            datelocPH =RangePH.index(lastPivotHigh)
            lastDatePH = daterangePH[datelocPH]
            pivotsHigh.append(lastPivotHigh)
            datesPH.append(lastDatePH)

    # For Pivot Lows
    for i in df.index:
        currentMin = min(RangePL , default=0)
        valuePL=round(df["Low"][i],2)
        RangePL=RangePL[1:9]
        RangePL.append(valuePL)
        daterangePL=daterangePL[1:9]
        daterangePL.append(df["Date"][i])
        if currentMin == min(RangePL , default=0):
            counterPL+=1
        else:
            counterPL = 0
        if counterPL ==  5:
            lastPivotLow=currentMin
            datelocPL =RangePL.index(lastPivotLow)
            lastDatePL = daterangePL[datelocPL]
            pivotsLow.append(lastPivotLow)
            datesPL.append(lastDatePL)
    
    #Pivot High Data Frame
    ph={'Date':datesPH,'PivotHighs':pivotsHigh}
    ph=pd.DataFrame(data=ph)
    
    #Pivot Low Data Frame
    pl={'Date':datesPL,'PivotLows':pivotsLow}
    pl=pd.DataFrame(data=pl)
    pl = pl[pl.Date != 0] #to remove the date with zero in first row


    PivotHL=pd.concat([PivotHL.set_index('Date') for PivotHL in [ph, pl]], axis=1).rename_axis('Date').reset_index()
    # PivotHL=ph.merge(pl,how='outer',on='Date') #can use merge or concat functions.
    PivotHL.sort_values(['Date'],inplace=True,ignore_index=True)
    # Merge pivots table with price history
    PH_pivots=df.merge(PivotHL,how='outer',on='Date')
    PH_pivots.sort_values(['Date'],inplace=True,ignore_index=True)
    
    pivLH=periodCounter1(PH_pivots,col1='PivotHighs',col2='PivotLows')
    pivHL=periodCounter2(PH_pivots,col1='PivotHighs',col2='PivotLows')
    # prdcounter=pd.concat([rev1.set_index('Date'),rev2.set_index('Date')],axis=1).reset_index()
    # print(prdcounter)

    # countPivH=periodCounter(PH_pivots,col='PivotHighs').rename(columns={'Date':'Date','NosPeriod':'PrdLstPvtH'})
    # countPivL=periodCounter(PH_pivots,col='PivotLows').rename(columns={'Date':'Date','NosPeriod':'PrdLstPvtL'})

    PH_pivots=pd.concat([PH_pivots.set_index('Date'),pivLH.set_index('Date'),pivHL.set_index('Date')],axis=1).reset_index()

    #calculate ATR using the price history
    PH_pivots['ATR']=atr(PH_pivots,20)
    #calculate Historic Volatility using the price history
    PH_pivots['HisVol']=HistVol(PH_pivots,20)
    PH_pivots['HistVol_ExpMove']=HistVolExpMove(PH_pivots,20)

    # print(PH_pivots)
    
    # timeD = dt.timedelta(days=30)
    # df.plot(x='Date',y='High')
    # df.plot(x='Date',y='Low')
    
    #Plot for Pivot High
    # for index in range(len(pivotsHigh)):
    #     # print(str(pivotsHigh[index])+" :" +str(datesPH[index]))
        
    #     plt.plot_date([datesPH[index],datesPH[index]+timeD],
    #         [pivotsHigh[index],pivotsHigh[index]] , linestyle='-' , linewidth=2, marker=',')
    
    # Plot for Pivot Low
    # for index in range(len(pivotsLow)):
    #     print(str(pivotsLow[index])+" :" +str(datesPL[index])) #Ignore the date with zero (first row)
        
    #     # need to remove zero from pivotsLow and datesPL
    #     plt.plot_date([pl.Date,pl.Date+timeD],
    #         [pl.PivotLows,pl.PivotLows] , linestyle='-' , linewidth=2, marker=',')

    # plt.show()
    fname={'date':datetime.today().strftime('%Y%m%d'),'symbol':stock}
    PH_pivots.to_csv('datasets/daily/{}-{}.csv'.format(fname['date'],fname['symbol']), index=False)
import pandas as pd
from datetime import datetime, timezone, timedelta
import calendar

def get_klines_iter(symbol, interval, start, end = None, limit=1000):
    # start and end must be isoformat YYYY-MM-DD
    # We are using utc time zone

    # the maximum records is 1000 per each Binance API call

    df = pd.DataFrame()

    if start is None:
        print('start time must not be None')
        return
    start = calendar.timegm(datetime.fromisoformat(start).timetuple()) * 1000

    if end is None:
        dt = datetime.now(timezone.utc)
        utc_time = dt.replace(tzinfo=timezone.utc)
        end = int(utc_time.timestamp()) * 1000
        return
    else:
        end = calendar.timegm(datetime.fromisoformat(end).timetuple()) * 1000
    last_time = None

    while len(df) == 0 or (last_time is not None and last_time < end):
        url = 'https://api.binance.com/api/v3/klines?symbol=' + \
              symbol + '&interval=' + interval + '&limit=1000'
        if(len(df) == 0):
            url += '&startTime=' + str(start)
        else:
            url += '&startTime=' + str(last_time)

        url += '&endTime=' + str(end)
        df2 = pd.read_json(url)
        df2.columns = ['Opentime', 'Open', 'High', 'Low', 'Close', 'Volume', 'Closetime',
                       'Quote asset volume', 'Number of trades', 'Taker by base', 'Taker buy quote', 'Ignore']
        dftmp = pd.DataFrame()
        dftmp = pd.concat([df2, dftmp], axis=0, ignore_index=True, keys=None)

        dftmp.Opentime = pd.to_datetime(dftmp.Opentime, unit='ms')
        dftmp['Date'] = dftmp.Opentime.dt.strftime("%d/%m/%Y")
        dftmp['Time'] = dftmp.Opentime.dt.strftime("%H:%M:%S")
        dftmp = dftmp.drop(['Quote asset volume', 'Closetime', 'Opentime',
                      'Number of trades', 'Taker by base', 'Taker buy quote', 'Ignore'], axis=1)
        column_names = ["Date", "Time", "Open", "High", "Low", "Close", "Volume"]
        dftmp.reset_index(drop=True, inplace=True)
        dftmp = dftmp.reindex(columns=column_names)
        string_dt = str(dftmp['Date'][len(dftmp) - 1]) + 'T' + str(dftmp['Time'][len(dftmp) - 1]) + '.000Z'
        utc_last_time = datetime.strptime(string_dt, "%d/%m/%YT%H:%M:%S.%fZ")
        last_time = (utc_last_time - datetime(1970, 1, 1)) // timedelta(milliseconds=1)
        df = pd.concat([df, dftmp], axis=0, ignore_index=True, keys=None)
    df.to_csv('0y_eth_only17andnew.csv', sep='\t', index=False)
get_klines_iter('ETHBUSD', '15m', '2024-03-10', '2024-03-11')
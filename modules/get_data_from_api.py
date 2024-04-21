from .config import api_key
import requests
from .database.db import get_db
from flask import jsonify, make_response, flash
from datetime import datetime, timedelta

# 查询所有用户的持仓，刷新overview和股价数据，相同的股票只查询一次
def refresh_all_info():
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute('SELECT DISTINCT stock_symbol FROM portfolio')
        stock_symbols = cursor.fetchall()
        for stock_symbol in stock_symbols:
            stock_symbol = stock_symbol[0]
            acquire_stock_data(stock_symbol)
            print(f"Refreshed all info for {stock_symbol}")
    except Exception as e:
        print(f"Error refreshing all info: {e}")
    finally:
        cursor.close()


# 获取资产的历史价格数据，并以字典形式返回，会检查cache
def get_stock_price_dict(symbol):
    '''check if symbol cached, if cached, retrieve from database, else, get it from online api'''
    if check_cached(symbol) == True:
        # return retrieve_from_cache(symbol)
        data = retrieve_from_cache(symbol)
        result = transform_plot_database(data)
    else:
        # return acquire_stock_data(symbol)
        data = acquire_stock_data(symbol)
        result = transform_plot_online(data)
    return result


# 获取股价数据，会检查cache,并返回json格式
def get_stock_price(symbol):
    '''check if symbol cached, if cached, retrieve from database, else, get it from online api'''
    if check_cached(symbol) == True:
        # return retrieve_from_cache(symbol)
        print('get stock price json, get from cache')
        data = retrieve_from_cache(symbol)
        result = transform_plot_database(data)
    else:
        # return acquire_stock_data(symbol)
        print('get stock price json, get from api')
        data = acquire_stock_data(symbol)
        result = transform_plot_online(data)

    return jsonify(result)


# 获取volume数据
def get_volume_dict(symbol):
    if check_cached(symbol) == False:
        acquire_stock_data(symbol)
    db = get_db()
    try:
        cursor = db.cursor()
        query = '''
        SELECT closing_date, volume
        FROM stock_data
        WHERE stock_symbol = ?
        ORDER BY closing_date DESC
        '''
        cursor.execute(query, (symbol.upper(),))
        data = cursor.fetchall()

        # 初始化结果字典
        result = {
            "closing_dates": [],
            "volumes": []
        }

        # 遍历查询结果，填充字典
        for row in data:
            closing_date, volume = row
            result["closing_dates"].append(closing_date)
            result["volumes"].append(volume)

    except Exception as e:
        print(f"An error occurred: {e}")
        return None

    return result

# 从api获取overview数据，并保存到数据库
def acquire_overview_to_save(symbol):
    '''获取股票的overview数据,并保存到数据库中'''
    symbol = str(symbol)
    url_overview = f'https://www.alphavantage.co/query?function=OVERVIEW&symbol={symbol.upper()}&apikey={api_key}'
    try:
        r = requests.get(url_overview)
        if r.status_code == 200:
            # 取request数据存入overview_data['Symbol'], overview_data['Name'], overview_data['Exchange'], overview_data['Currency'], overview_data['EPS'], overview_data['Beta']
            overview_result = r.json()
            overview_data = {
                'Symbol': overview_result.get('Symbol', ''),
                'Name': overview_result.get('Name', ''),
                'Exchange': overview_result.get('Exchange', ''),
                'Currency': overview_result.get('Currency', ''),
                'EPS': overview_result.get('EPS', ''),
                'Beta': overview_result.get('Beta', '')
            }
            save_overview_to_db(overview_data)  # save to database for next time
            print(f'success to retrieve [{symbol}] overview data and save to database')
        else:
            print('Failed to retrieve overview data')
            return make_response(jsonify({'error': 'Failed to retrieve overview data'}), r.status_code)
    except Exception as e:
        print(f"Error retrieving overview data: {e}")   
        return make_response(jsonify({'error': str(e)}), 500)



# 从数据库获取最近的股价，会检查cache
def get_recent_stock_price(symbol):
    '''check if symbol cached, if cached, retrieve from database, else, get it from online api'''
    if check_cached(symbol) == True:
        # return retrieve_from_cache(symbol)
        data = retrieve_from_cache(symbol)
        result = transform_plot_database(data)
    else:
        # return acquire_stock_data(symbol)
        data = acquire_stock_data(symbol)
        result = transform_plot_online(data)
    return (result['adjClosePrices'][0], result['dates'][0])


# 获取十年期美国国债yield
def get_US_10Y_bond_yield():
    url = f'https://www.alphavantage.co/query?function=TREASURY_YIELD&interval=monthly&maturity=10year&apikey={api_key}'
    try:
        r = requests.get(url)
        if r.status_code == 200:
            data = r.json()
            yield_data = data.get('data', [])
            if yield_data:
                return yield_data[0].get('value', '')
            else:
                return ''
        else:
            return ''
    except Exception as e:
        print(f"Error retrieving US 10Y bond yield: {e}")
        return ''




# 从api获取股价数据，并保存到数据库【不直接用】【核心】
def acquire_stock_data(symbol):
    '''获取adj_price近20年的数据,包含股价和overview'''
    symbol = str(symbol)
    url = f'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol={symbol.upper()}&outputsize=full&apikey={api_key}'
    acquire_overview_to_save(symbol)
    acquire_and_save_SPY()
    try:
        r = requests.get(url)
        if r.status_code == 200:
            data = r.json()
            daily_data = data.get('Time Series (Daily)', {})
            # 20 year data filter
            twenty_year_ago = (datetime.now() - timedelta(days=7300)).strftime('%Y-%m-%d')
            dates = [date for date in daily_data if date >= twenty_year_ago]
            adj_close_prices = [daily_data[date]['5. adjusted close'] for date in dates]
            open_price = [daily_data[date]['1. open'] for date in dates]
            high_price = [daily_data[date]['2. high'] for date in dates]
            low_price = [daily_data[date]['3. low'] for date in dates]
            close_price = [daily_data[date]['4. close'] for date in dates]
            volume = [daily_data[date]['6. volume'] for date in dates]
            result = {
                "symbol": symbol,
                "dates": dates,
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "adjClosePrices": adj_close_prices,
                "volume": volume
            }
            save_to_db(symbol, result) # save to database for next time
            return result
        else:
            return make_response(jsonify({'error': 'Failed to retrieve data'}), r.status_code)
    except Exception as e:
        return make_response(jsonify({'error': str(e)}), 500)







#更改股价格式到用来画图的格式【不直接用】
def transform_plot_database(data):
    '''Transform stock price data from database for drawing plot for stock's adj. closing price '''
    result = {
        "adjClosePrices": [],
        "dates": [],
        "symbol": data[0]["stock_symbol"]
    }

    for item in data:
        adj_close_price = "{:.2f}".format(item["adj_close_price"]) 
        closing_date = item["closing_date"]
        formatted_date = f"{closing_date.year}-{closing_date.month:02d}-{closing_date.day:02d}"
        result["adjClosePrices"].append(adj_close_price)
        result["dates"].append(formatted_date)

    result["adjClosePrices"].reverse()
    result["dates"].reverse()
    return result





#更改股价格式到用来画图的格式【不直接用】
def transform_plot_online(data):
    '''Transform stock price data from online api for drawing plot for stock's adj. closing price '''
    adj_close_prices = data["adjClosePrices"]
    dates = data["dates"]
    symbol = data["symbol"]
    output_data = {
        "adjClosePrices": adj_close_prices,  
        "dates": dates,  
        "symbol": symbol  
    }
    return output_data    





# 保存股价数据到数据库【不直接用】
def save_to_db(symbol, data):
    db = get_db()
    cursor = db.cursor()
    try:
        for date, open_p, high, low, close, adj_close, volume in zip(data['dates'], data['open'], data['high'], data['low'], data['close'], data['adjClosePrices'], data['volume']):
            cursor.execute("""
                INSERT INTO stock_data (stock_symbol, closing_date, open_price, high_price, low_price, close_price, adj_close_price, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(stock_symbol, closing_date) DO UPDATE SET
                    open_price = excluded.open_price,
                    high_price = excluded.high_price,
                    low_price = excluded.low_price,
                    close_price = excluded.close_price,
                    adj_close_price = excluded.adj_close_price,
                    volume = excluded.volume
            """, (symbol.upper(), date, open_p, high, low, close, adj_close, volume))
        db.commit()
    except Exception as e:
        db.rollback()  # Rollback in case of error
        print(f"Error saving to database: {e}")
    finally:
        cursor.close()




# 保存overview数据到数据库【不直接用】
def save_overview_to_db(overview_data):
    '''
    save overview data to database
    args:
        overview_data: dict, overview data, including symbol, company name, description, exchange, currency, eps, beta
    '''
    db = get_db()
    cursor = db.cursor()
    try:
        check_query = '''
            SELECT 1 FROM stock_overview WHERE symbol = ?
        '''
        if cursor.execute(check_query, (overview_data['Symbol'],)).fetchone():
            update_query = """
                UPDATE stock_overview
                SET company_name = ?, exchange = ?, currency = ?, eps = ?, beta = ?
                WHERE symbol = ?
            """
            cursor.execute(update_query, (overview_data['Name'], overview_data['Exchange'], overview_data['Currency'], overview_data['EPS'], overview_data['Beta'], overview_data['Symbol']))
            db.commit()
            return
        else:
            insert_query = """
                INSERT INTO stock_overview (symbol, company_name, exchange, currency, eps, beta)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            cursor.execute(insert_query, (overview_data['Symbol'], overview_data['Name'], overview_data['Exchange'], overview_data['Currency'], overview_data['EPS'], overview_data['Beta']))
            db.commit()
    except Exception as e:
        print(f"Error saving overview data to database: {e}")
        return 

# 从api获取news数据
def acquire_news(symbol):
    url = f'https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={symbol.upper()}&apikey={api_key}'
    r = requests.get(url)
    if r.status_code == 200:
        data = r.json()
        result = data['feed'][0:5]  # retrive top 5 news
    else:
        result = []
    return result


# 从api获取SPY数据并保存到数据库【不直接用】
def acquire_and_save_SPY():
    url = f'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol=SPY&outputsize=full&apikey={api_key}'
    try:    
        r = requests.get(url)
        if r.status_code == 200:
            data = r.json()
            daily_data = data.get('Time Series (Daily)', {})
            # Last year data filter
            twenty_year_ago = (datetime.now() - timedelta(days=7300)).strftime('%Y-%m-%d')
            dates = [date for date in daily_data if date >= twenty_year_ago]
            adj_close_prices = [daily_data[date]['5. adjusted close'] for date in dates]
            open_price = [daily_data[date]['1. open'] for date in dates]
            high_price = [daily_data[date]['2. high'] for date in dates]
            low_price = [daily_data[date]['3. low'] for date in dates]
            close_price = [daily_data[date]['4. close'] for date in dates]
            volume = [daily_data[date]['6. volume'] for date in dates]
            result = {
                "symbol": 'SPY',
                "dates": dates,
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "adjClosePrices": adj_close_prices,
                "volume": volume
            }
            save_to_db('SPY', result) # save to database for next time
            return result
        else:
            return make_response(jsonify({'error': 'Failed to retrieve data'}), r.status_code)
    except Exception as e:
        return make_response(jsonify({'error': str(e)}), 500)
    





def check_symbol_exists(symbol):
    url = f'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol={symbol.upper()}&apikey={api_key}'
    r = requests.get(url)
    if r.status_code == 200 and 'Error Message' not in r.json():
        return True
    return False


def check_cached(symbol):
    ''' check if symbol in db column: stock_symbol, if exists return true, else false '''
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute('SELECT closing_date FROM stock_data WHERE stock_symbol = ? ORDER BY closing_date DESC LIMIT 1', (symbol.upper(),))
        result = cursor.fetchone()
        if result:
            last_record_date = result[0]
            if isinstance(last_record_date, str):
                # 如果日期是字符串，才需要转换
                last_record_date = datetime.strptime(last_record_date, '%Y-%m-%d').date()
            current_date = datetime.now().date()
            # 判断最后记录的日期是否满足条件
            if last_record_date == current_date:
                return True
            elif current_date.weekday() >= 5:  # 周六或周日
                if last_record_date.weekday() == 4:  # 最后记录是周五
                    return True
                else:
                    return False
            elif current_date.weekday() == 0:
                if datetime.now().time() < datetime.strptime('17:00', '%H:%M').time():
                    return True
                else:
                    return False
            elif last_record_date == (current_date - timedelta(days=1)):
                if datetime.now().time() < datetime.strptime('17:00', '%H:%M').time():
                    return True
                else:
                    return False
        else:
            return False
    except Exception as e:
        print(f"Error checking symbol in database: {e}")
        return False
    finally:
        cursor.close()

def retrieve_from_cache(symbol):
    '''retrieve stock price data from cache'''
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute('SELECT * FROM stock_data WHERE stock_symbol = ?', (symbol.upper(),))
        rows = cursor.fetchall()  
        # Convert fetched rows to a list of dictionaries
        columns = [column[0] for column in cursor.description]  
        result = [dict(zip(columns, row)) for row in rows] 
        if not result:
            return None  
        return result
    except Exception as e:
        print(f"Error retrieving data from database: {e}")
        return None
    finally:
        cursor.close()

def acquire_daily_info(symbol, page_data):
    url = f'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol={symbol.upper()}&apikey={api_key}&outputsize=full'
    r = requests.get(url)
    if r.status_code == 200:
        daily_data = r.json()['Time Series (Daily)']
        dates = list(daily_data.keys())
        latest_date = dates[0]  
        previous_date = dates[1]  
            # today
        today_data = daily_data[latest_date]
            # previous day
        previous_data = daily_data[previous_date]
            # add to page_data
        page_data.update({
                'current_price': today_data['4. close'],
                'previous_close': previous_data['5. adjusted close'],
                'open': today_data['1. open'],
                'volume': today_data['6. volume'],
            })
    else:
        flash('Failed to retrieve daily stock data', 'error')

def acquire_overview(symbol, page_data):
    url = f'https://www.alphavantage.co/query?function=OVERVIEW&symbol={symbol.upper()}&apikey={api_key}'

    r = requests.get(url)
    if r.status_code == 200:
        stock_data = r.json()
            # Check retrieve success
        if 'Name' in stock_data:
            page_data['stock_data'] = stock_data
        else:
            pass
            # flash('Failed to retrieve additional stock data', 'error')
    else:
        flash('API request failed', 'error')

# 获取S&P500的数据
def get_SPY_data_dict():
    return get_stock_price_dict('SPY')
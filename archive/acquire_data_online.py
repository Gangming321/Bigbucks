import requests
import chart.config
from datetime import datetime, timedelta
from flask import jsonify, make_response, flash
from chart.db import get_db

api_key = chart.config.api_key
def check_symbol_exists(symbol):
    api_key = chart.config.api_key
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
        cursor.execute('SELECT 1 FROM stock_data WHERE stock_symbol = ?', (symbol.upper(),))
        result = cursor.fetchone()
        if result:
            return True
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
    url = f'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol={symbol.upper()}&apikey={api_key}'
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
            flash('Failed to retrieve additional stock data', 'error')
    else:
        flash('API request failed', 'error')

def acquire_stock_data(symbol):
    url = f'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol={symbol.upper()}&outputsize=full&apikey={api_key}'
    try:
        r = requests.get(url)
        if r.status_code == 200:
            data = r.json()
            daily_data = data.get('Time Series (Daily)', {})
            # Last year data filter
            one_year_ago = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
            dates = [date for date in daily_data if date >= one_year_ago]
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

def get_stock_data(symbol):
    '''check if symbol cached, if cached, retrieve from database, else, get it from online api'''
    if check_cached(symbol) == True:
        # return retrieve_from_cache(symbol)
        data = retrieve_from_cache(symbol)
        result = transform_plot_database(data)
    else:
        # return acquire_stock_data(symbol)
        data = acquire_stock_data(symbol)
        result = transform_plot_online(data)
    return jsonify(result)

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



def acquire_news(symbol):
    url = f'https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={symbol.upper()}&apikey={api_key}'
    r = requests.get(url)
    if r.status_code == 200:
        data = r.json()
        result = data['feed'][0:5]  # retrive top 5 news
    else:
        result = []
    return result
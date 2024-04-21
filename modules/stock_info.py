from flask import render_template, flash, Blueprint, request, redirect, url_for, jsonify
from .get_data_from_api import acquire_overview, acquire_daily_info, check_symbol_exists, get_stock_price, acquire_news, get_stock_price_dict, get_SPY_data_dict, get_volume_dict
import json

bp = Blueprint('info', __name__, url_prefix='/info')


@bp.route('/main', methods=['GET','POST'])
@bp.route('/main/<symbol>', methods=['GET','POST'])
def show_stock_info(symbol=None):
    page_data = {"title": "Duke Blue Pay: Stock Information", "inputValue": ""}  # 定义page_data
    if request.method == 'POST':
        # 从表单中获取股票代码
        symbol = request.form.get('ticker')
        if symbol:  # 如果用户通过表单提交了股票代码
            return redirect(url_for('info.show_stock_info', symbol=symbol))
        elif symbol == "":  # 如果没有输入股票代码
            error = "Error: Please enter a stock symbol."
            flash(error, 'error')
            return render_template("stock_info/stock_info.html", page_data=page_data)
    elif symbol:
        # 如果URL中有股票代码
        page_data = {"title": "Duke Blue Pay: " + symbol, "inputValue": symbol}
        if not check_symbol_exists(symbol):
            flash('Stock symbol not found: ' + symbol, 'error')
            return render_template("stock_info/stock_info.html", page_data=page_data)
        acquire_overview(symbol, page_data)
        return render_template("stock_info/stock_info.html", page_data=page_data, symbol=symbol)
    else:
        # 如果既不是POST请求，也没有symbol参数，返回初始页面
        page_data = {"title": "Duke Blue Pay: Stock Information", "inputValue": ""}
        return render_template("stock_info/stock_info.html", page_data=page_data)

# '''# 返回用来画股价折线图的数据，暂时还没做
# @bp.route('/pricing/<symbol>', methods=['GET','POST'])
# def retrieve_stock_prices(symbol):
#     return get_stock_price(symbol)'''
# # 返回用来画股价折线图的数据，暂时还没做
@bp.route('/pricing/<symbol>', methods=['GET','POST'])
def retrieve_stock_prices(symbol):
    adj_price = get_stock_price_dict(symbol)
    return render_template("stock_info/pricing.html", symbol=symbol, adj_price=adj_price)

@bp.route('/<symbol>/charts')
def show_chart(symbol):
    return render_template("stock_info/charts_select.html", symbol=symbol)

# 显示news界面
@bp.route('/<symbol>/news')
def show_news(symbol):
    news_items = acquire_news(symbol)
    return render_template("stock_info/news.html", symbol=symbol, news_items=news_items)

@bp.route('/<symbol>/adv_chart', methods=['GET','POST'])
def show_advanced_chart(symbol):
    error = ""
    stock_symbol = None
    chart_type = None
    chart_data = {}
    if request.method == 'POST':
        stock_symbol = request.form.get('stockSymbol')  # 使用.get方法，如果字段不存在，返回None
        chart_type = request.form.get('chart_type')  # 使用.get方法，如果字段不存在，返回None
    if stock_symbol == None or chart_type == None:
        error = "Error: Please select a stock symbol and chart type."
        flash(error, 'error')
        return render_template("stock_info/adv_chart.html", symbol=symbol)
    
    if chart_type == "Historical":
        raw_adj = get_stock_price_dict(stock_symbol)    
        chart_data['adj_close'] = [float(price) for price in raw_adj['adjClosePrices'][:252]]
        chart_data['dates'] = raw_adj['dates'][:252]
        # 倒序排列
        chart_data['adj_close'] = [float(price) for price in raw_adj['adjClosePrices'][:252]][::-1]
        chart_data['dates'] = raw_adj['dates'][:252][::-1]
        return render_template("stock_info/adv_chart.html", chart_data=chart_data, symbol=stock_symbol, chart_type=chart_type)
    
    elif chart_type == "Simple Return":
        raw_adj = get_stock_price_dict(stock_symbol)
        adj_close = [float(price) for price in raw_adj['adjClosePrices']][:252]
        simple_returns = []
        for i in range(1, len(adj_close)):
            simple_returns.append((adj_close[i] - adj_close[i-1]) / adj_close[i-1])
        simple_returns.insert(0, 0)
        chart_data['simple_returns'] = simple_returns
        chart_data['dates'] = raw_adj['dates'][:252]
        # 倒序排列
        chart_data['simple_returns'] = simple_returns[::-1]
        chart_data['dates'] = chart_data['dates'][::-1]
        return render_template("stock_info/adv_chart.html", chart_data=chart_data, symbol=stock_symbol, chart_type=chart_type)
    
    elif chart_type == "Yesterday vs Today":
        raw_adj = get_stock_price_dict(stock_symbol)
        adj_close = [float(price) for price in raw_adj['adjClosePrices']][:252]
        returns = []
        for i in range(1, len(adj_close)):
            returns.append((adj_close[i] - adj_close[i-1]) / adj_close[i-1])
        returns.insert(0, 0)
        chart_data['today'] = returns        
        yesterday_returns = [0] + returns[:-1]
        chart_data['yesterday'] = yesterday_returns
         # 倒序排列
        chart_data['today'] = returns[::-1]
        chart_data['yesterday'] = yesterday_returns[::-1]
        
        return render_template("stock_info/adv_chart.html", chart_data=chart_data, symbol=stock_symbol, chart_type=chart_type)
    
    elif chart_type == "Histogram of Simple Returns":
        raw_adj = get_stock_price_dict(stock_symbol)
        adj_close = [float(price) for price in raw_adj['adjClosePrices']][:252]
        simple_returns = []
        for i in range(1, len(adj_close)):
            simple_returns.append((adj_close[i] - adj_close[i-1]) / adj_close[i-1])
        simple_returns.insert(0, 0)
        chart_data['simple_returns'] = simple_returns
        chart_data['dates'] = raw_adj['dates'][:252]
        # 倒序排列
        chart_data['simple_returns'] = simple_returns[::-1]
        chart_data['dates'] = chart_data['dates'][::-1]
        return render_template("stock_info/adv_chart.html", chart_data=chart_data, symbol=stock_symbol, chart_type=chart_type)
    
    elif chart_type == "Daily Returns vs S&P500":
        # Draw stock and S& P 500 cumulative returns
        raw_adj = get_stock_price_dict(stock_symbol)
        adj_close = [float(price) for price in raw_adj['adjClosePrices']][:252]
        raw_spy = get_SPY_data_dict()
        spy_close = [float(price) for price in raw_spy['adjClosePrices']][:252]
        stock_returns = []
        spy_returns = []
        for i in range(1, len(adj_close)):
            stock_returns.append((adj_close[i] - adj_close[i-1]) / adj_close[i-1])
            spy_returns.append((spy_close[i] - spy_close[i-1]) / spy_close[i-1])

        stock_returns.insert(0, 0)
        spy_returns.insert(0, 0)

        for i in range(1, len(stock_returns)):
            stock_returns[i] = stock_returns[i] + stock_returns[i-1]
            spy_returns[i] = spy_returns[i] + spy_returns[i-1]
        
        chart_data['stock_returns'] = stock_returns
        chart_data['spy_returns'] = spy_returns
        chart_data['dates'] = raw_adj['dates'][:252]
        # 倒序排列
        chart_data['stock_returns'] = chart_data['stock_returns'][::-1]
        chart_data['spy_returns'] = chart_data['spy_returns'][::-1]
        chart_data['dates'] = chart_data['dates'][::-1]

        return render_template("stock_info/adv_chart.html", chart_data=chart_data, symbol=stock_symbol, chart_type=chart_type)
    
    elif chart_type == "Daily % Change vs S&P500":
        # Draw stock and S& P 500  returns
        raw_adj = get_stock_price_dict(stock_symbol)
        adj_close = [float(price) for price in raw_adj['adjClosePrices']][:252]
        raw_spy = get_SPY_data_dict()
        spy_close = [float(price) for price in raw_spy['adjClosePrices']][:252]
        stock_returns = []
        spy_returns = []
        for i in range(1, len(adj_close)):
            stock_returns.append((adj_close[i] - adj_close[i-1]) / adj_close[i-1])
            spy_returns.append((spy_close[i] - spy_close[i-1]) / spy_close[i-1])
        stock_returns.insert(0, 0)
        spy_returns.insert(0, 0)
        chart_data['stock_returns'] = stock_returns
        chart_data['spy_returns'] = spy_returns
        chart_data['dates'] = raw_adj['dates'][:252]
        # 倒序排列  
        chart_data['stock_returns'] = chart_data['stock_returns'][::-1]
        chart_data['spy_returns'] = chart_data['spy_returns'][::-1]
        chart_data['dates'] = chart_data['dates'][::-1]
        return render_template("stock_info/adv_chart.html", chart_data=chart_data, symbol=stock_symbol, chart_type=chart_type)

    elif chart_type == "Scatter Graph of X vs S&P500":
        raw_adj = get_stock_price_dict(stock_symbol)
        adj_close = [float(price) for price in raw_adj['adjClosePrices']][:252]
        raw_spy = get_SPY_data_dict()
        spy_close = [float(price) for price in raw_spy['adjClosePrices']][:252]
        stock_returns = []
        spy_returns = []
        for i in range(1, len(adj_close)):
            stock_returns.append((adj_close[i] - adj_close[i-1]) / adj_close[i-1])
            spy_returns.append((spy_close[i] - spy_close[i-1]) / spy_close[i-1])
        stock_returns.insert(0, 0)
        spy_returns.insert(0, 0)
        chart_data['stock_returns'] = stock_returns
        chart_data['spy_returns'] = spy_returns
        chart_data['dates'] = raw_adj['dates'][:252]
        # 倒序排列  
        chart_data['stock_returns'] = chart_data['stock_returns'][::-1]
        chart_data['spy_returns'] = chart_data['spy_returns'][::-1]      
        return render_template("stock_info/adv_chart.html", chart_data=chart_data, symbol=stock_symbol, chart_type=chart_type)
    elif chart_type == "Historical Volume":
        raw_volume = get_volume_dict(stock_symbol)
        chart_data['volume'] = [float(volume) for volume in raw_volume['volumes']][:252]
        chart_data['dates'] = [date.strftime("%Y-%m-%d") for date in raw_volume['closing_dates'][:252]]
        # 倒序排列
        chart_data['volume'] = chart_data['volume'][::-1]
        chart_data['dates'] = chart_data['dates'][::-1]
        return render_template("stock_info/adv_chart.html", chart_data=chart_data, symbol=stock_symbol, chart_type=chart_type)
    elif chart_type == "Volume Change":
        raw_volume = get_volume_dict(stock_symbol)
        volumes = [float(volume) for volume in raw_volume['volumes']][:252]
        volume_change = []
        for i in range(1, len(volumes)):
            volume_change.append((volumes[i] - volumes[i-1]) / volumes[i-1])
        volume_change.insert(0, 0)
        chart_data['volume_change'] = volume_change
        chart_data['dates'] = [date.strftime("%Y-%m-%d") for date in raw_volume['closing_dates'][:252]]
        # 倒序排列
        chart_data['volume_change'] = volume_change[::-1]
        chart_data['dates'] = chart_data['dates'][::-1]
        return render_template("stock_info/adv_chart.html", chart_data=chart_data, symbol=stock_symbol, chart_type=chart_type)

    elif chart_type == "Volume Change vs Price Change":
        raw_volume = get_volume_dict(stock_symbol)
        volumes = [float(volume) for volume in raw_volume['volumes']][:252]
        volume_change = []
        for i in range(1, len(volumes)):
            volume_change.append((volumes[i] - volumes[i-1]) / volumes[i-1])
        volume_change.insert(0, 0)
        raw_adj = get_stock_price_dict(stock_symbol)
        adj_close = [float(price) for price in raw_adj['adjClosePrices']][:252]
        price_change = []
        for i in range(1, len(adj_close)):
            price_change.append((adj_close[i] - adj_close[i-1]) / adj_close[i-1])
        price_change.insert(0, 0)
        chart_data['volume_change'] = volume_change
        chart_data['price_change'] = price_change
        # chart_data['dates'] = raw_adj['dates'][:252]
        # 倒序排列
        chart_data['volume_change'] = volume_change[::-1]
        chart_data['price_change'] = price_change[::-1]
        # chart_data['dates'] = chart_data['dates'][::-1]
        return render_template("stock_info/adv_chart.html", chart_data=chart_data, symbol=stock_symbol, chart_type=chart_type)
    
    else:
        error = "Error: Invalid chart type."
        flash(error, 'error')

    return render_template("stock_info/adv_chart.html", symbol=symbol, chart_data=chart_data)



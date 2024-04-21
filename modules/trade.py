from flask import render_template, Blueprint, request, flash, jsonify, session
from .auth import login_required
from .database.db import get_db
import datetime
from .get_data_from_api import check_symbol_exists, get_stock_price_dict
from .get_efficient_frontier import generate_universe_dict, generate_covariance_matrix, calculate_restricted_volatility, calculate_sharpe_ratio

bp = Blueprint('trade', __name__, url_prefix='/trade')


@bp.route('/main', methods=['GET', 'POST'])
@login_required
def trade_main():
    if request.method == 'GET':
        # 查询用户余额
        db = get_db()
        user_id = session['user_id']
        balance_query = "SELECT balance FROM user WHERE id = ?"
        balance_result = db.execute(balance_query, (user_id,)).fetchone()
        user_balance = round(balance_result['balance'],2)
        return render_template("/trade/trade_main.html", balance = user_balance)
    
    if request.method == 'POST':
        """input: transactionType, transactionTicker, transactionAmount, transactionDate"""
        db = get_db()
        error = None

        # 获取用户余额
        user_id = session['user_id']
        balance_query = "SELECT balance FROM user WHERE id = ?"
        balance_result = db.execute(balance_query, (user_id,)).fetchone()
        user_balance = round(balance_result['balance'],2)

        """获取表单信息"""
        transactionType = request.form.get('transactionType')
        transactionTicker = request.form.get('ticker').upper()  # Convert ticker to uppercase

        # amount
        amount = request.form.get('amount')
        if amount == "":
            error = 'Error: Please enter a positive integer as an amount'
            flash(error)
            return render_template("/trade/trade_main.html", balance = user_balance)            
        transactionAmount = int(float(amount)) 

        # date
        transactionDate = get_transaction_date(request.form.get('transactionDate'))

        # unit_price
        unit_price = request.form.get('adjClosePrice')

    
        # 检查ticker是否存在
        if not check_symbol_exists(transactionTicker):
            error = 'Error: Ticker does not exist'
            flash(error)
            return render_template("/trade/trade_main.html", balance = user_balance)

        # 检查amount是否大于0
        if transactionAmount <= 0:
            error = 'Error: Cannot trade with a negative amount'
            flash(error)
            return render_template("/trade/trade_main.html", balance = user_balance)

        # 检查是否输入整数
        if not is_integer(amount):
            error = 'Error: Please enter a positive integer'
            flash(error)
            return render_template("/trade/trade_main.html", balance = user_balance)

        transactionTotal = calculate_transaction_total(unit_price, transactionAmount)

        # # 检查账户余额是否充足
        # if user_balance < transactionTotal:
        #     error = 'Error: Insufficient account balance'
        #     flash(error)
        #     return render_template("/trade/trade_main.html")
        
        # 持仓验证逻辑
        if transactionType == 'buy':
            # 检查账户余额是否充足
            if user_balance < transactionTotal:
                error = 'Error: Insufficient account balance'
                flash(error)
                return render_template("/trade/trade_main.html", balance = user_balance)
        elif transactionType == 'sell':
            # 检查持仓数量是否充足
            portfolio_query = "SELECT quantity FROM portfolio WHERE user_id = ? AND stock_symbol = ?"
            portfolio_result = db.execute(portfolio_query, (user_id, transactionTicker)).fetchone()
            if portfolio_result is None or portfolio_result['quantity'] < transactionAmount:
                error = 'Error: Insufficient quantity in portfolio'
                flash(error)
                return render_template("/trade/trade_main.html", balance = user_balance)
        else:
            error = 'Error: Invalid transaction type'
            flash(error)
            return render_template("/trade/trade_main.html", balance = user_balance)
        
        # 检查持仓是否存在
        portfolio_query = "SELECT * FROM portfolio WHERE user_id = ? AND stock_symbol = ?"
        portfolio_result = db.execute(portfolio_query, (user_id, transactionTicker)).fetchone()

        if portfolio_result is None:
            # 插入新的持仓记录
            insert_portfolio_record(db, user_id, transactionTicker, transactionAmount, unit_price)
        else:
            # 更新持仓记录
            update_portfolio_record(db, user_id, transactionTicker, transactionAmount, unit_price, transactionType)

        insert_transaction_record(db, transactionDate, transactionType, transactionTicker, unit_price, transactionAmount)
        # 更新用户余额
        if transactionType == 'buy':
            new_balance = user_balance - transactionTotal
        elif transactionType == 'sell':
            new_balance = user_balance + transactionTotal
        update_balance_query = "UPDATE user SET balance = ? WHERE id = ?"
        db.execute(update_balance_query, (new_balance, user_id))    
        db.commit()

        # 制作confirm页面
        render_data = {'Type':transactionType, 'Amount':transactionAmount, 'Ticker':transactionTicker, 'Date':transactionDate, 'Unit_price':unit_price, 'Total':transactionTotal}
        return render_template('/trade/trade_success.html', data=render_data)


def get_transaction_date(input_date):
    Today = datetime.datetime.now().date()
    if not input_date:
        return Today
    else:
        return datetime.datetime.strptime(input_date, '%Y-%m-%d')



def calculate_transaction_total(unit_price, amount):
    return float(unit_price) * amount


def insert_transaction_record(db, transaction_date, transaction_type, symbol, unit_price, amount):
    """
    将交易记录插入数据库中。
    参数：
    - db: 数据库连接对象
    - transaction_date: 交易日期
    - transaction_type: 交易类型
    - symbol: 股票代码
    - unit_price: 单价
    - amount: 交易数量
    """
    db.execute(
        "INSERT INTO transactions (transaction_date, user_id, transaction_type, symbol, unit_price, amount) VALUES (?, ?, ?, ?, ?, ?)",
        (transaction_date, session['user_id'], transaction_type, symbol, unit_price, amount),
    )
    db.commit()


def is_integer(amount):
    return float(amount) == int(float(amount))


# 插入新记录的函数
def insert_portfolio_record(db, user_id, stock_symbol, transactionAmount, unit_price):
    """
    将新的持仓记录插入portfolio表中。

    参数：
    - db: 数据库连接对象
    - user_id: 用户ID
    - stock_symbol: 股票代码
    """
    insert_portfolio_query = "INSERT INTO portfolio (user_id, stock_symbol, quantity, average_cost) VALUES (?, ?, ?, ?)"
    db.execute(insert_portfolio_query, (user_id, stock_symbol, transactionAmount, unit_price))
    db.commit()


# 更新持仓数量和平均价格的函数
def update_portfolio_record(db, user_id, stock_symbol, transaction_amount, unit_price, transaction_type):
    """
    更新portfolio表中的持仓数量和平均价格。

    参数：
    - db: 数据库连接对象
    - user_id: 用户ID
    - stock_symbol: 股票代码
    - transaction_amount: 交易数量
    - unit_price: 交易单价
    """
    # 获取当前持仓数量和平均价格
    portfolio_query = "SELECT quantity, average_cost FROM portfolio WHERE user_id = ? AND stock_symbol = ?"
    portfolio_result = db.execute(portfolio_query, (user_id, stock_symbol)).fetchone()
    current_quantity = portfolio_result['quantity']
    current_average_cost = portfolio_result['average_cost']
    # 更新持仓数量和平均价格
    if transaction_type == 'buy':
        new_quantity = current_quantity + transaction_amount
        new_average_cost = ((float(current_quantity) * float(current_average_cost)) + (float(transaction_amount) * float(unit_price))) / new_quantity
    elif transaction_type == 'sell':
        new_quantity = current_quantity - transaction_amount
        new_average_cost = current_average_cost
        if new_quantity == 0:
            update_portfolio_query = "DELETE FROM portfolio WHERE user_id = ? AND stock_symbol = ?"
            db.execute(update_portfolio_query, (user_id, stock_symbol))
            db.commit()
            return
    update_portfolio_query = "UPDATE portfolio SET quantity = ?, average_cost = ? WHERE user_id = ? AND stock_symbol = ?"
    db.execute(update_portfolio_query, (new_quantity, new_average_cost, user_id, stock_symbol))
    db.commit()


@bp.route('/pricing/<symbol>/<date>', methods=['GET'])
@login_required
def get_price(symbol=None, date=None):
    """
    Retrieves the adjusted closing price for a given stock symbol and date.

    Args:
        symbol (str): The stock symbol.
        date (str): The date in the format 'YYYY-MM-DD'.

    Returns:
        dict: A dictionary containing the symbol, date, and adjusted closing price.

    Raises:
        JSONResponse: If the ticker does not exist or if there is no available data before the specified date.
    """
    
    if check_symbol_exists(symbol) == False:
        return jsonify({"error": "Ticker does not exist"}), 200
    result = get_stock_price_dict(symbol)
    
    # Testing
    # print('----------------------------------------------------')
    # generate_universe_dict([symbol])
    # generate_covariance_matrix(['a', 'aapl'])
    # calculate_sharpe_ratio({'A': {'quantity': 100, 'unit_price': 100}, 'AAPL': {'quantity': 200, 'unit_price': 50}}, 0)
    
    target_date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
    dates = [datetime.datetime.strptime(d, "%Y-%m-%d").date() for d in result['dates']]
    adjClosePrices = result['adjClosePrices']
    
    # 查找指定日期或之前最近的一个交易日
    if target_date not in dates:
        # 如果指定日期不在列表中，找到最近的一个早于指定日期的交易日
        dates_before_target = [d for d in dates if d < target_date]
        if not dates_before_target:
            return jsonify({"error": "指定日期之前没有可用数据。"}), 404
        nearest_date = max(dates_before_target)
    else:
        nearest_date = target_date

    nearest_date_index = dates.index(nearest_date)
    adjClosePrice = adjClosePrices[nearest_date_index]

    result_dict = {
        "symbol": symbol,
        "date": nearest_date.strftime("%Y-%m-%d"),
        "adjClosePrice": adjClosePrice
    }

    return jsonify(result_dict)



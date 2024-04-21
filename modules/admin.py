from .auth import admin_required
from flask import Blueprint, render_template, request, flash, jsonify
from .database.db import get_db
from .get_data_from_api import check_symbol_exists, get_stock_price_dict, acquire_overview, get_US_10Y_bond_yield
from .get_efficient_frontier import calculate_weighted_return_and_risk, calculate_sharpe_ratio
import datetime

bp = Blueprint('admin', __name__, url_prefix='/admin')


@bp.route('/', methods=['GET', 'POST'])
@admin_required
def admin():
    if request.method == 'GET':
        return render_template('admin/admin.html')


# List stocks across all users by ticker symbol, name, shares held, and price per share.
# 展示所有用户的持仓
@bp.route('user_stock_list', methods=['GET'])
@admin_required
def index_admin():
    db = get_db()
    today = datetime.date.today()
    
    # Get all the summary data for different users.
    try:
        records = db.execute(
            '''
            SELECT portfolio.* FROM portfolio
            JOIN user ON portfolio.user_id = user.id
            WHERE user.is_admin = FALSE
            ORDER BY portfolio.user_id
            '''
        ).fetchall()
        
        # Group the record data with user_id
        grouped_records = {}
        for record in records:
            # 假设get_adjusted_close_price函数返回的价格是正确的
            price = get_adjusted_close_price(record['stock_symbol'], today.strftime('%Y-%m-%d'))
            # 创建一个包含record数据和价格的字典
            record_with_price = {**record, 'price': price}
            # 将记录添加到对应user_id的列表中
            grouped_records.setdefault(record['user_id'], []).append(record_with_price)
        
        # print(grouped_records)
        
        # Initialize the aggregate data structure for ticker symbols
        ticker_summary = {}
        
        total_for_all_users = {
            'total_cost': 0,
            'total_value': 0,
            'total_pnl': 0,
            'current_price': 0
        }

        # Group the record data with user_id and also compute the aggregate info for each ticker symbol
        for record in records:
            # Get current price
            price = get_adjusted_close_price(record['stock_symbol'], today.strftime('%Y-%m-%d'))
            # Calculate total cost and total value for the record
            record_cost = record['quantity'] * record['average_cost']
            record_value = record['quantity'] * price
            # Update the aggregate info for the corresponding ticker symbol
            if record['stock_symbol'] in ticker_summary:
                ticker_summary[record['stock_symbol']]['total_quantity'] += record['quantity']
                ticker_summary[record['stock_symbol']]['total_cost'] += record_cost
                ticker_summary[record['stock_symbol']]['total_value'] += record_value
                ticker_summary[record['stock_symbol']]['total_pnl'] += record_value - record_cost
                ticker_summary[record['stock_symbol']]['current_price'] = price  # Add current price here
            else:
                ticker_summary[record['stock_symbol']] = {
                    'total_quantity': record['quantity'],
                    'total_cost': record_cost,
                    'total_value': record_value,
                    'total_pnl': record_value - record_cost,
                    'current_price': price  # Add current price here
                }
            
            total_for_all_users['total_cost'] += record_cost
            total_for_all_users['total_value'] += record_value
            total_for_all_users['total_pnl'] += record_value - record_cost

        # Calculate the weighted average unit price for each ticker symbol
        for symbol, summary in ticker_summary.items():
            if summary['total_quantity'] > 0:
                summary['weighted_avg_price'] = summary['total_cost'] / summary['total_quantity']
            else:
                summary['weighted_avg_price'] = 0
    
    except Exception as e:
        print(e)
        grouped_records = {}
        
    print(get_US_10Y_bond_yield())
    
    return render_template("admin/user_stock_list.html", 
                           page_data={"title": "Duke Blue Pay: Home"}, 
                           grouped_records=grouped_records,
                           ticker_summary=ticker_summary,
                           total_for_all_users=total_for_all_users,
                           today=today)

# List summary of current day's market orders across all users by ticker symbol, name, shares bought and shares sold.
# 当日市场订单摘要
@bp.route('today_transaction_summary', methods=['GET', 'POST'])
@admin_required
def today_transaction_summary():
    error = None
    if request.method == 'GET':
        return render_template('admin/today_transaction_summary.html')
    if request.method == 'POST':   
        db = get_db()
        query = '''
        SELECT
            transactions.symbol,
            stock_overview.company_name,
            sum(case when transactions.transaction_type = 'buy' then transactions.amount else 0 end) as buy_amount,
            sum(case when transactions.transaction_type = 'sell' then transactions.amount else 0 end) as sell_amount,
            DATE(transactions.transaction_date) AS transaction_date
        FROM
            transactions
            join stock_overview on transactions.symbol = stock_overview.symbol
        WHERE
            DATE(transactions.transaction_date) = ?
        GROUP BY
            transactions.symbol, stock_overview.company_name, transaction_date
        '''
        query_date = request.form['query_date']
        transactions = db.execute(query, (query_date,)).fetchall()
        if not transactions:
            error = 'No transactions found on this date'
            flash(error)
            return render_template('admin/today_transaction_summary.html')
        transactions_dic = [dict(row) for row in transactions]
        page_data = transactions_dic
        return render_template('admin/today_transaction_summary.html', page_data=page_data)
    # 获取当日所有交易

    return render_template('admin/today_transaction_summary.html')

# Enable BigBucks administrators to analyze the overall risk-return profile considering all stocks held by all account holders.
# 展示所有用户的σ, ROR, Sharpe Ratio
@bp.route('all_user_risk_return_profile', methods=['GET'])
@admin_required
def all_user_risk_return_profile():
    db = get_db()
    today = datetime.date.today()
    
    # Get all the summary data for different users.
    try:
        records = db.execute(
            '''
            SELECT 
            t.user_id, 
            t.symbol, 
            SUM(t.amount) AS total_quantity, 
            SUM(t.amount * t.unit_price) / SUM(t.amount) AS weighted_avg_unit_price
            FROM transactions t
            JOIN user u ON t.user_id = u.id
            WHERE u.is_admin = FALSE
            GROUP BY t.user_id, t.symbol
            ORDER BY t.user_id, t.symbol;
            '''
        ).fetchall()
        
        # for record in records:
        #     print(record['user_id'])
        #     print(record['symbol'])
        #     print(record['total_quantity'])
        #     print(record['weighted_avg_unit_price'])

        # Group the record data with user_id
        grouped_records = {}
        
        for record in records:
            user_id = record['user_id']
            symbol = record['symbol']
            total_quantity = record['total_quantity']
            weighted_avg_unit_price = record['weighted_avg_unit_price']

            # Check whether the id is already in the dict.
            if user_id not in grouped_records:
                grouped_records[user_id] = {}
            
            # Store the symbol info
            grouped_records[user_id][symbol] = {
                'quantity': total_quantity,
                'unit_price': weighted_avg_unit_price
            }
            
        # Calculate aggregate values for all users
        all_users_portfolio = {}

        for user_id, stocks in grouped_records.items():
            for symbol, details in stocks.items():
                if symbol in all_users_portfolio:
                    # If the symbol already exists in all_users_portfolio, update the total quantity and value for the weighted average
                    existing_quantity = all_users_portfolio[symbol]['quantity']
                    existing_total_value = all_users_portfolio[symbol]['unit_price'] * existing_quantity
                    additional_total_value = details['unit_price'] * details['quantity']
                    new_quantity = existing_quantity + details['quantity']
                    new_average_unit_price = (existing_total_value + additional_total_value) / new_quantity
                    all_users_portfolio[symbol]['quantity'] = new_quantity
                    all_users_portfolio[symbol]['unit_price'] = new_average_unit_price
                else:
                    # If the symbol does not exist in all_users_portfolio, add it directly
                    all_users_portfolio[symbol] = details.copy()

        # Now calculate the combined portfolio stats
        # You would need to ensure your functions can handle the all_users_portfolio data structure
        us_treasury_yield = float(get_US_10Y_bond_yield())/100
        all_users_weighted_rate_of_return, all_users_portfolio_volatility = calculate_weighted_return_and_risk(all_users_portfolio)
        all_users_sharpe_ratio = calculate_sharpe_ratio(all_users_portfolio, us_treasury_yield)

        # print(grouped_records)
        
        # for user_id, stocks in grouped_records.items():
        #     print(f"User ID: {user_id}")
        #     for symbol, details in stocks.items():
        #         print(f"  Symbol: {symbol}, Quantity: {details['quantity']}, Unit Price: {details['unit_price']}")

    except Exception as e:
        print(e)
        grouped_records = {}
        
    weighted_rate_of_return_dict = {}
    portfolio_volatility_dict = {}
    sharpe_ratio_dict = {}
    for user in grouped_records.keys():
        weighted_rate_of_return, portfolio_volatility = calculate_weighted_return_and_risk(grouped_records[user])
        weighted_rate_of_return_dict[user] = weighted_rate_of_return
        portfolio_volatility_dict[user] = portfolio_volatility
        sharpe_ratio_dict[user] = calculate_sharpe_ratio(grouped_records[user], us_treasury_yield)
    # print(weighted_rate_of_return_dict)
    # print(portfolio_volatility_dict)
    # print(sharpe_ratio_dict)
    
    return render_template('admin/all_user_risk_return_profile.html', 
                           page_data={"title": "Duke Blue Pay: Home"}, 
                           grouped_records=grouped_records,
                           weighted_rate_of_return_dict=weighted_rate_of_return_dict,
                           portfolio_volatility_dict=portfolio_volatility_dict,
                           sharpe_ratio_dict=sharpe_ratio_dict,
                           all_users_portfolio=all_users_portfolio,
                           all_users_weighted_rate_of_return=all_users_weighted_rate_of_return,
                           all_users_portfolio_volatility=all_users_portfolio_volatility,
                           all_users_sharpe_ratio=all_users_sharpe_ratio)


# Get today's adjusted close price for the particular stock.
def get_adjusted_close_price(symbol, date):
    if not check_symbol_exists(symbol):
        return None, "Ticker does not exist"

    result = get_stock_price_dict(symbol)
    target_date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
    dates = [datetime.datetime.strptime(d, "%Y-%m-%d").date() for d in result['dates']]
    adjClosePrices = result['adjClosePrices']

    if target_date not in dates:
        dates_before_target = [d for d in dates if d < target_date]
        if not dates_before_target:
            return None, "No available data before the specified date."
        nearest_date = max(dates_before_target)
    else:
        nearest_date = target_date

    nearest_date_index = dates.index(nearest_date)
    adjClosePrice = adjClosePrices[nearest_date_index]

    return float(adjClosePrice)


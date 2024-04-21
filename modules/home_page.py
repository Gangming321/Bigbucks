from flask import render_template, Blueprint, request, abort, session, redirect, url_for, flash
from werkzeug.security import check_password_hash, generate_password_hash
from .auth import login_required, admin_required
from .get_data_from_api import check_symbol_exists, get_stock_price_dict, acquire_overview
from .admin import get_adjusted_close_price
from .database.db import get_db
import datetime

bp = Blueprint('homepage', __name__, url_prefix='/homepage')

@bp.route('/index')
@login_required
def index():
    try:
        db = get_db()
        user_id = session['user_id']
        today = datetime.date.today()
        
        # Get the data from the database
        raw_records = db.execute(
            'SELECT * FROM portfolio WHERE user_id = ?', (user_id,)
        ).fetchall()
        
        # Convert records to dictionaries (assuming they are not already)
        records = [dict(record) for record in raw_records]
            
    except Exception as e:
        print(e)
        records = []
    
    # Create a dictionary to calculate the aggregate cost, value and PnL for every stock.
    portfolio_summary = {'portfolio_cost': 0, 'portfolio_value': 0, 'portfolio_pnl': 0}
    portfolio_cost = 0
    portfolio_value = 0
    portfolio_pnl = 0
    
    for record in records:
        page_data = {"title": "Duke Blue Pay: Home"}
        acquire_overview(record['stock_symbol'], page_data)
        if 'stock_data' in page_data:
            record['name'] = page_data['stock_data']['Name']
        else:
            record['name'] = 'N/A'  # handle error, no name found
            
        # Get today's price.
        record['current_price'] = get_adjusted_close_price(record['stock_symbol'], today.strftime('%Y-%m-%d'))
        
        # Calculate the total cost, value, pnl.
        record['total_cost'] = record['quantity'] * record['average_cost']
        record['current_value'] = record['quantity'] * record['current_price']
        record['PnL'] = record['current_value'] - record['total_cost']
        
        portfolio_cost += record['total_cost']
        portfolio_value += record['current_value']
        portfolio_pnl += record['PnL']
    
    # Update the dictionary.
    portfolio_summary['portfolio_cost'] = portfolio_cost
    portfolio_summary['portfolio_value'] = portfolio_value
    portfolio_summary['portfolio_pnl'] = portfolio_pnl
                                  
    # print(records)
    
    return render_template("index.html",
                           page_data={"title": "Duke Blue Pay: Home"},
                           records=records,
                           portfolio_summary=portfolio_summary,
                           user_id=user_id)
    

# @bp.route('/index_admin')
# @admin_required
# def index_admin():
#     db = get_db()
#     today = datetime.date.today()
    
#     # Get all the summary data for different users.
#     try:
#         records = db.execute(
#             '''
#             SELECT portfolio.* FROM portfolio
#             JOIN user ON portfolio.user_id = user.id
#             WHERE user.is_admin = FALSE
#             ORDER BY portfolio.user_id
#             '''
#         ).fetchall()
        
#         # Group the record data with user_id
#         grouped_records = {}
#         for record in records:
#             # 假设get_adjusted_close_price函数返回的价格是正确的
#             price = get_adjusted_close_price(record['stock_symbol'], today.strftime('%Y-%m-%d'))
            
#             # 创建一个包含record数据和价格的字典
#             record_with_price = {**record, 'price': price}
            
#             # 将记录添加到对应user_id的列表中
#             grouped_records.setdefault(record['user_id'], []).append(record_with_price)
        
#         print(grouped_records)
    
#     except Exception as e:
#         print(e)
#         grouped_records = {}
    
#     return render_template("index_admin.html", 
#                            page_data={"title": "Duke Blue Pay: Home"}, 
#                            grouped_records=grouped_records,
#                            today=today)


# # Get today's adjusted close price for the particular stock.
# def get_adjusted_close_price(symbol, date):
#     if not check_symbol_exists(symbol):
#         return None, "Ticker does not exist"

#     result = get_stock_price_dict(symbol)
#     target_date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
#     dates = [datetime.datetime.strptime(d, "%Y-%m-%d").date() for d in result['dates']]
#     adjClosePrices = result['adjClosePrices']

#     if target_date not in dates:
#         dates_before_target = [d for d in dates if d < target_date]
#         if not dates_before_target:
#             return None, "No available data before the specified date."
#         nearest_date = max(dates_before_target)
#     else:
#         nearest_date = target_date

#     nearest_date_index = dates.index(nearest_date)
#     adjClosePrice = adjClosePrices[nearest_date_index]

#     return float(adjClosePrice)

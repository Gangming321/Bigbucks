from flask import Blueprint, render_template, session, jsonify, flash, redirect, url_for
from .get_efficient_frontier import generate_universe_dict, generate_covariance_matrix, calculate_restricted_volatility, calculate_portfolio_volatility, calculate_sharpe_ratio, calculate_weighted_return_and_risk
from .get_data_from_api import get_US_10Y_bond_yield, refresh_all_info
from .database.db import get_db
from .auth import login_required 

bp = Blueprint('risk', __name__, url_prefix='/risk')

@bp.route('/test', methods=['GET', 'POST'])
def test():
    refresh_all_info()
    return 'test'

@bp.route('/efficient_frontier', methods=['GET', 'POST'])
@login_required
def efficient_frontier():
    # stock_list 是从portfolio数据库读user_id = session['user_id']的数据所有stock_symbol的列表
    db = get_db()
    # 从数据库获取用户的持仓信息（股票代码，持仓数量，最新单位价格）
    raw_stock_list = db.execute(
        '''
        SELECT
            portfolio.stock_symbol,
            portfolio.quantity,
            recent_stock_price.adj_close_price as unit_price
        FROM
            portfolio
            JOIN (
                SELECT
                    sd1.stock_symbol,
                    sd1.closing_date,
                    sd1.adj_close_price
                FROM
                    stock_data sd1
                    JOIN (
                        SELECT
                            stock_symbol,
                            max(closing_date) AS max_date
                        FROM
                            stock_data
                        GROUP BY
                            stock_symbol) sd2 ON sd1.stock_symbol = sd2.stock_symbol
                        AND sd1.closing_date = sd2.max_date) AS recent_stock_price ON portfolio.stock_symbol = recent_stock_price.stock_symbol
        WHERE portfolio.user_id = ?
        ''', (session['user_id'],)
    ).fetchall()

    # stock_list = [row['stock_symbol'] for row in raw_stock_list]
    # 构造一个包含资产symbol和持仓数量和单位价格的字典
    position_dict = {row['stock_symbol']: {'quantity': row['quantity'], 'unit_price': row['unit_price']} for row in raw_stock_list}
    # 如果position_dict不到2个元素，报错
    if len(position_dict) < 2:
        error = 'Error: You need to have at least two stocks in your portfolio to calculate efficient frontier, try to buy some stocks first.'
        flash(error)
        return redirect(url_for('trade.trade_main'))
    

    # position_dict = {row['stock_symbol']: row['quantity'] for row in raw_stock_list}
    stock_list = list(position_dict.keys())
    us_treasury_yield = float(get_US_10Y_bond_yield())/100
    sharpe_ratio = calculate_sharpe_ratio(position_dict, us_treasury_yield)
    # print('sharpe ratio:', sharpe_ratio)
    # 如果stock_list为空，返回一个空的页面
    if not stock_list:
        return render_template("/risk/efficient_frontier.html", res_efficient_frontier=[], unres_efficient_frontier=[])
    cov_matrix = generate_covariance_matrix(stock_list)
    universe_dict=generate_universe_dict(stock_list)
    cov_matrix = generate_covariance_matrix(stock_list)
    res_efficient_frontier = calculate_restricted_volatility(universe_dict, cov_matrix)

    unres_efficient_frontier = calculate_portfolio_volatility(universe_dict, cov_matrix)
    weighted_return_and_risk = calculate_weighted_return_and_risk(position_dict)
    # 计算夏普比例
    page_data ={}
    # page_data['res_efficient_frontier'] = {}
    # page_data['res_efficient_frontier']['x'] = [round(x, 5) for x in res_efficient_frontier[0]['volatility']]
    # page_data['res_efficient_frontier']['y'] = [round(y, 5) for y in res_efficient_frontier[0]['return']]
    # page_data['unres_efficient_frontier'] = {}
    # page_data['unres_efficient_frontier']['x'] = [round(x, 5) for x in unres_efficient_frontier[0]['volatility']]
    # page_data['unres_efficient_frontier']['y'] = [round(y, 5) for y in unres_efficient_frontier[0]['return']]
    page_data['weighted_return'] = weighted_return_and_risk[0]
    page_data['weighted_risk'] = weighted_return_and_risk[1]
    page_data['sharpe_ratio'] = sharpe_ratio

    return render_template("/risk/efficient_frontier.html", page_data=page_data, res_efficient_frontier=res_efficient_frontier, unres_efficient_frontier=unres_efficient_frontier)

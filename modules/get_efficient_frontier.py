import sys
import numpy as np
import pandas as pd
from .get_data_from_api import get_stock_price_dict

class Portfolio:
    def __init__(self):
        self.all_name = []
        self.all_ror = []
        self.all_std = []
        self.all_cov = None
        self.matrix_l = None
        self.all_ans_vec = []
        self.all_vola = []
        self.all_vola_res = []

    def load_asset_data_from_dict(self, data_dict):
        """
        Load asset data from a dictionary, including the asset name, rate of return, and standard deviation.
        """
        try:
            df = pd.DataFrame(data_dict)
            self.all_name = df['Ticker'].tolist()
            self.all_ror = df['Rate of Return'].astype(float).tolist()
            self.all_std = df['Standard Deviation'].astype(float).tolist()
        except KeyError:
            return "Invalid dictionary format. Required keys: 'Ticker', 'Rate of Return', 'Standard Deviation'"

    def read_and_compute_covariance_matrix(self, matrix):
        try:
            if matrix.shape[0] != len(self.all_std) or matrix.shape[1] != len(self.all_std):
                sys.exit("Correlation matrix size does not match the number of assets.")
            # convert the type
            self.all_cov = np.array(matrix, dtype=np.float64)
        except:
            return "Invalid matrix format"

    def construct_portfolio_matrix(self):
        num_assets = len(self.all_name)
        A = np.vstack((np.ones(num_assets), self.all_ror)).astype(np.float64)
        Sigma = self.all_cov
        self.matrix_l = np.block([[Sigma, A.T], [A, np.zeros((2, 2))]])

    def calculate_portfolio_volatility(self, rp):
        num_assets = len(self.all_name)
        matrix_r = np.zeros(num_assets + 2, dtype=np.float64)
        matrix_r[-2] = 1
        matrix_r[-1] = rp

        try:
            matrix_ans = np.linalg.solve(self.matrix_l, matrix_r)
            ans_vec = matrix_ans[:-2]
            vola = np.sqrt(np.dot(np.dot(ans_vec.T, self.all_cov), ans_vec))
            self.all_ans_vec.append(ans_vec.tolist())
            self.all_vola.append(vola)
        except np.linalg.LinAlgError:
            print("Singular matrix encountered during calculation")
            return None  # Ensure method returns None if it fails

    def calculate_restricted_volatility(self, rp):
        num_assets = len(self.all_name)
        index = int(rp * 1000 +500)
        if index < 0 or index >= len(self.all_ans_vec):
            print(f"Warning: Index {index} out of range for all_ans_vec with length {len(self.all_ans_vec)}")
            return

        ans_vec_temp = np.array(self.all_ans_vec[index])

        # Set negative weights to a small positive value
        min_positive_weight = 0.000001
        ans_vec_temp[ans_vec_temp < 0] = min_positive_weight

        # Normalize weights to ensure their sum equals 1
        if np.sum(ans_vec_temp) > 0:
            ans_vec_temp /= np.sum(ans_vec_temp)
        else:
            print("Warning: Sum of weights is zero after adjustment, cannot normalize.")
            return

        # Calculate volatility for the adjusted weight vector
        vola_res = np.sqrt(np.dot(np.dot(ans_vec_temp.T, self.all_cov), ans_vec_temp))
        self.all_vola_res.append(vola_res)

    def get_vola(self):
        vola_list = []
        for rp, volatility in zip(np.arange(-0.5, 1.5, 0.001), self.all_vola):
            vola_list.append((rp, volatility))
        return vola_list

    def get_vola_res(self):
        vola_res_list = []
        for rp, volatility_res in zip(np.arange(-0.5, 1.5, 0.001), self.all_vola_res):
            vola_res_list.append((rp, volatility_res))
        return vola_res_list


def calculate_portfolio_volatility(universe_dict, covariance_matrix):
    '''
    Calculate the volatility of the portfolio.
    args:   
        universe_dict: dict, the dictionary that contains the assets
        covariance_matrix: np.array, covariance matrix
    '''
    portfolio = Portfolio()
    portfolio.load_asset_data_from_dict(universe_dict)
    portfolio.read_and_compute_covariance_matrix(covariance_matrix)
    portfolio.construct_portfolio_matrix()

    for rp in np.arange(-0.5, 1.5, 0.001):
        portfolio.calculate_portfolio_volatility(rp)
        portfolio.calculate_restricted_volatility(rp)

    return portfolio.get_vola()

def calculate_restricted_volatility(universe_dict, covariance_matrix):
    '''
    Calculate the volatility of the portfolio (Short sale forbidden.)
    args:   
        universe_dict: dict, the dictionary that contains the assets
        covariance_matrix: np.array, covariance matrix
    '''
    portfolio = Portfolio()
    portfolio.load_asset_data_from_dict(universe_dict)
    portfolio.read_and_compute_covariance_matrix(covariance_matrix)
    portfolio.construct_portfolio_matrix()

    for rp in np.arange(-0.5, 1.5, 0.001):
        portfolio.calculate_portfolio_volatility(rp)
        portfolio.calculate_restricted_volatility(rp)

    return portfolio.get_vola_res()



def generate_universe_dict(ticker_list):
    '''
    从db数据库读取近一年的股价数据, 生成一个包含资产ticker, rate of return, standard deviation的字典,annualized 
    args:
        ticker_list: list, 包含股票ticker的列表
    '''
    data_dict = {
        'Ticker': [],
        'Rate of Return': [],
        'Standard Deviation': []
    }
    for ticker in ticker_list:
        data = get_stock_price_dict(ticker)
        time_scope = 252
        if len(data['adjClosePrices']) <= time_scope:
            data = {key: values[:len(data['adjClosePrices'])] for key, values in data.items()}
        else:
            data = {key: values[:time_scope] for key, values in data.items()}
        # print(data)
        data_dict['Ticker'].append(ticker)
        # 确保价格数据是浮点数类型
        adjClosePrices = np.array(data['adjClosePrices'][-time_scope:][::-1]).astype(float)
        # 计算年化收益率
        daily_returns = np.diff(adjClosePrices) / adjClosePrices[:-1]
        # print(daily_returns)
        rate_of_return = np.mean(daily_returns)
        annual_rate_of_return = (1 + rate_of_return) ** time_scope - 1
        # print(ticker, 'annual rate of return:', annual_rate_of_return)
        data_dict['Rate of Return'].append(annual_rate_of_return)
        # 计算标准差
        standard_deviation = np.std(daily_returns)
        annual_standard_deviation = standard_deviation * np.sqrt(252)
        data_dict['Standard Deviation'].append(annual_standard_deviation)
        # data_dict['Standard Deviation'].append(standard_deviation)
    return data_dict



def generate_covariance_matrix(ticker_list):
    '''
    Calculate the covariance matrix of returns.
    args:
        ticker_list: list, which contains the list of the stock symbol
    '''
    # Set the length of 1 year.
    time_scope = 252
    df = pd.DataFrame()
    
    for ticker in ticker_list:
        # Get the price data for each stock.
        data = get_stock_price_dict(ticker)
        # Convert to ndarray for further calculation.
        adjClosePrices = np.array(data['adjClosePrices'][:time_scope][::-1]).astype(float)  
        # print('*********************************************************')
        # print(adjClosePrices)
        
        # Add the adjusted close prices to the dataframe.
        df[f'{ticker}'] = adjClosePrices
        df[f'{ticker}_rtn'] = df[f'{ticker}'].pct_change()

    # Drop the NaN value.
    df = df.dropna()
    
    # Drop the excessive columns.
    for ticker in ticker_list:
        df = df.drop(f'{ticker}', axis=1)

    # Calculate the covariance matrix.
    covariance_matrix = df.cov()
    # print(covariance_matrix)
    
    return covariance_matrix


def calculate_sharpe_ratio(position_dict, risk_free_rate):
    '''
    Calculate the sharpe ratio.
    args:
        position_dict: dict, which contains the dictionary of "asset symbol, position quantity, unit price"
        {'A': {'quantity': 100, 'unit_price': 100}, 'AAPL': {'quantity': 200, 'unit_price': 50}}
        risk_free_rate: float
    '''
    # Generate the stock list and the covariance matrix.
    stock_symbol_list = list(position_dict.keys())
    stock_universe = generate_universe_dict(stock_symbol_list)
    covariance_matrix = generate_covariance_matrix(stock_symbol_list)

    # Calculate the weights for the stocks
    total_value = sum(position['unit_price'] * position['quantity'] for position in position_dict.values())
    for position in position_dict.values():
        position['weight'] = (position['unit_price'] * position['quantity']) / total_value


    # Calculate the weighted ROR for the portfolio.
    weighted_rate_of_return = sum(
        position['weight'] * stock_universe['Rate of Return'][stock_universe['Ticker'].index(symbol)]
        for symbol, position in position_dict.items() if symbol in stock_universe['Ticker']
    )
    

    # Convert the weights to ndarrray.
    weights = np.array([position['weight'] for position in position_dict.values()])

    # Calculate the volatility of the portfolio
    portfolio_variance = weights.T @ covariance_matrix @ weights
    portfolio_volatility = np.sqrt(portfolio_variance)
    # print(f'portfolio volatility is {portfolio_volatility}')

    # 将日回报率和无风险利率转换为年化形式
    # annual_weighted_rate_of_return = (1 + weighted_rate_of_return) ** 252 - 1
    annual_weighted_rate_of_return = weighted_rate_of_return
    # print(f'return is {annual_weighted_rate_of_return}.')

    # Get the annual risk free rate.
    annual_risk_free_rate = risk_free_rate

    # Calculate the Sharpe Ratio
    sharpe_ratio = (annual_weighted_rate_of_return - annual_risk_free_rate) / portfolio_volatility
    # print(f'sharpe_ratio is {sharpe_ratio}.')

    return sharpe_ratio

def calculate_weighted_return_and_risk(position_dict):
    '''
    Calculate the weighted return and risk for the portfolio.
    args:
        position_dict: dict, which contains the dictionary of "asset symbol, position quantity, unit price"
        {'A': {'quantity': 100, 'unit_price': 100}, 'AAPL': {'quantity': 200, 'unit_price': 50}}
    '''
    # Generate the stock list and the covariance matrix.
    stock_symbol_list = list(position_dict.keys())
    stock_universe = generate_universe_dict(stock_symbol_list)
    covariance_matrix = generate_covariance_matrix(stock_symbol_list)

    # Calculate the weights for the stocks
    total_value = sum(position['unit_price'] * position['quantity'] for position in position_dict.values())
    for position in position_dict.values():
        position['weight'] = (position['unit_price'] * position['quantity']) / total_value

    # Calculate the weighted ROR for the portfolio.
    weighted_rate_of_return = sum(
        position['weight'] * stock_universe['Rate of Return'][stock_universe['Ticker'].index(symbol)]
        for symbol, position in position_dict.items() if symbol in stock_universe['Ticker']
    )
    

    # Convert the weights to ndarrray.
    weights = np.array([position['weight'] for position in position_dict.values()])

    # Calculate the volatility of the portfolio
    portfolio_variance = weights.T @ covariance_matrix @ weights
    portfolio_volatility = np.sqrt(portfolio_variance)


    return weighted_rate_of_return, portfolio_volatility

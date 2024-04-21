import unittest
from __init__ import create_app # 导入你的Flask应用工厂函数
from modules.database.db import get_db # 导入数据库相关函数
from init_db import init_db
import os
DATABASE_TEST = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'bigbucksdb.db')

class TEST_AUTH(unittest.TestCase):
    def setUp(self):
        """测试前执行的设置"""
        self.app = create_app() # 假设你有一个可以接受测试配置的工厂函数
        self.client = self.app.test_client()
        # 初始化数据库，如果需要的话
        with self.app.app_context():
            init_db(DATABASE_TEST) # 初始化测试数据库
            # 可以在这里添加测试用户，确保测试环境与实际情况相符
            db = get_db(DATABASE_TEST)
            db.execute("INSERT INTO user (username, password, is_admin, balance) VALUES ('testuser', 'scrypt:32768:8:1$EJpz4IGswcZuGlL3$8089e0de328a19756786651579355167085de7e09118bc9b6b9689f83047297626eaf21bc82be92caedc03c612b183e6eaa81c01c3543ff8b97cf6d53b785652', 0, 1000000)")
            db.commit()

    def tearDown(self):
        """测试后执行的清理，如关闭数据库连接"""
        with self.app.app_context():
            init_db(DATABASE_TEST)

    def test_login_success(self):
        """测试用户成功登录"""
        response = self.client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'testpassword'
        }, follow_redirects=False)  # 注意这里改为了 False，以便捕获重定向前的响应

        # 检查是否接收到重定向响应
        self.assertEqual(response.status_code, 302, "应该收到一个重定向响应")

    def test_login_fail(self):
        """测试用户登录失败（错误的密码）"""
        response = self.client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'wrongpassword',
            'is_admin': 0
        })
        self.assertIn(b'Incorrect password.', response.data) # 确保响应中有错误消息
    
    def test_register_success(self):
        """测试用户成功注册"""
        response = self.client.post('/auth/register', data={
            'username': 'testuser2',
            'password': 'testpassword',
            'admin_code': 'admin'
        }, follow_redirects=False)  # 注意这里改为了 False，以便捕获重定向前的响应        
        self.assertEqual(response.status_code, 302, "应该收到一个重定向响应")

    def test_register_fail(self):
        """测试用户注册失败（已经存在的用户）"""
        response = self.client.post('/auth/register', data={
            'username': 'testuser',
            'password': 'testpassword',
            'admin_code': ''
        })         
        self.assertIn(b'is already registered', response.data) # 确保响应中有错误消息
        # 未输入账号或者密码
        response = self.client.post('/auth/register', data={
            'username': '',
            'password': 'testpassword',
            'admin_code': ''
        })         
        self.assertIn(b'Username is required.', response.data) # 确保响应中有错误消息  
        response = self.client.post('/auth/register', data={
            'username': 'testuser2',
            'password': '',
            'admin_code': ''
        })      
        self.assertIn(b'Password is required.', response.data) # 确保响应中有错误消息

    def test_logout(self):
        response = self.client.get('/auth/logout',  follow_redirects=False)  
        self.assertEqual(response.status_code, 302, "应该收到一个重定向响应")    
        response = self.client.get('/auth/logout',  follow_redirects=True) 
        self.assertIn(b'Log In', response.data)
   

class TEST_TRADE(unittest.TestCase):
    def setUp(self):
        """测试前执行的设置"""
        self.app = create_app() # 假设你有一个可以接受测试配置的工厂函数
        self.client = self.app.test_client()
        # 初始化数据库，如果需要的话
        with self.app.app_context():
            init_db(DATABASE_TEST) # 初始化测试数据库
            # 可以在这里添加测试用户，确保测试环境与实际情况相符
            db = get_db(DATABASE_TEST)
            db.execute("INSERT INTO user (username, password, is_admin, balance) VALUES ('testuser', 'scrypt:32768:8:1$EJpz4IGswcZuGlL3$8089e0de328a19756786651579355167085de7e09118bc9b6b9689f83047297626eaf21bc82be92caedc03c612b183e6eaa81c01c3543ff8b97cf6d53b785652', 0, 1000000)")
            # db.execute("INSERT INTO transactions (transaction_date, transaction_type, symbol, unit_price, volume) VALUES (2022-01-01, 'buy', 'AA', 100, 88)")
            db.commit()    
    
    def tearDown(self):
        """测试后执行的清理，如关闭数据库连接"""
        with self.app.app_context():
            init_db(DATABASE_TEST)  

    def test_get_main_without_login(self):
        '''未登录的情况下，访问trade会跳转到login'''
        response = self.client.get('/trade/main',  follow_redirects=False)  
        self.assertEqual(response.status_code, 302, "应该收到一个重定向响应") 
        response = self.client.get('/trade/main',  follow_redirects=True)  
        self.assertIn(b'Login Required', response.data)

    def test_get_main_with_login(self):
        '''登陆到情况下可以访问'''
        self.client.post('/auth/login', data={'username': 'testuser', 'password': 'testpassword'})
        response = self.client.get('/trade/main',  follow_redirects=False)
        self.assertEqual(response.status_code, 200) 
        self.assertNotIn(b'Login Required', response.data)
    
    def test_trade_value(self):
        # 先登录
        self.client.post('/auth/login', data={'username': 'testuser', 'password': 'testpassword'})
        # 正常购买请求
        response = self.client.post('/trade/main', data={
            'transactionType': 'buy',
            'adjClosePrice': 50,
            'amount': '10',
            'ticker': 'AA',
            'date': '2022-01-01'
        })
        self.assertNotIn(b'Error', response.data)

        # 余额不足
        response = self.client.post('/trade/main', data={
            'transactionType': 'buy',
            'adjClosePrice': 50,
            'amount': '2000000',
            'ticker': 'AA',
            'date': '2022-01-01'
        })
        self.assertIn(b'Error: Insufficient account balance', response.data)

        # 股票不足
        response = self.client.post('/trade/main', data={
            'transactionType': 'sell',
            'adjClosePrice': 50,
            'amount': '2000000',
            'ticker': 'AA',
            'date': '2022-01-01'
        })
        self.assertIn(b'Error: Insufficient quantity in portfolio', response.data)

        # 数量为负数
        response = self.client.post('/trade/main', data={
            'transactionType': 'buy',
            'adjClosePrice': 50,
            'amount': '-10',
            'ticker': 'AA',
            'date': '2022-01-01'
        })
        self.assertIn(b'Error: Cannot trade with a negative amount', response.data)
    
        # 数量为非整数
        response = self.client.post('/trade/main', data={
            'transactionType': 'buy',
            'adjClosePrice': 50,
            'amount': '10.01',
            'ticker': 'AA',
            'date': '2022-01-01'
        })
        self.assertIn(b'Error: Please enter a positive integer', response.data)
            
        # ticker 不存在
        response = self.client.post('/trade/main', data={
            'transactionType': 'buy',
            'adjClosePrice': 50,
            'amount': '10',
            'ticker': 'AAggfdsdfad',
            'date': '2022-01-01'
        })
        self.assertIn(b'Error: Ticker does not exist', response.data)  



if __name__ == '__main__':
    unittest.main()

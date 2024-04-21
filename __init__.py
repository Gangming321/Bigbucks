from flask import Flask, g, current_app, redirect, url_for, session
import os
from apscheduler.schedulers.background import BackgroundScheduler
from modules.get_data_from_api import refresh_all_info
from datetime import datetime

refresh_app = None
scheduler = None

def create_app():
    app = Flask(__name__)
    app.secret_key = "bigbigbucks2024"
    app.config['DATABASE'] = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'bigbucksdb.db')

    # 用来自动关闭数据库连接，防止锁死
    @app.teardown_appcontext
    def close_connection(exception):
        db = g.pop('db', None)
        if db is not None:
            db.close()
            
    # 重定向root到homepage
    @app.route('/')
    def redirect_home_page():
        return redirect(url_for('auth.login'))


    # 注册路由
    import modules.home_page as home_page  
    app.register_blueprint(home_page.bp)
    import modules.auth as auth
    app.register_blueprint(auth.bp)
    import modules.trade as trade
    app.register_blueprint(trade.bp)
    import modules.stock_info as stock_info
    app.register_blueprint(stock_info.bp)
    import modules.risk_analysis as risk_analysis
    app.register_blueprint(risk_analysis.bp)
    import modules.admin as admin
    app.register_blueprint(admin.bp)


    global scheduler
    # 初始化调度器
    if scheduler is None:
        scheduler = BackgroundScheduler()
        scheduler.add_job(
            func=refresh_stock_data,
            trigger='cron',  # 使用cron风格的触发器
            hour='17-23',    # 每天17点到23点执行一次
            minute='0',      # 每小时的0分钟执行
            id='stock_refresh_job',  # 任务ID
            name='Refresh stock data every minute',  # 任务名称
            replace_existing=True)  # 如果任务已存在，替换它
        scheduler.start()
    
    @app.teardown_appcontext
    def shutdown_scheduler(exception):
        if scheduler and scheduler.running:
            print('Shutting down scheduler')    
            scheduler.shutdown(wait=False)
        return exception
    
    return app

# 创建一个新的app用来刷新数据
def create_refresh_app():
    app = Flask(__name__)
    app.secret_key = "bigbigbucks2024"
    app.config['DATABASE'] = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'bigbucksdb.db')
    return app


def refresh_stock_data():
    global refresh_app
    if refresh_app is None:
        refresh_app = create_refresh_app()
    with refresh_app.app_context():
        print('Auto refreshing all info at', datetime.now())
        refresh_all_info()
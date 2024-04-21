### 运行这个来初始化数据库
import os
from __init__ import create_app  

SCHEMA_SQL_PATH = os.path.join(os.path.dirname(__file__), 'modules', 'database', 'schema.sql')
# SCHEMA_SQL_PATH = os.path.join(os.getcwd(), 'modules', 'database', 'schema.sql')
DATABASE = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'bigbucksdb.db')

app = create_app()

def init_db(db_path=DATABASE):
    with app.app_context():
        # 使用应用上下文中的 get_db 函数
        from modules.database.db import get_db
        db = get_db(db_path)
        with open(SCHEMA_SQL_PATH, mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

if __name__ == '__main__':
    print('Initializing the database...')
    init_db()
    print('Database initialized.')

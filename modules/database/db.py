import sqlite3
from flask import g,current_app
import os

DATABASE = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'bigbucksdb.db')


# def get_db():
#     if 'db' not in g:
#         g.db = sqlite3.connect(
#             current_app.config['DATABASE'],
#             detect_types=sqlite3.PARSE_DECLTYPES
#         )
#         g.db.row_factory = sqlite3.Row

#     return g.db

def get_db(db_path=None):
    if 'db' not in g:
        # 如果没有提供db_path，使用配置中的DATABASE路径
        database_path = db_path if db_path else current_app.config.get('DATABASE', DATABASE)
        g.db = sqlite3.connect(
            database_path,
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row

    return g.db


# def init_db():
#     db = get_db()
#     with current_app.open_resource('schema.sql') as f:
#         db.executescript(f.read().decode('utf8'))
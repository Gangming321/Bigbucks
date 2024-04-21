# 运行这个文件来打开网页服务器
from __init__ import create_app



app = create_app()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)


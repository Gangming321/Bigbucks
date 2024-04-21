# 使用官方 Python 运行环境作为父镜像
FROM python:3.8-slim

# 设置工作目录
WORKDIR /app

# 将当前目录内容复制到位于 /app 的容器中
COPY . /app

# 更新 pip 到最新版本，并显示版本
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    && rm -rf /var/lib/apt/lists/*

# 更新 pip 并安装依赖
RUN pip install --upgrade pip && pip install -r requirements.txt

# 初始化数据库（如果需要）
RUN python init_db.py

# 使端口 5001 可供此容器外的环境使用
EXPOSE 5001

# 在容器启动时运行应用程序
CMD ["python", "run.py"]

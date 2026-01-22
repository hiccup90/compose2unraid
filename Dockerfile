# Dockerfile
FROM python:3.9-alpine

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 拷贝代码
COPY . .

# 设置环境变量，确保 Python 输出直接刷新到日志
ENV PYTHONUNBUFFERED=1

EXPOSE 5000

CMD ["python", "app.py"]

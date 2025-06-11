FROM python:3.12-slim
ENV TZ=Asia/Shanghai
WORKDIR /root/tgbot
RUN #apt-get update && apt-get install -y --no-install-recommends ffmpeg && apt-get clean && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml /root/tgbot/
RUN pip install --no-cache-dir uv && uv sync
COPY src/ /root/tgbot/


EXPOSE 8080
VOLUME ["/data"]

CMD ["python","-u", "main.py"]
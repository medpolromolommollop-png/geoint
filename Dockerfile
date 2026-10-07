FROM python:3.11-slim

RUN useradd -m -u 1000 user
WORKDIR /home/user/app

COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY --chown=user geoint.py .

USER user
ENV HOME=/home/user PATH=/home/user/.local/bin:$PATH

CMD ["python", "geoint.py"]

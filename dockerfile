FROM pytorch/pytorch:2.7.1-cuda12.8-cudnn9-devel

WORKDIR /app
ENV PYTHONPATH=/app

# Instalacja zależności
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopiujemy pliki do kontenera
COPY main.py ./
COPY LLM-config.yml ./
COPY modules ./modules

VOLUME /app/pllum-lora-model
VOLUME /app/models--CYFRAGOVPL--Llama-PLLuM-8B-chat
#COPY models--CYFRAGOVPL--Llama-PLLuM-8B-chat /app/model


CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

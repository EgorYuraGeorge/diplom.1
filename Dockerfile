FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p uploads 
&& mkdir -p uploads/videos 
&& mkdir -p uploads/homeworks 
&& mkdir -p uploads/answers 
&& mkdir -p uploads/chat_files

EXPOSE 5000

CMD ["python", "app.py"]
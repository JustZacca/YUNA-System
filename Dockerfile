# Usa un'immagine base di Python
FROM python:3.13-slim

# Imposta la cartella di lavoro
WORKDIR /app

# Copia i file del progetto nella cartella di lavoro
COPY . /app
COPY .env /app/.env

# Installa le dipendenze
RUN pip install --no-cache-dir -r requirements.txt

# Espone la porta (se la tua app serve su una porta, come un web server)
EXPOSE 5000

# Comando per eseguire l'app (modifica se necessario)
CMD ["python", "kan.py"]

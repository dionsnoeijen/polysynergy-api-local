FROM python:3.11-slim

WORKDIR /app

# Install dependencies (minimal)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Set env for SQLite path or other config (optioneel)
ENV PROJECT_DB=./data/project.db

# Expose FastAPI port
EXPOSE 8090

# Start server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8090"]
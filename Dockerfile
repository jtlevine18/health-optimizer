FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ .
RUN npm run build

FROM python:3.11-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config.py .
COPY src/ src/

# Copy built frontend to serve as static files
COPY --from=frontend-build /app/frontend/dist /app/static

# Serve frontend from FastAPI
RUN pip install --no-cache-dir aiofiles

EXPOSE 7860

CMD ["python", "-m", "uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "7860"]

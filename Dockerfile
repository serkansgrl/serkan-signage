FROM python:3.12-alpine
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN addgroup -S signage && adduser -S -G signage signage
# This build intentionally fails until reviewed application source is added.
COPY app.py /app/app.py
RUN python -m py_compile /app/app.py && chown signage:signage /app/app.py
USER signage
EXPOSE 8098
CMD ["python", "/app/app.py"]

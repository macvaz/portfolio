# Official Playwright Python image (browsers + OS deps + Python).
# Docs: https://playwright.dev/docs/docker
FROM mcr.microsoft.com/playwright/python:v1.55.0-noble

WORKDIR /app

# Pin Playwright Python to the same major/minor as the image browsers.
RUN pip install --no-cache-dir playwright==1.55.0

COPY get_morningstar_token.py /app/get_morningstar_token.py

ENTRYPOINT ["python", "/app/get_morningstar_token.py"]

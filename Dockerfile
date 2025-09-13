FROM python:3.11-slim
RUN useradd -m -u 1000 user

USER user

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg sox libsox-fmt-all libsndfile1 && rm -rf /var/lib/apt/lists/*


ENV HOME=/home/user \
	PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

# Install base (slow-changing and heavy) requirements first
COPY --chown=user requirements-base.txt .
RUN pip install --no-cache-dir --timeout=900 -r requirements-base.txt

# Download Demucs model by running a test separation and then remove the output
COPY --chown=user test.mp3 .
RUN python -m demucs -n htdemucs_6s -d cpu test.mp3
RUN rm -r separated

# Now copy the rest of your requirements and install them
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=user main.py .
EXPOSE 7860
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
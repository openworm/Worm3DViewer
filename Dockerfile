FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git  \
    libxrender1 procps libgl1-mesa-glx xvfb \
    && rm -rf /var/lib/apt/lists/*


COPY requirements.txt ./
RUN pip3 install  -r   requirements.txt


COPY *.py *.stl *.obj ./
COPY Sibernetic/* ./Sibernetic/
COPY NeuroML2/* ./NeuroML2/
COPY NeuroML2/cells/* ./NeuroML2/cells/

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
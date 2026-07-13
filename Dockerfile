FROM python:3.13-slim

WORKDIR /app

RUN apt-get update
RUN apt-get install -y \
    build-essential \
    curl \
    git  
RUN apt-get install -y \
    libxrender1 procps libgl1 xvfb \
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
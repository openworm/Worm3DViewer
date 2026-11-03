FROM python:3.13-slim

WORKDIR /app

RUN apt-get update
RUN apt-get install -y \
    curl   
RUN apt-get install -y \
    build-essential \
    git  
RUN apt-get install -y \
    libxrender1 procps libgl1 xvfb \
    && rm -rf /var/lib/apt/lists/*


COPY requirements.txt ./
# TODO: test/update with latest versions 
RUN pip3 install  -r   requirements.txt
RUN pip3 install pyvista==0.46.4 stpyvista==0.1.4


COPY *.py *.stl *.obj ./
COPY Sibernetic/* ./Sibernetic/
COPY NeuroML2/* ./NeuroML2/
COPY NeuroML2/cells/* ./NeuroML2/cells/

EXPOSE 8080

HEALTHCHECK CMD curl --fail http://localhost:8080/_stcore/health

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0"]
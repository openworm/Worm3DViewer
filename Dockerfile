FROM python:3.13-slim

WORKDIR /app

RUN apt-get update
RUN apt-get install -y \
    curl unzip
RUN apt-get install -y \
    build-essential \
    git  
RUN apt-get install -y \
    libxrender1 procps libgl1 xvfb \
    && rm -rf /var/lib/apt/lists/*


COPY requirements.txt ./
# TODO: test/update with latest versions 
RUN pip3 install  -r   requirements.txt
RUN pip3 install pyvista stpyvista


# The Witvliet et al. 2021 cell STL files (not in the repo): downloaded here, so
# this layer is cached until the script changes
COPY download_witvliet2021.sh ./
RUN ./download_witvliet2021.sh

COPY *.py *.stl *.obj ./
COPY .streamlit/* ./.streamlit/
# The splash screen: its scenes (splash.json) and their pictures, and the logo
COPY images/splash.json images/*.png ./images/
COPY fastview_web/*.html fastview_web/*.js ./fastview_web/
COPY Sibernetic/* ./Sibernetic/
COPY NeuroML2/* ./NeuroML2/
COPY NeuroML2/cells/* ./NeuroML2/cells/

# Build the mesh caches (in ./cache) that the app reads: it does not build meshes
# itself (see meshcache.py). Then export the models for the fast view (fastview.py)
RUN python models3d.py -cache \
    && python virtualworm.py -cache \
    && python witvliet2021.py -cache \
    && python fastview.py -export

EXPOSE 8080

HEALTHCHECK CMD curl --fail http://localhost:8080/_stcore/health

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0"]
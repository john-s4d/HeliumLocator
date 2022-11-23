PY=python 
.PHONY:
    run
    all
    typehint
    lint
    black
    install

run:
    # $(PY) -i src/main.py 0 0
    jupyter-lab

all:
    @+make black
    @+make typehint
    @+make lint
    @+make run

typehint:
    mypy --ignore-missing-imports src/

lint:
    pylint src/

black:
    black -l 79 src/*.py

install:
    pip install pandas==1.4.0 jupyterlab==3.2.9 
    conda install ipykernel ipywidgets==7.6.5
    $(PY) -m ipykernel install --user --name gpslink
    pip install folium==0.12.1.post1 matplotlib==3.5.1 scipy==1.8.0 scikit-learn==1.0.2
    pip install google-api-python-client pyCrypto
    pip3 install --upgrade oauth2client
    pip install earthengine-api
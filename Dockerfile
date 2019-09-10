# This Dockerfile constructs a docker image that contains an installation
# of the popeye library.
#
# Example build:
#   docker build --no-cache --tag nben/popeye `pwd`
#

FROM continuumio/anaconda:2019.03

LABEL MAINTAINER="Noah C. Benson <nben@nyu.edu>"

ENV PATH "/opt/conda/bin:$PATH"

RUN apt-get update && apt-get upgrade -y && apt-get install -y gcc libgl1-mesa-glx

RUN /opt/conda/bin/conda update --yes -n base conda \
 && /opt/conda/bin/conda install --yes -c conda-forge py4j nibabel s3fs
RUN /opt/conda/bin/conda install --yes -c conda-forge ipywidgets
RUN /opt/conda/bin/pip install --upgrade setuptools

RUN /opt/conda/bin/conda install --yes numpy scipy matplotlib pandas
RUN /opt/conda/bin/pip install pimms neuropythy
RUN git clone https://github.com/kdesimone/popeye \
 && cd popeye \
 && /opt/conda/bin/pip install -r requirements.txt \
 && /opt/conda/bin/python setup.py install

COPY docker/main.sh /main.sh
COPY docker/main.py /main.py
RUN chmod 755 /main.sh

# And mark it as the entrypoint
#CMD ["/main.sh"]
ENTRYPOINT ["tini", "-g", "--", "/main.sh"]

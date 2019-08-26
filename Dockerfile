# This Dockerfile constructs a docker image that contains an installation
# of the popeye library.
#
# Example build:
#   docker build --no-cache --tag nben/popeye `pwd`
#

FROM continuumio/anaconda:2019.03

LABEL MAINTAINER="Noah C. Benson <nben@nyu.edu>"

run apt-get update && apt-get upgrade -y && apt-get install -y gcc libgl1-mesa-glx

RUN conda update --yes -n base conda && conda install --yes -c conda-forge py4j nibabel s3fs
RUN conda install --yes -c conda-forge ipywidgets
RUN pip install --upgrade setuptools

RUN conda install --yes numpy scipy matplotlib pandas
RUN pip install pimms neuropythy popeye

COPY docker/main.sh /main.sh
COPY docker/main.py /main.py
RUN chmod 755 /main.sh

# And mark it as the entrypoint
#CMD ["/main.sh"]
ENTRYPOINT ["tini", "-g", "--", "/main.sh"]

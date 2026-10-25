FROM condaforge/miniforge3:latest

WORKDIR /app
COPY environment.yml /tmp/environment.yml
RUN conda env create -f /tmp/environment.yml && conda clean -afy
ENV PATH="/opt/conda/envs/sales-analytics/bin:${PATH}"
COPY . /app
CMD ["bash"]

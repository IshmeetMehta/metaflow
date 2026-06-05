FROM us-west1-docker.pkg.dev/platform-sandbox-495413/spsearch-qualitycheck-metaflow-image/sp-search-firelight-qualitycheck:v1

# Force-upgrade pip to the latest version so it can handle modern PyPI dependency trees
RUN pip install --upgrade pip

# Install the packages straight from the public PyPI index.
# (If 'fireworks-ai-rec' was an internal fork, we use 'fireworks-ai' which is the official open-source package)
RUN pip install --no-cache-dir \
    fireworks-ai==0.19.20 \
    dnn==0.7.5
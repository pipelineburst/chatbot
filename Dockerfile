FROM docker.io/library/python:3.9-slim@sha256:8a84bc20c838be617ba720f98a894d41c4fdaa8de27c2233b9ed9335fd061420

WORKDIR /src

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt \
    && apt-get update && apt-get -y install \
       vim \
       curl 

# RUN mkdir /usr/src/app/.streamlit
# COPY config.toml /usr/src/app/.streamlit/config.toml 
ENV STREAMLIT_SERVER_RUN_ON_SAVE=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
ENV STREAMLIT_THEME_BASE="dark"
ENV STREAMLIT_THEME_TEXT_COLOR="#00617F"
ENV STREAMLIT_THEME_FONT="sans serif"
ENV STREAMLIT_THEME_BACKGROUND_COLOR="#C1C6C8"
ENV STREAMLIT_THEME_SECONDARY_BACKGROUND_COLOR="#00617F"
ENV STREAMLIT_THEME_PRIMARY_COLOR="#C1C6C8"

COPY src/ src/

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["streamlit", "run", "src/main.py", "--server.port=8501", "--server.address=0.0.0.0"]
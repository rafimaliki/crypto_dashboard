FROM apache/superset:6.0.0

USER root
RUN /app/.venv/bin/python -m ensurepip
RUN /app/.venv/bin/python -m pip install psycopg2-binary prophet plotly

USER superset

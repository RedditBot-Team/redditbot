FROM python:3

RUN python3 -m venv /opt/venv

COPY requirements.txt .
RUN . /opt/venv/bin/activate && pip install -r requirements.txt

COPY src ./src
COPY redditbot-discord-firebase-adminsdk.json .
CMD . /opt/venv/bin/activate && exec python /src/main.py
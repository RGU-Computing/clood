FROM python:3.7-buster

WORKDIR /app

RUN \
  echo "deb https://deb.nodesource.com/node_16.x buster main" > /etc/apt/sources.list.d/nodesource.list && \
  wget -qO- https://deb.nodesource.com/gpgkey/nodesource.gpg.key | apt-key add - && \
  apt-get update && \
  apt-get install -yqq nodejs yarn && \
  pip install -U pip && pip install pipenv && \
  npm i -g npm@^8

RUN pip install --no-cache --upgrade pip setuptools

# Serverless part
COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

RUN npm install
RUN npm install serverless
RUN npm i -g nodemon
RUN npm install serverless-python-requirements


EXPOSE 3000

CMD ["node", "./node_modules/serverless/bin/serverless.js", "requirements", "install"]
CMD ["nodemon","-e","py","--exec", "npm", "run","dev"]




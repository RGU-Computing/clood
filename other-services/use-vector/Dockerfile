FROM node:17-alpine as build

WORKDIR /app
ENV PATH /app/node_modules/.bin:$PATH

# Serverless part
COPY serverless.yml /app
COPY package.json /app
COPY package-lock.json /app
COPY . /app
RUN npm ci
RUN npm install serverless


EXPOSE 4100

CMD ["node", "./node_modules/serverless/bin/serverless.js", "offline", "start",  "--host", "0.0.0.0"]
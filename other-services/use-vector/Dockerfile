FROM node:20-alpine as build

WORKDIR /app
ENV PATH /app/node_modules/.bin:$PATH

# Serverless part
COPY serverless.yml /app
COPY package.json /app
COPY package-lock.json /app
COPY . /app
RUN npm config set fetch-timeout 60000
RUN npm config set fetch-retries 5
RUN npm config set fetch-retry-factor 10
RUN npm ci  --legacy-peer-deps
RUN npm install serverless@3.11.0 --legacy-peer-deps


EXPOSE 4100

CMD ["npx", "serverless", "offline", "start", "--host", "0.0.0.0"]
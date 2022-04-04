# build environment
FROM node:17-alpine as build
WORKDIR /dashboard
ENV PATH /dashboard/node_modules/.bin:$PATH

COPY . ./
RUN npm i
EXPOSE 8000
CMD [ "npm", "start" ]
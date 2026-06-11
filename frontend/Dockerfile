FROM node:22-slim AS build
WORKDIR /srv
COPY package.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /srv/dist /usr/share/nginx/html
EXPOSE 80

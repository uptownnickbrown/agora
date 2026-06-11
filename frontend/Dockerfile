FROM node:22-slim AS build
WORKDIR /srv
COPY package.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /srv/dist /usr/share/nginx/html
# Local-dev defaults; Railway overrides PORT/API_HOST/DNS_RESOLVER per env.
ENV PORT=80 API_HOST=api API_PORT=8000 DNS_RESOLVER="127.0.0.11 ipv6=off"
EXPOSE 80

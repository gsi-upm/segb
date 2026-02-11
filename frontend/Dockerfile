FROM node:20-alpine3.19 AS build

WORKDIR /app
COPY segb-ui/package*.json ./

# Use npm ci to install dependencies based on package-lock.json (it fails if package-lock.json is missing or differs from package.json)
RUN npm ci

ARG VITE_API_URL=/api
ENV VITE_API_URL=${VITE_API_URL}

COPY segb-ui .
RUN npm run build

FROM nginx:stable-alpine3.21-perl

COPY infrastructure/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=3s --retries=10 CMD wget -qO- http://localhost:8080/ || exit 1

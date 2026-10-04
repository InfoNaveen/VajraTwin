# VajraTwin frontend — React + Vite GCS, served as static files by nginx.
# Build stage
FROM node:20-alpine AS build
WORKDIR /app

# VITE_API_BASE_URL is baked at build time (Vite inlines import.meta.env).
# For same-host docker-compose the browser reaches the backend on localhost:8000.
ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

COPY package.json package-lock.json* ./
RUN npm install
COPY . .
RUN npm run build

# Serve stage
FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]

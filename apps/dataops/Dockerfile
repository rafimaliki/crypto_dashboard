FROM node:lts-alpine AS listener
WORKDIR /app
COPY package.json package.json
RUN npm i
COPY listener.js listener.js
CMD ["node", "listener.js"]

FROM node:lts-alpine AS persistence
WORKDIR /app
COPY package.json package.json
RUN npm i
COPY persistence.js persistence.js
CMD ["node", "persistence.js"]

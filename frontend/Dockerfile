FROM node:23-alpine

WORKDIR /app

COPY package.json .
COPY package-lock.json .

RUN apk update
RUN npm ci

COPY . .
RUN npm run build

ENV HOST=0.0.0.0

CMD ["npm", "run", "preview"]
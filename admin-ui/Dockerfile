# Admin UI image — Next.js 14 dev mode
FROM node:20-alpine

WORKDIR /app

# ติดตั้ง deps ก่อน (cache layer)
COPY package.json package-lock.json* ./
RUN npm install

# Copy source
COPY . .

EXPOSE 3000

# Dev mode (override ใน production ด้วย `npm run build && npm start`)
CMD ["npm", "run", "dev"]

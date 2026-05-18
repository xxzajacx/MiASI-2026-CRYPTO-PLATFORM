FROM node:20-alpine as builder

WORKDIR /app

# Copy package files first for better layer caching
COPY package*.json ./
RUN npm install

# Copy source code
COPY . .

# Build the React app
RUN npm run build


FROM nginx:alpine

# Copy built files from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

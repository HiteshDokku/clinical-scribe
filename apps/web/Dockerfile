# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files in their correct monorepo structure
COPY apps/web/package*.json ./apps/web/
# Run npm ci from inside the app directory
WORKDIR /app/apps/web
RUN npm ci

# Copy the actual source and the packages directory
WORKDIR /app
COPY apps/web/ ./apps/web/
COPY packages/ ./packages/

# Build the app
WORKDIR /app/apps/web
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built assets from builder
COPY --from=builder /app/apps/web/dist /usr/share/nginx/html

# Copy custom nginx configuration
COPY apps/web/nginx.conf /etc/nginx/conf.d/default.conf

# Default nginx configuration will serve the files on port 80
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

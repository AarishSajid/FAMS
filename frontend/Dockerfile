FROM node:20-alpine

# Set working directory
WORKDIR /app

# Install dependencies based on the preferred package manager
COPY package.json package-lock.json* ./
RUN npm install

# Copy the rest of the application code
COPY . .

# Build the immutable production bundle
RUN npm run build

# Run as the built-in non-root user; it must own the app dir
RUN chown -R node:node /app
USER node

# Expose the port the app runs on
EXPOSE 3000

# Start the production server (root filesystem is read-only at runtime;
# .next/cache and /tmp are provided via tmpfs in docker-compose)
CMD ["npm", "run", "start"]

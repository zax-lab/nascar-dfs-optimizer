# Use node:20-alpine as base image for building
FROM node:20-alpine AS builder

# Set working directory
WORKDIR /app

# Copy package files from frontend directory
COPY apps/frontend/package.json apps/frontend/package-lock.json* ./

# Install dependencies (use npm install as fallback if no lockfile)
RUN npm install

# Copy application code
COPY apps/frontend/ ./

# Build Next.js app
RUN npm run build

# Use node:20-alpine as base image for production
FROM node:20-alpine AS runner

# Set working directory
WORKDIR /app

# Install wget for health checks
RUN apk add --no-cache wget

# Create non-root user
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copy necessary files from builder
# Use shell form to handle potentially missing public directory
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

# Copy public directory if it exists (handled by pre-creating it)
COPY --from=builder /app/public ./public

# Set ownership
RUN chown -R nextjs:nodejs /app

# Set environment to production
ENV NODE_ENV=production

# Expose port 3000
EXPOSE 3000

# Switch to non-root user
USER nextjs

# Run production server
CMD ["node", "server.js"]

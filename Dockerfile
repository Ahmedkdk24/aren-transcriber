FROM node:18

# Set working directory
WORKDIR /workspace/aren-transcriber/frontend

# Install dependencies
COPY package.json package-lock.json ./
RUN npm install

# Copy project files
COPY . .

# Build the frontend
RUN npm run build

# Expose frontend port
EXPOSE 3000

# Run frontend
CMD ["npm", "run", "start"]

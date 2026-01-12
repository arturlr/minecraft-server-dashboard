# Use Node.js LTS version
FROM node:20-alpine

# Set working directory
WORKDIR /app

# Install Python and pip for Python linting
RUN apk add --no-cache python3 py3-pip

# Copy package files for both dashboard and webapp
COPY dashboard/package*.json ./dashboard/
COPY webapp/package*.json ./webapp/

# Install dependencies for dashboard
WORKDIR /app/dashboard
RUN npm ci

# Install dependencies for webapp
WORKDIR /app/webapp
RUN npm ci

# Install ESLint and Prettier globally for linting
WORKDIR /app
RUN npm install -g eslint prettier eslint-plugin-vue @vue/eslint-config-prettier

# Install Python linters
RUN pip3 install --break-system-packages flake8 pylint black autopep8

# Copy the rest of the application
COPY . .

# Set working directory back to root
WORKDIR /app

# Default command
CMD ["/bin/sh"]

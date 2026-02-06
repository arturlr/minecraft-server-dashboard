## 1. Generate Secrets
bash
chmod +x setup-secrets.sh
./setup-secrets.sh


## 2. Create .env File
bash
cp .env.example .env
# Edit .env with your values:

AWS_REGION=us-west-2
INSTANCE_ID=local-dev
ECR_REGISTRY=514046899996.dkr.ecr.us-west-2.amazonaws.com
IMAGE_TAG=latest
MINECRAFT_VERSION=LATEST
MINECRAFT_MEMORY=2G
MINECRAFT_TYPE=VANILLA
TIMEZONE=America/Los_Angeles


## 3. Build Custom Images Locally
bash
cd docker/msd-metrics && docker build -t msd-metrics:latest .
cd ../msd-logs && docker build -t msd-logs:latest .
cd ../..


## 4. Start Everything
bash
docker-compose up -d


## 5. Verify
bash
docker-compose ps                     # All 3 running?
docker-compose logs minecraft         # Minecraft starting?
curl localhost:25566/health            # msd-logs healthy?
# Connect Minecraft client to localhost:25565


## 6. Useful Commands
bash
docker-compose logs -f                # Follow all logs
docker-compose restart minecraft      # Restart one service
docker-compose down                   # Stop everything
docker-compose down -v                # Stop + remove volumes
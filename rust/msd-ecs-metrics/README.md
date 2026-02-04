# ECS Minecraft Metrics Collector

Rust application for collecting Minecraft server metrics in ECS containers.

## Features

- **ECS-native**: Uses ECS metadata endpoints and environment variables
- **Multi-cluster support**: Includes cluster name in CloudWatch dimensions
- **Container health checks**: Built-in health check endpoint for ECS
- **Minecraft monitoring**: Player count and server status tracking
- **System metrics**: CPU, memory, and network bandwidth monitoring

## Environment Variables

Required:
- `SERVER_ID`: Custom server ID (e.g., minecraft-server-1)

Optional:
- `ECS_CLUSTER_NAME` or `CLUSTER_NAME`: Cluster name (auto-detected if not set)
- `ECS_TASK_ARN`: Task ARN (auto-detected if not set)

## Usage

### Build
```bash
./build.sh --docker
```

### Run locally
```bash
cargo run -- --dry-run --host localhost --port 25565
```

### Health check
```bash
./target/release/msd-ecs-metrics --health-check
```

## CloudWatch Metrics

Namespace: `MinecraftDashboard/ECS`

Metrics:
- `CPUUtilization` (Percent)
- `MemoryUtilization` (Percent) 
- `ActivePlayers` (Count)
- `NetworkIn/Out` (Bytes/Second)
- `ContainerHealth` (0/1)

Dimensions:
- `ServerId`: Custom server ID
- `ClusterName`: ECS cluster name

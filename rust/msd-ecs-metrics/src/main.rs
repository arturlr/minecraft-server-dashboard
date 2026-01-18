use anyhow::{Context, Result};
use aws_sdk_cloudwatch::types::{Dimension, MetricDatum, StandardUnit};
use sysinfo::{Networks, System};
use std::fs;
use std::path::Path;
use std::time::{SystemTime, UNIX_EPOCH};
use tokio::time::{sleep, Duration};
use mc_query::status;

const NAMESPACE: &str = "MinecraftDashboard/ECS";
const STATE_FILE: &str = "/tmp/network_monitor_state.json";
const INTERVAL_SECS: u64 = 60;

#[derive(serde::Serialize, serde::Deserialize, Default)]
struct NetworkState {
    prev_received: u64,
    prev_transmitted: u64,
    prev_time: u64,
}

struct MetricsCollector {
    cloudwatch_client: aws_sdk_cloudwatch::Client,
    server_id: String,
    cluster_name: String,
    task_arn: String,
    system: System,
    networks: Networks,
    server_host: String,
    server_port: u16,
}

impl MetricsCollector {
    async fn new(server_host: String, server_port: u16) -> Result<Self> {
        let config = aws_config::load_from_env().await;
        let cloudwatch_client = aws_sdk_cloudwatch::Client::new(&config);

        // Get ECS metadata
        let server_id = Self::get_server_id()?;
        let cluster_name = Self::get_cluster_name().await?;
        let task_arn = Self::get_task_arn().await?;

        Ok(Self {
            cloudwatch_client,
            server_id,
            cluster_name,
            task_arn,
            system: System::new_all(),
            networks: Networks::new_with_refreshed_list(),
            server_host,
            server_port,
        })
    }

    fn get_server_id() -> Result<String> {
        // Get from environment variable set in task definition
        std::env::var("SERVER_ID")
            .context("SERVER_ID environment variable not set")
    }

    async fn get_cluster_name() -> Result<String> {
        // Try ECS metadata endpoint first
        if let Ok(cluster) = Self::get_ecs_metadata("Cluster").await {
            return Ok(cluster);
        }
        
        // Fallback to environment variable
        std::env::var("ECS_CLUSTER_NAME")
            .or_else(|_| std::env::var("CLUSTER_NAME"))
            .unwrap_or_else(|_| "unknown".to_string())
            .pipe(Ok)
    }

    async fn get_task_arn() -> Result<String> {
        // Try ECS metadata endpoint
        if let Ok(task_arn) = Self::get_ecs_metadata("TaskARN").await {
            return Ok(task_arn);
        }
        
        // Fallback to environment variable or hostname
        std::env::var("ECS_TASK_ARN")
            .or_else(|_| {
                let hostname = std::env::var("HOSTNAME")?;
                Ok(format!("task/{}", hostname))
            })
            .unwrap_or_else(|_| "unknown".to_string())
            .pipe(Ok)
    }

    async fn get_ecs_metadata(field: &str) -> Result<String> {
        // ECS Task Metadata Endpoint V4
        let metadata_uri = std::env::var("ECS_CONTAINER_METADATA_URI_V4")
            .context("ECS_CONTAINER_METADATA_URI_V4 not available")?;
        
        let client = reqwest::Client::new();
        let response = client
            .get(&format!("{}/task", metadata_uri))
            .send()
            .await?;
        
        let metadata: serde_json::Value = response.json().await?;
        
        metadata.get(field)
            .and_then(|v| v.as_str())
            .map(|s| s.to_string())
            .context(format!("Field {} not found in ECS metadata", field))
    }

    fn load_network_state(&self) -> NetworkState {
        if Path::new(STATE_FILE).exists() {
            if let Ok(contents) = fs::read_to_string(STATE_FILE) {
                if let Ok(state) = serde_json::from_str(&contents) {
                    return state;
                }
            }
        }
        NetworkState::default()
    }

    fn save_network_state(&self, state: &NetworkState) -> Result<()> {
        let contents = serde_json::to_string(state)?;
        fs::write(STATE_FILE, contents)?;
        Ok(())
    }

    async fn collect_and_send_metrics(&mut self, dry_run: bool) -> Result<()> {
        let mut metric_data = Vec::new();
        let dimensions = vec![
            Dimension::builder()
                .name("ServerId")
                .value(&self.server_id)
                .build(),
            Dimension::builder()
                .name("ClusterName")
                .value(&self.cluster_name)
                .build(),
        ];

        let timestamp = aws_sdk_cloudwatch::primitives::DateTime::from_secs(
            SystemTime::now().duration_since(UNIX_EPOCH)?.as_secs() as i64
        );

        // Collect CPU metrics (container-level)
        self.system.refresh_cpu_usage();
        let cpu_usage = self.system.global_cpu_usage();

        metric_data.push(
            MetricDatum::builder()
                .metric_name("CPUUtilization")
                .value((cpu_usage as f64 * 100.0).round() / 100.0)
                .unit(StandardUnit::Percent)
                .set_dimensions(Some(dimensions.clone()))
                .timestamp(timestamp)
                .build(),
        );

        // Collect Memory metrics (container-level)
        self.system.refresh_memory();
        let total_memory = self.system.total_memory();
        let used_memory = self.system.used_memory();
        let memory_usage_percent = ((used_memory as f64 / total_memory as f64) * 10000.0).round() / 100.0;

        metric_data.push(
            MetricDatum::builder()
                .metric_name("MemoryUtilization")
                .value(memory_usage_percent)
                .unit(StandardUnit::Percent)
                .set_dimensions(Some(dimensions.clone()))
                .timestamp(timestamp)
                .build(),
        );

        // Collect Minecraft player count
        match self.get_minecraft_players().await {
            Ok(player_count) => {
                metric_data.push(
                    MetricDatum::builder()
                        .metric_name("ActivePlayers")
                        .value(player_count as f64)
                        .unit(StandardUnit::Count)
                        .set_dimensions(Some(dimensions.clone()))
                        .timestamp(timestamp)
                        .build(),
                );
            }
            Err(e) => eprintln!("Failed to get player count: {}", e),
        }

        // Collect Network bandwidth metrics
        self.networks.refresh(true);
        if let Some(network) = self.get_container_network() {
            let curr_received = network.total_received();
            let curr_transmitted = network.total_transmitted();
            let current_time = SystemTime::now().duration_since(UNIX_EPOCH)?.as_secs();

            let prev_state = self.load_network_state();

            if prev_state.prev_time > 0 {
                let time_diff = current_time - prev_state.prev_time;

                if time_diff > 0 {
                    let rx_bandwidth = (((curr_received - prev_state.prev_received) as f64) / (time_diff as f64) * 100.0).round() / 100.0;
                    let tx_bandwidth = (((curr_transmitted - prev_state.prev_transmitted) as f64) / (time_diff as f64) * 100.0).round() / 100.0;

                    metric_data.push(
                        MetricDatum::builder()
                            .metric_name("NetworkIn")
                            .value(rx_bandwidth.max(0.0))
                            .unit(StandardUnit::BytesSecond)
                            .set_dimensions(Some(dimensions.clone()))
                            .timestamp(timestamp)
                            .build(),
                    );

                    metric_data.push(
                        MetricDatum::builder()
                            .metric_name("NetworkOut")
                            .value(tx_bandwidth.max(0.0))
                            .unit(StandardUnit::BytesSecond)
                            .set_dimensions(Some(dimensions.clone()))
                            .timestamp(timestamp)
                            .build(),
                    );
                }
            }

            // Save current state for next iteration
            let new_state = NetworkState {
                prev_received: curr_received,
                prev_transmitted: curr_transmitted,
                prev_time: current_time,
            };
            self.save_network_state(&new_state)?;
        }

        // Container health metric
        let health_status = if self.is_healthy().await { 1.0 } else { 0.0 };
        metric_data.push(
            MetricDatum::builder()
                .metric_name("ContainerHealth")
                .value(health_status)
                .unit(StandardUnit::None)
                .set_dimensions(Some(dimensions.clone()))
                .timestamp(timestamp)
                .build(),
        );

        if dry_run {
            println!("\n=== DRY-RUN: Would send {} metrics to CloudWatch ===", metric_data.len());
            for metric in &metric_data {
                println!("  {} = {} {:?}",
                    metric.metric_name().unwrap_or("unknown"),
                    metric.value().unwrap_or(0.0),
                    metric.unit()
                );
            }
            println!("=== End of metrics ===\n");
        } else {
            // Send all metrics to CloudWatch
            if !metric_data.is_empty() {
                let metric_count = metric_data.len();
                self.cloudwatch_client
                    .put_metric_data()
                    .namespace(NAMESPACE)
                    .set_metric_data(Some(metric_data))
                    .send()
                    .await
                    .context("Failed to send metrics to CloudWatch")?;

                println!("Successfully sent {} metrics to CloudWatch for server {}", metric_count, self.server_id);
            }
        }
        Ok(())
    }

    async fn get_minecraft_players(&self) -> Result<i32> {
        let response = status(&self.server_host, self.server_port).await?;
        Ok(response.players.online as i32)
    }

    fn get_container_network(&self) -> Option<&sysinfo::NetworkData> {
        // In containers, typically eth0 is the main interface
        self.networks.get("eth0")
            .or_else(|| {
                // Fallback to first available interface
                self.networks.iter().next().map(|(_, data)| data)
            })
    }

    async fn is_healthy(&self) -> bool {
        // Basic health check - can we query the Minecraft server?
        self.get_minecraft_players().await.is_ok()
    }

    pub async fn health_check(&self) -> Result<()> {
        if self.is_healthy().await {
            println!("Health check: OK");
            Ok(())
        } else {
            anyhow::bail!("Health check: FAILED - Cannot connect to Minecraft server")
        }
    }
}

// Extension trait for pipe operations
trait Pipe<T> {
    fn pipe<F, U>(self, f: F) -> U
    where
        F: FnOnce(T) -> U;
}

impl<T> Pipe<T> for T {
    fn pipe<F, U>(self, f: F) -> U
    where
        F: FnOnce(T) -> U,
    {
        f(self)
    }
}

#[tokio::main]
async fn main() -> Result<()> {
    println!("Starting ECS Minecraft metrics collector...");

    // Parse command-line arguments
    let args: Vec<String> = std::env::args().collect();
    let dry_run = args.contains(&"--dry-run".to_string());
    let health_check = args.contains(&"--health-check".to_string());

    let mut server_host = "localhost".to_string();
    let mut server_port = 25565u16;

    // Parse host and port arguments
    for i in 0..args.len() {
        if args[i] == "--host" && i + 1 < args.len() {
            server_host = args[i + 1].clone();
        }
        if args[i] == "--port" && i + 1 < args.len() {
            if let Ok(port) = args[i + 1].parse::<u16>() {
                server_port = port;
            }
        }
    }

    let collector = MetricsCollector::new(server_host.clone(), server_port).await?;

    // Handle health check mode
    if health_check {
        return collector.health_check().await;
    }

    if dry_run {
        println!("Running in DRY-RUN mode - metrics will not be sent to CloudWatch");
    }

    println!("Monitoring server: {}:{}", server_host, server_port);
    println!("Server ID: {}", collector.server_id);
    println!("Cluster: {}", collector.cluster_name);
    println!("Task ARN: {}", collector.task_arn);

    let mut collector = collector;

    loop {
        match collector.collect_and_send_metrics(dry_run).await {
            Ok(_) => {},
            Err(e) => eprintln!("Error collecting metrics: {}", e),
        }

        sleep(Duration::from_secs(INTERVAL_SECS)).await;
    }
}

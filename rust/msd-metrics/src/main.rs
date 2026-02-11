use anyhow::{Context, Result};
use aws_sdk_cloudwatch::types::{Dimension, MetricDatum, StandardUnit};
use sysinfo::{Networks, System};
use std::fs;
use std::path::Path;
use std::time::{SystemTime, UNIX_EPOCH};
use tokio::time::{sleep, Duration};
use mc_query::status;

const NAMESPACE: &str = "MinecraftDashboard";
const STATE_FILE: &str = "/var/tmp/network_monitor_state.json";
const INTERVAL_SECS: u64 = 60;

#[derive(serde::Serialize, serde::Deserialize, Default)]
struct NetworkState {
    prev_received: u64,
    prev_transmitted: u64,
    prev_time: u64,
}

struct MetricsCollector {
    cloudwatch_client: aws_sdk_cloudwatch::Client,
    instance_id: String,
    region: String,
    system: System,
    networks: Networks,
    server_host: String,
    server_port: u16,
}

impl MetricsCollector {
    async fn new(server_host: String, server_port: u16) -> Result<Self> {
        let config = aws_config::load_from_env().await;
        let cloudwatch_client = aws_sdk_cloudwatch::Client::new(&config);

        // Get instance metadata
        let instance_id = Self::get_instance_id().await?;
        let region = Self::get_region().await?;

        Ok(Self {
            cloudwatch_client,
            instance_id,
            region,
            system: System::new_all(),
            networks: Networks::new_with_refreshed_list(),
            server_host,
            server_port,
        })
    }

    async fn get_instance_id() -> Result<String> {
        // Try environment variable first (set by docker-compose)
        if let Ok(instance_id) = std::env::var("INSTANCE_ID") {
            if !instance_id.is_empty() {
                return Ok(instance_id);
            }
        }

        // Try ec2metadata, fallback to hostname
        match tokio::process::Command::new("ec2metadata")
            .arg("--instance-id")
            .output()
            .await
        {
            Ok(output) if output.status.success() => {
                Ok(String::from_utf8(output.stdout)?.trim().to_string())
            }
            _ => {
                // Fallback to hostname
                let output = tokio::process::Command::new("hostname")
                    .output()
                    .await?;
                Ok(String::from_utf8(output.stdout)?.trim().to_string())
            }
        }
    }

    async fn get_region() -> Result<String> {
        // Try ec2metadata first, fallback to "unknown"
        match tokio::process::Command::new("ec2metadata")
            .arg("--availability-zone")
            .output()
            .await
        {
            Ok(output) if output.status.success() => {
                let az = String::from_utf8(output.stdout)?.trim().to_string();
                Ok(az[..az.len()-1].to_string())
            }
            _ => Ok("unknown".to_string())
        }
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
                .name("InstanceId")
                .value(&self.instance_id)
                .build(),
        ];

        // Collect CPU metrics
        self.system.refresh_cpu_usage();
        let global_cpu_usage = self.system.global_cpu_usage();

        metric_data.push(
            MetricDatum::builder()
                .metric_name("cpu_usage")
                .value((global_cpu_usage as f64 * 100.0).round() / 100.0)
                .unit(StandardUnit::Percent)
                .set_dimensions(Some(dimensions.clone()))
                .timestamp(
                    aws_sdk_cloudwatch::primitives::DateTime::from_secs(
                        SystemTime::now().duration_since(UNIX_EPOCH)?.as_secs() as i64
                    )
                )
                .build(),
        );

        // Collect Memory metrics
        self.system.refresh_memory();
        let total_memory = self.system.total_memory();
        let used_memory = self.system.used_memory();
        let memory_usage_percent = ((used_memory as f64 / total_memory as f64) * 10000.0).round() / 100.0;

        metric_data.push(
            MetricDatum::builder()
                .metric_name("memory_usage")
                .value(memory_usage_percent)
                .unit(StandardUnit::Percent)
                .set_dimensions(Some(dimensions.clone()))
                .timestamp(
                    aws_sdk_cloudwatch::primitives::DateTime::from_secs(
                        SystemTime::now().duration_since(UNIX_EPOCH)?.as_secs() as i64
                    )
                )
                .build(),
        );

        // Collect Minecraft player count
        match self.get_minecraft_players().await {
            Ok(player_count) => {
                metric_data.push(
                    MetricDatum::builder()
                        .metric_name("active_players")
                        .value(player_count as f64)
                        .unit(StandardUnit::Count)
                        .set_dimensions(Some(dimensions.clone()))
                        .timestamp(
                            aws_sdk_cloudwatch::primitives::DateTime::from_secs(
                                SystemTime::now().duration_since(UNIX_EPOCH)?.as_secs() as i64
                            )
                        )
                        .build(),
                );
            }
            Err(e) => eprintln!("Failed to get player count: {}", e),
        }

        // Collect Network bandwidth metrics
        self.networks.refresh(true);
        let default_interface = Self::get_default_interface()?;

        if let Some(network) = self.networks.get(&default_interface) {
            let curr_received = network.total_received();
            let curr_transmitted = network.total_transmitted();
            let current_time = SystemTime::now().duration_since(UNIX_EPOCH)?.as_secs();

            let prev_state = self.load_network_state();

            if prev_state.prev_time > 0 {
                let time_diff = current_time - prev_state.prev_time;

                if time_diff > 0 {
                    let rx_bandwidth = (((curr_received - prev_state.prev_received) as f64) / (time_diff as f64) * 100.0).round() / 100.0;
                    let tx_bandwidth = (((curr_transmitted - prev_state.prev_transmitted) as f64) / (time_diff as f64) * 100.0).round() / 100.0;

                    let rx_bandwidth = rx_bandwidth.max(0.0);
                    let tx_bandwidth = tx_bandwidth.max(0.0);

                    metric_data.push(
                        MetricDatum::builder()
                            .metric_name("receive_bandwidth")
                            .value(rx_bandwidth)
                            .unit(StandardUnit::BytesSecond)
                            .set_dimensions(Some(dimensions.clone()))
                            .timestamp(
                                aws_sdk_cloudwatch::primitives::DateTime::from_secs(
                                    current_time as i64
                                )
                            )
                            .build(),
                    );

                    metric_data.push(
                        MetricDatum::builder()
                            .metric_name("transmit_bandwidth")
                            .value(tx_bandwidth)
                            .unit(StandardUnit::BytesSecond)
                            .set_dimensions(Some(dimensions.clone()))
                            .timestamp(
                                aws_sdk_cloudwatch::primitives::DateTime::from_secs(
                                    current_time as i64
                                )
                            )
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

                println!("Successfully sent {} metrics to CloudWatch", metric_count);
            }
        }
        Ok(())
    }

    async fn get_minecraft_players(&self) -> Result<i32> {
        let response = status(&self.server_host, self.server_port).await?;
        Ok(response.players.online as i32)
    }

    fn get_default_interface() -> Result<String> {
        let output = std::process::Command::new("ip")
            .args(["route", "show", "default"])
            .output()?;

        let output_str = String::from_utf8(output.stdout)?;

        for line in output_str.lines() {
            if line.contains("default") {
                let parts: Vec<&str> = line.split_whitespace().collect();
                if let Some(idx) = parts.iter().position(|&x| x == "dev") {
                    if let Some(interface) = parts.get(idx + 1) {
                        return Ok(interface.to_string());
                    }
                }
            }
        }

        anyhow::bail!("Could not determine default network interface")
    }
}

#[tokio::main]
async fn main() -> Result<()> {
    println!("Starting system metrics collector...");

    // Parse command-line arguments
    let args: Vec<String> = std::env::args().collect();
    let dry_run = args.contains(&"--dry-run".to_string());

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

    if dry_run {
        println!("Running in DRY-RUN mode - metrics will not be sent to CloudWatch");
    }

    println!("Monitoring server: {}:{}", server_host, server_port);

    let mut collector = MetricsCollector::new(server_host, server_port).await?;
    println!("Monitoring instance: {} in region: {}", collector.instance_id, collector.region);

    loop {
        match collector.collect_and_send_metrics(dry_run).await {
            Ok(_) => {},
            Err(e) => eprintln!("Error collecting metrics: {}", e),
        }

        sleep(Duration::from_secs(INTERVAL_SECS)).await;
    }
}
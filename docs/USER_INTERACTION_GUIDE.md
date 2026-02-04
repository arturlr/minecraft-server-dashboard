# Minecraft Server Dashboard - User Interaction Guide

## Getting Started

### Logging In
1. Navigate to the Minecraft Server Dashboard URL
2. Click **Sign In with Google**
3. Authenticate using your Google account via Amazon Cognito
4. Upon successful login, you'll see the main dashboard

### Understanding Your Role
- **Admin Users**: Full access to all servers, can manage user permissions
- **Regular Users**: Access only to servers you own or have been invited to

## Main Dashboard

### Server List View
The dashboard displays all Minecraft servers you have access to:
- **Server Name**: Displayed from the EC2 instance `Name` tag
- **Server State**: Running, Stopped, or Pending
- **IP Address**: Connection address (visible when running)
- **Monthly Cost**: Current month's estimated cost
- **Active Players**: Real-time player count

### Server Actions
Each server card provides quick actions:
- **Power Button**: Start/stop the server
- **Restart Button**: Restart a running server
- **Settings Icon**: Open server configuration
- **Users Icon**: Manage server access (admin only)

## Starting and Stopping Servers

### Starting a Server
1. Click the **power icon** on a stopped server
2. Watch the real-time status updates:
   - PROCESSING: Action is being executed
   - COMPLETED: Server successfully started
   - FAILED: Error occurred (check error message)
3. Wait for the server state to change to "Running"
4. IP address will appear once the server is online

**Note**: First-time server starts trigger automatic configuration (IAM profile, CloudWatch alarms, default settings)

### Stopping a Server
1. Click the **power icon** on a running server
2. Confirm the stop action
3. Monitor status updates until completion
4. Server state changes to "Stopped"

### Restarting a Server
1. Click the **restart icon** on a running server
2. Server will stop and automatically restart
3. Useful for applying configuration changes or clearing memory

## Real-Time Monitoring

### Live Metrics
When viewing a running server, you'll see:
- **CPU Usage**: Current processor utilization
- **Memory Usage**: RAM consumption
- **Network Traffic**: Inbound/outbound data transfer
- **Active Players**: Number of connected users

Metrics update automatically via GraphQL subscriptions.

## Server Configuration

### Accessing Settings
1. Click the **settings icon** on any server
2. The Server Settings panel opens with multiple sections

### Basic Configuration

#### Minecraft Server Settings
- **Working Directory**: Path where Minecraft files are located (e.g., `/home/ubuntu/minecraft`)
- **Run Command**: Command to start Minecraft (e.g., `java -Xmx2G -jar server.jar nogui`)

#### Auto-Configuration
New servers automatically receive:
- CPU-based shutdown (5% threshold, 30 minutes)
- Default Minecraft commands
- CloudWatch alarm creation

### Auto-Shutdown Policies

#### CPU-Based Shutdown
Stops the server when CPU usage is consistently low:
- **Threshold**: CPU percentage (1-100%)
- **Evaluation Period**: Minutes below threshold (1-60)
- **Recommended**: 5% threshold, 30-minute period

#### User-Based Shutdown
Stops the server when player count drops:
- **Threshold**: Number of connected players (0-N)
- **Evaluation Period**: Minutes below threshold (1-60)
- **Recommended**: 0 players, 15-30 minute period
- **Cost Savings**: ~$20-50/month in EC2 costs vs ~$0.40/month in CloudWatch costs

**Note**: CPU-based and user-based shutdown are mutually exclusive. Choose one.

### Scheduled Operations

#### Quick Presets
Select common schedules with one click:
- **Weekday Evenings**: Mon-Fri, 6 PM - 11 PM
- **Weekends**: Sat-Sun, 10 AM - 11 PM
- **Business Hours**: Mon-Fri, 9 AM - 5 PM

#### Custom Schedules
Create your own start/stop times:
1. Enable **Start Schedule** or **Stop Schedule**
2. Enter cron expression (5-field format)
   - Format: `minute hour day month day-of-week`
   - Example: `0 18 * * 1-5` (6 PM, Monday-Friday)
3. View visual summary with day chips and runtime calculation

#### Schedule Validation
The system provides smart warnings:
- Start time after stop time (server runs overnight)
- Short runtime duration (< 2 hours)
- Timing conflicts with shutdown policies

**Note**: Scheduled operations and CloudWatch alarms work together. Ensure they don't conflict.

### Configuration Validation
Real-time feedback on your settings:
- **Green Check**: Configuration valid
- **Yellow Warning**: Potential issues (review warnings)
- **Red Error**: Invalid configuration (must fix)

View detailed validation in the **ServerConfigDebug** component.

## User Management (Admin Only)

### Adding Users to a Server
1. Click the **user icon with plus** on a server
2. Enter the user's Gmail address (without @gmail.com)
3. Click **ADD**
4. User must have logged in at least once to create their profile

### Removing Users
1. Open the server's user management panel
2. Click **Remove** next to the user's name
3. Confirm the removal

**Note**: Users must log in to the dashboard before they can be added to servers.

## Cost Monitoring

### Monthly Cost Tracking
- View current month's cost for each server
- Costs update daily from AWS Cost Explorer
- Includes EC2 instance, storage, and data transfer costs

### Cost Optimization Tips
- Enable auto-shutdown policies to reduce idle time
- Use user-based shutdown for maximum savings
- Schedule servers to run only when needed
- Monitor costs regularly and adjust policies

## Troubleshooting

### Server Won't Start
- Check IAM profile is correctly associated (auto-fixed on first start)
- Verify security group allows port 25565
- Review CloudWatch logs for errors
- Ensure EC2 instance has `App: minecraft` tag

### Configuration Not Saving
- Check for validation errors (red indicators)
- Ensure all required fields are filled
- Review error messages in the UI
- Try refreshing the page and reapplying

### Auto-Shutdown Not Working
- Verify CloudWatch alarm is created (check AWS Console)
- Ensure threshold and evaluation period are appropriate
- Check that only one shutdown policy is enabled
- Review alarm history in CloudWatch

### Can't Add User
- Confirm user has logged in at least once
- Verify you're using the correct Gmail address
- Check you have admin permissions
- Ensure user profile exists in Cognito

### Real-Time Updates Not Working
- Check your internet connection
- Refresh the browser page
- Verify GraphQL subscriptions are active
- Check browser console for errors

## Best Practices

### Server Management
- Always start servers from the dashboard (not AWS Console)
- Let auto-configuration run on first start
- Use descriptive server names (EC2 `Name` tag)
- Tag all Minecraft servers with `App: minecraft`

### Cost Optimization
- Enable user-based shutdown for idle detection
- Use scheduled operations for predictable usage
- Stop servers when not in use
- Monitor monthly costs regularly

### Security
- Only grant access to trusted users
- Use security groups to restrict access
- Don't share server IP addresses publicly
- Regularly review user permissions

### Configuration
- Test shutdown policies before relying on them
- Use quick presets for common schedules
- Review validation warnings before saving
- Document custom configurations

## Advanced Features

### Cron Expression Format
For custom schedules, use standard 5-field cron:
- `minute (0-59)`
- `hour (0-23)`
- `day of month (1-31)`
- `month (1-12)`
- `day of week (0-6, 0=Sunday)`

Examples:
- `0 18 * * 1-5`: 6 PM, Monday-Friday
- `30 14 * * 6,0`: 2:30 PM, Saturday and Sunday
- `0 9 1 * *`: 9 AM, first day of every month

### GraphQL Subscriptions
The dashboard uses real-time subscriptions for:
- Server state changes
- Performance metrics updates
- Action status updates (start/stop/restart)

No configuration needed - works automatically.

### Auto-Configuration Details
First server start automatically configures:
- IAM instance profile (EC2AWSMinecraftProfile)
- CloudWatch alarm for CPU-based shutdown
- Default Minecraft working directory and command
- Metric collection for monitoring

## Getting Help

### Support Resources
- Check validation warnings and errors in the UI
- Review CloudWatch logs for detailed error messages
- Consult AWS documentation for EC2 and CloudWatch
- Contact your administrator for permission issues

### Common Questions
**Q: Why can't I see all servers?**
A: You only see servers you own or have been invited to. Contact an admin for access.

**Q: How long does it take to start a server?**
A: Typically 2-5 minutes, depending on EC2 instance type and Minecraft server size.

**Q: Can I use this with non-Minecraft servers?**
A: The dashboard is designed specifically for Minecraft servers with the `App: minecraft` tag.

**Q: What happens if I stop a server with players connected?**
A: Players will be disconnected. Use user-based shutdown to avoid this.

**Q: How accurate are the cost estimates?**
A: Costs update daily from AWS Cost Explorer and reflect actual AWS charges.

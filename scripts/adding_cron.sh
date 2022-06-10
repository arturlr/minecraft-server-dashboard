#!/bin/sh

cat << EOF > ${HOME}/port_count.sh
#!/bin/bash
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
PORT_COUNT=$(netstat -an | grep ESTABLISHED | grep '\.25565' | wc -l)
aws cloudwatch put-metric-data --metric-name UserCount --dimensions Instance=\${INSTANCE_ID} --namespace "MinecraftDashboard" --value \${PORT_COUNT}
EOF

chmod +x ${HOME}/port_count.sh

sudo crontab -l > cron_bkp
sudo echo "*/3 * * * * sudo ${HOME}/port_count.sh >/dev/null 2>&1" >> cron_bkp
sudo crontab cron_bkp
sudo rm cron_bkp
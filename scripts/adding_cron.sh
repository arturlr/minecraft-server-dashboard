#!/bin/sh

WORKING_DIR="/opt/aws"

cat << EOF > ${WORKING_DIR}/port_count.sh
#!/bin/bash
INSTANCE_ID=\$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
PORT_COUNT=\$(netstat -an | grep ESTABLISHED | grep '\.25565' | wc -l)
REGION="\$(curl -s http://169.254.169.254/latest/meta-data/local-hostname | cut -d . -f 2)"
aws cloudwatch put-metric-data --metric-name UserCount --dimensions Instance=\${INSTANCE_ID} --namespace "MinecraftDashboard" --value \${PORT_COUNT} --region \${REGION}
EOF

chmod +x ${WORKING_DIR}/port_count.sh

sudo crontab -l > cron_bkp
sudo echo "*/3 * * * * sudo ${WORKING_DIR}/port_count.sh >/dev/null 2>&1" >> cron_bkp
sudo crontab cron_bkp
sudo rm cron_bkp
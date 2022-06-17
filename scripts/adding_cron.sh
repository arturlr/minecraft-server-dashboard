#!/bin/sh


# check if port_count.sh exists.
if [ ! -f ${WORKING_DIR}/port_count.sh ]; then

curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

if [ ! -f /usr/share/collectd/types.db ]; then
    sudo mkdir -p /usr/share/collectd
    sudo touch /usr/share/collectd/types.db
fi

# aws ssm send-command --document-name "AmazonCloudWatch-ManageAgent" --instance-ids ${INSTANCE_ID} \
#     --parameters '{"action":["configure"],"mode":["ec2"],"optionalConfigurationLocation":["/amplify/minecraftserverdashboard/amazoncloudwatch-linux"],"optionalConfigurationSource":["ssm"],"optionalRestart":["yes"]}' \
#     --region ${AWS_REGION}

# aws ssm send-command --document-name "AWS-ConfigureAWSPackage" --instance-ids ${INSTANCE_ID} \
#     --parameters '{"action":["Install"],"installationType":["In-place update"],"name":["AmazonCloudWatchAgent"]}'
#     --region ${AWS_REGION}

cat << EOF > ${WORKING_DIR}/port_count.sh
#!/bin/bash
INSTANCE_ID=\$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
PORT_COUNT=\$(netstat -an | grep ESTABLISHED | grep '\.25565' | wc -l)
REGION=\$(curl -s http://169.254.169.254/latest/meta-data/local-hostname | cut -d . -f 2)
aws cloudwatch put-metric-data --metric-name UserCount --dimensions Instance=\${INSTANCE_ID} --namespace "MinecraftDashboard" --value \${PORT_COUNT} --region \${REGION}
EOF

chmod +x ${WORKING_DIR}/port_count.sh

sudo crontab -l > cron_bkp
sudo echo "*/3 * * * * sudo ${WORKING_DIR}/port_count.sh >/dev/null 2>&1" >> cron_bkp
sudo crontab cron_bkp
sudo rm cron_bkp

fi
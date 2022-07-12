#!/bin/sh

# check if port_count.sh exists.
if [ ! -f ${HOME}/port_count.sh ]; then

cat << EOF > ${HOME}/port_count.sh
#!/bin/bash
INSTANCE_ID=\$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
PORT_COUNT=\$(netstat -an | grep ESTABLISHED | grep '\.25565' | wc -l)
REGION=\$(curl -s http://169.254.169.254/latest/meta-data/local-hostname | cut -d . -f 2)
aws cloudwatch put-metric-data --metric-name UserCount --dimensions InstanceId=\${INSTANCE_ID} --namespace "MinecraftDashboard" --value \${PORT_COUNT} --region \${REGION}
EOF

chmod +x ${HOME}/port_count.sh

sudo crontab -l > cron_bkp
sudo echo "*/1 * * * * sudo ${HOME}/port_count.sh >/dev/null 2>&1" >> cron_bkp
sudo crontab cron_bkp
sudo rm cron_bkp

APT=$(which apt)
YUM=$(which yum)

case $APT in /usr*)
   sudo apt-get -y install zip net-tools 
esac

case $YUM in /usr*)

   sudo yum -y install zip 
esac

curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

if [ ! -f /usr/share/collectd/types.db ]; then
    sudo mkdir -p /usr/share/collectd
    sudo touch /usr/share/collectd/types.db
fi

fi
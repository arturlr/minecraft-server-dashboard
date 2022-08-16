#!/bin/bash
DATE_SUFFIX=$(date +%y%m%d-%H%M)
DATE_TICKS=$(date +%s)
TICK_SUFFIX=${DATE_TICKS:6:4}
POOL_ID=$(aws ssm get-parameter --name /amplify/minecraftserverdashboard/userpoolid --query Parameter.Value --output text)
AMPLIFY_APPID=$(aws amplify list-apps --query 'apps[*].[appId, name]' --output text | awk '/minecraft/ {print $1}')
AMPLIFY_APP_URL="https://main.${AMPLIFY_APPID}.amplifyapp.com/"
COG_CLIENTS=$(aws cognito-idp list-user-pool-clients --user-pool-id $POOL_ID --query 'UserPoolClients[].[ClientId]' --output text)
COG_DOMAIN=$(aws cognito-idp describe-user-pool --user-pool-id $POOL_ID --query UserPool.Domain --output text)
REGION=$(aws cognito-idp describe-user-pool --user-pool-id $POOL_ID --query UserPool.Arn --output text | cut -d : -f 4)

# Add Amplify URL to the Cognito clients callback and logout configurations
while IFS= read -r line ; do aws cognito-idp update-user-pool-client --user-pool-id $POOL_ID --client-id $line --callback-urls $AMPLIFY_APP_URL --logout-urls $AMPLIFY_APP_URL --supported-identity-providers "COGNITO" "Google" --allowed-o-auth-flows "code" --allowed-o-auth-scopes "aws.cognito.signin.user.admin" "email" "openid" "phone" "profile"; done <<< "$COG_CLIENTS"

# Making sure that the minecraftdashboard cognito domain is unique
aws cognito-idp delete-user-pool-domain --user-pool-id $POOL_ID --domain $COG_DOMAIN
aws cognito-idp create-user-pool-domain --user-pool-id $POOL_ID --domain minecraftdashboard-$TICK_SUFFIX

echo "Cognito Domain: minecraftdashboard-$TICK_SUFFIX.auth.$REGION.amazoncognito.com"


https://console.cloud.google.com/apis/credentials (select the project you crated fro the minecraft dashboabr on step 1)


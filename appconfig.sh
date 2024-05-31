#!/usr/bin/env bash

DARKGRAY='\033[1;30m'
RED='\033[0;31m'    
LIGHTRED='\033[1;31m'
GREEN='\033[0;32m'    
YELLOW='\033[1;33m'
BLUE='\033[0;34m'    
PURPLE='\033[0;35m'    
LIGHTPURPLE='\033[1;35m'
CYAN='\033[0;36m'    
WHITE='\033[1;37m'
SET='\033[0m'
DATESUFFIX=$(date +%Y-%m-%d-%H%M) 

STACKNAME=$(cat samconfig.toml | grep stack_name |  tr -d '"' | awk '{print $3}')
AWSREGION=$(cat samconfig.toml | grep region |  tr -d '"' | awk '{print $3}')

if [ -z "$STACKNAME" ]; then
    echo -e "${RED} Stack name could not be found at the samconfig.toml file ${RED}${SET} - Fail"
    exit 1
fi

if [ -z "$AWSREGION" ]; then
    echo -e "${RED} AWS Region could not be found at the samconfig.toml file ${RED}${SET} - Fail"
    exit 1
fi

echo -e "${WHITE}---- StackName: ${WHITE}${YELLOW}${STACKNAME} at ${AWSREGION}${YELLOW}${SET}"


APPSYNCURL=$(aws cloudformation describe-stacks --stack-name $STACKNAME --query "Stacks[0].Outputs[?OutputKey=='AppSyncUrl'].OutputValue" --output text --region $AWSREGION)
if [ -z "$APPSYNCURL" ]; then
    echo -e "${RED} APPSYNCURL not found at the stack output ${RED}${SET} - Fail"
    exit 1
fi
echo -e "- ApiUrl: ${YELLOW}${APPSYNCURL}${SET}"

CLOUDFRONTURL=$(aws cloudformation describe-stacks --stack-name $STACKNAME --query "Stacks[0].Outputs[?OutputKey=='CloudFrontUrl'].OutputValue" --output text --region $AWSREGION)
echo -e "- CloudFront domain name: ${YELLOW}${CLOUDFRONTURL}${SET}"

COGNITOUSERPOOLCLIENTID=$(aws cloudformation describe-stacks --stack-name $STACKNAME --query "Stacks[0].Outputs[?OutputKey=='CognitoUserPoolClientId'].OutputValue" --output text --region $AWSREGION)
echo -e "- Cognito user pool client id: ${YELLOW}${COGNITOUSERPOOLCLIENTID}${SET}"

COGNITOUSERPOOLID=$(aws cloudformation describe-stacks --stack-name $STACKNAME --query "Stacks[0].Outputs[?OutputKey=='CognitoUserPoolId'].OutputValue" --output text --region $AWSREGION)
echo -e "- Cognito user pool id: ${YELLOW}${COGNITOUSERPOOLID}${SET}"

IDENTITYPOOLID=$(aws cloudformation describe-stacks --stack-name $STACKNAME --query "Stacks[0].Outputs[?OutputKey=='IdentityPoolId'].OutputValue" --output text --region $AWSREGION)
echo -e "- Cognito identity pool id: ${YELLOW}${IDENTITYPOOLID}${SET}"


COGNITODOMAINNAME=$(aws cloudformation describe-stacks --stack-name $STACKNAME --query "Stacks[0].Outputs[?OutputKey=='CognitoDomainName'].OutputValue" --output text --region $AWSREGION)
echo -e "- Cognito domain name: ${YELLOW}${COGNITODOMAINNAME}${SET}"

S3WEBBUCKETNAME=$(aws cloudformation describe-stacks --stack-name $STACKNAME --query "Stacks[0].Outputs[?OutputKey=='S3WebBucketName'].OutputValue" --output text --region $AWSREGION)
echo -e "- S3 Web bucket name: ${YELLOW}${S3WEBBUCKETNAME}${SET}"

echo -e "-- Creating .env file"

# Saving it to overwrite the default one
echo "VITE_AWS_REGION=${AWSREGION}" > dashboard/.env
# Adding to the new file
echo "VITE_GRAPHQL_ENDPOINT=${APPSYNCURL}" >> dashboard/.env
echo "VITE_CLOUDFRONT_URL=https://${CLOUDFRONTURL}" >> dashboard/.env
echo "VITE_IDENTITY_POOL_ID=${IDENTITYPOOLID}" >> dashboard/.env
echo "VITE_COGNITO_USER_POOL_CLIENT_ID=${COGNITOUSERPOOLCLIENTID}" >> dashboard/.env
echo "VITE_COGNITO_USER_POOL_ID=${COGNITOUSERPOOLID}" >> dashboard/.env
echo "VITE_COGNITO_DOMAIN=${COGNITODOMAINNAME}.auth.${AWSREGION}.amazoncognito.com" >> dashboard/.env
echo "VITE_BUCKET_NAME=${S3WEBBUCKETNAME}" >> dashboard/.env

echo "VITE_ADMIN_GROUP_NAME=admin" >> dashboard/.env
echo "VITE_I18N_LOCALE=en" >> dashboard/.env
echo "VITE_I18N_FALLBACK_LOCALE=en" >> dashboard/.env

# cd dashboard
# npm install
# npm run build
# aws s3 cp dist "s3://${S3WEBBUCKETNAME}" --recursive
# cd ..

# echo -e "- Web App available at: ${YELLOW}https://${CLOUDFRONT}${SET}" 
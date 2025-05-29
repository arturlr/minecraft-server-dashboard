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

parent_stack=$(cat samconfig.toml | grep stack_name |  tr -d '"' | awk '{print $3}')
region=$(cat samconfig.toml | grep region |  tr -d '"' | awk '{print $3}')
account_id=$(aws sts get-caller-identity --query "Account" --output text)

# Function to extract outputs from a stack
get_stack_outputs() {
    local stack_name=$1
    local region=$2
    
    echo "Fetching outputs from stack: ${stack_name}..."
    local stack_outputs=$(aws cloudformation describe-stacks --stack-name $stack_name --region $region --query "Stacks[0].Outputs || []" --output json)
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to retrieve stack outputs for ${stack_name}${SET}"
        return 1
    fi
    
    echo $stack_outputs > "$stack_name.json"
}

process_stacks() {
    local stacks=$1
    local region=$2

    for stack in $stacks; do
        echo -e "${WHITE}==== Processing ${stack} =====${SET}"
        local outputs=$(get_stack_outputs $stack $region)
        if [ $? -ne 0 ]; then
            echo -e "${RED}Failed to process stack ${stack}${SET}"
            continue
        fi
        
        # Check if outputs file exists and is not empty
        if [ ! -f "$stack.json" ] || [ ! -s "$stack.json" ]; then
            echo -e "${RED}No outputs file found for stack ${stack}${SET}"
            continue
        fi
        
        # Check if the JSON contains actual outputs or just an empty array
        local output_count=$(jq 'length' "$stack.json")
        if [ "$output_count" -eq 0 ]; then
            echo -e "${YELLOW}Stack ${stack} has no outputs${SET}"
            rm "$stack.json"
            continue
        fi

        while IFS= read -r line; do
            eval "$line"
        done < <(jq -r '.[] | "\(.OutputKey)=\"\(.OutputValue)\""' "$stack.json")        
        rm "$stack.json"
    done
}

if [ -z "$parent_stack" ]; then
    echo -e "${RED} Stack name could not be found at the samconfig.toml file ${RED}${SET} - Fail"
    exit 1
fi

if [ -z "$region" ]; then
    echo -e "${YELLOW}AWS region not found in samconfig.toml, using default region from AWS config${SET}"
    region=$(aws configure get region)
    if [ -z "$region" ]; then
        echo -e "${RED}No AWS region specified in samconfig.toml or AWS config${SET} - Fail"
        exit 1
    fi
fi

echo -e "${GREEN}Using stack name: ${parent_stack} in region: ${region}${SET}"

# Start processing from the main stack
echo -e "${WHITE}==== Getting all Stacks from ${parent_stack} =====${SET}"

stacks=$(aws cloudformation list-stacks --query "StackSummaries[?contains(StackName, \`${parent_stack}\`) && (StackStatus==\`CREATE_COMPLETE\`||StackStatus==\`UPDATE_COMPLETE\`)].StackName" --region $region --output json | jq -r '.[]')

process_stacks "$stacks" "$region"

echo -e "- ApiUrl: ${GREEN}${GraphQLAPIEndpoint}${SET}"
echo -e "- CloudFront domain name: ${GREEN}${CloudFrontDomain}${SET}"
echo -e "- Cognito user pool client id: ${GREEN}${CognitoUserPoolClientId}${SET}"
echo -e "- Cognito user pool id: ${GREEN}${CognitoUserPoolId}${SET}"
echo -e "- Cognito identity pool id: ${GREEN}${CognitoIdentityPool}${SET}"
echo -e "- Cognito domain name: ${GREEN}${CognitoDomainName}${SET}"
echo -e "- S3 Web bucket name: ${GREEN}${WebAppBucket}${SET}"
echo -e "- S3 Support bucket name: ${GREEN}${SupportBucket}${SET}"
echo -e "- AWS Account ID: ${GREEN}${account_id}${SET}"
echo -e "${WHITE}---- Uploading cloudwath agent config file to S3 ${WHITE}${SET}"
aws s3 cp amazon-cloudwatch-agent.json "s3://${SupportBucket}/amazon-cloudwatch-agent.json" --region $region

echo -e "-- Creating .env file"

# Saving it to overwrite the default one
echo "VITE_AWS_REGION=${region}" > dashboard/.env
# Adding to the new file
echo "VITE_GRAPHQL_ENDPOINT=${GraphQLAPIEndpoint}" >> dashboard/.env
echo "VITE_CLOUDFRONT_URL=https://${CloudFrontDomain}" >> dashboard/.env
echo "VITE_IDENTITY_POOL_ID=${CognitoIdentityPool}" >> dashboard/.env
echo "VITE_COGNITO_USER_POOL_CLIENT_ID=${CognitoUserPoolClientId}" >> dashboard/.env
echo "VITE_COGNITO_USER_POOL_ID=${CognitoUserPoolId}" >> dashboard/.env
echo "VITE_COGNITO_DOMAIN=${CognitoDomainName}.auth.${region}.amazoncognito.com" >> dashboard/.env
echo "VITE_BUCKET_NAME=${WebAppBucket}" >> dashboard/.env

echo "VITE_ADMIN_GROUP_NAME=admin" >> dashboard/.env
echo "VITE_AWS_ACCOUNT_ID=${account_id}" >> dashboard/.env
echo "VITE_I18N_LOCALE=en" >> dashboard/.env
echo "VITE_I18N_FALLBACK_LOCALE=en" >> dashboard/.env

# cd dashboard
# npm install
# npm run build
# aws s3 cp dist "s3://${WebAppBucket}" --recursive
# cd ..

# echo -e "- Web App available at: ${GREEN}https://${CloudFrontDomain}${SET}" 
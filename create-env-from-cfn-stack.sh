#!/usr/bin/env bash

# Color definitions
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

# Function to get stack output value by key
get_output_value() {
    local stack_name=$1
    local output_key=$2
    local region=$3
    
    aws cloudformation describe-stacks \
        --stack-name "$stack_name" \
        --region "$region" \
        --query "Stacks[0].Outputs[?OutputKey=='${output_key}'].OutputValue" \
        --output text 2>/dev/null
}

# Main script
main() {
    # Get stack name from command line argument
    parent_stack=$1
    region=$2
    
    if [ -z "$parent_stack" ]; then
        echo -e "${RED}Usage: $0 <stack-name> [region]${SET}"
        echo -e "${YELLOW}Example: $0 my-minecraft-stack us-west-2${SET}"
        exit 1
    fi
    
    if [ -z "$region" ]; then
        echo -e "${YELLOW}Region not provided, using default region from AWS config${SET}"
        region=$(aws configure get region)
        if [ -z "$region" ]; then
            echo -e "${RED}No AWS region specified and no default region configured${SET}"
            exit 1
        fi
    fi
    
    echo -e "${GREEN}Using stack name: ${parent_stack} in region: ${region}${SET}"
    
    # Get AWS account ID
    account_id=$(aws sts get-caller-identity --query "Account" --output text)
    
    # Verify stack exists
    echo -e "${WHITE}==== Fetching stack outputs from ${parent_stack} =====${SET}"
    
    if ! aws cloudformation describe-stacks --stack-name "$parent_stack" --region "$region" &>/dev/null; then
        echo -e "${RED}Stack ${parent_stack} not found in region ${region}${SET}"
        exit 1
    fi
    
    # Get outputs directly from parent stack
    GraphQLAPIEndpoint=$(get_output_value "$parent_stack" "GraphQLAPIEndpoint" "$region")
    CloudFrontDomain=$(get_output_value "$parent_stack" "CloudFrontDomain" "$region")
    CognitoUserPoolClientId=$(get_output_value "$parent_stack" "CognitoUserPoolClientId" "$region")
    CognitoUserPoolId=$(get_output_value "$parent_stack" "CognitoUserPoolId" "$region")
    CognitoIdentityPool=$(get_output_value "$parent_stack" "CognitoIdentityPool" "$region")
    CognitoDomainName=$(get_output_value "$parent_stack" "CognitoDomainName" "$region")
    WebAppBucket=$(get_output_value "$parent_stack" "WebAppBucket" "$region")
    SupportBucket=$(get_output_value "$parent_stack" "SupportBucket" "$region")
    
    # Display found values
    echo -e "- ApiUrl: ${GREEN}${GraphQLAPIEndpoint}${SET}"
    echo -e "- CloudFront domain name: ${GREEN}${CloudFrontDomain}${SET}"
    echo -e "- Cognito user pool client id: ${GREEN}${CognitoUserPoolClientId}${SET}"
    echo -e "- Cognito user pool id: ${GREEN}${CognitoUserPoolId}${SET}"
    echo -e "- Cognito identity pool id: ${GREEN}${CognitoIdentityPool}${SET}"
    echo -e "- Cognito domain name: ${GREEN}${CognitoDomainName}${SET}"
    echo -e "- S3 Web bucket name: ${GREEN}${WebAppBucket}${SET}"
    echo -e "- S3 Support bucket name: ${GREEN}${SupportBucket}${SET}"
    echo -e "- AWS Account ID: ${GREEN}${account_id}${SET}"
    echo ""
    
    # Create .env file
    echo -e "${WHITE}---- Creating webapp/.env file ----${SET}"
    
    cat > webapp/.env << EOF
VITE_AWS_REGION=${region}
VITE_GRAPHQL_ENDPOINT=${GraphQLAPIEndpoint}
VITE_CLOUDFRONT_URL=https://${CloudFrontDomain}
VITE_IDENTITY_POOL_ID=${CognitoIdentityPool}
VITE_COGNITO_USER_POOL_CLIENT_ID=${CognitoUserPoolClientId}
VITE_COGNITO_USER_POOL_ID=${CognitoUserPoolId}
VITE_COGNITO_DOMAIN=${CognitoDomainName}.auth.${region}.amazoncognito.com
VITE_BUCKET_NAME=${WebAppBucket}
VITE_ADMIN_GROUP_NAME=admin
VITE_AWS_ACCOUNT_ID=${account_id}
VITE_I18N_LOCALE=en
VITE_I18N_FALLBACK_LOCALE=en
EOF
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}.env file created successfully at webapp/.env${SET}"
    else
        echo -e "${RED}Failed to create .env file${SET}"
        exit 1
    fi
    
    # Upload CloudWatch agent config to S3
    echo ""
    echo -e "${WHITE}---- Uploading CloudWatch agent config ----${SET}"
    
    if [ -f "amazon-cloudwatch-agent.json" ]; then
        echo -e "Uploading amazon-cloudwatch-agent.json to s3://${SupportBucket}/"
        if aws s3 cp amazon-cloudwatch-agent.json "s3://${SupportBucket}/amazon-cloudwatch-agent.json" --region "$region"; then
            echo -e "${GREEN}CloudWatch config uploaded successfully${SET}"
        else
            echo -e "${YELLOW}Warning: Failed to upload CloudWatch config${SET}"
        fi
    else
        echo -e "${YELLOW}Warning: amazon-cloudwatch-agent.json not found in current directory${SET}"
        echo -e "${YELLOW}CloudWatch agent will not be configured on EC2 instances${SET}"
    fi
    
    # Upload Rust metrics binary to S3
    echo ""
    echo -e "${WHITE}---- Uploading Rust metrics binary ----${SET}"
    
    if [ -f "rust/msd-metrics/target/release/msd-metrics" ]; then
        echo -e "Uploading msd-metrics binary to s3://${SupportBucket}/"
        if aws s3 cp rust/msd-metrics/target/release/msd-metrics "s3://${SupportBucket}/msd-metrics" --region "$region"; then
            echo -e "${GREEN}Rust metrics binary uploaded successfully${SET}"
        else
            echo -e "${YELLOW}Warning: Failed to upload Rust metrics binary${SET}"
        fi
    else
        echo -e "${YELLOW}Warning: rust/msd-metrics/target/release/msd-metrics not found${SET}"
        echo -e "${YELLOW}Build it first with: cd rust/msd-metrics && cargo build --release${SET}"
    fi
    
    # Upload SSM scripts to S3
    echo ""
    echo -e "${WHITE}---- Uploading SSM scripts ----${SET}"
    
    if [ -d "scripts" ]; then
        script_count=$(find scripts -name "*.sh" | wc -l)
        if [ "$script_count" -gt 0 ]; then
            echo -e "Uploading ${script_count} script(s) from scripts/ to s3://${SupportBucket}/scripts/"
            if aws s3 sync scripts/ "s3://${SupportBucket}/scripts/" --exclude "*" --include "*.sh" --region "$region"; then
                echo -e "${GREEN}SSM scripts uploaded successfully${SET}"
            else
                echo -e "${YELLOW}Warning: Failed to upload SSM scripts${SET}"
            fi
        else
            echo -e "${YELLOW}No .sh files found in scripts/ directory${SET}"
        fi
    else
        echo -e "${YELLOW}Warning: scripts/ directory not found${SET}"
        echo -e "${YELLOW}Create it to store SSM bash scripts${SET}"
    fi
    
    echo ""
    echo -e "${GREEN}Configuration complete!${SET}"
    echo -e "Next steps:"
    echo -e "  ${CYAN}cd webapp${SET}"
    echo -e "  ${CYAN}npm install${SET}"
    echo -e "  ${CYAN}npm run build${SET}"
    echo -e "  ${CYAN}aws s3 cp dist s3://${WebAppBucket} --recursive${SET}"
    echo ""
    echo -e "- Web App will be available at: ${GREEN}https://${CloudFrontDomain}${SET}"
}

# Run main function with command line arguments
main "$@"

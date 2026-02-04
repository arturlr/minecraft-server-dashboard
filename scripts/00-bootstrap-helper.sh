#!/bin/bash
# Helper functions for bootstrap status reporting

INSTANCE_ID=$(ec2-metadata --instance-id | cut -d " " -f 2)
REGION=$(ec2metadata --availability-zone | sed 's/[a-z]$//')
PROJECT_NAME="${1:-msd}"
ENV_NAME="${2:-dev}"
TABLE_NAME="${PROJECT_NAME}-${ENV_NAME}-CoreTable"

update_bootstrap_stage() {
    local stage="$1"
    local status="$2"  # in_progress, completed, failed
    local error_msg="${3:-}"
    
    echo "[$(date)] Bootstrap stage: $stage - $status"
    
    local item="{\"PK\": {\"S\": \"SERVER#${INSTANCE_ID}\"}, \"SK\": {\"S\": \"CONFIG\"}, \"bootstrapStage\": {\"S\": \"$stage\"}, \"bootstrapStatus\": {\"S\": \"$status\"}"
    
    if [ -n "$error_msg" ]; then
        item="${item}, \"bootstrapError\": {\"S\": \"$error_msg\"}"
    fi
    
    item="${item}}"
    
    aws dynamodb update-item \
        --table-name "$TABLE_NAME" \
        --key "{\"PK\": {\"S\": \"SERVER#${INSTANCE_ID}\"}, \"SK\": {\"S\": \"CONFIG\"}}" \
        --update-expression "SET bootstrapStage = :stage, bootstrapStatus = :status, lastUpdated = :timestamp" \
        --expression-attribute-values "{\":stage\": {\"S\": \"$stage\"}, \":status\": {\"S\": \"$status\"}, \":timestamp\": {\"N\": \"$(date +%s)\"}}" \
        --region "$REGION" 2>&1 || echo "Warning: Failed to update DynamoDB status"
}

run_stage() {
    local stage_name="$1"
    local script_path="$2"
    shift 2
    local script_args="$@"
    
    update_bootstrap_stage "$stage_name" "in_progress"
    
    if bash "$script_path" $script_args; then
        update_bootstrap_stage "$stage_name" "completed"
        return 0
    else
        local exit_code=$?
        update_bootstrap_stage "$stage_name" "failed" "Script exited with code $exit_code"
        return $exit_code
    fi
}

export -f update_bootstrap_stage
export -f run_stage
export INSTANCE_ID REGION TABLE_NAME

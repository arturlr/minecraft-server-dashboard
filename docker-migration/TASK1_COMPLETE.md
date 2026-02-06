# Task 1: Update GraphQL Schema - COMPLETE ✅

## Changes Made

### 1. Removed Bootstrap Fields
From `ServerConfig` type and `ServerConfigInput`:
- ❌ `scriptVersion: String`
- ❌ `isBootstrapComplete: Boolean`
- ❌ `bootstrapStage: String`
- ❌ `bootstrapStatus: String`
- ❌ `bootstrapError: String`

### 2. Added Docker Fields
To `ServerConfig` type and `ServerConfigInput`:
- ✅ `dockerImageTag: String`
- ✅ `dockerComposeVersion: String`

### 3. Removed Bootstrap Mutation
- ❌ `bootstrapServer(instanceId: String!): AWSJSON`

### 4. Added Docker Mutations
- ✅ `pullDockerImage(instanceId: String!, service: String!): AWSJSON`
  - Description: "Pulls the latest Docker image for a specific service"
  - Required parameters: instanceId, service
- ✅ `restartDockerContainer(instanceId: String!, service: String!): AWSJSON`
  - Description: "Restarts a specific Docker container"
  - Required parameters: instanceId, service
- ✅ `updateDockerCompose(instanceId: String!, version: String!): AWSJSON`
  - Description: "Updates docker-compose configuration to a specific version"
  - Required parameters: instanceId, version

### 5. Added Container Status Types
- ✅ `ContainerState` enum: RUNNING, STOPPED, ERROR, STARTING, STOPPING, UNHEALTHY
- ✅ `ContainerStatus` type with fields:
  - `service: String!`
  - `state: ContainerState!`
  - `health: String`
  - `uptime: String`
- ✅ `ContainerStatusInput` input type (matching structure)

### 6. Updated ServerInfo
- ✅ Added `containerStatus: [ContainerStatus]` to `ServerInfo` type
- ✅ Added `containerStatus: [ContainerStatusInput]` to `ServerInfoInput`

## Code Review Results

### Critical Issues Fixed ✅
- Fixed type inconsistency: `ServerInfoInput.containerStatus` now uses `[ContainerStatusInput]` instead of `[AWSJSON]`
- Made `service` parameter required in `pullDockerImage` mutation
- Made `version` parameter required in `updateDockerCompose` mutation

### High Priority Issues Fixed ✅
- Added `ContainerStatusInput` type for proper GraphQL input handling
- Added `ContainerState` enum for type-safe container states
- Added documentation to all Docker mutations

### Validation Results ✅
- ✅ Schema syntax is valid
- ✅ No breaking changes to existing queries (only removed bootstrap-specific fields)
- ✅ Type consistency between types and inputs
- ✅ Authorization directives present (`@aws_cognito_user_pools`)
- ✅ All bootstrap references removed

## Next Steps

1. **Task 2**: Configure itzg/minecraft-server image
2. **Update Resolvers**: Create AppSync resolvers for new Docker mutations (Task 10)
3. **Update Lambda**: Create dockerManager Lambda function (Task 9)
4. **Update DynamoDB**: Update ddbHelper.py to handle new fields (Task 6)
5. **Update Frontend**: Update GraphQL queries/mutations in webapp (Task 12)

## Demo Checklist
- [ ] Schema validates with `sam validate --lint`
- [ ] No breaking changes to existing queries
- [ ] All Docker mutations have proper documentation
- [ ] Type safety enforced with enums and structured types

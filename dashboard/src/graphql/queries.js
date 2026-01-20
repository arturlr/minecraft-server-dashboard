/* eslint-disable */
// this is an auto generated file. This will be overwritten

export const ec2Discovery = /* GraphQL */ `
  query ec2Discovery {
    ec2Discovery {
      id
      name
      type
      userEmail
      state
      vCpus
      memSize
      diskSize
      launchTime
      publicIp
      initStatus
      iamStatus
      runningMinutes
      runningMinutesCacheTimestamp
      configStatus
      configValid
      configWarnings
      configErrors
      autoConfigured
    }
  }
`;
export const ec2CostCalculator = /* GraphQL */ `
  query ec2CostCalculator {
    ec2CostCalculator {
      id
      timePeriod
      UnblendedCost
      UsageQuantity
    }
  }
`;
export const getLoginAudit = /* GraphQL */ `
  query GetLoginAudit($id: ID!) {
    getLoginAudit(id: $id) {
      id
      actionUser
      action
      instanceId
      expirationEpoch
      createdAt
    }
  }
`;
export const listLoginAudits = /* GraphQL */ `
  query ListLoginAudits(
    $filter: ModelLoginAuditFilterInput
    $limit: Int
    $nextToken: String
  ) {
    listLoginAudits(filter: $filter, limit: $limit, nextToken: $nextToken) {
      items {
        id
        email
        action
        expirationEpoch
        createdAt
        updatedAt
      }
      nextToken
    }
  }
`;

export const getServerConfig = /* GraphQL */ `
query GetServerConfig($id: String!) {
  getServerConfig(id: $id) {
    id
    runCommand
    workDir
    shutdownMethod
    stopScheduleExpression
    startScheduleExpression
    alarmThreshold
    alarmEvaluationPeriod
    timezone
    isBootstrapComplete
    minecraftVersion
    latestPatchUpdate
    createdAt
    updatedAt
    autoConfigured
  }
}
`;

export const getServerUsers = /* GraphQL */ `
  query GetServerUsers($instanceId: String!) {
    getServerUsers(instanceId: $instanceId) {
      id
      email
      fullName
    }
  }
`;

export const searchUserByEmail = /* GraphQL */ `
  query SearchUserByEmail($email: AWSEmail!) {
    searchUserByEmail(email: $email) {
      id
      email
      fullName
    }
  }
`;

export const getec2ActionValidatorStatus = /* GraphQL */ `
  query Getec2ActionValidatorStatus($id: String!) {
    getec2ActionValidatorStatus(id: $id) {
      id
      action
      status
      timestamp
      message
      userEmail
    }
  }
`;

export const ec2MetricsHandler = /* GraphQL */ `
  query ec2MetricsHandler($id: String!) {
    ec2MetricsHandler(id: $id) {
      id
      cpuStats
      networkStats
      memStats
      activeUsers
    }
  }
`;
/* eslint-disable */
// this is an auto generated file. This will be overwritten

export const listServers = /* GraphQL */ `
  query ListServers {
    listServers {
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
export const getMonthlyCost = /* GraphQL */ `
  query GetMonthlyCost {
    getMonthlyCost {
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

export const getAdminUsers = /* GraphQL */ `
  query GetAdminUsers {
    getAdminUsers {
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

export const getServerActionStatus = /* GraphQL */ `
  query GetServerActionStatus($id: String!) {
    getServerActionStatus(id: $id) {
      id
      action
      status
      timestamp
      message
      userEmail
    }
  }
`;

export const getServerMetrics = /* GraphQL */ `
  query GetServerMetrics($id: String!) {
    getServerMetrics(id: $id) {
      id
      cpuStats
      networkStats
      memStats
      activeUsers
    }
  }
`;
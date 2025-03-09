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
    runCommand
    workDir
    shutdownMethod
    scheduleExpression
    alarmThreshold
    alarmEvaluationPeriod
    groupMembers
  }
}
`;
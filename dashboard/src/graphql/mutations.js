/* eslint-disable */
// this is an auto generated file. This will be overwritten

export const putServerMetric = /* GraphQL */ `
  mutation PutServerMetric($input: ServerMetricInput!) {
    putServerMetric(input: $input) {
      id
      cpuStats
      networkStats
      memStats
      activeUsers
      alertMsg
    }
  }
`;
export const onChangeState = /* GraphQL */ `
  mutation OnChangeState($input: ServerInfoInput!) {
    onChangeState(input: $input) {
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
export const fixServerRole = /* GraphQL */ `
  mutation FixServerRole($instanceId: String!) {
    fixServerRole(instanceId: $instanceId)
  }
`;
export const startServer = /* GraphQL */ `
  mutation StartServer($instanceId: String!) {
    startServer(instanceId: $instanceId) 
  }
`;
export const stopServer = /* GraphQL */ `
  mutation StopServer($instanceId: String!) {
    stopServer(instanceId: $instanceId) 
  }
`;
export const restartServer = /* GraphQL */ `
  mutation RestartServer($instanceId: String!) {
    restartServer(instanceId: $instanceId) 
  }
`;

export const PutLogAudit = /* GraphQL */ `
  mutation putLogAudit(
    $input: LogAuditInput!
  ) {
    putLogAudit(input: $input) {
      id
      actionUser
      action
      instanceId
      expirationEpoch
      createdAt
    }
  }
`;

export const PutLogAuditWithInviteeEmail = /* GraphQL */ `
  mutation putLogAudit(
    $input: LogAuditInput!
  ) {
    putLogAudit(input: $input) {
      id
      actionUser
      action
      instanceId
      inviteeEmail
      expirationEpoch
      createdAt
    }
  }
`;

export const deleteLoginAudit = /* GraphQL */ `
  mutation DeleteLoginAudit(
    $input: id!
  ) {
    deleteLoginAudit(input: $input) {
      id
    }
  }
`;

export const putServerConfig = /* GraphQL */ `
  mutation PutServerConfig($input: ServerConfigInput!) {
    putServerConfig(input: $input) {
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

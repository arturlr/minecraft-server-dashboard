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
export const createLoginAudit = /* GraphQL */ `
  mutation CreateLoginAudit(
    $input: CreateLoginAuditInput!
    $condition: ModelLoginAuditConditionInput
  ) {
    createLoginAudit(input: $input, condition: $condition) {
      id
      email
      action
      expirationEpoch
      createdAt
      updatedAt
    }
  }
`;
export const updateLoginAudit = /* GraphQL */ `
  mutation UpdateLoginAudit(
    $input: UpdateLoginAuditInput!
    $condition: ModelLoginAuditConditionInput
  ) {
    updateLoginAudit(input: $input, condition: $condition) {
      id
      email
      action
      expirationEpoch
      createdAt
      updatedAt
    }
  }
`;
export const deleteLoginAudit = /* GraphQL */ `
  mutation DeleteLoginAudit(
    $input: DeleteLoginAuditInput!
    $condition: ModelLoginAuditConditionInput
  ) {
    deleteLoginAudit(input: $input, condition: $condition) {
      id
      email
      action
      expirationEpoch
      createdAt
      updatedAt
    }
  }
`;

export const putServerConfig = /* GraphQL */ `
  mutation PutServerConfig($input: ServerConfigInput!) {
    putServerConfig(input: $input) {
      id
    }
  }
`;
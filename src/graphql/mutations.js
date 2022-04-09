/* eslint-disable */
// this is an auto generated file. This will be overwritten

export const putServerMetric = /* GraphQL */ `
  mutation PutServerMetric($input: ServerMetricInput!) {
    putServerMetric(input: $input) {
      id
      monthlyUsage
      dailyUsage
      cpuStats
      networkStats
      activeUsers
    }
  }
`;
export const changeServerState = /* GraphQL */ `
  mutation ChangeServerState($input: ServerInfoInput!) {
    changeServerState(input: $input) {
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
      instanceStatus
      systemStatus
      runCommand
      workingDir
    }
  }
`;
export const triggerServerAction = /* GraphQL */ `
  mutation TriggerServerAction($input: ServerActionInput!) {
    triggerServerAction(input: $input)
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

/* eslint-disable */
// this is an auto generated file. This will be overwritten

export const onPutServerMetric = /* GraphQL */ `
  subscription OnPutServerMetric {
    onPutServerMetric {
      id
      cpuStats
      networkStats
      memStats
      activeUsers
    }
  }
`;
export const onChangeState = /* GraphQL */ `
  subscription OnChangeState {
    onChangeState {
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
      groupMembers
    }
  }
`;
export const onCreateLoginAudit = /* GraphQL */ `
  subscription OnCreateLoginAudit {
    onCreateLoginAudit {
      id
      email
      action
      expirationEpoch
      createdAt
      updatedAt
    }
  }
`;
export const onUpdateLoginAudit = /* GraphQL */ `
  subscription OnUpdateLoginAudit {
    onUpdateLoginAudit {
      id
      email
      action
      expirationEpoch
      createdAt
      updatedAt
    }
  }
`;
export const onDeleteLoginAudit = /* GraphQL */ `
  subscription OnDeleteLoginAudit {
    onDeleteLoginAudit {
      id
      email
      action
      expirationEpoch
      createdAt
      updatedAt
    }
  }
`;

import { Amplify } from 'aws-amplify';

export function configAmplify() {
    Amplify.configure({
        Auth: {
            Cognito: {
                loginWith: {
                    oauth: {
                        redirectSignIn: [
                            `${window.location.origin}/`,
                        ],
                        redirectSignOut: [
                            `${window.location.origin}/`,
                        ],
                        domain: import.meta.env.VITE_COGNITO_DOMAIN,
                        scopes: [
                            'phone',
                            'email',
                            'profile',
                            'openid',
                            'aws.cognito.signin.user.admin'
                        ],
                        responseType: 'code'
                    },
                },
                identityPoolId: import.meta.env.VITE_IDENTITY_POOL_ID, // REQUIRED - Amazon Cognito Identity Pool ID
                region: import.meta.env.VITE_AWS_REGION, // REQUIRED - Amazon Cognito Region
                userPoolId: import.meta.env.VITE_COGNITO_USER_POOL_ID, // OPTIONAL - Amazon Cognito User Pool ID for authenticated user access
                userPoolClientId: import.meta.env.VITE_COGNITO_USER_POOL_CLIENT_ID, // OPTIONAL - Amazon Cognito Web Client ID for authenticated user access
            },
        },
        API: {
            GraphQL: {
                endpoint: import.meta.env.VITE_GRAPHQL_ENDPOINT,
                region: import.meta.env.VITE_AWS_REGION,
                defaultAuthMode: 'userPool'
            }
        },
    })
}


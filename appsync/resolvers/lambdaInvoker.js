import { util } from '@aws-appsync/utils'

export function request(ctx) {
    return {
        operation: 'Invoke',
        payload: ctx
    };
}

export function response(ctx) {
    const { result, error } = ctx;
    if (error) {
       util.error(error.message, error.type, result);
    }
    return result;
}

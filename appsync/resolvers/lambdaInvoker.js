import { util } from '@aws-appsync/utils'

export function request(ctx) {
    return {
        operation: 'Invoke',
        payload: ctx
    };
}

export function response(ctx) {
    const { error, data } = ctx.result;
    if (error) {
        util.error(error.message, error.name, null);
    }
    return data;
}

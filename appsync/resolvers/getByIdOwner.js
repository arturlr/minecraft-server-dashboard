import * as ddb from '@aws-appsync/utils/dynamodb'
	
// if($context.result["Owner"] == $context.identity.username)
// https://docs.aws.amazon.com/appsync/latest/devguide/security-authorization-use-cases.html

export function request(ctx) {
	return ddb.get({ key: { id: ctx.args.id } })
}

// $utils.unauthorized()
export const response = (ctx) => ctx.result
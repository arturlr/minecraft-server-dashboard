import { util } from '@aws-appsync/utils';
import * as ddb from '@aws-appsync/utils/dynamodb';

/**
 * AWS AppSync resolver function to update an existing record in a DynamoDB table.
 *
 * @param {Object} ctx - The resolver context object.
 * @param {Object} ctx.args - The input arguments for the resolver.
 * @param {string} ctx.args.id - The ID of the record to update.
 * @param {Object} ctx.args.rest - The remaining input arguments representing the attributes to update.
 * @returns {Object} The result of the DynamoDB update operation.
 */
export function request(ctx) {
  const { id, ...rest } = ctx.args;

  // Create an object with the attributes to update or remove
  const values = Object.entries(rest).reduce((obj, [key, value]) => {
    // If the value is falsy (null or undefined), use ddb.operations.remove() to remove the attribute
    // Otherwise, use the provided value to update the attribute
    obj[key] = value ?? ddb.operations.remove();
    return obj;
  }, {});

  // Update the DynamoDB record
  return ddb.update({
    // Specify the primary key of the record to update
    key: { id },
    // Spread the 'values' object to update or remove attributes
    // Increment the 'version' attribute by 1
    update: { ...values, version: ddb.operations.increment(1) },
  });
}

/**
 * AWS AppSync resolver function to handle the response from the DynamoDB update operation.
 *
 * @param {Object} ctx - The resolver context object.
 * @param {Object} ctx.error - The error object, if an error occurred during the update operation.
 * @param {Object} ctx.result - The result of the DynamoDB update operation.
 * @returns {Object} The result of the DynamoDB update operation, or an error message if an error occurred.
 */
export function response(ctx) {
  const { error, result } = ctx;
  if (error) {
    // If an error occurred, append the error message and type
    util.appendError(error.message, error.type);
  }
  return result;
}

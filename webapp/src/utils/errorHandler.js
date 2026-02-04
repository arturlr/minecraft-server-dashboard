/**
 * Error handling utilities for GraphQL and network errors
 */

/**
 * Parse GraphQL error response and extract user-friendly message
 * @param {Error} error - The error object from GraphQL or network request
 * @returns {string} - User-friendly error message
 */
export function parseGraphQLError(error) {
  // Check for GraphQL errors array
  if (error.errors && Array.isArray(error.errors) && error.errors.length > 0) {
    const firstError = error.errors[0];
    
    // Extract message from error
    if (firstError.message) {
      return firstError.message;
    }
  }

  // Check for error message property
  if (error.message) {
    // Handle common network errors
    if (error.message.includes('Network Error') || error.message.includes('NetworkError')) {
      return 'Network connection error. Please check your internet connection and try again.';
    }
    
    if (error.message.includes('timeout') || error.message.includes('Timeout')) {
      return 'Request timed out. Please try again.';
    }
    
    if (error.message.includes('Unauthorized') || error.message.includes('401')) {
      return 'You are not authorized to perform this action. Please sign in again.';
    }
    
    if (error.message.includes('Forbidden') || error.message.includes('403')) {
      return 'You do not have permission to perform this action.';
    }
    
    if (error.message.includes('Not Found') || error.message.includes('404')) {
      return 'The requested resource was not found.';
    }
    
    // Return the original message if it's user-friendly
    return error.message;
  }

  // Fallback to generic error message
  return 'An unexpected error occurred. Please try again.';
}

/**
 * Retry a failed async operation with exponential backoff
 * @param {Function} operation - Async function to retry
 * @param {number} maxRetries - Maximum number of retry attempts (default: 2)
 * @param {number} baseDelay - Base delay in milliseconds (default: 1000)
 * @returns {Promise} - Result of the operation
 */
export async function retryOperation(operation, maxRetries = 2, baseDelay = 1000) {
  let lastError;
  
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await operation();
    } catch (error) {
      lastError = error;
      
      // Don't retry on certain errors
      if (
        error.message?.includes('Unauthorized') ||
        error.message?.includes('Forbidden') ||
        error.message?.includes('401') ||
        error.message?.includes('403')
      ) {
        throw error;
      }
      
      // If this was the last attempt, throw the error
      if (attempt === maxRetries) {
        throw error;
      }
      
      // Calculate delay with exponential backoff
      const delay = baseDelay * Math.pow(2, attempt);
      console.log(`Retry attempt ${attempt + 1}/${maxRetries} after ${delay}ms`);
      
      // Wait before retrying
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }
  
  throw lastError;
}

/**
 * Check if an error is a network error that should be retried
 * @param {Error} error - The error to check
 * @returns {boolean} - True if the error should be retried
 */
export function isRetryableError(error) {
  if (!error) return false;
  
  const message = error.message?.toLowerCase() || '';
  
  return (
    message.includes('network') ||
    message.includes('timeout') ||
    message.includes('econnrefused') ||
    message.includes('enotfound') ||
    message.includes('etimedout')
  );
}

/**
 * Create a standardized error notification object
 * @param {Error} error - The error object
 * @param {string} defaultMessage - Default message if error parsing fails
 * @returns {Object} - Notification object with text and color
 */
export function createErrorNotification(error, defaultMessage = 'Operation failed') {
  const message = parseGraphQLError(error);
  
  return {
    text: message || defaultMessage,
    color: 'error',
    timeout: 5000
  };
}

/**
 * Create a standardized success notification object
 * @param {string} message - Success message
 * @returns {Object} - Notification object with text and color
 */
export function createSuccessNotification(message) {
  return {
    text: message,
    color: 'success',
    timeout: 3500
  };
}

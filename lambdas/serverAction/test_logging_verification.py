"""
Verification script for enhanced logging in ServerAction Lambda

This script verifies that the enhanced logging is properly implemented
by checking for key logging statements in the code.
"""

import re

def verify_logging_enhancements():
    """Verify that enhanced logging has been added to ServerAction Lambda"""
    
    with open('lambdas/serverAction/index.py', 'r') as f:
        content = f.read()
    
    # Check for enhanced authorization logging
    auth_checks = [
        r'logger\.info\(f"Authorization check:',
        r'logger\.info\(f"Authorization SUCCESS:',
        r'logger\.warning\(f"Authorization DENIED:',
        r'logger\.error\(f"Authorization check FAILED',
    ]
    
    # Check for enhanced queue operation logging
    queue_checks = [
        r'logger\.info\(f"Queue operation initiated:',
        r'logger\.info\(f"Queue operation: Sending message to SQS',
        r'logger\.info\(f"Queue operation SUCCESS:',
        r'logger\.error\(f"Queue operation FAILED',
    ]
    
    # Check for enhanced AppSync status logging
    appsync_checks = [
        r'logger\.info\(f"AppSync status update:',
        r'logger\.info\(f"AppSync status update SUCCESS:',
        r'logger\.error\(f"AppSync status update FAILED',
    ]
    
    # Check for exception logging with exc_info=True
    exception_checks = [
        r'exc_info=True',
    ]
    
    results = {
        'authorization_logging': 0,
        'queue_logging': 0,
        'appsync_logging': 0,
        'exception_logging': 0
    }
    
    for pattern in auth_checks:
        if re.search(pattern, content):
            results['authorization_logging'] += 1
    
    for pattern in queue_checks:
        if re.search(pattern, content):
            results['queue_logging'] += 1
    
    for pattern in appsync_checks:
        if re.search(pattern, content):
            results['appsync_logging'] += 1
    
    for pattern in exception_checks:
        results['exception_logging'] += len(re.findall(pattern, content))
    
    print("ServerAction Lambda Logging Verification Results:")
    print("=" * 60)
    print(f"Authorization logging statements: {results['authorization_logging']}/4")
    print(f"Queue operation logging statements: {results['queue_logging']}/4")
    print(f"AppSync status logging statements: {results['appsync_logging']}/3")
    print(f"Exception logging with exc_info: {results['exception_logging']}")
    print("=" * 60)
    
    all_passed = (
        results['authorization_logging'] >= 4 and
        results['queue_logging'] >= 4 and
        results['appsync_logging'] >= 3 and
        results['exception_logging'] >= 3
    )
    
    if all_passed:
        print("✓ All logging enhancements verified in ServerAction Lambda")
        return True
    else:
        print("✗ Some logging enhancements missing in ServerAction Lambda")
        return False

def verify_processor_logging_enhancements():
    """Verify that enhanced logging has been added to ServerActionProcessor Lambda"""
    
    with open('lambdas/serverActionProcessor/index.py', 'r') as f:
        content = f.read()
    
    # Check for enhanced action processing logging
    processing_checks = [
        r'logger\.info\(f"Action processing started:',
        r'logger\.info\(f"Action processing:',
        r'logger\.info\(f"Routing action to handler:',
        r'logger\.error\(f"Action processing FAILED',
    ]
    
    # Check for enhanced handler logging
    handler_checks = [
        r'logger\.info\(f"Server action handler started:',
        r'logger\.info\(f"IAM role fix handler started:',
        r'logger\.info\(f"Config update handler started:',
    ]
    
    # Check for enhanced AppSync status logging
    appsync_checks = [
        r'logger\.info\(f"AppSync status update:',
        r'logger\.info\(f"AppSync status update SUCCESS:',
        r'logger\.error\(f"AppSync status update FAILED',
    ]
    
    # Check for exception logging with exc_info=True
    exception_checks = [
        r'exc_info=True',
    ]
    
    results = {
        'processing_logging': 0,
        'handler_logging': 0,
        'appsync_logging': 0,
        'exception_logging': 0
    }
    
    for pattern in processing_checks:
        if re.search(pattern, content):
            results['processing_logging'] += 1
    
    for pattern in handler_checks:
        if re.search(pattern, content):
            results['handler_logging'] += 1
    
    for pattern in appsync_checks:
        if re.search(pattern, content):
            results['appsync_logging'] += 1
    
    for pattern in exception_checks:
        results['exception_logging'] += len(re.findall(pattern, content))
    
    print("\nServerActionProcessor Lambda Logging Verification Results:")
    print("=" * 60)
    print(f"Action processing logging statements: {results['processing_logging']}/4")
    print(f"Handler logging statements: {results['handler_logging']}/3")
    print(f"AppSync status logging statements: {results['appsync_logging']}/3")
    print(f"Exception logging with exc_info: {results['exception_logging']}")
    print("=" * 60)
    
    all_passed = (
        results['processing_logging'] >= 4 and
        results['handler_logging'] >= 3 and
        results['appsync_logging'] >= 3 and
        results['exception_logging'] >= 8
    )
    
    if all_passed:
        print("✓ All logging enhancements verified in ServerActionProcessor Lambda")
        return True
    else:
        print("✗ Some logging enhancements missing in ServerActionProcessor Lambda")
        return False

if __name__ == '__main__':
    result1 = verify_logging_enhancements()
    result2 = verify_processor_logging_enhancements()
    
    if result1 and result2:
        print("\n" + "=" * 60)
        print("✓ ALL LOGGING ENHANCEMENTS VERIFIED SUCCESSFULLY")
        print("=" * 60)
        exit(0)
    else:
        print("\n" + "=" * 60)
        print("✗ SOME LOGGING ENHANCEMENTS MISSING")
        print("=" * 60)
        exit(1)

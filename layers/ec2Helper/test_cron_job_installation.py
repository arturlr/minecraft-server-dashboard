#!/usr/bin/env python3
"""
Integration test for cron job installation and configuration.

This test verifies:
1. Cron job is installed during bootstrap
2. Cron job runs every minute
3. Cron job does not create duplicates

Requirements: 2.5, 6.5
"""
import subprocess
import re
import sys


def run_command(command):
    """Execute a shell command and return output"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)


def test_cron_job_exists():
    """
    Test that the cron job for port_count.sh exists.
    
    Validates: Requirements 2.5, 6.5
    """
    print("Test 1: Verifying cron job exists...")
    
    returncode, stdout, stderr = run_command("crontab -l 2>/dev/null")
    
    if returncode != 0:
        print(f"  ❌ FAIL: Could not read crontab (returncode: {returncode})")
        print(f"     stderr: {stderr}")
        return False
    
    # Check if the port_count.sh cron job exists
    if "/usr/local/port_count.sh" in stdout:
        print(f"  ✅ PASS: Cron job for port_count.sh found")
        return True
    else:
        print(f"  ❌ FAIL: Cron job for port_count.sh not found")
        print(f"     Current crontab:\n{stdout}")
        return False


def test_cron_job_runs_every_minute():
    """
    Test that the cron job is configured to run every minute.
    
    Validates: Requirements 2.5
    """
    print("\nTest 2: Verifying cron job runs every minute...")
    
    returncode, stdout, stderr = run_command("crontab -l 2>/dev/null")
    
    if returncode != 0:
        print(f"  ❌ FAIL: Could not read crontab")
        return False
    
    # Look for the cron job line
    cron_lines = [line for line in stdout.split('\n') if '/usr/local/port_count.sh' in line]
    
    if not cron_lines:
        print(f"  ❌ FAIL: No cron job found for port_count.sh")
        return False
    
    # Check if it's configured to run every minute (*/1 * * * * or * * * * *)
    cron_line = cron_lines[0]
    
    # Match patterns for "every minute"
    # Valid patterns: */1 * * * *, * * * * *, or 0-59 * * * *
    every_minute_patterns = [
        r'^\*/1\s+\*\s+\*\s+\*\s+\*',  # */1 * * * *
        r'^\*\s+\*\s+\*\s+\*\s+\*',     # * * * * *
    ]
    
    is_every_minute = any(re.match(pattern, cron_line.strip()) for pattern in every_minute_patterns)
    
    if is_every_minute:
        print(f"  ✅ PASS: Cron job configured to run every minute")
        print(f"     Cron expression: {cron_line.strip()}")
        return True
    else:
        print(f"  ❌ FAIL: Cron job not configured to run every minute")
        print(f"     Found: {cron_line.strip()}")
        return False


def test_no_duplicate_cron_jobs():
    """
    Test that there are no duplicate cron jobs for port_count.sh.
    
    Validates: Requirements 6.5
    """
    print("\nTest 3: Verifying no duplicate cron jobs...")
    
    returncode, stdout, stderr = run_command("crontab -l 2>/dev/null")
    
    if returncode != 0:
        print(f"  ❌ FAIL: Could not read crontab")
        return False
    
    # Count occurrences of port_count.sh in crontab
    cron_lines = [line for line in stdout.split('\n') if '/usr/local/port_count.sh' in line and not line.strip().startswith('#')]
    
    count = len(cron_lines)
    
    if count == 0:
        print(f"  ❌ FAIL: No cron job found for port_count.sh")
        return False
    elif count == 1:
        print(f"  ✅ PASS: Exactly one cron job found (no duplicates)")
        return True
    else:
        print(f"  ❌ FAIL: Found {count} duplicate cron jobs for port_count.sh")
        print(f"     Duplicate entries:")
        for i, line in enumerate(cron_lines, 1):
            print(f"       {i}. {line.strip()}")
        return False


def test_cron_job_output_redirection():
    """
    Test that the cron job redirects output to prevent cron emails.
    
    This is a best practice to avoid filling up mail spool.
    """
    print("\nTest 4: Verifying output redirection...")
    
    returncode, stdout, stderr = run_command("crontab -l 2>/dev/null")
    
    if returncode != 0:
        print(f"  ❌ FAIL: Could not read crontab")
        return False
    
    # Look for the cron job line
    cron_lines = [line for line in stdout.split('\n') if '/usr/local/port_count.sh' in line]
    
    if not cron_lines:
        print(f"  ❌ FAIL: No cron job found for port_count.sh")
        return False
    
    cron_line = cron_lines[0]
    
    # Check if output is redirected (>/dev/null or &>/dev/null or similar)
    has_output_redirect = '>/dev/null' in cron_line or '&>/dev/null' in cron_line
    
    if has_output_redirect:
        print(f"  ✅ PASS: Output is redirected to prevent cron emails")
        return True
    else:
        print(f"  ⚠️  WARNING: Output not redirected (may generate cron emails)")
        print(f"     Cron line: {cron_line.strip()}")
        return True  # Not a failure, just a warning


def main():
    """Run all cron job installation tests"""
    print("=" * 70)
    print("Cron Job Installation Tests")
    print("Testing Requirements: 2.5, 6.5")
    print("=" * 70)
    
    tests = [
        test_cron_job_exists,
        test_cron_job_runs_every_minute,
        test_no_duplicate_cron_jobs,
        test_cron_job_output_redirection,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"  ❌ ERROR: Test raised exception: {e}")
            results.append(False)
    
    print("\n" + "=" * 70)
    print(f"Test Summary: {sum(results)}/{len(results)} tests passed")
    print("=" * 70)
    
    if all(results):
        print("✅ All tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

# Manual SES Setup Guide

Since SES requires email verification and can be tricky with CloudFormation, it's easier to set up manually.

## Prerequisites
- AWS CLI configured with appropriate permissions
- Access to the email address you want to verify

## Setup Steps

### 1. Verify Email Identity
```bash
# Replace with your actual email address
aws ses verify-email-identity --email-address noreply@yourdomain.com --region us-west-2
```

### 2. Check Verification Status
```bash
aws ses get-identity-verification-attributes --identities noreply@yourdomain.com --region us-west-2
```

### 3. Check Your Email
After running the verify command, check your email for a verification link from AWS and click it.

### 4. Verify the Identity is Active
```bash
aws ses list-verified-email-addresses --region us-west-2
```

## SES Sandbox Mode

New AWS accounts start in SES sandbox mode, which means:
- You can only send TO verified email addresses
- You can send FROM verified email addresses
- Daily sending quota is limited (usually 200 emails/day)
- Sending rate is limited (usually 1 email/second)

### Request Production Access (Optional)
If you need to send to unverified addresses:

1. Go to AWS SES Console → Account dashboard
2. Click "Request production access"
3. Fill out the form explaining your use case
4. Wait for approval (usually 24-48 hours)

## Testing SES

Once verified, test sending an email:

```bash
aws ses send-email \
  --source noreply@yourdomain.com \
  --destination ToAddresses=test@yourdomain.com \
  --message Subject={Data="Test Email"},Body={Text={Data="This is a test email from SES"}} \
  --region us-west-2
```

## Lambda Integration

Your Lambda functions already have the necessary IAM permissions to use SES. They can send emails using the boto3 SES client:

```python
import boto3

ses = boto3.client('ses', region_name='us-west-2')

response = ses.send_email(
    Source='noreply@yourdomain.com',
    Destination={'ToAddresses': ['user@example.com']},
    Message={
        'Subject': {'Data': 'Server Notification'},
        'Body': {'Text': {'Data': 'Your server has been started.'}}
    }
)
```

## Common Issues

1. **Email not received**: Check spam folder, verify the email address is correct
2. **Access denied**: Make sure you're using the correct region (us-west-2)
3. **Sandbox limitations**: Remember you can only send to verified addresses in sandbox mode
4. **Rate limiting**: Don't exceed 1 email/second in sandbox mode

## Next Steps

After SES is set up, your Minecraft dashboard can send notifications for:
- Server start/stop confirmations
- Error notifications
- Scheduled maintenance alerts
- Cost threshold warnings
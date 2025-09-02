# Get Your FREE FRED API Key (2 Minutes)

## Step 1: Visit FRED API Registration
Go to: https://fred.stlouisfed.org/docs/api/api_key.html

## Step 2: Click "Request API Key"
Fill out the simple form:
- Name: Your name
- Email: Your email
- Organization: Your company/personal
- Intended Use: "Financial data analysis and research"

## Step 3: Get Instant API Key
- Check your email for the API key
- It arrives immediately (no approval needed)

## Step 4: Add to Your System
Once you have the key, store it in AWS Secrets Manager:

```bash
aws secretsmanager create-secret \
    --name "finance-tracker/fred-api-key" \
    --description "FRED API key for economic data" \
    --secret-string '{"api_key":"YOUR_FRED_API_KEY_HERE"}'
```

## Step 5: Deploy Your System
Your Finance Tracker will automatically use the FRED API for additional economic indicators!

## What You Get with FRED API:
- Interest rates and yield curves
- Economic indicators (GDP, inflation, employment)
- Federal Reserve policy rates
- Treasury auction results
- Historical economic data

All FREE with your API key!

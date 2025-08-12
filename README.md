# AWS Marketplace to Azure Integration

## Overview
This project demonstrates an integration flow where a customer purchases a product on AWS Marketplace, and the request is processed through Azure services for fulfillment.

### Flow Steps
1. **Customer purchases on AWS Marketplace**
2. **AWS Marketplace** sends a webhook with registration token, agreement ID, and other details
3. **Azure Logic App** receives the webhook and forwards the request
4. **Azure Function App (`manav`)** processes the request:
    - Parses and validates input
    - Calls AWS APIs to resolve the customer and set deployment parameters
    - Returns a JSON response
5. **Logic App** receives the response and continues the workflow (e.g., notifies customer, updates records)

### Architecture Diagram
```
[AWS Marketplace]
        |
        v
[Azure Logic App]
        |
        v
[Azure Function App (manav)]
        |
        v
[Logic App: Notify/Continue]
```

## Repository Contents
- `manav/` - Azure Function code
- `requirements.txt` - Python dependencies
- `host.json`, `local.settings.json` - Azure Functions configuration

## Getting Started
1. Clone this repository
2. Set up your Azure Function App and Logic App
3. Configure AWS credentials as environment variables in Azure
4. Deploy the solution

import os
import logging
import uuid
import json
from urllib.parse import parse_qs, urlencode
import azure.functions as func
from boto3 import Session
from botocore.config import Config

def gen_random_secret(length=40):
    import random
    import string
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    try:
        # 1) Read raw body (works for x-www-form-urlencoded)
        raw = ''
        if req.get_body():
            raw = req.get_body().decode('utf-8')
        elif req.params:
            # If body missing, try to form raw from params
            raw = urlencode(req.params)

        # 2) Parse key=value&... (URL-decodes values)
        # Fix: Handle None values in parse_qs result
        parsed = {k: v[0] if v and v[0] is not None else '' for k, v in parse_qs(raw).items()}

        token = parsed.get('x-amzn-marketplace-token') or parsed.get('registrationToken') or parsed.get('token')
        agreement_id = parsed.get('x-amzn-marketplace-agreement-id') or parsed.get('agreementId') or parsed.get('agreement-id')
        product_id = parsed.get('x-amzn-marketplace-product-id') or parsed.get('productId') or parsed.get('product-id')

        if not token and not agreement_id:
            logging.warning('No token or agreementId found in request: %s', parsed)
            return func.HttpResponse('missing registration token or agreementId', status_code=400)

        # AWS credentials & region from env vars
        aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
        aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        aws_region = os.getenv('AWS_REGION', 'us-east-1')

        session = Session(
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=aws_region
        )

        # 3) ResolveCustomer (seller account) if token present
        resolved = None
        if token:
            # FIX: Use correct AWS service name
            metering_client = session.client('meteringmarketplace', config=Config(region_name=aws_region))
            response = metering_client.resolve_customer(RegistrationToken=token)
            resolved = response
            logging.info('ResolveCustomer response: %s', response)

            if not product_id and 'ProductCode' in resolved:
                product_id = resolved['ProductCode']

        # 4) Prepare PutDeploymentParameter input
        deploy_name = parsed.get('deploymentName') or parsed.get('name') or os.getenv('DEPLOYMENT_PARAMETER_NAME', 'saas-api-key')
        secret_string = parsed.get('secretString') or gen_random_secret(40)
        expiration_date = parsed.get('expirationDate')

        deploy_client = session.client('marketplace-deployment', config=Config(region_name=aws_region))

        put_input = {
            'agreementId': agreement_id,
            'productId': product_id,
            'catalog': 'AWSMarketplace',
            'deploymentParameter': {
                'name': deploy_name,
                'secretString': secret_string
            },
            'clientToken': str(uuid.uuid4())
        }
        if expiration_date:
            put_input['expirationDate'] = expiration_date

        put_resp = deploy_client.put_deployment_parameter(**put_input)
        logging.info('PutDeploymentParameter response: %s', put_resp)

        # 5) Success response (body must be a string)
        return func.HttpResponse(
            body=json.dumps({
                "message": "PutDeploymentParameter called",
                "resolveCustomer": resolved,
                "putDeploymentParameter": put_resp
            }),
            status_code=200,
            mimetype="application/json"
        )
    except Exception as e:
        logging.error('Error in fulfillment flow', exc_info=True)
        return func.HttpResponse(
            body=json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )

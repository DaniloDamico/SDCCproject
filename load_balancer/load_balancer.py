import json
import logging
import os
import socket
import threading
import time
import xmlrpc.client
import zipfile
from socketserver import ThreadingMixIn
from urllib.parse import urlparse
from xmlrpc.server import SimpleXMLRPCServer, SimpleXMLRPCRequestHandler

import boto3
import docker
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

global number_of_servers
global load_balancer_port
global local_timeout
global elasticity_sleep
global faas_volume
global gateway_api_url
global aws_account_id
global aws_role

SHARED_VOLUME = "/faas"
FAAS_FUNCTION_NAME = "function.py"
FAAS_HANDLER_NAME = "handler.py"
LAMBDA_NAME = "Faas_lambda"
HANDLER_FUNCTION = "handler.lambda_handler"
PYTHONVER = "python3.8"
API_NAME = "FaasApi"
STAGE_NAME = "stage"

HANDLER_CODE = """
import subprocess

FUNCTION_PATH = "./function.py"


def lambda_handler(event, context):
    try:
        parameter = int(event['parameter'])

        print(f"about to call function with par {parameter}")
        process = subprocess.Popen(['python', FUNCTION_PATH, str(parameter)], stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        if process.returncode == 0:
            result = stdout.decode('utf-8')
        else:
            result = stderr.decode('utf-8')

        return {
            'statusCode': 200,
            'body': f"{result}"
        }
    except ValueError:
        return {
            'statusCode': 400,
            'body': "Please provide a valid integer as input."
        }

"""

# List of server URLs
server_urls = []
round_robin_index = 0


class SimpleThreadedXMLRPCServer(ThreadingMixIn, SimpleXMLRPCServer):
    pass


def balance_request(param):
    if server.connection_count == 2 * number_of_servers:
        return offload_to_cloud(param)

    global round_robin_index
    s_url = server_urls[round_robin_index]
    round_robin_index = (round_robin_index + 1) % len(server_urls)

    logger.info(f"server chosen: {s_url}")
    proxy = xmlrpc.client.ServerProxy(s_url)
    response = proxy.call_function(param)
    logger.info(f"response: {response}")
    return response


def offload_to_cloud(param):
    logger.info("OFFLOADING TO CLOUD")
    payload = {'parameter': str(param)}

    response = requests.post(gateway_api_url, json=payload)

    # Check the response
    if response.status_code == 200:
        try:
            logger.info("Cloud request was successful")
            logger.info(response.json())
            body_text = response.json()['body']
            return body_text
        except ValueError:
            return "a server error occurred"
    else:
        logger.error(f"Cloud request failed with status code: {response.status_code}")
        logger.error(response.text)
        return "Cloud request failed"


class RequestHandler(SimpleXMLRPCRequestHandler):
    rpc_paths = ('/',)

    def __init__(self, request, client_address, server):
        self.server = server
        self.server.connection_count += 1
        logger.info(f"number of active connections: {server.connection_count}")
        super().__init__(request, client_address, server)

    def finish(self):
        self.server.connection_count -= 1
        super().finish()


def find_empty_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('localhost', 0))
    _, empty_port = s.getsockname()
    s.close()
    return empty_port


def elasticity():
    while True:
        time.sleep(elasticity_sleep)
        current_connections = server.connection_count
        target_servers = current_connections
        #logger.info(f"Elasticity thread active. Current Connections: {current_connections} Target Servers: {target_servers}")

        if len(server_urls) < target_servers and len(server_urls) < 2 * number_of_servers:
            logging.info("Increasing the number of servers")
            # Increase the number of servers
            new_server()

        elif len(server_urls) > target_servers and len(server_urls) > 1 and len(server_urls) > number_of_servers:
            # Decrease the number of servers
            logging.info("Decreasing the number of servers")
            removed_server = server_urls.pop()
            parsed_url = urlparse(removed_server)
            hostname = parsed_url.hostname
            kill_container_by_name(hostname)


def main():
    server.register_function(balance_request, 'call_faas')
    server.connection_count = 0

    # elasticity thread
    connection_check_thread = threading.Thread(target=elasticity)
    connection_check_thread.daemon = True
    connection_check_thread.start()

    logger.info(f"listening on port {port}")
    server.serve_forever()


def new_server():
    environment = []
    server_port = find_empty_port()
    url = f"SERVER_PORT={server_port}"
    environment.append(url)
    environment.append(f"LOCAL_TIMEOUT={local_timeout}")
    environment.append(f"API_URL={gateway_api_url}")

    hostname = f"server{server_port}"

    client = docker.from_env()
    shared_file = SHARED_VOLUME + "/" + FAAS_FUNCTION_NAME

    client.containers.run(
        image="server-image",
        environment=environment,
        network="fibonacci-network",
        hostname=hostname,
        volumes={shared_file: {'bind': shared_file, 'mode': 'rw'}},
        name=hostname,
        detach=True
    )

    server_urls.append(f"http://{hostname}:{server_port}")


def kill_container_by_name(hostname):
    try:
        client = docker.from_env()
        container = client.containers.get(hostname)
        #logging.info(f"Trying to remove container with hostname: {hostname}")
        # Stop and remove the container
        container.stop()
        container.remove()

        logging.info(f"Container {hostname} removed successfully.")
    except docker.errors.NotFound:
        logging.error(f"Container {hostname} not found.")
    except Exception as e:
        logging.error(f"Error stopping/removing container {hostname}: {e}")


def initialize_faas():
    client = docker.from_env()

    exec_command = f"redis-cli GET {faas_function_name}"
    function_code = client.containers.get(faas_container_name).exec_run(exec_command, stdout=True)
    function_code = function_code.output.decode("utf8").strip()

    with open(SHARED_VOLUME + "/" + FAAS_FUNCTION_NAME, "w") as f:
        f.write(function_code)

    with open(SHARED_VOLUME + "/" + FAAS_HANDLER_NAME, "w") as f:
        f.write(HANDLER_CODE)

    lambda_client = boto3.client('lambda')
    api_gateway_client = boto3.client('apigateway')

    # Create a zip file with your code
    zip_file_name = "function.zip"
    with zipfile.ZipFile(zip_file_name, 'w') as zipf:
        zipf.write(SHARED_VOLUME + "/" + FAAS_FUNCTION_NAME, arcname=FAAS_FUNCTION_NAME)
        zipf.write(SHARED_VOLUME + "/" + FAAS_HANDLER_NAME, arcname=FAAS_HANDLER_NAME)

    # LAMBDA
    try:
        lambda_client.get_function(FunctionName=LAMBDA_NAME)
        response = lambda_client.update_function_code(
            FunctionName=LAMBDA_NAME,
            ZipFile=open(zip_file_name, 'rb').read()
        )
        logging.info(f"Lambda updated successfully: {response}")
    except lambda_client.exceptions.ResourceNotFoundException:

        # Create a new function if it doesn't exist
        response = lambda_client.create_function(
            FunctionName=LAMBDA_NAME,
            Runtime=PYTHONVER,
            Role=aws_role,
            Handler=HANDLER_FUNCTION,
            Code={
                'ZipFile': open(zip_file_name, 'rb').read(),
            },
            Timeout=30,
            MemorySize=3008,
            Publish=True
        )
        logging.info(f"Lambda function created successfully: {response}")

    # Create rest api
    rest_api = api_gateway_client.create_rest_api(
        name=API_NAME
    )

    rest_api_id = rest_api["id"]

    # Get the rest api's root id
    root_resource_id = api_gateway_client.get_resources(
        restApiId=rest_api_id
    )['items'][0]['id']

    # Create an api resource
    api_resource = api_gateway_client.create_resource(
        restApiId=rest_api_id,
        parentId=root_resource_id,
        pathPart='greeting'
    )

    api_resource_id = api_resource['id']

    # Add a post method to the rest api resource
    api_gateway_client.put_method(
        restApiId=rest_api_id,
        resourceId=api_resource_id,
        httpMethod='ANY',
        authorizationType='NONE',
    )

    api_gateway_client.put_method_response(
        restApiId=rest_api_id,
        resourceId=api_resource_id,
        httpMethod='ANY',
        statusCode='200'
    )

    arn_uri = f"arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/arn:aws:lambda:us-east-1:{aws_account_id}:function:{LAMBDA_NAME}/invocations"

    api_gateway_client.put_integration(
        restApiId=rest_api_id,
        resourceId=api_resource_id,
        httpMethod='ANY',
        type='AWS',
        integrationHttpMethod='POST',
        uri=arn_uri,
        credentials=aws_role,
    )

    api_gateway_client.put_integration_response(
        restApiId=rest_api_id,
        resourceId=api_resource_id,
        httpMethod='ANY',
        statusCode='200',
        selectionPattern=''
    )

    api_gateway_client.create_deployment(
        restApiId=rest_api_id,
        stageName='dev',
    )

    global gateway_api_url
    gateway_api_url = f"https://{rest_api_id}.execute-api.us-east-1.amazonaws.com/dev/greeting"




if __name__ == '__main__':
    local_timeout = int(os.environ.get("LOCAL_TIMEOUT"))
    load_balancer_port = int(os.environ.get("LOAD_BALANCER_PORT"))
    elasticity_sleep = int(os.environ.get("ELASTICITY_SLEEP"))

    faas_container_name = os.environ.get("FAAS_CONTAINER_NAME")
    faas_function_name = os.environ.get("FAAS_FUNCTION_NAME")

    aws_account_id = os.environ.get("AWS_ACCOUNT_ID")
    aws_role = os.environ.get("AWS_ROLE")

    initialize_faas()

    if int(os.environ.get("NUMBER_OF_SERVERS")) > 1:
        number_of_servers = int(os.environ.get("NUMBER_OF_SERVERS"))
    else:
        number_of_servers = 1

    for i in range(number_of_servers):
        new_server()

    address = "0.0.0.0"
    port = int(load_balancer_port)
    server = SimpleThreadedXMLRPCServer((address, port), requestHandler=RequestHandler)

    main()

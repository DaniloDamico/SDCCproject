import json
import logging
import os
import socket
import threading
import time
import xmlrpc.client
from socketserver import ThreadingMixIn
from urllib.parse import urlparse
from xmlrpc.server import SimpleXMLRPCServer, SimpleXMLRPCRequestHandler

import docker
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

global number_of_servers
global load_balancer_port
global local_fibonacci_timeout
global elasticity_sleep

# List of server URLs
server_urls = []
round_robin_index = 0


class SimpleThreadedXMLRPCServer(ThreadingMixIn, SimpleXMLRPCServer):
    pass


def balance_request(param):

    if server.connection_count == 2*number_of_servers:
        return offload_to_cloud(param)

    global round_robin_index
    s_url = server_urls[round_robin_index]
    round_robin_index = (round_robin_index + 1) % len(server_urls)

    logger.info(f"server chosen: {s_url }")
    proxy = xmlrpc.client.ServerProxy(s_url)
    response = proxy.call_function(param)
    logger.info(f"response: {response}")
    return response


def offload_to_cloud(param):
    api_url = "https://gi4ubwu7s6.execute-api.us-east-1.amazonaws.com/fibonacciStage/fibonacciResource"

    payload = {
        "value": str(param),
    }

    response = requests.get(api_url, json=payload)

    # Check the response
    if response.status_code == 200:
        try:
            logger.info("Cloud request was successful")
            logger.info(response.json())
            data = response.json()
            body = data.get("body")
            body = json.loads(body)
            return body.get("result")
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
        logger.info(
            f"Elasticity thread active. Current Connections: {current_connections} Target Servers: {target_servers}")

        if len(server_urls) < target_servers and len(server_urls) < 2 * number_of_servers:
            logging.info("Increasing the number of servers")
            # Increase the number of servers
            environment = []
            server_port = find_empty_port()
            url = f"SERVER_PORT={server_port}"
            environment.append(url)
            environment.append(f"LOCAL_FIBONACCI_TIMEOUT={local_fibonacci_timeout}")

            hostname = f"server{server_port}"
            new_server(environment, hostname)
            server_urls.append(f"http://{hostname}:{server_port}")

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


def new_server(environment, hostname):
    client = docker.from_env()
    client.containers.run(
        image="server-image",
        environment=environment,
        network="fibonacci-network",
        hostname=hostname,
        name=hostname,
        detach=True
    )


def kill_container_by_name(hostname):
    try:
        client = docker.from_env()
        container = client.containers.get(hostname)
        logging.info(f"Trying to remove container with hostname: {hostname}")
        # Stop and remove the container
        container.stop()
        container.remove()

        logging.info(f"Container {hostname} removed successfully.")
    except docker.errors.NotFound:
        logging.error(f"Container {hostname} not found.")
    except Exception as e:
        logging.error(f"Error stopping/removing container {hostname}: {e}")


def create_new_servers():
    for i in range(number_of_servers):
        environment = []
        server_port = find_empty_port()
        url = f"SERVER_PORT={server_port}"
        environment.append(url)
        environment.append(f"LOCAL_FIBONACCI_TIMEOUT={local_fibonacci_timeout}")

        hostname = f"server{server_port}"
        new_server(environment, hostname)
        server_urls.append(f"http://{hostname}:{server_port}")


if __name__ == '__main__':
    local_fibonacci_timeout = int(os.environ.get("LOCAL_FIBONACCI_TIMEOUT"))
    load_balancer_port = int(os.environ.get("LOAD_BALANCER_PORT"))
    elasticity_sleep = int(os.environ.get("ELASTICITY_SLEEP"))

    if int(os.environ.get("NUMBER_OF_SERVERS")) > 1:
        number_of_servers = int(os.environ.get("NUMBER_OF_SERVERS"))
    else:
        number_of_servers = 1

    create_new_servers()
    address = "0.0.0.0"
    port = int(load_balancer_port)
    server = SimpleThreadedXMLRPCServer((address, port), requestHandler=RequestHandler)

    main()

import logging
import os
import random
import xmlrpc.client
from socketserver import ThreadingMixIn
from xmlrpc.server import SimpleXMLRPCServer

import docker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

global number_of_servers
global load_balancer_port
global local_fibonacci_timeout

# List of server URLs
server_urls = []


class SimpleThreadedXMLRPCServer(ThreadingMixIn, SimpleXMLRPCServer):
    pass


def balance_request(n):
    server = random.choice(server_urls)
    logger.info(f"server chosen: {server}")
    proxy = xmlrpc.client.ServerProxy(server)
    result = proxy.fibonacci(n)
    logger.info(f"{result}")
    return result


def main():
    address = "0.0.0.0"
    port = int(load_balancer_port)
    server = SimpleThreadedXMLRPCServer((address, port))
    server.register_function(balance_request, 'fibonacci')
    logger.info(f"listening on port {port}")
    server.serve_forever()


def create_new_servers():
    client = docker.from_env()
    for i in range(2, int(number_of_servers) + 1):
        environment = []
        server_port = int(load_balancer_port) + i
        url = f"SERVER_PORT={server_port}"
        environment.append(url)
        environment.append(f"LOCAL_FIBONACCI_TIMEOUT={local_fibonacci_timeout}")

        hostname = f"server{i}"

        client.containers.run(
            image="server-image",
            environment=environment,
            network="fibonacci-network",
            hostname=hostname,
            detach=True
        )
        server_urls.append(f"http://{hostname}:{server_port}")


if __name__ == '__main__':
    local_fibonacci_timeout = os.environ.get("LOCAL_FIBONACCI_TIMEOUT")
    load_balancer_port = os.environ.get("LOAD_BALANCER_PORT")

    first_server_port = int(load_balancer_port) + 1
    server_urls.append(f"http://server1:{first_server_port}")

    if int(os.environ.get("NUMBER_OF_SERVERS")) > 1:
        number_of_servers = int(os.environ.get("NUMBER_OF_SERVERS"))
        create_new_servers()
    else:
        number_of_servers = 1

    main()

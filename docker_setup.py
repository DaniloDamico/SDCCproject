import subprocess
from dotenv import load_dotenv
import os


def write_dockercompose():
    local_fibonacci_timeout = os.environ.get("LOCAL_FIBONACCI_TIMEOUT")
    number_of_servers = os.environ.get("NUMBER_OF_SERVERS")
    load_balancer_port = os.environ.get("LOAD_BALANCER_PORT")
    server_port = int(load_balancer_port) + 1

    content = f"""
    services:
        server1:
            build:
                context: ./server
            environment:
                - SERVER_PORT={server_port}
                - LOCAL_FIBONACCI_TIMEOUT={local_fibonacci_timeout}
            image: server-image
            networks:
                - fibonacci-network
                
                
        loadbalancer:
            build:
                context: ./load_balancer
            environment:
                - NUMBER_OF_SERVERS={number_of_servers}
                - LOAD_BALANCER_PORT={load_balancer_port}
                - LOCAL_FIBONACCI_TIMEOUT={local_fibonacci_timeout}
            ports:
                - "{load_balancer_port}:{load_balancer_port}"
            networks:
                - fibonacci-network
            volumes:
                - /var/run/docker.sock:/var/run/docker.sock

    networks:
        fibonacci-network:
            name: fibonacci-network
    """

    with open("docker-compose.yml", "w") as f:
        f.write(content)


def main():
    # Load environment variables from the .env file
    load_dotenv()
    write_dockercompose()

    subprocess.run(["docker-compose", "up", "-d"])


if __name__ == '__main__':
    main()

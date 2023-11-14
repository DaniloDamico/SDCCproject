import subprocess
from dotenv import load_dotenv
import os


def write_dockercompose():
    local_fibonacci_timeout = os.environ.get("LOCAL_TIMEOUT")
    number_of_servers = os.environ.get("NUMBER_OF_SERVERS")
    load_balancer_port = os.environ.get("LOAD_BALANCER_PORT")
    elasticity_sleep = os.environ.get("ELASTICITY_SLEEP")

    faas_container_name = os.environ.get("FAAS_CONTAINER_NAME")
    faas_function_name = os.environ.get("FAAS_FUNCTION_NAME")

    credentials_path = os.environ.get("CREDENTIALS_PATH")
    aws_account_id = os.environ.get("AWS_ACCOUNT_ID")
    aws_role = os.environ.get("AWS_ROLE")

    content = f"""
    services:
        server:
            build:
                context: ./server
            image: server-image
            networks:
                - fibonacci-network
                
                
        loadbalancer:
            build:
                context: ./load_balancer
            environment:
                - NUMBER_OF_SERVERS={number_of_servers}
                - LOAD_BALANCER_PORT={load_balancer_port}
                - LOCAL_TIMEOUT={local_fibonacci_timeout}
                - ELASTICITY_SLEEP={elasticity_sleep}
                - FAAS_CONTAINER_NAME={faas_container_name}
                - FAAS_FUNCTION_NAME={faas_function_name}
                - AWS_ACCOUNT_ID={aws_account_id}
                - AWS_ROLE={aws_role}
                - AWS_DEFAULT_REGION={os.environ.get("AWS_DEFAULT_REGION")}
            ports:
                - "{load_balancer_port}:{load_balancer_port}"
            networks:
                - fibonacci-network
            volumes:
                - /var/run/docker.sock:/var/run/docker.sock
                - /faas:/faas
                - {credentials_path}:/root/.aws/credentials:ro

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

    subprocess.run(["docker-compose", "build", "server"])
    subprocess.run(["docker-compose", "network", "create", "fibonacci-network"])
    subprocess.run(["docker-compose", "up", "loadbalancer", "-d"])


if __name__ == '__main__':
    main()

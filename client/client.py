import os
import xmlrpc.client

from dotenv import load_dotenv

global load_balancer_url


def send_to_docker(n):
    proxy = xmlrpc.client.ServerProxy(load_balancer_url)
    result = proxy.call_faas(n)
    print(result)


if __name__ == '__main__':
    load_dotenv()
    load_balancer_url = "http://127.0.0.1:" + os.environ.get("LOAD_BALANCER_PORT") + "/"

    try:
        while True:
            user_input = input("insert parameter of the FaaS function:")

            try:
                send_to_docker(user_input)
            except xmlrpc.client.Fault:
                print("Something unusual was sent from the other side of the connection:")
                continue
    except KeyboardInterrupt:
        print("\nShutting down")

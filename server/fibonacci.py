import json
import logging
import multiprocessing
import os
import xmlrpc.server
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
global local_fibonacci_timeout


def fibonacci(n):
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    else:
        return fibonacci(n - 1) + fibonacci(n - 2)


def fibonacci_cloud(n):
    api_url = "https://gi4ubwu7s6.execute-api.us-east-1.amazonaws.com/fibonacciStage/fibonacciResource"

    payload = {
        "value": str(n),
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


def local_manager(queue, n):
    result = str(fibonacci(n))
    queue.put(result)


def fibonacci_manager(n):
    # Execute local computation in a new process
    queue = multiprocessing.Queue()
    process = multiprocessing.Process(target=local_manager, args=(queue, n))
    process.start()
    process.join(timeout=local_fibonacci_timeout)

    if process.is_alive():
        process.kill()

    try:
        result = queue.get(False)
    except Exception:
        logger.info("local execution took too long. Offloading to cloud.")
        result = fibonacci_cloud(n)

    output = f"Number {n}, result: {result}"
    logger.info(output)
    return output


def main():
    global local_fibonacci_timeout
    local_fibonacci_timeout = int(os.environ.get("LOCAL_FIBONACCI_TIMEOUT"))

    address = "0.0.0.0"
    port = int(os.getenv('SERVER_PORT', 8001))
    server = xmlrpc.server.SimpleXMLRPCServer((address, port))
    logger.info(f"listening on port {port}")
    server.register_function(fibonacci_manager, "fibonacci")
    server.serve_forever()


if __name__ == '__main__':
    main()

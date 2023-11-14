import json
import logging
import multiprocessing
import os
import subprocess
import xmlrpc.server

import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
global local_timeout
global api_url

FUNCTION_PATH = '/faas/function.py'


def offload_to_cloud(n):

    payload = {'parameter': str(n)}
    response = requests.post(api_url, json=payload)

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


def local_faas_manager(queue, par):
    try:
        logging.info(f"about to call function with par {par}")
        process = subprocess.Popen(['python', FUNCTION_PATH, str(par)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        if process.returncode == 0:
            logging.info("function executed successfully")
            logging.info(f"{stdout.decode('utf-8')}")
            queue.put(stdout.decode('utf-8'))
        else:
            logging.info(f"an error occurred during the script execution: {process.returncode}")
            logging.info(f"{stderr.decode('utf-8')}")
            queue.put(stderr.decode('utf-8'))
    except Exception as e:
        queue.put(e)


def faas_manager(par):
    # Execute local computation in a new process
    queue = multiprocessing.Queue()
    process = multiprocessing.Process(target=local_faas_manager, args=(queue, par))
    process.start()
    process.join(timeout=local_timeout)

    if process.is_alive():
        process.kill()

    try:
        result = queue.get(False)
    except Exception:
        logger.info("local execution took too long. Offloading to cloud.")
        result = offload_to_cloud(par)

    output = f"Number {par}, result: {result}"
    logger.info(output)
    return output


def main():
    global local_timeout
    local_timeout = int(os.environ.get("LOCAL_TIMEOUT"))
    global api_url
    api_url = os.environ.get("API_URL")

    address = "0.0.0.0"
    port = int(os.getenv('SERVER_PORT', 8001))
    server = xmlrpc.server.SimpleXMLRPCServer((address, port))
    logger.info(f"listening on port {port}")
    server.register_function(faas_manager, "call_function")
    server.serve_forever()


if __name__ == '__main__':
    main()

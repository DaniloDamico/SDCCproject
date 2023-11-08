import logging
import os
import json

logger = logging.getLogger()
print('Loading function')


def lambda_handler(event, context):
    logger.setLevel(os.environ.get("LOG_LEVEL", logging.INFO))
    logger.debug("Event: %s", event)

    value = event.get("value")
    result = None
    try:
        if value is not None:
            value = int(value)
            a, b = 0, 1
            for _ in range(value):
                a, b = b, a + b
            result = a
            logger.info("The Fibonacci number of %s is %s", value, result)
        else:
            logger.error("I can't calculate the Fibonacci number of %s.", value)
    except ValueError:
        logger.warning("Something unexpected went wrong")

    response = {
        "statusCode": 200,  # HTTP status code
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps({"result": result})
    }

    return response

from loguru import logger
import datetime
import json

from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2
from google.protobuf import duration_pb2


def create_task(cfg, payload, task_name, delay):
    """Create a task with a payload, and a delay in s
    
    """
    
    duration = duration_pb2.Duration()

    duration.FromSeconds(1800)
    
    # Construct the request body.
    task = {
        "dispatch_deadline": duration,
        "http_request": {  # Specify the type of request.
            "http_method": tasks_v2.HttpMethod.POST,
            "url": cfg['url'],  # The full url path that the task will be sent to.
            'oidc_token': {
               'service_account_email': cfg['service_account']
            },
        }
    }
    
    if delay is not None:
        # Convert "seconds from now" into an rfc3339 datetime string.
        d = datetime.datetime.utcnow() + datetime.timedelta(seconds=delay)

        # Create Timestamp protobuf.
        timestamp = timestamp_pb2.Timestamp()
        timestamp.FromDatetime(d)

        # Add the timestamp to the tasks.
        task["schedule_time"] = timestamp
    
    if isinstance(payload, dict):
        # Convert dict to JSON string
        payload = json.dumps(payload)
        # specify http content-type to application/json
        task["http_request"]["headers"] = {"Content-type": "application/json"}

    # The API expects a payload of type bytes.
    converted_payload = payload.encode()
    
    task["name"] = task_name

    # Add the payload to the request.
    task["http_request"]["body"] = converted_payload

    """ No lead time.
    if in_seconds is not None:
        # Convert "seconds from now" into an rfc3339 datetime string.
        d = datetime.datetime.utcnow() + datetime.timedelta(seconds=in_seconds)

        # Create Timestamp protobuf.
        timestamp = timestamp_pb2.Timestamp()
        timestamp.FromDatetime(d)

        # Add the timestamp to the tasks.
        task["schedule_time"] = timestamp
    """
    
    return task

def deploy_task(cfg, task):
    
    # Create a client.
    client = tasks_v2.CloudTasksClient()
    
    task["name"] = client.task_path(cfg['project'], cfg['location'], cfg['queue'], task["name"])

    # Construct the fully qualified queue name.
    parent = client.queue_path(
        cfg['project'], 
        cfg['location'], 
        cfg['queue'],
    )
    
    # Use the client to build and send the task.
    response = client.create_task(request={"parent": parent, "task": task})

    logger.info("Created task {}".format(response.name))
    
    return 1
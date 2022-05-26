"""h2ox-w2w - run daily"""

import datetime
import json
import logging
import os
import sys
import traceback
from datetime import timedelta

from flask import Flask, request
from loguru import logger

from h2ox.w2w.reservoirs import post_inference, refresh_reservoir_levels
from h2ox.w2w.slackbot import SlackMessenger
from h2ox.w2w.w2w_utils import create_task, deploy_task

app = Flask(__name__)


if __name__ != "__main__":
    # Redirect Flask logs to Gunicorn logs
    gunicorn_logger = logging.getLogger("gunicorn.error")
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
    app.logger.info("Service started...")
else:
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))


def format_stacktrace():
    parts = ["Traceback (most recent call last):\n"]
    parts.extend(traceback.format_stack(limit=25)[:-2])
    parts.extend(traceback.format_exception(*sys.exc_info())[1:])
    return "".join(parts)


@app.route("/", methods=["POST"])
def run_daily():

    """Receive a request and queue downloading ecmwf data

    Request params:
    ---------------

        today: str


    # refresh reservoir levels
    # run inference
    # post to results table
    # enqueue tomorrow's run

    #if pubsub:
    envelope = request.get_json()
    if not envelope:
        msg = "no Pub/Sub message received"
        print(f"error: {msg}")
        return f"Bad Request: {msg}", 400

    if not isinstance(envelope, dict) or "message" not in envelope:
        msg = "invalid Pub/Sub message format"
        print(f"error: {msg}")
        return f"Bad Request: {msg}", 400

    request_json = envelope["message"]["data"]

    if not isinstance(request_json, dict):
        json_data = base64.b64decode(request_json).decode("utf-8")
        request_json = json.loads(json_data)

    logger.info('request_json: '+json.dumps(request_json))

    # parse request
    today_str = request_json['today']

    """

    payload = request.get_json()

    if not payload:
        msg = "no message received"
        print(f"error: {msg}")
        return f"Bad Request: {msg}", 400

    logger.info("payload: " + json.dumps(payload))

    if not isinstance(payload, dict):
        msg = "invalid task format"
        print(f"error: {msg}")
        return f"Bad Request: {msg}", 400

    token = os.environ.get("SLACKBOT_TOKEN")
    target = os.environ.get("SLACKBOT_TARGET")

    if token is not None and target is not None:

        slackmessenger = SlackMessenger(
            token=token,
            target=target,
            name="w2w-run-daily",
        )
    else:
        slackmessenger = None

    requeue = os.environ.get("REQUEUE")
    if requeue is not None:
        requeue = requeue.lower() == "true"

    today_str = payload["today"]

    today = datetime.datetime.strptime(today_str, "%Y-%m-%d").replace(tzinfo=None)

    # step 1-> refresh reservoir levels
    filled_datapts = refresh_reservoir_levels(today)
    if slackmessenger is not None:
        slackmessenger.message(f" W2W ::: added {filled_datapts} data points")

    # step 2-> rerun inference and post results
    basin_networks = json.loads(os.environ.get("BASIN_NETWORKS"))
    url = os.environ.get("INFERENCE_URL_ROOT")
    msg = post_inference(today, basin_networks, url)
    if slackmessenger is not None:
        slackmessenger.message(f"W2W ::: inference: {json.dumps(msg)}")

    # step 3 -> enqueue tomorrow
    if requeue:
        enqueue_tomorrow(today)
        if slackmessenger is not None:
            slackmessenger.message(
                f"W2W ::: enqueued {(today+timedelta(hours=24)).isoformat()}"
            )

    return f"Ran day {today_str}", 200


def enqueue_tomorrow(today):

    tomorrow = today + timedelta(hours=24)

    cfg = dict(
        project=os.environ["project"],
        queue=os.environ["queue"],  # queue name
        location=os.environ["location"],  # queue
        url=os.environ["url"],  # service url
        service_account=os.environ["service_account"],  # service acct
    )

    task = create_task(
        cfg=cfg,
        payload=dict(today=tomorrow.isoformat()[0:10]),
        task_name=tomorrow.isoformat()[0:10],
        delay=24 * 3600,
    )

    deploy_task(cfg, task)

import datetime
import os

from h2ox.w2w.w2w_utils import create_task, deploy_task

if __name__ == "__main__":

    today = datetime.datetime.now().isoformat()[0:10]

    cfg = dict(
        project=os.environ["project"],
        queue=os.environ["queue"],
        location=os.environ["location"],
        service_account=os.environ["service_account"],
        url=os.environ["url"],
    )

    payload = dict(today=today)

    task = create_task(cfg=cfg, payload=payload, task_name=today, delay=0)

    deploy_task(cfg, task)

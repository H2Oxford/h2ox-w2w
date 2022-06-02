[<img alt="Wave2Web Hack" width="1000px" src="https://github.com/H2Oxford/.github/raw/main/profile/img/wave2web-banner.png" />](https://www.wricitiesindia.org/content/wave2web-hack)

H2Ox is a team of Oxford University PhD students and researchers who won first prize in the[Wave2Web Hackathon](https://www.wricitiesindia.org/content/wave2web-hack), September 2021, organised by the World Resources Institute and sponsored by Microsoft and Blackrock. In the Wave2Web hackathon, teams competed to predict reservoir levels in four reservoirs in the Kaveri basin West of Bangaluru: Kabini, Krishnaraja Sagar, Harangi, and Hemavathy. H2Ox used sequence-to-sequence models with meterological and forecast forcing data to predict reservoir levels up to 90 days in the future.

The H2Ox dashboard can be found at [https://h2ox.org](https://h2ox.org). The data API can be accessed at [https://api.h2ox.org](https://api.h2ox.org/docs#/). All code and repos can be [https://github.com/H2Oxford](https://github.com/H2Oxford). Our Prototype Submission Slides are [here](https://docs.google.com/presentation/d/1J_lmFu8TTejnipl-l8bXUZdKioVseRB4tTzqK6sEokI/edit?usp=sharing). The H2Ox team is [Lucas Kruitwagen](https://github.com/Lkruitwagen), [Chris Arderne](https://github.com/carderne), [Tommy Lees](https://github.com/tommylees112), and [Lisa Thalheimer](https://github.com/geoliz).

# H2Ox - W2W
This repo is for a dockerised service to update reservoir data and inference in [BigQuery](https://cloud.google.com/bigquery) tables that back the [h2ox api](https://api.h2ox.org/docs#/).
This service obtains selected reservoirs from a BigQuery tracking table then obtains reservoir levels from the [India-WRIS](indiawris.gov.in/wris/#/) API.
For basin networks where reservoir data, and forecast and historical meteorological data is available, the service calls a [TorchServe](https://pytorch.org/serve/) endpoint that serves the trained models from [h2ox-ai](https://github.com/H2Oxford/h2ox-ai).
The inferred predictions are then posted back to a BigQuery table that the h2ox api caches queries from.

## Installation

This repo can be `pip` installed:

    pip install https://github.com/H2Oxford/h2ox-w2w.git

For development, the repo can be pip installed with the `-e` flag and `[dev]` options:

    git clone https://github.com/H2Oxford/h2ox-w2w.git
    cd h2ox-w2w
    pip install -e .[dev]

For containerised deployment, a docker container can be built from this repo:

    docker build -t <my-tag> .

Cloudbuild container registery services can also be targeted at forks of this repository.

## Useage

### Credentials

A slackbot messenger is also implemented to post updates to a slack workspace.
Follow [these](https://api.slack.com/bot-users) instuctions to set up a slackbot user, and then set the `SLACKBOT_TOKEN` and `SLACKBOT_TARGET` environment variables.

### Service details

The Flask app in `main.py` listens for a POST http request and then triggers the ingestion workflow.
The http request must have a json payload with a YYYY-mm-dd datetime string keyed to "today": `{"today":"<YYYY-mm-dd>"}`.
The script then:

1. queries reservoir levels from the WRIS API and stores this data in the bigquery table
2. where data is sufficiently complete, packages data for inference and calls the TorchServe endpoint
3. posts inference data to a results BigQuery table
5. enqueues tomorrows task in the cloud task queue


The following environment variables are required:

    SLACKBOT_TOKEN=<my-slackbot-token>                 # a token for a slack-bot messenger
    SLACKBOT_TARGET=<my-slackbot-target>               # target channel to issue ingestion updates
    BASIN_NETWORKS=<json-parseable-list>               # a json-parseable list of scope basin networks to run
    INFERENCE_URL_ROOT=<http://my/torchserve/endpoint> # the endpoint url for the served models

To requeue the next day's ingestion, the ingestion script will push a task to a [cloud task queue](https://cloud.google.com/tasks/docs/creating-queues) to enqueue ingestion for tomorrow. This way a continuous service is created that runs daily. The additional environment variables will be required:

    project=<my-gcp-project>            # gcp project associated with queue and cloud storage
    queue=<my-queue-name>               # queue name where pending tasks can be places
    location=<my-queue-region>          # location name for task queue
    url=<http://my/dockerised/service>  # url of the entrypoint for the docker container to be run
    service_account=<myacct@email.com>  # service account for submitting tasks and http request


Environment variables can be put in a `.env` file and passed to the docker container at runtime:

    docker run --env-file=.env -t <my-tag>


## Citation


Our Wave2Web submission can be cited as:

    Kruitwagen, L., Arderne, C., Lees, T., Thalheimer, L, Kuzma, S., & Basak, S. (2022): Wave2Web: Near-real-time reservoir availability prediction for water security in India. Preprint submitted to EarthArXiv, doi: 10.31223/X5V06F. Available at https://eartharxiv.org/repository/view/3381/

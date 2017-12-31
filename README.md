# GCP Night King

A service for resurrecting preempted GCE instances.


## Overview

This repository contains a service that restarts preempted GCE instances.

It uses Google Cloud Pub/Sub for reporting instance preemption.

When a machine is about to be preempted, if it wants to be restarted,
it should publish a Pub/Sub message to a known topic (e.g. "night-king-preempt"):

```json
{
    "name": "<instance-name>",
    "zone": "<instance-zone>"
}
```

The Night King service listens on the Pub/Sub topic, and tries to restart instances accordingly.


## Installation

Create a Pub/Sub topic & subscription:

```sh
gcloud pubsub topics create night-king-preempt
gcloud pubsub subscriptions create night-king-preempt --topic night-king-preempt
```

### Running The Night King service

The Night King service is a Python application.
To run it directly, you'll need Python 3.4+ and [Pipenv](https://docs.pipenv.org/):

```sh
pipenv install
pipenv run python -m nightking.lurker --project <project-id>
```

The detailed help:

```sh
pipenv run python -m nightking.lurker --help
The Night King GCE instance resurrection service.

Usage:
  lurker.py --project <gce-project-id> [--subscription-name <subscription-name>]
  lurker.py (-h | --help)
  lurker.py --version

Options:
  -h --help                                Show this screen.
  --version                                Show version.
  --project <gce-project-id>               GCE project ID.
  --subscription-name <subscription-name>  Name of Pub/Sub subscription name to listen to [default: night-king-preempt].
```

You'll also need to have [Google Cloud SDK authorization](https://cloud.google.com/sdk/docs/) set up for the service to be able to receive messages from Google Pub/Sub.

Beyond that, there are multiple ways to have the service running "in production" (e.g., not in the foreground of your dev-machine terminal).

You can use whatever method fits your environment (and deployment-setup contributions are welcome).

## Configure Shutdown Script

To have preempted instances publish a message, use the included [shutdown script](https://cloud.google.com/compute/docs/shutdownscript) (or integrate it with an existing shutdown script):

```sh
gcloud compute instances create my-resurrectable-instance \
    --preemptible --metadata-from-file shutdown-script=zombie.sh [...]
```

Note: when providing explicit scopes, make sure to include the `https://www.googleapis.com/auth/pubsub` scope to allow the instance to publish messages to topics (it is included in the default scopes).


## Development

Use either Pipenv or Docker to hack on the service locally.

For Pipenv workflow - take a look at the `Running ...` section.

If you add / remove / modify Python dependencies, also run `pipenv run pip freeze > requirements.txt` to keep the Pipfile and requirements.txt files in sync (one is used by Pipenv, and one is used by Docker).

For Docker workflow, either build or pull the Docker image:

```sh
# building locally:
docker build -t itamarost/gcp-night-king:v1-py3 .
# pulling prebuilt image:
docker pull itamarost/gcp-night-king:v1-py3
```

Then run it locally to hack on it:

```sh
docker run -it --rm -v $HOME/.config/gcloud:/root/.config/gcloud itamarost/gcp-night-king:v1-py3 --project <project-id>
```

Note: the bind-mount is useful to use your own Google Cloud credentials (same as when using Pipenv) - feel free to use other methods to obtain appropriate Google Cloud credentials.

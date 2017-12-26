# GCP Night King

A small service for resurrecting preempted GCE instances.

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

TODO - service deployment

## Configure Shutdown Script

To have preempted instances publish a message, use the included [shutdown script](https://cloud.google.com/compute/docs/shutdownscript) (or integrate it with an existing shutdown script):

```sh
gcloud compute instances create my-resurrectable-instance \
    --preemptible --metadata-from-file shutdown-script=zombie.sh [...]
```

Note: when providing explicit scopes, make sure to include the `https://www.googleapis.com/auth/pubsub` scope to allow the instance to publish messages to topics (it is included in the default scopes).

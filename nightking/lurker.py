#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright 2017 Itamar Ostricher

"""The Night King GCE instance resurrection service.

Usage:
  lurker.py --project <gce-project-id> [--subscription-name <subscription-name>]
  lurker.py (-h | --help)
  lurker.py --version

Options:
  -h --help                                Show this screen.
  --version                                Show version.
  --project <gce-project-id>               GCE project ID.
  --subscription-name <subscription-name>  Name of Pub/Sub subscription name to listen to [default: night-king-preempt].
"""

import json
import logging
import time

from apiclient import errors
from docopt import docopt
from googleapiclient import discovery
from google.cloud import pubsub_v1


logger = logging.getLogger('nightking.lurker')


class GoogleCloud:
  """Helper class for interacting with Google Cloud compute API."""

  def __init__(self, project_id):
    # disable cache discovery
    # https://github.com/google/google-api-python-client/issues/299#issuecomment-268915510
    compute = discovery.build('compute', 'v1', cache_discovery=False)
    self.inst_api = compute.instances()
    self.project_id = project_id

  def get_instance(self, zone, inst_name):
    """Return a dictionary describing a GCE instance, if it exists."""
    return self.inst_api.get(project=self.project_id, zone=zone,
                             instance=inst_name).execute()

  def start_instance(self, zone, inst_name):
    """Call the start GCE instance API, returning the operation response."""
    return self.inst_api.start(project=self.project_id, zone=zone,
                               instance=inst_name).execute()


def resurrect_instance(project_id, instance_desc):
  """Try resurrecting a terminated (preempted) GCE instance.

  Input `instance_desc`: dictionary with the instance 'name' and 'zone'.

  Ignores instance if: it doesn't exist; it's already running.
  Retry if: instance not yet terminated.
  """
  try:
    inst_name, zone = instance_desc['name'], instance_desc['zone']
  except KeyError:
    logger.error('Parsed message missing mandatory fields: %r', instance_desc)
    return
  except TypeError:
    logger.error('Parsed message not valid dictionary: %r', instance_desc)
    return
  logger.info('Got resurrection request for instance "%s" in zone "%s"',
              inst_name, zone)

  gcloud = GoogleCloud(project_id)
  keep_trying = True
  while keep_trying:
    keep_trying = False
    try:
      gce_inst = gcloud.get_instance(zone, inst_name)
    except (errors.HttpError, TypeError):
      logger.warning('No instance named "%s" in zone "%s"', inst_name, zone)
    else:
      if gce_inst['status'] == 'STOPPING':
        logger.info('Instance "%s" in zone "%s" not yet terminated - waiting..',
                    inst_name, zone)
        keep_trying = True
        time.sleep(30.0)
      elif gce_inst['status'] != 'TERMINATED':
        logger.info('Instance "%s" in zone "%s" not terminated',
                    inst_name, zone)
      else:
        logger.info('Attempting to start instance "%s" in zone "%s"',
                    inst_name, zone)
        response = gcloud.start_instance(zone, inst_name)
        logger.debug('Started GCE operation: %r', response)


def make_callback(subscription_path, project_id):
  """Return a callback closure"""

  def callback(message):
    """Handle Pub/Sub resurrection message.

    Ignore (and ACK) messages that are not well-formed.
    Try handle any other message, ACKing it eventually (always).
    """
    logger.info('Handling message from subscription "%s"', subscription_path)
    # parse the message, ACK on failure to avoid duplicate deliveries
    try:
      instance_desc = json.loads(message.data)
    except:
      logger.exception('Failed parsing JSON message - ignoring it\n%s', message)
    else:
      resurrect_instance(project_id, instance_desc)
    finally:
      logger.info('ACKing message\n%s', message)
      message.ack()

  return callback


def main(project_id, subscription_name):
  """Subscribe to Pub/Sub topic, handling GCE-instance-resurrection messages."""
  subscriber = pubsub_v1.SubscriberClient()
  subscription_path = subscriber.subscription_path(
      project_id, subscription_name)
  subscriber.subscribe(subscription_path,
                       callback=make_callback(subscription_path, project_id))
  # The subscriber is non-blocking, so we must keep the main thread from
  # exiting to allow it to process messages in the background.
  logger.info('Listening for messages on subscription: %s', subscription_path)
  while True:
    time.sleep(60)


def configure_logging():
  """Configure DEBUG-level logging with console output."""
  logger.setLevel(logging.DEBUG)
  ch = logging.StreamHandler()
  ch.setLevel(logging.DEBUG)
  formatter = logging.Formatter(
      '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
  ch.setFormatter(formatter)
  logger.addHandler(ch)


if __name__ == '__main__':
  args = docopt(__doc__, version='Night King Service 0.1')
  configure_logging()
  main(args['--project'], args['--subscription-name'])

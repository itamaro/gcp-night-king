# -*- coding: utf-8 -*-
# Copyright 2017 Itamar Ostricher

import json
from unittest import mock

from apiclient import errors
import pytest

from nightking import lurker


@pytest.fixture(scope='module')
def callback():
  return lurker.make_callback('path', 'project')


class MockPubSubMessage:
  """A mock class for Pub/Sub messages"""

  def __init__(self, data):
    self.data = data
    self.acked = False

  def ack(self):
    self.acked = True


def test_resurrect(mocker, callback):
  """Test that when a VM is in TERMINATED state it is restarted."""
  mocker.patch.object(lurker.GoogleCloud, '__init__',
                      auto_spec=True, return_value=None)
  mocker.patch.object(lurker.GoogleCloud, 'get_instance',
                      auto_spec=True, return_value={'status': 'TERMINATED'})
  mocker.patch.object(lurker.GoogleCloud, 'start_instance', auto_spec=True)
  message = MockPubSubMessage('{"name": "foo", "zone": "bar"}')
  callback(message)
  assert message.acked is True
  lurker.GoogleCloud.get_instance.assert_called_once_with('bar', 'foo')
  lurker.GoogleCloud.start_instance.assert_called_once_with('bar', 'foo')


def test_resurrect_realistic_flow(mocker, callback):
  """Test that when a VM is RUNNING -> STOPPING -> TERMINATED,
     it is restarted eventually."""
  mocker.patch.object(lurker.GoogleCloud, '__init__',
                      auto_spec=True, return_value=None)
  mocker.patch.object(
      lurker.GoogleCloud, 'get_instance', auto_spec=True,
      side_effect=[
          {'status': 'RUNNING'},
          {'status': 'RUNNING'},
          {'status': 'RUNNING'},
          {'status': 'STOPPING'},
          {'status': 'TERMINATED'},
      ])
  mocker.patch.object(lurker.GoogleCloud, 'start_instance', auto_spec=True)
  mocker.patch('time.sleep')  # skip the wait
  message = MockPubSubMessage('{"name": "foo", "zone": "bar"}')
  callback(message)
  assert message.acked is True
  assert 5 == lurker.GoogleCloud.get_instance.call_count
  lurker.GoogleCloud.start_instance.assert_called_once_with('bar', 'foo')


def test_resurrect_still_running(mocker, callback):
  """Test that when a VM is in RUNNING state for a while nothing happens."""
  mocker.patch.object(lurker.GoogleCloud, '__init__',
                      auto_spec=True, return_value=None)
  mocker.patch.object(lurker.GoogleCloud, 'get_instance',
                      auto_spec=True, return_value={'status': 'RUNNING'})
  mocker.patch.object(lurker.GoogleCloud, 'start_instance', auto_spec=True)
  mocker.patch('time.sleep')  # skip the wait
  message = MockPubSubMessage('{"name": "foo", "zone": "bar"}')
  callback(message)
  assert message.acked is True
  assert lurker.GoogleCloud.get_instance.call_count > 2
  lurker.GoogleCloud.start_instance.assert_not_called()


def test_resurrect_stopping(mocker, callback):
  """Test that when a VM is in STOPPING state it will be
     restarted after it reaches the TERMINATED state."""
  mocker.patch.object(lurker.GoogleCloud, '__init__',
                      auto_spec=True, return_value=None)
  mocker.patch.object(
      lurker.GoogleCloud, 'get_instance', auto_spec=True,
      side_effect=[{'status': 'STOPPING'}, {'status': 'TERMINATED'}])
  mocker.patch.object(lurker.GoogleCloud, 'start_instance', auto_spec=True)
  mocker.patch('time.sleep')  # skip the wait
  message = MockPubSubMessage('{"name": "foo", "zone": "bar"}')
  callback(message)
  assert message.acked is True
  assert 2 == lurker.GoogleCloud.get_instance.call_count
  lurker.GoogleCloud.start_instance.assert_called_once_with('bar', 'foo')


def test_resurrect_no_such_vm(mocker, callback):
  """Test that when there's no such VM nothing happens."""
  mocker.patch.object(lurker.GoogleCloud, '__init__',
                      auto_spec=True, return_value=None)
  mocker.patch.object(lurker.GoogleCloud, 'get_instance',
                      auto_spec=True, side_effect=errors.HttpError)
  mocker.patch.object(lurker.GoogleCloud, 'start_instance', auto_spec=True)
  message = MockPubSubMessage('{"name": "foo", "zone": "bar"}')
  callback(message)
  assert message.acked is True
  lurker.GoogleCloud.get_instance.assert_called_once_with('bar', 'foo')
  lurker.GoogleCloud.start_instance.assert_not_called()


def test_invalid_json(mocker, callback):
  """Test that invalid JSON doesn't crash the service, and message is ACKed."""
  mocker.patch('nightking.lurker.resurrect_instance')
  message = MockPubSubMessage('foo')
  callback(message)
  assert message.acked is True
  lurker.resurrect_instance.assert_not_called()


def test_missing_fields(mocker, callback):
  """Test that missing JSON doesn't crash the service, and message is ACKed."""
  mocker.spy(lurker, 'resurrect_instance')
  mocker.patch.object(lurker.GoogleCloud, '__init__',
                      auto_spec=True, return_value=None)
  mocker.patch.object(lurker.GoogleCloud, 'get_instance', auto_spec=True)
  message = MockPubSubMessage('{"foo": "bar"}')
  callback(message)
  assert message.acked is True
  lurker.resurrect_instance.assert_called_once()
  lurker.GoogleCloud.get_instance.assert_not_called()

import abc
import argparse
import pytest
import subprocess

from tests.marqo_test import MarqoTestCase


class BaseTestCase(MarqoTestCase):
    @abc.abstractmethod
    def prepare(self):

        pass

@pytest.mark.marqo_from_version('2.5')
class TestPartialUpdateExistingIndex(BaseTestCase):
    def prepare(self):
        # Create structured and unstructured indexes and add some documents
        pass

    def test_partialUpdate_scoreModifiers_success(self):
        # This runs on to_version
        pass

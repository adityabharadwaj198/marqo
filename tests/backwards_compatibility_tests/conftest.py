import pytest
import semver

from marqo.core.embed.embed import logger


def pytest_addoption(parser):
    parser.addoption("--version", action="store", default="2.7", help="version to start from")
    # parser.addoption("--to_version", action="store", default="2.8", help="version to migrate to")

@pytest.fixture
def version(request):
    return request.config.getoption("--version")


def pytest_collection_modifyitems(config, items):
    version = config.getoption("--version") # This version will help us determine which test to skip v/s which test to collect.
    # The actual value inside the version can be from_version value (in case of test run where we run prepare on a from_version marqo instance,
    # and tests on a to_version marqo instance) or a to_version value (in case of a full test run where we run prepare and test on the same Marqo instance)

    for item in items:
        version_marker = item.get_closest_marker("marqo_version")

        if version_marker:
            test_version = version_marker.args[0] #test_version is the version defined as the argument in the "marqo_version" marker above each compatibility test
            logger.debug(f"Checking test: {item.name} with version: {test_version}")
            # Compare the test's required version with the version
            logger.debug(f"Test version: {test_version}, v/s version supplied in pytest arguments: {version}")
            test_version = semver.VersionInfo.parse(test_version)
            version = semver.VersionInfo.parse(version)
            # TODO: review this logic to see if it is correct
            if test_version > version:
                item.add_marker(pytest.mark.skip(reason=f"Test requires marqo_version {test_version} which is not greater than version {version}. Skipping."))

    logger.debug(f"Total collected tests: {len(items)}")

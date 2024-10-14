import abc
import argparse
import pytest
import subprocess
from typing import List, Optional, Set
from base_test_case import BaseTestCase

# Keep track of containers that need cleanup
containers_to_cleanup: Set[str] = set()


def pull_marqo_image(image: str):
    """Pull the specified Marqo Docker image."""
    try:
        subprocess.run(["docker", "pull", image], check=True)
    except subprocess.CalledProcessError as e:
        raise Exception(f"Failed to pull Docker image {image}: {e}")


def start_marqo_container(version: str, image: Optional[str] = None, transfer_state: Optional[str] = None):
    """Start a Marqo container after pulling the required image."""
    image = image or f"marqoai/marqo:{version}"
    container_name = f"marqo-{version}"

    # Pull the image before starting the container
    pull_marqo_image(image)

    cmd = ["docker", "run", "-d", "--name", container_name, image]
    if transfer_state:
        cmd.extend(["--volumes-from", transfer_state])

    try:
        subprocess.run(cmd, check=True)
        containers_to_cleanup.add(container_name)
    except subprocess.CalledProcessError as e:
        raise Exception(f"Failed to start container for version {version}: {e}")


def stop_marqo_container(version: str):
    """Stop a Marqo container but don't remove it yet."""
    container_name = f"marqo-{version}"
    try:
        subprocess.run(["docker", "stop", container_name], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Warning: Failed to stop container {container_name}: {e}")


def cleanup_containers():
    """Remove all containers that were created during the test."""
    for container_name in containers_to_cleanup:
        try:
            subprocess.run(["docker", "rm", "-f", container_name], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Warning: Failed to remove container {container_name}: {e}")
    containers_to_cleanup.clear()


def backwards_compatibility_test(from_version: str, to_version: str, from_image: Optional[str] = None,
                                 to_image: Optional[str] = None):
    try:
        # Step 1: Start from_version container and prepare
        start_marqo_container(from_version, from_image)
        print("Pulled marqo container");
        print("now will run tests for prepare")
        run_tests("prepare", from_version, to_version, "http://localhost:8882")
        print("ran prepare mode tests")
        # Step 2: Stop from_version container (but don't remove it)
        stop_marqo_container(from_version)
        print("stopped marqo container")

        # Step 3: Start to_version container, transferring state
        start_marqo_container(to_version, to_image, transfer_state=f"marqo-{from_version}")
        print("started marqo container in to_version by transferring state")
        # Step 4: Run tests
        run_tests("test", from_version, to_version, "http://localhost:8882")
        print("ran tests in test mode")
    finally:
        # Stop the to_version container (but don't remove it yet)
        stop_marqo_container(to_version)
        # Clean up all containers at the end
        cleanup_containers()


def rollback_test(from_version: str, to_version: str, from_image: Optional[str] = None, to_image: Optional[str] = None):
    try:
        # Steps 1-3: Same as backwards_compatibility_test
        backwards_compatibility_test(from_version, to_version, from_image, to_image)

        # Step 4: Stop to_version container (but don't remove it)
        stop_marqo_container(to_version)

        # Step 5: Start from_version container, transferring state back
        start_marqo_container(from_version, from_image, transfer_state=f"marqo-{to_version}")

        # Step 6: Run tests
        run_tests("test", from_version, to_version, "http://localhost:8882")
    finally:
        # Stop the final container (but don't remove it yet)
        stop_marqo_container(from_version)
        # Clean up all containers at the end
        cleanup_containers()

def run_tests(mode: str, from_version: str, to_version: str, marqo_api: str):
    if mode == "prepare":
        tests = [test for test in BaseTestCase.__subclasses__()
                 if getattr(test, 'marqo_from_version', '0') <= from_version]
        print("printing tests", tests)
        for test in tests:
            test().prepare()
    elif mode == "test":
        pytest.main([f"--marqo-api={marqo_api}",
                     f"-m", f"marqo_from_version<='{from_version}' or marqo_version<='{to_version}'"])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Marqo Testing Runner")
    parser.add_argument("--mode", choices=["backwards_compatibility", "rollback"], required=True)
    parser.add_argument("--from_version", required=True)
    parser.add_argument("--to_version", required=True)
    parser.add_argument("--from_image", default=None)
    parser.add_argument("--to_image", default=None)
    parser.add_argument("--marqo-api", default="http://localhost:8882")
    args = parser.parse_args()

    if args.mode == "backwards_compatibility":
        backwards_compatibility_test(args.from_version, args.to_version, args.from_image, args.to_image)
    elif args.mode == "rollback":
        rollback_test(args.from_version, args.to_version, args.from_image, args.to_image)

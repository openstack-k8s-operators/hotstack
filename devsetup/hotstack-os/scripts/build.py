#!/usr/bin/env python3
# Copyright Red Hat, Inc.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""
Build all HotsTac(k)os container images.

Builds base images and all service container images with support for
parallel builds and configurable service lists.
"""

import argparse
import logging
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ANSI color codes and status indicators
class Colors:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    NC = "\033[0m"  # No Color

    # Status indicators
    DONE = f"{GREEN}[DONE]{NC}"
    FAILED = f"{RED}[FAILED]{NC}"


# Default image lists
# Infrastructure images (no OPENSTACK_BRANCH build arg needed)
DEFAULT_INFRA_IMAGES = ["dnsmasq", "haproxy", "ovn"]

# OpenStack service images (require OPENSTACK_BRANCH build arg)
DEFAULT_OPENSTACK_IMAGES = [
    "keystone",
    "glance",
    "placement",
    "nova",
    "neutron",
    "cinder",
    "heat",
]


class ImageBuilder:
    """Handles building HotsTac(k)os container images."""

    def __init__(
        self,
        context: Path,
        apt_proxy: Optional[str] = None,
        openstack_branch: str = "stable/2025.1",
        parallel_jobs: int = 1,
        infra_images: Optional[List[str]] = None,
        openstack_images: Optional[List[str]] = None,
        verbose: bool = False,
    ):
        """Initialize the image builder.

        :param context: Containerfiles directory
        :param apt_proxy: Optional apt caching proxy URL
        :param openstack_branch: OpenStack branch to build
        :param parallel_jobs: Number of parallel builds
        :param infra_images: Infrastructure images to build (or None for defaults)
        :param openstack_images: OpenStack images to build (or None for defaults)
        :param verbose: Show verbose build output
        """
        self.context = context
        self.apt_proxy = apt_proxy
        self.openstack_branch = openstack_branch
        self.parallel_jobs = parallel_jobs
        self.verbose = verbose

        # Use provided image lists or defaults
        self.infra_images = infra_images if infra_images else DEFAULT_INFRA_IMAGES
        self.openstack_images = (
            openstack_images if openstack_images else DEFAULT_OPENSTACK_IMAGES
        )

        # Setup logging for verbose mode
        self.loggers = {}
        if self.verbose:
            self._setup_logging()

    def _setup_logging(self) -> None:
        """Setup per-image loggers that output to stdout with prefixes."""
        # Configure root logger to not interfere
        logging.basicConfig(level=logging.WARNING)

    def _get_logger(self, image: str) -> logging.Logger:
        """Get or create a logger for an image.

        :param image: Image name
        :returns: Logger instance configured for the image
        """
        if image not in self.loggers:
            logger = logging.getLogger(f"build.{image}")
            logger.setLevel(logging.INFO)
            logger.propagate = False

            # Create handler that outputs to stdout with image prefix
            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(logging.INFO)
            formatter = logging.Formatter(f"[{image}] %(message)s")
            handler.setFormatter(formatter)
            logger.addHandler(handler)

            self.loggers[image] = logger

        return self.loggers[image]

    def print_build_plan(self) -> None:
        """Print the build plan showing all images to be built."""
        total = 2 + len(self.infra_images) + len(self.openstack_images)
        print("\n" + "=" * 60)
        print(f"Build Plan (Total: {total} images, Parallelism: {self.parallel_jobs})")
        print("=" * 60)
        print(f"Base images (2): base-builder, base-runtime")
        print(
            f"Infrastructure images ({len(self.infra_images)}): {', '.join(self.infra_images)}"
        )
        print(
            f"OpenStack images ({len(self.openstack_images)}): {', '.join(self.openstack_images)}"
        )
        print("=" * 60)

    def build_image(
        self,
        image: str,
        containerfile: Path,
        tag: str,
        build_args: Optional[Dict[str, str]] = None,
        target: Optional[str] = None,
    ) -> Tuple[str, bool, str]:
        """Build a single container image.

        :param image: Image name for logging
        :param containerfile: Path to Containerfile
        :param tag: Image tag to apply
        :param build_args: Optional build arguments
        :param target: Optional build target stage
        :returns: Tuple of (image_name, success, error_message)
        """
        cmd = ["buildah", "bud"]

        if target:
            cmd.extend(["--target", target])

        cmd.extend(["-t", tag, "-f", str(containerfile)])

        if build_args:
            for key, value in build_args.items():
                if value:  # Only add non-empty values
                    cmd.extend(["--build-arg", f"{key}={value}"])

        cmd.append(str(self.context))

        try:
            if self.verbose:
                # Get logger for this image
                logger = self._get_logger(image)

                # Log build info
                logger.info("=" * 60)
                logger.info(f"Building: {tag}")
                logger.info(f"Command: {' '.join(cmd)}")
                logger.info("=" * 60)

                # Stream output line-by-line with image prefix
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )

                # Stream each line through logger
                for line in process.stdout:
                    logger.info(line.rstrip())

                process.wait()
                if process.returncode != 0:
                    return (image, False, "Build failed (see output above)")
                return (image, True, "")
            else:
                # Capture output for quiet mode
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                return (image, True, "")
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else e.stdout
            return (image, False, error_msg)

    def build_base_images(self) -> bool:
        """Build base builder and runtime images.

        :returns: True if successful, False otherwise
        """
        print("Building base images...")

        build_args = {"APT_PROXY": self.apt_proxy} if self.apt_proxy else {}
        containerfile = self.context / "base-openstack.containerfile"

        # Prepare base image builds
        base_builds = [
            {
                "image": "base-builder",
                "tag": "localhost/hotstack-os-base-builder:latest",
                "target": "builder",
            },
            {
                "image": "base-runtime",
                "tag": "localhost/hotstack-os-base:latest",
                "target": "runtime",
            },
        ]

        failed_builds = []
        completed = 0
        total = len(base_builds)

        # Build base images (can be parallel since they're independent stages)
        with ThreadPoolExecutor(max_workers=min(2, self.parallel_jobs)) as executor:
            future_to_image = {}
            for build in base_builds:
                future = executor.submit(
                    self.build_image,
                    build["image"],
                    containerfile,
                    build["tag"],
                    build_args=build_args,
                    target=build["target"],
                )
                future_to_image[future] = build["image"]

            # Process completed builds
            for future in as_completed(future_to_image):
                image_name = future_to_image[future]
                try:
                    image, success, error = future.result()
                    completed += 1
                    if success:
                        print(f"  [{completed}/{total}] {image} {Colors.DONE}")
                    else:
                        print(f"  [{completed}/{total}] {image} {Colors.FAILED}")
                        failed_builds.append((image, error))
                except Exception as e:
                    completed += 1
                    print(f"  [{completed}/{total}] {image_name} {Colors.FAILED}")
                    failed_builds.append((image_name, str(e)))

        if failed_builds:
            self._report_build_failures(failed_builds)
            return False

        return True

    def _report_build_failures(self, failed_builds: List[Tuple[str, str]]) -> None:
        """Report build failures with error details.

        :param failed_builds: List of (image_name, error_message) tuples
        """
        print(
            f"\n{Colors.RED}Build failed for: {', '.join(img for img, _ in failed_builds)}{Colors.NC}"
        )
        print("\nErrors:")
        for image, error in failed_builds:
            print(f"\n{image}:")
            print(f"  {error[:500]}")  # Truncate long errors
        print("\nIf you see permission errors, try: buildah unshare buildah rm --all")
        print(
            f"If you see storage/layer errors, try reducing BUILD_PARALLEL in .env (current: {self.parallel_jobs})"
        )

    def _prepare_infra_image_builds(self) -> List[Dict[str, any]]:
        """Prepare infrastructure image build configurations.

        :returns: List of build configuration dictionaries
        """
        builds = []
        for image in self.infra_images:
            build_args = {"APT_PROXY": self.apt_proxy} if self.apt_proxy else {}
            builds.append(
                {
                    "image": image,
                    "containerfile": self.context / f"{image}.containerfile",
                    "tag": f"localhost/hotstack-os-{image}:latest",
                    "build_args": build_args,
                }
            )
        return builds

    def _prepare_openstack_image_builds(self) -> List[Dict[str, any]]:
        """Prepare OpenStack image build configurations.

        :returns: List of build configuration dictionaries
        """
        builds = []
        for image in self.openstack_images:
            build_args = {}
            if self.apt_proxy:
                build_args["APT_PROXY"] = self.apt_proxy
            if self.openstack_branch:
                build_args["OPENSTACK_BRANCH"] = self.openstack_branch

            builds.append(
                {
                    "image": image,
                    "containerfile": self.context / f"{image}.containerfile",
                    "tag": f"localhost/hotstack-os-{image}:latest",
                    "build_args": build_args,
                }
            )
        return builds

    def build_service_images(self) -> bool:
        """Build all service container images.

        :returns: True if successful, False otherwise
        """
        print(f"\nBuilding service container images...")

        # Prepare all image builds
        all_images = []
        all_images.extend(self._prepare_infra_image_builds())
        all_images.extend(self._prepare_openstack_image_builds())

        # Build images using ThreadPoolExecutor (works for both serial and parallel)
        failed_builds = []
        completed = 0
        total = len(all_images)

        with ThreadPoolExecutor(max_workers=self.parallel_jobs) as executor:
            # Submit all build jobs
            future_to_image = {}
            for img in all_images:
                future = executor.submit(
                    self.build_image,
                    img["image"],
                    img["containerfile"],
                    img["tag"],
                    build_args=img.get("build_args"),
                )
                future_to_image[future] = img["image"]

            # Process completed builds
            for future in as_completed(future_to_image):
                image_name = future_to_image[future]
                try:
                    image, success, error = future.result()
                    completed += 1
                    if success:
                        print(f"  [{completed}/{total}] {image} {Colors.DONE}")
                    else:
                        print(f"  [{completed}/{total}] {image} {Colors.FAILED}")
                        failed_builds.append((image, error))
                except Exception as e:
                    completed += 1
                    print(f"  [{completed}/{total}] {image_name} {Colors.FAILED}")
                    failed_builds.append((image_name, str(e)))

        # Report results
        if failed_builds:
            self._report_build_failures(failed_builds)
            return False

        print(f"\n{Colors.DONE} All service images built successfully")
        return True


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments.

    :returns: Parsed command line arguments
    """
    parser = argparse.ArgumentParser(
        description="Build all HotsTac(k)os container images"
    )
    parser.add_argument(
        "--env-file", type=Path, required=True, help="Path to .env file"
    )
    parser.add_argument(
        "--parallel",
        type=int,
        default=None,
        help="Number of parallel builds (default: from BUILD_PARALLEL env or 1)",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Show verbose build output"
    )

    return parser.parse_args()


def load_env_file(env_file: Path) -> None:
    """Load environment variables from .env file into os.environ.

    :param env_file: Path to .env file (required)
    :raises FileNotFoundError: If the .env file doesn't exist
    """
    if not env_file.exists():
        raise FileNotFoundError(f".env file not found: {env_file}")

    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                # Only set if not already in environment (env vars take precedence)
                if key not in os.environ:
                    os.environ[key] = value


def main():
    """Main build script."""
    args = parse_arguments()

    # Determine project directory
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent
    containerfiles_dir = project_dir / "containerfiles"

    print("=== Building HotsTac(k)os Container Images ===\n")

    # Load environment configuration from .env file (if not already in environment)
    load_env_file(args.env_file)

    # Get build parameters from environment variables
    apt_proxy = os.environ.get("APT_PROXY")
    openstack_branch = os.environ.get("OPENSTACK_BRANCH", "stable/2025.1")

    # Determine parallel jobs (CLI arg > env var > default)
    if args.parallel is not None:
        parallel_jobs = args.parallel
    else:
        parallel_jobs = int(os.environ.get("BUILD_PARALLEL", "1"))

    # Get image lists from environment (comma-separated) or use defaults
    infra_images = None
    if "BUILD_INFRA_IMAGES" in os.environ:
        infra_images = [
            s.strip() for s in os.environ["BUILD_INFRA_IMAGES"].split(",") if s.strip()
        ]

    openstack_images = None
    if "BUILD_OPENSTACK_IMAGES" in os.environ:
        openstack_images = [
            s.strip()
            for s in os.environ["BUILD_OPENSTACK_IMAGES"].split(",")
            if s.strip()
        ]

    # Create builder instance
    builder = ImageBuilder(
        context=containerfiles_dir,
        apt_proxy=apt_proxy,
        openstack_branch=openstack_branch,
        parallel_jobs=parallel_jobs,
        infra_images=infra_images,
        openstack_images=openstack_images,
        verbose=args.verbose,
    )

    # Print build plan
    builder.print_build_plan()

    # Build base images first
    if not builder.build_base_images():
        print(f"\n{Colors.RED}Base image build failed!{Colors.NC}")
        return 1

    # Build service images
    if not builder.build_service_images():
        return 1

    print(f"\n{Colors.GREEN}[DONE]{Colors.NC} Build complete!")
    print("Next step: sudo make install")
    return 0


if __name__ == "__main__":
    sys.exit(main())

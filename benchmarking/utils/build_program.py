#!/usr/bin/env python

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os

import pkg_resources

from .custom_logger import getLogger
from .subprocess_with_logger import processRun


def buildUsingBuck(dst, platform, buck_target):
    _setUpTempDirectory(dst)

    final_command = f"{buck_target} --out {dst}"
    result, _ = processRun(final_command.split())

    getLogger().info("\n".join(result))

    if _isBuildSuccessful(dst, platform, final_command):
        os.chmod(dst, 0o500)
        return True
    return False


def buildProgramPlatform(dst, repo_dir, framework, frameworks_dir, platform, *args):
    script = getBuildScript(framework, frameworks_dir, platform, dst)
    _setUpTempDirectory(dst)

    if os.name == "nt":
        result, _ = processRun([script, repo_dir, dst])
    else:
        cmds = ["sh", script, repo_dir, dst]
        if args:
            cmds.extend(list(args))
        result, _ = processRun(cmds)

    getLogger().info("\n".join(result))

    if _isBuildSuccessful(dst, platform, script):
        os.chmod(dst, 0o500)
        return True
    return False


def _setUpTempDirectory(dst):
    dst_dir = os.path.dirname(dst)

    if os.path.isfile(dst):
        os.remove(dst)
    elif not os.path.isdir(dst_dir):
        os.makedirs(dst_dir)


def _isBuildSuccessful(dst, platform, script):
    if not os.path.isfile(dst) and (
        not (os.path.isdir(dst) and platform.startswith("ios"))
    ):
        getLogger().error(f'Build program using "{script}" failed.')
        return False
    return True


def getBuildScript(framework, frameworks_dir, platform, dst):
    if not frameworks_dir:
        try:
            build_script = _readFromBinary(framework, frameworks_dir, platform, dst)
        except BaseException as e:
            getLogger().info(f"We will load from old default path due to {e}.")
            frameworks_dir = str(
                os.path.dirname(os.path.realpath(__file__))
                + "/../../specifications/frameworks"
            )
            build_script = _readFromPath(framework, frameworks_dir, platform, dst)
    else:
        try:
            build_script = _readFromPath(framework, frameworks_dir, platform, dst)
        except BaseException as e:
            getLogger().info(f"We will load from binary due to {e}.")
            build_script = _readFromBinary(framework, frameworks_dir, platform, dst)

    return build_script


def _readFromPath(framework, frameworks_dir, platform, dst):
    # if user provide frameworks_dir, we want to validate its correctness.
    assert os.path.isdir(frameworks_dir), f"{frameworks_dir} must be specified."
    framework_dir = os.path.join(frameworks_dir, framework)
    assert os.path.isdir(framework_dir), f"{framework_dir} must be specified."
    platform_dir = os.path.join(framework_dir, platform)
    build_script = None
    if os.path.isdir(platform_dir) and os.path.isfile(
        f"{platform_dir}/build.sh"
    ):
        build_script = f"{platform_dir}/build.sh"
    if build_script is None:
        # Ideally, should check the parent directory until the
        # framework directory. Save this for the future
        build_script = f"{framework_dir}/build.sh"
        getLogger().warning(
            (
                (f"Directory {platform_dir} " + "doesn't exist. Use ")
                + f"{framework_dir} instead"
            )
        )

    assert os.path.isfile(build_script), (
        f"Cannot find build script in {framework_dir} for "
        + f"platform {platform}"
    )


    return build_script


def _readFromBinary(framework, frameworks_dir, platform, dst):
    script_path = os.path.join(
        "specifications/frameworks", framework, platform, "build.sh"
    )
    if not pkg_resources.resource_exists("aibench", script_path):
        raise Exception(
            f"cannot find the build script in the binary under {script_path}."
        )

    raw_build_script = pkg_resources.resource_string("aibench", script_path)
    if not os.path.exists(os.path.dirname(dst)):
        os.makedirs(os.path.dirname(dst))
    with open(os.path.join(os.path.dirname(dst), "build.sh"), "w") as f:
        f.write(raw_build_script.decode("utf-8"))
    return f.name

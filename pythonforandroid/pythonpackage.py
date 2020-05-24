# Copyright 2020 Andrzej Cichocki

# This file is part of Cowpox.
#
# Cowpox is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Cowpox is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Cowpox.  If not, see <http://www.gnu.org/licenses/>.

# This file incorporates work covered by the following copyright and
# permission notice:

# Copyright (c) 2010-2017 Kivy Team and other contributors
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from pep517.envbuild import BuildEnvironment
from pep517.wrappers import Pep517HookCaller
from urllib.parse import urlparse, unquote as urlunquote
from tempfile import TemporaryDirectory
import functools, os, pytoml, shutil, subprocess, sys, tarfile, tempfile, textwrap, time, zipfile

def transform_dep_for_pip(dependency):
    if dependency.find("@") > 0 and (
            dependency.find("@") < dependency.find("://") or
            "://" not in dependency
            ):
        # WORKAROUND FOR UPSTREAM BUG:
        # https://github.com/pypa/pip/issues/6097
        # (Please REMOVE workaround once that is fixed & released upstream!)
        #
        # Basically, setup_requires() can contain a format pip won't install
        # from a requirements.txt (PEP 508 URLs).
        # To avoid this, translate to an #egg= reference:
        if dependency.endswith("#"):
            dependency = dependency[:-1]
        url = (dependency.partition("@")[2].strip().partition("#egg")[0] +
               "#egg=" +
               dependency.partition("@")[0].strip()
              )
        return url
    return dependency


def extract_metainfo_files_from_package(
        package,
        output_folder,
        debug=False
        ):
    """ Extracts metdata files from the given package to the given folder,
        which may be referenced in any way that is permitted in
        a requirements.txt file or install_requires=[] listing.

        Current supported metadata files that will be extracted:

        - pytoml.yml  (only if package wasn't obtained as wheel)
        - METADATA
    """

    if package is None:
        raise ValueError("package cannot be None")

    if not os.path.exists(output_folder) or os.path.isfile(output_folder):
        raise ValueError("output folder needs to be existing folder")

    if debug:
        print("extract_metainfo_files_from_package: extracting for " +
              "package: " + str(package))

    # A temp folder for making a package copy in case it's a local folder,
    # because extracting metadata might modify files
    # (creating sdists/wheels...)
    temp_folder = tempfile.mkdtemp(prefix="pythonpackage-package-copy-")
    try:
        # Package is indeed a folder! Get a temp copy to work on:
        if is_filesystem_path(package):
            shutil.copytree(
                parse_as_folder_reference(package),
                os.path.join(temp_folder, "package")
            )
            package = os.path.join(temp_folder, "package")

        # Because PEP517 can be noisy and contextlib.redirect_* fails to
        # contain it, we will run the actual analysis in a separate process:
        try:
            subprocess.check_output([
                sys.executable,
                "-c",
                "import importlib\n"
                "import json\n"
                "import os\n"
                "import sys\n"
                "sys.path = [os.path.dirname(sys.argv[3])] + sys.path\n"
                "m = importlib.import_module(\n"
                "    os.path.basename(sys.argv[3]).partition('.')[0]\n"
                ")\n"
                "m._extract_metainfo_files_from_package_unsafe("
                "    sys.argv[1],"
                "    sys.argv[2],"
                ")",
                package, output_folder, os.path.abspath(__file__)],
                stderr=subprocess.STDOUT,  # make sure stderr is muted.
                cwd=os.path.join(os.path.dirname(__file__), "..")
            )
        except subprocess.CalledProcessError as e:
            output = e.output.decode("utf-8", "replace")
            if debug:
                print("Got error obtaining meta info.")
                print("Detail output:")
                print(output)
                print("End of Detail output.")
            raise ValueError(
                "failed to obtain meta info - "
                "is '{}' a valid package? "
                "Detailed output:\n{}".format(package, output)
                )
    finally:
        shutil.rmtree(temp_folder)


def _get_system_python_executable():
    """ Returns the path the system-wide python binary.
        (In case we're running in a virtualenv or venv)
    """
    # This function is required by get_package_as_folder() to work
    # inside a virtualenv, since venv creation will fail with
    # the virtualenv's local python binary.
    # (venv/virtualenv incompatibility)

    # Abort if not in virtualenv or venv:
    if not hasattr(sys, "real_prefix") and (
            not hasattr(sys, "base_prefix") or
            os.path.normpath(sys.base_prefix) ==
            os.path.normpath(sys.prefix)):
        return sys.executable

    # Extract prefix we need to look in:
    if hasattr(sys, "real_prefix"):
        search_prefix = sys.real_prefix  # virtualenv
    else:
        search_prefix = sys.base_prefix  # venv

    def python_binary_from_folder(path):
        def binary_is_usable(python_bin):
            """ Helper function to see if a given binary name refers
                to a usable python interpreter binary
            """

            # Abort if path isn't present at all or a directory:
            if not os.path.exists(
                os.path.join(path, python_bin)
            ) or os.path.isdir(os.path.join(path, python_bin)):
                return
            # We should check file not found anyway trying to run it,
            # since it might be a dead symlink:
            try:
                filenotfounderror = FileNotFoundError
            except NameError:  # Python 2
                filenotfounderror = OSError
            try:
                # Run it and see if version output works with no error:
                subprocess.check_output([
                    os.path.join(path, python_bin), "--version"
                ], stderr=subprocess.STDOUT)
                return True
            except (subprocess.CalledProcessError, filenotfounderror):
                return False

        python_name = "python" + sys.version
        while (not binary_is_usable(python_name) and
               python_name.find(".") > 0):
            # Try less specific binary name:
            python_name = python_name.rpartition(".")[0]
        if binary_is_usable(python_name):
            return os.path.join(path, python_name)
        return None

    # Return from sys.real_prefix if present:
    result = python_binary_from_folder(search_prefix)
    if result is not None:
        return result

    # Check out all paths in $PATH:
    bad_candidates = []
    good_candidates = []
    ever_had_nonvenv_path = False
    ever_had_path_starting_with_prefix = False
    for p in os.environ.get("PATH", "").split(":"):
        # Skip if not possibly the real system python:
        if not os.path.normpath(p).startswith(
                os.path.normpath(search_prefix)
                ):
            continue

        ever_had_path_starting_with_prefix = True

        # First folders might be virtualenv/venv we want to avoid:
        if not ever_had_nonvenv_path:
            sep = os.path.sep
            if (
                ("system32" not in p.lower() and
                 "usr" not in p and
                 not p.startswith("/opt/python")) or
                {"home", ".tox"}.intersection(set(p.split(sep))) or
                "users" in p.lower()
            ):
                # Doesn't look like bog-standard system path.
                if (p.endswith(os.path.sep + "bin") or
                        p.endswith(os.path.sep + "bin" + os.path.sep)):
                    # Also ends in "bin" -> likely virtualenv/venv.
                    # Add as unfavorable / end of candidates:
                    bad_candidates.append(p)
                    continue
            ever_had_nonvenv_path = True

        good_candidates.append(p)

    # If we have a bad env with PATH not containing any reference to our
    # real python (travis, why would you do that to me?) then just guess
    # based from the search prefix location itself:
    if not ever_had_path_starting_with_prefix:
        # ... and yes we're scanning all the folders for that, it's dumb
        # but i'm not aware of a better way: (@JonasT)
        for root, dirs, files in os.walk(search_prefix, topdown=True):
            for name in dirs:
                bad_candidates.append(os.path.join(root, name))

    # Sort candidates by length (to prefer shorter ones):
    def candidate_cmp(a, b):
        return len(a) - len(b)
    good_candidates = sorted(
        good_candidates, key=functools.cmp_to_key(candidate_cmp)
    )
    bad_candidates = sorted(
        bad_candidates, key=functools.cmp_to_key(candidate_cmp)
    )

    # See if we can now actually find the system python:
    for p in good_candidates + bad_candidates:
        result = python_binary_from_folder(p)
        if result is not None:
            return result

    raise RuntimeError(
        "failed to locate system python in: {}"
        " - checked candidates were: {}, {}"
        .format(sys.real_prefix, good_candidates, bad_candidates)
    )


def get_package_as_folder(dependency):
    """ This function downloads the given package / dependency and extracts
        the raw contents into a folder.

        Afterwards, it returns a tuple with the type of distribution obtained,
        and the temporary folder it extracted to. It is the caller's
        responsibility to delete the returned temp folder after use.

        Examples of returned values:

        ("source", "/tmp/pythonpackage-venv-e84toiwjw")
        ("wheel", "/tmp/pythonpackage-venv-85u78uj")

        What the distribution type will be depends on what pip decides to
        download.
    """

    venv_parent = tempfile.mkdtemp(
        prefix="pythonpackage-venv-"
    )
    try:
        # Create a venv to install into:
        try:
            if int(sys.version.partition(".")[0]) < 3:
                # Python 2.x has no venv.
                subprocess.check_output([
                    sys.executable,  # no venv conflict possible,
                                     # -> no need to use system python
                    "-m", "virtualenv",
                    "--python=" + _get_system_python_executable(),
                    os.path.join(venv_parent, 'venv')
                ], cwd=venv_parent)
            else:
                # On modern Python 3, use venv.
                subprocess.check_output([
                    _get_system_python_executable(), "-m", "venv",
                    os.path.join(venv_parent, 'venv')
                ], cwd=venv_parent)
        except subprocess.CalledProcessError as e:
            output = e.output.decode('utf-8', 'replace')
            raise ValueError(
                'venv creation unexpectedly ' +
                'failed. error output: ' + str(output)
            )
        venv_path = os.path.join(venv_parent, "venv")

        # Update pip and wheel in venv for latest feature support:
        try:
            filenotfounderror = FileNotFoundError
        except NameError:  # Python 2.
            filenotfounderror = OSError
        try:
            subprocess.check_output([
                os.path.join(venv_path, "bin", "pip"),
                "install", "-U", "pip", "wheel",
            ])
        except filenotfounderror:
            raise RuntimeError(
                "venv appears to be missing pip. "
                "did we fail to use a proper system python??\n"
                "system python path detected: {}\n"
                "os.environ['PATH']: {}".format(
                    _get_system_python_executable(),
                    os.environ.get("PATH", "")
                )
            )

        # Create download subfolder:
        os.mkdir(os.path.join(venv_path, "download"))

        # Write a requirements.txt with our package and download:
        with open(os.path.join(venv_path, "requirements.txt"),
                  "w", encoding="utf-8"
                 ) as f:
            def to_unicode(s):  # Needed for Python 2.
                try:
                    return s.decode("utf-8")
                except AttributeError:
                    return s
            f.write(to_unicode(transform_dep_for_pip(dependency)))
        try:
            subprocess.check_output(
                [
                    os.path.join(venv_path, "bin", "pip"),
                    "download", "--no-deps", "-r", "../requirements.txt",
                    "-d", os.path.join(venv_path, "download")
                ],
                stderr=subprocess.STDOUT,
                cwd=os.path.join(venv_path, "download")
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError("package download failed: " + str(e.output))

        if len(os.listdir(os.path.join(venv_path, "download"))) == 0:
            # No download. This can happen if the dependency has a condition
            # which prohibits install in our environment.
            # (the "package ; ... conditional ... " type of condition)
            return (None, None)

        # Get the result and make sure it's an extracted directory:
        result_folder_or_file = os.path.join(
            venv_path, "download",
            os.listdir(os.path.join(venv_path, "download"))[0]
        )
        dl_type = "source"
        if not os.path.isdir(result_folder_or_file):
            # Must be an archive.
            if result_folder_or_file.endswith((".zip", ".whl")):
                if result_folder_or_file.endswith(".whl"):
                    dl_type = "wheel"
                with zipfile.ZipFile(result_folder_or_file) as f:
                    f.extractall(os.path.join(venv_path,
                                              "download", "extracted"
                                             ))
                    result_folder_or_file = os.path.join(
                        venv_path, "download", "extracted"
                    )
            elif result_folder_or_file.find(".tar.") > 0:
                # Probably a tarball.
                with tarfile.open(result_folder_or_file) as f:
                    f.extractall(os.path.join(venv_path,
                                              "download", "extracted"
                                             ))
                    result_folder_or_file = os.path.join(
                        venv_path, "download", "extracted"
                    )
            else:
                raise RuntimeError(
                    "unknown archive or download " +
                    "type: " + str(result_folder_or_file)
                )

        # If the result is hidden away in an additional subfolder,
        # descend into it:
        while os.path.isdir(result_folder_or_file) and \
                len(os.listdir(result_folder_or_file)) == 1 and \
                os.path.isdir(os.path.join(
                    result_folder_or_file,
                    os.listdir(result_folder_or_file)[0]
                )):
            result_folder_or_file = os.path.join(
                result_folder_or_file,
                os.listdir(result_folder_or_file)[0]
            )

        # Copy result to new dedicated folder so we can throw away
        # our entire virtualenv nonsense after returning:
        result_path = tempfile.mkdtemp()
        shutil.rmtree(result_path)
        shutil.copytree(result_folder_or_file, result_path)
        return (dl_type, result_path)
    finally:
        shutil.rmtree(venv_parent)


def _extract_metainfo_files_from_package_unsafe(
        package,
        output_path
        ):
    # This is the unwrapped function that will
    # 1. make lots of stdout/stderr noise
    # 2. possibly modify files (if the package source is a local folder)
    # Use extract_metainfo_files_from_package_folder instead which avoids
    # these issues.

    clean_up_path = False
    path_type = "source"
    path = parse_as_folder_reference(package)
    if path is None:
        # This is not a path. Download it:
        (path_type, path) = get_package_as_folder(package)
        if path_type is None:
            # Download failed.
            raise ValueError(
                "cannot get info for this package, " +
                "pip says it has no downloads (conditional dependency?)"
            )
        clean_up_path = True

    try:
        build_requires = []
        metadata_path = None

        if path_type != "wheel":
            # We need to process this first to get the metadata.

            # Ensure pyproject.toml is available (pep517 expects it)
            if not os.path.exists(os.path.join(path, "pyproject.toml")):
                with open(os.path.join(path, "pyproject.toml"), "w") as f:
                    f.write(textwrap.dedent(u"""\
                    [build-system]
                    requires = ["setuptools", "wheel"]
                    build-backend = "setuptools.build_meta"
                    """))

            # Copy the pyproject.toml:
            shutil.copyfile(
                os.path.join(path, 'pyproject.toml'),
                os.path.join(output_path, 'pyproject.toml')
            )

            # Get build backend and requirements from pyproject.toml:
            with open(os.path.join(path, 'pyproject.toml')) as f:
                build_sys = pytoml.load(f)['build-system']
                backend = build_sys["build-backend"]
                build_requires.extend(build_sys["requires"])

            # Get a virtualenv with build requirements and get all metadata:
            env = BuildEnvironment()
            metadata = None
            with env:
                hooks = Pep517HookCaller(path, backend)
                env.pip_install(
                    [transform_dep_for_pip(req) for req in build_requires]
                )
                reqs = hooks.get_requires_for_build_wheel({})
                env.pip_install([transform_dep_for_pip(req) for req in reqs])
                try:
                    metadata = hooks.prepare_metadata_for_build_wheel(path)
                except Exception:  # sadly, pep517 has no good error here
                    pass
            if metadata is not None:
                metadata_path = os.path.join(
                    path, metadata, "METADATA"
                )
        else:
            # This is a wheel, so metadata should be in *.dist-info folder:
            metadata_path = os.path.join(
                path,
                [f for f in os.listdir(path) if f.endswith(".dist-info")][0],
                "METADATA"
            )

        # Store type of metadata source. Can be "wheel", "source" for source
        # distribution, and others get_package_as_folder() may support
        # in the future.
        with open(os.path.join(output_path, "metadata_source"), "w") as f:
            try:
                f.write(path_type)
            except TypeError:  # in python 2 path_type may be str/bytes:
                f.write(path_type.decode("utf-8", "replace"))

        # Copy the metadata file:
        shutil.copyfile(metadata_path, os.path.join(output_path, "METADATA"))
    finally:
        if clean_up_path:
            shutil.rmtree(path)


def is_filesystem_path(dep):
    """ Convenience function around parse_as_folder_reference() to
        check if a dependency refers to a folder path or something remote.

        Returns True if local, False if remote.
    """
    return (parse_as_folder_reference(dep) is not None)


def parse_as_folder_reference(dep):
    """ See if a dependency reference refers to a folder path.
        If it does, return the folder path (which parses and
        resolves file:// urls in the process).
        If it doesn't, return None.
    """
    # Special case: pep508 urls
    if dep.find("@") > 0 and (
            (dep.find("@") < dep.find("/") or "/" not in dep) and
            (dep.find("@") < dep.find(":") or ":" not in dep)
            ):
        # This should be a 'pkgname @ https://...' style path, or
        # 'pkname @ /local/file/path'.
        return parse_as_folder_reference(dep.partition("@")[2].lstrip())

    # Check if this is either not an url, or a file URL:
    if dep.startswith(("/", "file://")) or (
            dep.find("/") > 0 and
            dep.find("://") < 0) or (dep in ["", "."]):
        if dep.startswith("file://"):
            dep = urlunquote(urlparse(dep).path)
        return dep
    return None

def _extract_info_from_package(dependency):
    with TemporaryDirectory() as output_folder:
        extract_metainfo_files_from_package(dependency, output_folder, debug=False)
        with open(os.path.join(output_folder, "METADATA"), "r", encoding="utf-8") as f:
            # Get metadata and cut away description (is after 2 linebreaks)
            metadata_entries = f.read().partition("\n\n")[0].splitlines()
        for meta_entry in metadata_entries:
            if meta_entry.lower().startswith("name:"):
                return meta_entry.partition(":")[2].strip()
        raise ValueError("failed to obtain package name")

package_name_cache = {}

def get_package_name(dependency, use_cache=True):
    def timestamp():
        try:
            return time.monotonic()
        except AttributeError:
            return time.time()  # Python 2.
    try:
        value = package_name_cache[dependency]
        if value[0] + 600.0 > timestamp() and use_cache:
            return value[1]
    except KeyError:
        pass
    result = _extract_info_from_package(dependency)
    package_name_cache[dependency] = (timestamp(), result)
    return result

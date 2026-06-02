#!/usr/bin/env python3

import sys
import os
import subprocess
import tempfile
import yaml
import shutil
import re

ignore_folders = ["/snap/"]

def get_file_list(work: str, snap_path: str) -> tuple[dict|None, str]:
    """ Uncompress the snap and return a tuple with a dictionary and the snap name.
        The dictionary has the file paths as keys and an object with the destination
        (a string with the path if it's a link) and type (a string with 'file' or 'link') as value.

        param work: a temporary directory to uncompress the snap
        param snap_path: the path to the snap file to uncompress
        return: a tuple with the file list and the snap name, or (None, ERROR_STRING) if it fails
    """

    output_path = os.path.join(work, 'squashfs-root')
    r = subprocess.run(['unsquashfs', '-d', output_path, snap_path])
    if r.returncode != 0:
        return None, f'Failed to uncompress snap {snap_path}'

    filelist = {}
    for (basefolder, folders, files) in os.walk(output_path):
        for filename in files:
            filepath = os.path.join(basefolder, filename)
            destination = filepath
            while os.path.islink(destination):
                destination = os.path.join(basefolder, os.readlink(destination))
            if filepath == destination:
                destination = None
                type = "file"
            else:
                destination = destination[len(output_path):]
                type = "link"
            filepath = filepath[len(output_path):]
            ignore_this = False
            for ignore in ignore_folders:
                if filepath.startswith(ignore):
                    ignore_this = True
                    break
            if ignore_this:
                continue
            filelist[filepath] = {"destination": destination, "type": type}

    with open(os.path.join(output_path, 'meta', 'snap.yaml'), 'r') as snapyaml:
        data = yaml.load(snapyaml, Loader=yaml.Loader)
        snap_name = data['name']
    return filelist, snap_name


def download_from_store(work: str, snap: str, channel: str = '--stable') -> tuple[str | None, str | None]:
    """ Download a snap from the store and return its path and any error message.
        The error message is valid only if the path is None.

        param work: a temporary directory to download the snap
        param snap: the name of the snap to download
        param channel: the channel to download from (default: --stable)
        return: a tuple with the snap path and None, or (None, ERROR_STRING) if it fails,
        being ERROR_STRING a string with the error message
    """
    r1 = subprocess.run(['snap', 'download', snap, channel, '--target-directory', work])
    if r1.returncode != 0:
        return None, f'Failed to download the snap {snap} from {channel}'
    snap_name = None
    for f in os.listdir(work):
        fullpath = os.path.join(work, f)
        if not os.path.isfile(fullpath):
            continue
        if f.startswith(snap + '_') and f.endswith('.snap'):
            snap_name = fullpath
    if snap_name is None:
        return None, f'Failed to find the snap file'
    return snap_name, None


def remove_updated_libraries(original_filelist, new_filelist):
    """If a library is updated to a new minor version, we must not fail.
       To find them, check for the soft links XXXX.so and XXXX.so.Y that
       point to the same file, with the same major version. If we find
       them, we remove both the old and new files."""

    # Regex to find libXXXXX.so
    library_regex = re.compile('.*/lib[-_a-zA-Z0-9\\.]+\\.so$')
    # Regex to find libXXXXX.so.Y with a major version number
    library_with_major_regex = re.compile('.*/lib[-_a-zA-Z0-9\\.]+\\.so\\.[0-9]+$')
    # Regex to find libXXXXX.so.Y.Z(.D...) with a full version number
    library_with_full_version_regex = re.compile('.*/lib[-_a-zA-Z0-9\\.]+\\.so\\.[0-9]+(\\.[0-9]+)+$')

    old_so_files = [f for f in original_filelist if library_regex.match(f)]
    old_so_X_files = [f for f in original_filelist if library_with_major_regex.match(f)]
    old_so_X_Y_files = [f for f in original_filelist if library_with_full_version_regex.match(f)]

    for lib_full in old_so_X_Y_files:
        # full libraries must be files; the soft links are the others
        if original_filelist[lib_full]['type'] != 'file':
            continue

        # check if there is a soft link with the same name but without the version number
        so_name = None
        for libname in old_so_files:
            if (lib_full.startswith(libname) and
                original_filelist[libname]['type'] == 'link' and
                original_filelist[libname]['destination'] == lib_full):
                so_name = libname
                break

        # check if there is a soft link with the same name and major version number
        so_version_name = None
        for libname in old_so_X_files:
            if (lib_full.startswith(libname) and
                original_filelist[libname]['type'] == 'link' and
                original_filelist[libname]['destination'] == lib_full):
                so_version_name = libname
                break

        # if there is neither a soft link without the version number nor with the same major version,
        # we must ignore it
        if so_name is None and so_version_name is None:
            continue

        if so_name is not None and so_version_name is not None:
            # if there are both, we must check that they point to the same file;
            if original_filelist[so_name]['destination'] != original_filelist[so_version_name]['destination']:
                continue

        so_name_new_dest = None
        # check if there is a soft link with the same name but without the version number in the new snap
        if so_name in new_filelist and new_filelist[so_name]['type'] == 'link':
            so_name_new_dest = new_filelist[so_name]['destination']

        so_version_name_new_dest = None
        # check if there is a soft link with the same name and major version number in the new snap
        if so_version_name in new_filelist and new_filelist[so_version_name]['type'] == 'link':
            so_version_name_new_dest = new_filelist[so_version_name]['destination']

        if so_name_new_dest is None and so_version_name_new_dest is None:
            continue

        # if there are both in the new filelist, they must point to the same file
        if so_name_new_dest is not None and so_version_name_new_dest is not None and so_name_new_dest != so_version_name_new_dest:
            continue

        # if we reach this point, it means that this is a library and has been updated to a new minor version, so we can ignore it
        del original_filelist[lib_full]
        if so_name_new_dest is not None:
            del new_filelist[so_name_new_dest]
        else:
            del new_filelist[so_version_name_new_dest]


def _extract_python_modules_name(file_list, regex):
    python_modules = {}
    for f in file_list:
        m = regex.match(f)
        if not m:
            continue
        module_name = m.group(0).replace('.egg-info/', '').replace('.dist-info/', '')
        pos = module_name.rfind('-')
        if pos != -1:
            module_name = module_name[:pos]
        if module_name not in python_modules:
            python_modules[module_name] = []
        python_modules[module_name].append(f)
    return python_modules


def _remove_duplicated_python_modules_with_re(original_filelist, new_filelist, regex):
    old_python_modules = _extract_python_modules_name(original_filelist, regex)
    new_python_modules = _extract_python_modules_name(new_filelist, regex)
    for module in old_python_modules:
        if module in new_python_modules:
            # if there are files with the same name in both snaps, we can ignore them
            for f in old_python_modules[module]:
                del original_filelist[f]
            for f in new_python_modules[module]:
                del new_filelist[f]


def remove_duplicated_python_modules(original_filelist, new_filelist):
    python_module_regex = re.compile('(/usr)?/lib/python3/dist-packages/[_a-zA-Z0-9]+-[0-9](\\.[0-9]+)*\\.(egg|dist)-info/')
    _remove_duplicated_python_modules_with_re(original_filelist, new_filelist, python_module_regex)

    python_module_regex = re.compile('(/usr)?/lib/python3/dist-packages/[_a-zA-Z0-9]+/')
    _remove_duplicated_python_modules_with_re(original_filelist, new_filelist, python_module_regex)


def remove_duplicated_files(original_filelist, new_filelist):
    missing_files = [p for p in original_filelist if p not in new_filelist or original_filelist[p]['type'] != new_filelist[p]['type']]
    new_files = [p for p in new_filelist if p not in original_filelist or original_filelist[p]['type'] != new_filelist[p]['type']]

    return missing_files, new_files

def remove_wacom_files(original_filelist, new_filelist):
    wacom_regex = re.compile('.*/usr/share/libwacom/.*\\.(tablet|stylus|svg)$')

    new_files = [f for f in new_filelist if not wacom_regex.match(f)]
    missing_files = [f for f in original_filelist if not wacom_regex.match(f)]

    return missing_files, new_files


def remove_locale_files(original_filelist, new_filelist):
    locale_regex = re.compile('.*/usr/share/locale/.*\\.mo$')

    new_files = [f for f in new_filelist if not locale_regex.match(f)]
    missing_files = [f for f in original_filelist if not locale_regex.match(f)]

    return missing_files, new_files

def __main__():
    local_snap = sys.argv[1]

    work = tempfile.mkdtemp()
    local_filelist, snap_name = get_file_list(work, local_snap)
    shutil.rmtree(work)
    if local_filelist is None:
        print(f'Failed to get local filelist for {snap_name}')
        sys.exit(-1)

    work = tempfile.mkdtemp()
    snap_data = None
    if len(sys.argv) == 2:
        snap_data, _ = download_from_store(work, snap_name)
    else:
        snap_data = sys.argv[2]
    if snap_data is None:
        print(f'Failed to get snap data for {snap_name}')
        sys.exit(-1)
    upstream_filelist, _ = get_file_list(work, snap_data)
    shutil.rmtree(work)

    if upstream_filelist is None:
        print(f'Failed to get upstream filelist for {snap_name}')
        sys.exit(-1)

    remove_updated_libraries(upstream_filelist, local_filelist)
    remove_duplicated_python_modules(upstream_filelist, local_filelist)

    missing_files, new_files = remove_duplicated_files(upstream_filelist, local_filelist)
    missing_files, new_files = remove_locale_files(missing_files, new_files)

    missing_files.sort()
    with open("missing.txt", "w") as f:
        for missing in missing_files:
            f.write(f"{missing}\n")

    new_files.sort()
    with open("new.txt", "w") as f:
        for newfiles in new_files:
            f.write(f"{newfiles}\n")

if __name__ == "__main__":
    __main__()
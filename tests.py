#!/usr/bin/env python3

import unittest
import find_new_removed_files

class TestRemoveUpdatedLibraries(unittest.TestCase):
    def test_updated_library(self):
        old_filelist = {
            '/lib/libfoo.so': {'type': 'link', 'destination': '/lib/libfoo.so.1.0'},
            '/lib/libfoo.so.1': {'type': 'link', 'destination': '/lib/libfoo.so.1.0'},
            '/lib/libfoo.so.1.0': {'type': 'file'}
        }
        new_filelist = {
            '/lib/libfoo.so': {'type': 'link', 'destination': '/lib/libfoo.so.1.3'},
            '/lib/libfoo.so.1': {'type': 'link', 'destination': '/lib/libfoo.so.1.3'},
            '/lib/libfoo.so.1.3': {'type': 'file'}
        }
        find_new_removed_files.remove_updated_libraries(old_filelist, new_filelist)
        self.assertIn('/lib/libfoo.so', old_filelist)
        self.assertIn('/lib/libfoo.so.1', old_filelist)
        self.assertNotIn('/lib/libfoo.so.1.0', old_filelist)
        self.assertIn('/lib/libfoo.so', new_filelist)
        self.assertIn('/lib/libfoo.so.1', new_filelist)
        self.assertNotIn('/lib/libfoo.so.1.3', new_filelist)


    def test_updated_library2(self):
        old_filelist = {
            '/lib/libfoo.so': {'type': 'link', 'destination': '/lib/libfoo.so.1.0'},
            '/lib/libfoo.so.1.0': {'type': 'file'}
        }
        new_filelist = {
            '/lib/libfoo.so': {'type': 'link', 'destination': '/lib/libfoo.so.1.3'},
            '/lib/libfoo.so.1.3': {'type': 'file'}
        }
        find_new_removed_files.remove_updated_libraries(old_filelist, new_filelist)
        self.assertIn('/lib/libfoo.so', old_filelist)
        self.assertNotIn('/lib/libfoo.so.1.0', old_filelist)
        self.assertIn('/lib/libfoo.so', new_filelist)
        self.assertNotIn('/lib/libfoo.so.1.3', new_filelist)


    def test_updated_library3(self):
        old_filelist = {
            '/lib/libfoo.so.1': {'type': 'link', 'destination': '/lib/libfoo.so.1.0'},
            '/lib/libfoo.so.1.0': {'type': 'file'}
        }
        new_filelist = {
            '/lib/libfoo.so.1': {'type': 'link', 'destination': '/lib/libfoo.so.1.3'},
            '/lib/libfoo.so.1.3': {'type': 'file'}
        }
        find_new_removed_files.remove_updated_libraries(old_filelist, new_filelist)
        self.assertIn('/lib/libfoo.so.1', old_filelist)
        self.assertNotIn('/lib/libfoo.so.1.0', old_filelist)
        self.assertIn('/lib/libfoo.so.1', new_filelist)
        self.assertNotIn('/lib/libfoo.so.1.3', new_filelist)


    def test_do_not_know_updated_library(self):
        old_filelist = {
            '/lib/libfoo.so': {'type': 'link', 'destination': '/lib/libfoo.so.1.0'},
            '/lib/libfoo.so.1.0': {'type': 'file'}
        }
        new_filelist = {
            '/lib/libfoo.so.1': {'type': 'link', 'destination': '/lib/libfoo.so.1.3'},
            '/lib/libfoo.so.1.3': {'type': 'file'}
        }
        find_new_removed_files.remove_updated_libraries(old_filelist, new_filelist)
        self.assertIn('/lib/libfoo.so', old_filelist)
        self.assertIn('/lib/libfoo.so.1.0', old_filelist)
        self.assertIn('/lib/libfoo.so.1', new_filelist)
        self.assertIn('/lib/libfoo.so.1.3', new_filelist)


    def test_remove_duplicates(self):
        old_filelist = {
            '/lib/libfoo.so': {'type': 'link', 'destination': '/lib/libfoo.so.1.0'},
            '/lib/libfoo.so.1.0': {'type': 'file'},
            '/lib/libbar.so': {'type': 'file'}
        }
        new_filelist = {
            '/lib/libfoo.so': {'type': 'link', 'destination': '/lib/libfoo.so.1.0'},
            '/lib/libfoo.so.1.0': {'type': 'file'},
            '/lib/libbaz.so': {'type': 'file'}
        }
        missing_files, new_files = find_new_removed_files.remove_duplicated_files(old_filelist, new_filelist)
        self.assertEqual(missing_files, ['/lib/libbar.so'])
        self.assertEqual(new_files, ['/lib/libbaz.so'])


    def test_remove_duplicates2(self):
        old_filelist = {
            '/lib/libfoo.so': {'type': 'link', 'destination': '/lib/libfoo.so.1.0'},
            '/lib/libfoo.so.1.0': {'type': 'file'},
            '/lib/libbar.so': {'type': 'file'}
        }
        new_filelist = {
            '/lib/libfoo.so': {'type': 'link', 'destination': '/lib/libfoo.so.1.0'},
            '/lib/libfoo.so.1.0': {'type': 'file'},
            '/lib/libbar.so': {'type': 'link'}
        }
        missing_files, new_files = find_new_removed_files.remove_duplicated_files(old_filelist, new_filelist)
        self.assertEqual(missing_files, ['/lib/libbar.so'])
        self.assertEqual(new_files, ['/lib/libbar.so'])


    def test_remove_python_modules2(self):
        old_filelist = {
            '/usr/lib/python3/dist-packages/foo-1.0.0.egg-info/test1': {'type': 'file'},
            '/usr/lib/python3/dist-packages/foo-1.0.0.egg-info/test2': {'type': 'file'},
        }
        new_filelist = {
            '/usr/lib/python3/dist-packages/foo-1.4.0.egg-info/test1': {'type': 'file'},
            '/usr/lib/python3/dist-packages/foo-1.4.0.egg-info/test2': {'type': 'file'},
        }
        find_new_removed_files.remove_duplicated_python_modules(old_filelist, new_filelist)
        self.assertEqual(old_filelist, {})
        self.assertEqual(new_filelist, {})


    def test_remove_python_modules3(self):
        old_filelist = {
            '/usr/lib/python3/dist-packages/meson-1.8.4.dist-info/INSTALLER': {'type': 'file'},
            '/usr/lib/python3/dist-packages/meson-1.8.4.dist-info/METADATA': {'type': 'file'},
            '/usr/lib/python3/dist-packages/meson-1.8.4.dist-info/RECORD': {'type': 'file'},
            '/usr/lib/python3/dist-packages/meson-1.8.4.dist-info/REQUESTED': {'type': 'file'},
            '/usr/lib/python3/dist-packages/meson-1.8.4.dist-info/WHEEL': {'type': 'file'},
            '/usr/lib/python3/dist-packages/meson-1.8.4.dist-info/direct_url.json': {'type': 'file'},
        }
        new_filelist = {
            '/usr/lib/python3/dist-packages/meson-1.10.2.dist-info/INSTALLER': {'type': 'file'},
            '/usr/lib/python3/dist-packages/meson-1.10.2.dist-info/METADATA': {'type': 'file'},
            '/usr/lib/python3/dist-packages/meson-1.10.2.dist-info/RECORD': {'type': 'file'},
            '/usr/lib/python3/dist-packages/meson-1.10.2.dist-info/REQUESTED': {'type': 'file'},
            '/usr/lib/python3/dist-packages/meson-1.10.2.dist-info/WHEEL': {'type': 'file'},
            '/usr/lib/python3/dist-packages/meson-1.10.2.dist-info/direct_url.json': {'type': 'file'},
        }
        find_new_removed_files.remove_duplicated_python_modules(old_filelist, new_filelist)
        self.assertEqual(old_filelist, {})
        self.assertEqual(new_filelist, {})

    def test_remove_translations(self):
        old_filelist = {
            '/usr/share/locale/es/test.mo': {'type': 'file'},
            '/usr/share/locale/es/test2.mo': {'type': 'file'},
            '/usr/bin/locale/es/test.mo': {'type': 'file'},
        }
        new_filelist = {
            '/usr/bin/locale/es/test2.mo': {'type': 'file'},
            '/usr/share/locale/es/test2.mo': {'type': 'file'},
            '/usr/share/locale/es/test3.mo': {'type': 'file'},
        }
        old_filelist, new_filelist = find_new_removed_files.remove_locale_files(old_filelist, new_filelist)
        self.assertEqual(old_filelist, ['/usr/bin/locale/es/test.mo'])
        self.assertEqual(new_filelist, ['/usr/bin/locale/es/test2.mo'])


    def test_remove_libwacom(self):
        old_filelist = {
            '/usr/share/libwacom/test1.tablet': {'type': 'file'},
            '/usr/share/libwacom/layouts/test1.svg': {'type': 'file'},
            '/usr/share/libwacom/test3.tablet': {'type': 'file'},
        }
        new_filelist = {
            '/usr/share/libwacom/test2.tablet': {'type': 'file'},
            '/usr/share/libwacom/layouts/test2.svg': {'type': 'file'},
            '/usr/share/libwacom/test3.tablet': {'type': 'file'},
        }
        old_filelist, new_filelist = find_new_removed_files.remove_wacom_files(old_filelist, new_filelist)
        self.assertEqual(old_filelist, [])
        self.assertEqual(new_filelist, [])

    def test_remove_bash_completion_files(self):
        old_filelist = {
            '/usr/share/bash-completion/test1.bash': {'type': 'file'},
            '/usr/share/bash-completion/test2.bash': {'type': 'file'},
            '/usr/share/bash-completion/test3.bash': {'type': 'file'},
        }
        new_filelist = {
            '/usr/share/bash-completion/test2.bash': {'type': 'file'},
            '/usr/share/bash-completion/test3.bash': {'type': 'file'},
            '/usr/share/bash-completion/test4.bash': {'type': 'file'},
        }
        old_filelist, new_filelist = find_new_removed_files.remove_bash_completion_files(old_filelist, new_filelist)
        self.assertEqual(old_filelist, [])
        self.assertEqual(new_filelist, [])


if __name__ == '__main__':
    unittest.main()
import unittest
from file_manager import FileManager
import os
from pathlib import Path


class TestFileManager(unittest.TestCase):

    def test_prepare_edition_dir_no_dir_at_start(self) -> None:
        test_file_manager = FileManager()  # executes .prepare_edition_dir

        is_dir = Path(test_file_manager.edition_dir).is_dir()
        dir_content_list = os.listdir(test_file_manager.edition_dir)
        os.rmdir(test_file_manager.edition_dir)

        self.assertTrue(is_dir)
        self.assertEqual(dir_content_list, [])

    def test_prepare_edition_dir_empty_dir_at_start(self) -> None:
        test_file_manager = FileManager()
        test_file_manager.prepare_edition_dir()

        is_dir = Path(test_file_manager.edition_dir).is_dir()
        dir_content_list = os.listdir(test_file_manager.edition_dir)
        os.rmdir(test_file_manager.edition_dir)

        self.assertTrue(is_dir)
        self.assertEqual(dir_content_list, [])

    def test_prepare_edition_dir_dir_with_files_at_start(self) -> None:
        test_file_manager = FileManager()
        with open(Path(test_file_manager.edition_dir) / 'file',
                  'w') as file:
            file.write('dawqa')
        test_file_manager.prepare_edition_dir()

        is_dir = Path(test_file_manager.edition_dir).is_dir()
        dir_content_list = os.listdir(test_file_manager.edition_dir)
        os.rmdir(test_file_manager.edition_dir)

        self.assertTrue(is_dir)
        self.assertEqual(dir_content_list, [])

    def test_prepare_edition_dir_dir_with_subdirs_at_start(self) -> None:
        test_file_manager = FileManager()
        os.mkdir(Path(test_file_manager.edition_dir) / 'dir')
        with open(Path(test_file_manager.edition_dir) / 'dir' / 'file',
                  'w') as file:
            file.write('dawqa')
        test_file_manager.prepare_edition_dir()

        is_dir = Path(test_file_manager.edition_dir).is_dir()
        dir_content_list = os.listdir(test_file_manager.edition_dir)
        os.rmdir(test_file_manager.edition_dir)

        self.assertTrue(is_dir)
        self.assertEqual(dir_content_list, [])

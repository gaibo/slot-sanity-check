import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))  # Allow test file to see parent dir modules

import unittest
from pathlib import Path
import xml.etree.ElementTree as ET
from utils import xml_dfs_get_text_set

# python -m unittest test_module1 test_module2 
# python -m unittest test_module1.TestClass 
# python -m unittest test_module1.TestClass.test_method
# python -m unittest -v test_module
# python -m unittest


class TestXMLParse(unittest.TestCase):
    def setUp(self) -> None:
        # Load XML example file/tree/root (ui_chara_db)
        mod_path = Path(r'Bowser (C05) - Swole Dedede')
        readable_param_patch_ui_chara_db = list(mod_path.glob('**/ui_chara_db.prcxml'))
        ui_chara_db_tree = ET.parse(readable_param_patch_ui_chara_db[0])
        self.struct_root_swole = ui_chara_db_tree.getroot()  # <struct> opening tag
        # Load another XML example file/tree/root (msg_name)
        readable_param_patch_msg_name = list(mod_path.glob('**/msg_name.xmsbt'))
        msg_name_tree = ET.parse(readable_param_patch_msg_name[0])
        self.xmsbt_root_swole = msg_name_tree.getroot()  # <xmsbt> opening tag

    def test_understanding(self) -> None:
        # Assert understanding of XML tools: tag, attrib, text (already did this above)
        list_node = list(self.struct_root_swole)[0]    # Always a <list> tag in context of these mods
        self.assertEqual(list_node.tag, 'list')
        modified_indexes = [child for child in list_node if child.tag == 'struct']
        mod_idx = modified_indexes[0]
        mod_lines = list(mod_idx)
        with self.subTest(i=1):
            self.assertEqual(mod_lines[0].tag, 'byte')
            self.assertEqual(mod_lines[0].attrib['hash'], 'n05_index')
            self.assertEqual(mod_lines[0].text, '13')
        with self.subTest(i=2):
            self.assertEqual(mod_lines[1].tag, 'hash40')
            self.assertEqual(mod_lines[1].attrib['hash'], 'characall_label_c13')
            self.assertEqual(mod_lines[1].text, 'vc_narration_characall_koopa')
    
    def test_DFS_for_text(self) -> None:        
        # Do a DFS for interesting stuff; in this case, look for "text" (mostly inside structs)
        struct_text_set = xml_dfs_get_text_set(self.struct_root_swole)
        self.assertTrue('vc_narration_characall_koopa' in struct_text_set)
        self.assertTrue('dummy' in struct_text_set)
        xmsbt_text_set = xml_dfs_get_text_set(self.xmsbt_root_swole)
        self.assertTrue('Swole Dedede' in xmsbt_text_set)
        self.assertTrue('SWOLE DEDEDE' in xmsbt_text_set)
        self.assertTrue('The Ripped\nPenguin' in xmsbt_text_set)


if __name__ == '__main__':
    unittest.main()

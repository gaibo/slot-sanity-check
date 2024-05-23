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

    def test_understanding(self):
        # Load XML example file/tree/root
        mod_path = Path(r'Bowser (C05) - Swole Dedede')
        readable_param_patch_ui_chara_db = list(mod_path.glob('**/ui_chara_db.prcxml'))
        ui_chara_db_tree = ET.parse(readable_param_patch_ui_chara_db[0])
        struct_root = ui_chara_db_tree.getroot()  # <struct> opening tag

        # Assert understanding of XML tools: tag, attrib, text (already did this above)
        list_node = list(struct_root)[0]    # Specific "list" 
        self.assertTrue(list_node.tag == 'list')
        modified_indexes = [child for child in list_node if child.tag == 'struct']
        mod_idx = modified_indexes[0]
        mod_lines = list(mod_idx)
        self.assertTrue(mod_lines[0].tag == 'byte')
        self.assertTrue(mod_lines[0].attrib['hash'] == 'n05_index')
        self.assertTrue(mod_lines[0].text == '13')
    
    def test_dfs(self):
        # Load XML example file/tree/root
        mod_path = Path(r'Bowser (C05) - Swole Dedede')
        readable_param_patch_ui_chara_db = list(mod_path.glob('**/ui_chara_db.prcxml'))
        ui_chara_db_tree = ET.parse(readable_param_patch_ui_chara_db[0])
        struct_root = ui_chara_db_tree.getroot()  # <struct> opening tag
        
        # Do a DFS for interesting stuff; in this case, look for "text" (mostly inside structs)
        text_set = xml_dfs_get_text_set(struct_root)
        self.assertTrue('vc_narration_characall_koopa' in text_set)


if __name__ == '__main__':
    unittest.main()

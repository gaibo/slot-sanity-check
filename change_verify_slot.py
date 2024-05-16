from pathlib import Path, PurePath
import os
import re
from collections import Counter
from typing import Set, List, Callable, Tuple
import pandas as pd
import openpyxl
import json
import xml.etree.ElementTree as ET
import sys

"""
This script aims to speed up folder/file renaming necessary to change the
effective character slot of Smash Ultimate mods. Note this won't automatically
work for every mod - textures for some characters like Wario won't work if
transferred from even slot to odd slot, etc.

As a blackbox script, we'll try to be non-destructive and explicit by:
1) creating duplicate folder instead of modifying in existing folder,
2) pretty printing everything staged to be "renamed" (not technically renaming
   since we'll create new files with the name) as sanity check before executing.
This script will NOT change any of your existing files! And if it fails,
rest easy knowing nothing on your computer has been deleted - there may be a
new temporary folder that you can safely delete!

The script will have 2 somewhat standalone features:
1) slot "verification" (run script without specifying new slot):
   I'll somewhat rudely require you to include the slot in the name of the mod
   source folder, e.g. script will reject "cool_falcon_mod" until you rename it
   "cool_falcon_mod_c00" or "C00". This is honestly just best practice for
   everyone involved; note if your mod spans multiple slots, it shouldn't need
   this script in the first place because this script is for changing one
   numbered slot to another.
   Anyway, I'll use this slot info to sanity check the naming of all files and
   folders included in the mod, and I'll also check the fighter code name and
   maybe even config.json. You'd be surprised how often mods are published
   broken, or containing accidental unrelated files!
   Since verification is completely harmless, I've also built in "batch
   verification", i.e. if you point the script at a folder (no naming
   requirement) containing a bunch of mod folders, it will try to run its normal
   verfication on each mod subfolder.
2) slot "renaming" (run script with the new slot argument):
   The new slot mod folder I generate will be named following your source folder
   formatting. Yet another reason we'll require the source folder to include
   the mod slot in its name!

Here is a brainstorming list of folders/files that should be modified to slot
(this is not "theoretically" complete, but practically over the hundreds of
 mods I use, these are the folders/files with slot-specific names):
- camera/fighter/<fighter_code>/c0X/ -> c0Y
- effect/fighter/<fighter_code>/ef_<fighter_code>_c0X.eff -> c0Y
                               /trail_c0X/ -> c0Y
                               /model/<*very_specific_effect>_c0X/c00/ -> c0Y
- fighter/<fighter_code>/model/body/c0X/ -> c0Y
                              /<*warioman_nikita_etc>/c0X/ -> c0Y
                        /motion/c0X/ -> c0Y
- sound/bank/fighter_voice/vc_<fighter_code>_c0X.* -> c0Y
            /fighter/se_<fighter_code>_c0X.* -> c0Y
- ui/replace/chara/chara_[0-13]/chara_[0-13]_<fighter_code>_0X -> 0Y
    /message/msg_name.xmsbt -> could edit 00 to 01, etc. but number not standard
    /param/ui_chara_db.prcxml -> ideally don't change, because can't change prcx
- config.json -> edit declared file additions; just check that new slot is there

The above list assumes the mod is designed for one slot number, and that you
would not concurrently set the same mod on multiple slots (you could, but we're
keeping files (e.g. vc_narration_characall.nus3audio, msg_name.msbt) that will
lead to Arcropolis "file conflict", i.e. one slot's mod files take questionable
precendence over another's, because only one can be "active". You can fix file
conflicts by simply renaming the file you'd prefer to deactivate.
Some other renaming notes off the top of my head:
- item/ subfolder slots should not be renamed, e.g. to modify Snake's items,
  the new textures must be c00.
- I'm not sure whether to rename Kirby Cap folders included with other fighters.
  Probably not, because we want Kirby's C00 costumes to change, right?
  fighter/kirby/model/copy_<fighter_code>_cap/c0X/ -> c0Y???
- There is no one-slot solution (yet) for character selection screen announcer
  voice lines. Right now, you have to replace the whole audio file at
  sound/bank/narration/vc_narration_characall.nus3audio
- ui/replace/chara/ subfolders must accomodate numbers 0 to 13; though most
  mods don't go past 6, you may need to go to 10 for Pokemon Trainer, 12 for
  boss portraits, 13 for Joker.
  Character UI:
    *- chara_0 = record portrait (square face)
    *- chara_1 = CSS(character select screen)/boxing ring portrait (square,
                 character most in bottom right)
    *- chara_2 = stock icon (square cartoon icon)
    *- chara_3 = vs./results portrait (square, character full in bottom left)
    *- chara_4 = battle portrait (square face in diamond)
    - chara_5 = spirit portrait (no alts)
    *- chara_6 = final smash portrait (1:2 horizontal rectangle, eyes)
    - chara_7 = CSS icon (no alts)
    - chara_10 = Pokemon Trainer pokemon masks
    - chara_12 = boss portraits
    - chara_13 = alternate battle portrait for unmasked Joker
- ui/message/msg_name.msbt and ui/param/ui_chara_db.prc are often changed in
  mods to .xmsbt and .prcxml (or .prcx) to take advantage of Arcropolis's
  "param patching" which allows for one-slot text (really hope a similar system
  is invented for announcer voice lines). Editing these files to appropriately
  change active slots of character names may be tricky. Please sanity check
  by reading WataPascul's or Miguel's fantastic guides.
  - Technically we could be very intrusive and edit numbers in .prcxml,
    then edit corresponding numbers in .xmsbt. We could even link in code to
    generate the param patching files by diffing non-one-slotted MSBT and PRC
    with parcel.exe. But that would be a lot of effort for something not a lot
    of people would use, I think.
"""


def extract_slot_from_path(mod_path: PurePath | str) -> int:
    """ Extract mod slot number from mod's name, given mod's directory root
        NOTE: PurePath (parent class of Path with no I/O) used to make explicit that nothing is edited
    :param mod_path: directory/path-like designation of mod's location
    :return: mod slot number as int
    """
    if not isinstance(mod_path, PurePath):
        mod_path = PurePath(mod_path)
    mod_name = mod_path.name    # More human-readable than full path
    mod_name_slot_first_match = re.search(r'[cC]0(\d)', mod_name)   # re.search() gets first match
    if mod_name_slot_first_match is not None:
        # Successfully found source slot!
        mod_name_slot = int(mod_name_slot_first_match.group(1))  # Int from 0 to 7
        return mod_name_slot
    else:
        raise ValueError(f"'{mod_name}': I can't find slot number in this name; "
                         f"please put 'C0X' or 'c0X' (where X is the slot number) somewhere in the directory name!")


def replace_slot_into_path(mod_path: Path | str, new_slot: int | str) -> Path:
    """ Replace mod slot number from mod's name, given mod's directory root and the new slot number
    :param mod_path: directory/path-like designation of mod's location
    :param new_slot: new slot (as int 0-7 or string 'C0X')
    :return: Path with new directory name (the directory likely won't exist yet)
    """
    if not isinstance(mod_path, Path):
        mod_path = Path(mod_path)
    mod_name = mod_path.name    # More human-readable than full path
    if isinstance(new_slot, str):
        new_slot = int(new_slot[-1])    # Kind of unhinged way to get slot digit in case it's formatted 'c0X'
    new_name = re.sub(r'([cC])0\d', fr'\g<1>0{new_slot}', mod_name)     # Preserves letter case of original name!
    if new_name == mod_name:
        # We're going to be very strict here...
        raise ValueError(f"'{mod_name}', new slot {new_slot}: I tried to replace slot but it's the same name!")
    else:
        return mod_path.with_name(new_name)


def collect_dirlist_filelist(root_path: Path | str) -> Tuple[List[Path], List[Path]]:
    """ Return list of all nested directories and list of all files after walking it
        NOTE: I originally wrote this in Python 3.10, when pathlib didn't have Path.walk() built-in;
              this is extremely annoying, but I am importing os exclusively to use os.walk()
        NOTE: no "duplicate" names in output because full paths are used; List rather than Set to preserve walk order
    :param root_path: Path to directory
    :return: (list of dirs, list of files)
    """
    if not isinstance(root_path, Path):
        root_path = Path(root_path)
    if not root_path.is_dir():
        raise ValueError(f"'{root_path.name}': shouldn't be walking a non-directory")
    dirlist, filelist = [], []
    for root, dirs, files in os.walk(root_path):
        if dirs:
            dirlist += [Path(root)/dir_i for dir_i in dirs]
        if files:
            filelist += [Path(root)/file_i for file_i in files]
    return dirlist, filelist


def flatten_dict(nested_dict: dict, separator: str | None = '_', parent: str = '') -> dict:
    """ Flatten nested dictionary to single level of keys and values; unless separator is set to None,
        keys are casted to strings for now (I can imagine expanding to allow types with + operator
        overloading, and casting to string if it's a mix, but that seems more trouble than it's worth);
        separator is used to concatenate nested keys, keeping them unique when flattened
    :param nested_dict: Python dictionary
    :param separator: string used to concatenate parent key with nested key; set None to allow
                      overwriting values (keeping the most nested) rather than generating new keys!
    :param parent: used to pass parent key state during recursion; set '' to initialize at root
    :return: flattened dict
    """
    flattened_dict = {}
    for key, value in nested_dict.items():
        if separator is None:
            full_path_str_key = key     # Don't generate new unique key
        else:
            full_path_str_key = parent + separator + str(key) if parent else str(key)   # No separator if root
        if isinstance(value, dict):
            # Recurse
            flattened_value_dict = flatten_dict(value, separator=separator, parent=full_path_str_key)
            flattened_dict |= flattened_value_dict
        else:
            flattened_dict[full_path_str_key] = value
    return flattened_dict


def pretty_print_dir(root_path: Path | str) -> None:
    """ Aesthetically print file structure, i.e. recursively show names of sub-directories and files;
        sort order is alphabetical directories first, then alphabetical files starting with extension
        NOTE: I structure this function as an initialization wrapper + recursive function instead of
              just the recursive function with default base case because each node needs to show whether
              it's the "last child", which is an inelegant bit of state to pass recursively. Instead, I
              print the edge case (root node) in this initial wrapper, then have recursive function
              "look ahead" and print only the children of each node.
    :param root_path: directory/path-like
    :return: None
    """
    if not isinstance(root_path, Path):
        root_path = Path(root_path)
    if not root_path.is_dir():
        raise ValueError(f"'{root_path.name}': can't pretty-print a non-directory")
    print(root_path.name)   # Unique starting case that won't be covered during recursion
    _pretty_print_dir_recurse(root_path, level=1)    # Note how level 1 indicates children of root


def _pretty_print_dir_recurse(dir_path: Path, level: int) -> None:
    """ Helper: recursively print children of directories; assumes node is directory whose name was already printed
    :param dir_path: Path to directory
    :param level: how deep into subdirectories we are
    :return: None
    """
    if not dir_path.is_dir():
        raise ValueError(f"'{dir_path.name}': shouldn't be recursively printing a non-directory")
    # Sort children by alphabetical directories first, then alphabetical files starting with extension!
    # NOTE: I'm being very explicit here because technically .iterdir()'s output order is undefined
    sorted_children = sorted(dir_path.iterdir(), key=lambda p: ' '+p.name if p.suffix == '' else p.suffix+p.name)
    for i, child in enumerate(sorted_children):
        if i+1 == len(sorted_children):
            # Dirty way to indicate last element
            pretty_print = _pretty_print_last_child
        else:
            pretty_print = _pretty_print_non_last_child
        pretty_print(child, level)
        if child.is_dir():
            _pretty_print_dir_recurse(child, level=level+1)


def _pretty_print_non_last_child(general_path: PurePath, level: int) -> None:
    """ Helper: aesthetically print a Path name with certain number of indentations
    :param general_path: Path
    :param level: how deep into subdirectories we are
    :return: None
    """
    print(' '*4*(level-1), end='')
    print('|-- ', end='')
    print(general_path.name, end='\n')


def _pretty_print_last_child(general_path: PurePath, level: int) -> None:
    """ Helper: aesthetically print a Path name with certain number of indentations
    :param general_path: Path
    :param level: how deep into subdirectories we are
    :return: None
    """
    print(' '*4*(level-1), end='')
    print('L__ ', end='')
    print(general_path.name, end='\n')


def fuzzy_match_heuristic(element_1: str, element_2: str) -> float:
    """ Simple heuristic to compare similarity of two strings - [0: no matching letters, 1: anagram]
    :param element_1: string 1
    :param element_2: string 2
    :return: float in range [0, 1]
    """
    if len(element_1) > len(element_2):
        long, short = element_1, element_2
    else:
        short, long = element_1, element_2
    counter_long, counter_short = Counter(long), Counter(short)
    acc = 0     # Tally total number of common letters
    for char in counter_short.keys():
        acc += min(counter_long.get(char, 0), counter_short[char])  # min is what they have in commmon
    return acc / len(long)  # Heuristic


def fuzzy_matches(element: str, knowledge_bank: Set[str], threshold: float = 0.75,
                  heuristic: Callable[[str, str], float] = fuzzy_match_heuristic) -> List[str]:
    """ Return sorted list of known things with highest fuzzy match heuristic to element (past threshold)
    :param element: new thing to match
    :param knowledge_bank: known things to match to
    :param threshold: heuristic numerical threshold [0, 1] to register as a "match"
    :param heuristic: heuristic function whose value is compared to threshold
    :return: (ordered) list of known things
    """
    match_dict = {knowledge: heuristic(element, knowledge)
                  for knowledge in knowledge_bank if heuristic(element, knowledge) >= threshold}
    sorted_matches = sorted(match_dict.items(), key=lambda kv: kv[1], reverse=True)
    return list(map(lambda kv: kv[0], sorted_matches))


def load_internals_spreadsheet(location_path: Path | str = '.') -> pd.DataFrame:
    """ Try to find and load latest "Smash Ultimate 13.0.1 Internal Numbers and Codes" spreadsheet
        NOTE: raises FileNotFoundError if spreadsheet is not found
    :param location_path: directory/path-like; by default searches the directory this script is currently in
    :return: pd.DataFrame of the spreadsheet
    """
    if not isinstance(location_path, Path):
        location_path = Path(location_path)
    search_for_file = sorted(location_path.glob("Smash Ultimate 13.0.1 Internal Numbers and Codes*.xlsx"),
                             reverse=True)  # Version-agnostic, but prefer latest!
    if len(search_for_file) == 0:
        raise FileNotFoundError(f"'Smash Ultimate 13.0.1 Internal Numbers and Codes' spreadsheet not found "
                                f"at location '{str(location_path.absolute())}'")
    else:
        latest_found_file = search_for_file[0]
        internals_spreadsheet = pd.read_excel(location_path / latest_found_file, index_col=0)
        return internals_spreadsheet


def get_internals_spreadsheet_fighter_codes(internals_spreadsheet: pd.DataFrame) -> List[str]:
    """ To be used with load_internals_spreadsheet(); get character/fighter code name list from spreadsheet
    :param internals_spreadsheet: pd.DataFrame spreadsheet loaded with load_internals_spreadsheet()
    :return: list of (string) code names
    """
    # I'm committed to not changing this extremely long/explicit column name, so code should be futureproof
    known_fighter_codes = internals_spreadsheet['Character/Fighter Codes (red has name_id in ui_chara_db.prc '
                                                'but no customizable fighter directory in root of data.arc)'].dropna()
    known_fighter_codes_list = known_fighter_codes.to_list()
    return known_fighter_codes_list


def do_verification(mod_path: Path | str) -> bool:
    if not isinstance(mod_path, Path):
        mod_path = Path(mod_path)
    if not mod_path.is_dir():
        raise ValueError(f"'{mod_path.name}': can't verify a non-directory")
    print(f"---- '{mod_path.name}' ----")
    mod_slot = extract_slot_from_path(mod_path)     # Raises ValueError if can't
    print(f"Mod slot C0{mod_slot} successfully found in mod name! Nice naming convention!")
    dirfile_success, configjson_success, params_success, spellcheck_success = [True]*4  # Initialize as passing

    # Search mod directory for slot-specific things:
    # 1a) Find directories/files with slot number in name
    mod_dirs, mod_files = collect_dirlist_filelist(mod_path)    # Kind of brute force pre-walk
    re_slot_filter = re.compile(r'(?<!\d)0[0-7](?!\d)')  # .glob() can't weed out '_001.nutexb'; need this regex!
    slot_specific_dirs = [d for d in mod_dirs if re_slot_filter.search(d.name) is not None]
    slot_specific_files = [f for f in mod_files if re_slot_filter.search(f.name) is not None]
    # 1b) VERIFY if any slot numbers don't match actual slot
    if mod_slot == 0:
        re_not_mod_slot_digit_helper = r'[1-7]'
    elif mod_slot == 7:
        re_not_mod_slot_digit_helper = r'[0-6]'
    else:
        # Want to avoid given digit; I can't think of a good way to do this with [^{mod_slot}] or \d
        re_not_mod_slot_digit_helper = fr'(?:[0-{mod_slot-1}]|[{mod_slot+1}-7])'
    re_not_mod_slot_filter = re.compile(fr'(?<!\d)0{re_not_mod_slot_digit_helper}(?!\d)')
    wrong_slot_dirs = [d for d in slot_specific_dirs if re_not_mod_slot_filter.search(d.name) is not None]
    wrong_slot_files = [f for f in slot_specific_files if re_not_mod_slot_filter.search(f.name) is not None]
    if wrong_slot_dirs:
        dirfile_success = False
        print("FAILURE: Wrong slot DIRECTORIES found! Please manually check/fix these:")
        for wrong in wrong_slot_dirs:
            print(wrong.relative_to(mod_path))
    elif wrong_slot_files:
        dirfile_success = False
        print("FAILURE: Wrong slot FILES found (uh, actually decent chance of false positives from custom victory "
              "screens, custom victory music, etc.)! Please manually check/fix these:")
        for wrong in wrong_slot_files:
            print(wrong.relative_to(mod_path))
    else:
        print("SUCCESS: No wrong slot directories/files found! Moving on...")

    print('\n', end='')     # Print newline between sections for aesthetics

    # 2a) Find config.json
    file_addition_config = list(mod_path.glob('config.json'))   # .glob() is good for constant name files
    # 2b) VERIFY slot-related text - fine to have extra slots/files configured, but must have actual slot
    re_mod_slot_filter = re.compile(fr'(?<!\d)0{mod_slot}(?!\d)')
    if file_addition_config:
        print(f"config.json (Arcropolis file addition configuration) found! "
              f"Should be fine to have extra/unused configurations, but checking actual slot "
              f"(C0{mod_slot}) is configured...")
        with open(file_addition_config[0], 'r') as config_json:
            config_json_data = json.load(config_json)
            # config.json has universal pattern of
            # 'new-dir-files':
            #     'fighter/<fighter_code>/c0X':
            #         [list of relative paths to files which should be detected by above slot]
            slot_filepathlist_dict = config_json_data['new-dir-files']  # Un-nest from new-dir-files
            correct_slot_names = [slot_name for slot_name in slot_filepathlist_dict.keys()
                                  if re_mod_slot_filter.search(slot_name) is not None]
            if correct_slot_names:
                if len(correct_slot_names) > 1:
                    print(f"WARNING: {len(correct_slot_names)} config.json slot names "
                          f"with mod slot C0{mod_slot} found! Maybe different characters (Kirby cap?)? "
                          f"It's unusual for a mod to have this, so alerting just in case.")
                for correct_slot_name in correct_slot_names:
                    # Realistically this loop will only execute once, unless for example both Pikachu and
                    # Cloud have C07 edits (i.e. both have their added files listed in same config.json somehow)
                    added_files_list = slot_filepathlist_dict[correct_slot_name]
                    for added_file in added_files_list:
                        if (re_mod_slot_filter.search(added_file) is None
                                or re_not_mod_slot_filter.search(added_file) is not None):
                            # Complex condition: looking for suspicious cases of either
                            # 1) correct slot labeled file not there or 2) wrong slot labeled file is there;
                            # Note this is labeled "warning" and not "failure" because many characters have different
                            # textures on different slots, and for a mod to be moveable in that case, default (non-
                            # slot-labeled) texture files could be reused and declared for other slots in config.json!
                            print(f"WARNING: '{correct_slot_name}': '{added_file}' doesn't seem to be "
                                  f"specific to C0{mod_slot}; not necessarily wrong, alerting just in case")
            else:
                configjson_success = False
                print(f"FAILURE: config.json - no C0{mod_slot} slot key designated to receive additional files. "
                      f"That's the whole purpose of config.json.")
        if configjson_success:
            print(f"SUCCESS: config.json seems to have configurations for C0{mod_slot}! Moving on...")
    else:
        print("No config.json (Arcropolis file addition configuration) found. Moving on...")

    print('\n', end='')  # Print newline between sections for aesthetics

    # 3a) Find msg_name.msbt/.xmsbt and ui_chara_db.prc/.prcx/.prcxml
    # Despite being a param patch, .prcx is compiled so can't be easily read without external software
    unreadable_params_msg_name = list(mod_path.glob('**/msg_name.msbt'))
    unreadable_params_ui_chara_db = (list(mod_path.glob('**/ui_chara_db.prc'))
                                     + list(mod_path.glob('**/ui_chara_db.prcx')))
    readable_param_patch_msg_name = list(mod_path.glob('**/msg_name.xmsbt'))
    readable_param_patch_ui_chara_db = list(mod_path.glob('**/ui_chara_db.prcxml'))  # More rarely used
    # 3b) VERIFY .xmsbt slot "index values", which may not necessarily be slot numbers but generally are
    # Note: I believe no reason to "verify" ui_chara_db if there's no readable msg_name - a mod like Giga Bowser
    #       Character Expansion will edit it to unlock the character, but there's no pattern to follow;
    #       we check ui_chara_db in conjunction with msg_name though because "index values" must match
    if unreadable_params_msg_name:
        print("WARNING: msg_name.msbt (modified overwrite of default text names) found, but we can't read/verify it!")
    if readable_param_patch_msg_name:
        print("msg_name.xmsbt (Arcropolis msg_name.msbt param patch) found! Likely for purpose of single-slot text.")
        if unreadable_params_ui_chara_db:
            print("WARNING: ui_chara_db exists but not in readable .prcxml format; we can't read/verify it!")
        elif readable_param_patch_ui_chara_db:
            print(f"ui_chara_db.prcxml (Arcropolis ui_chara_db.prc param patch) found! This means we can verify "
                  f"msg_name.xmsbt contents with certainty by checking 'n0{mod_slot}_index' value!")
        else:
            print("WARNING: no ui_chara_db found, despite modified msg_name! Might be intentional to overwrite "
                  "character's every slot's text; not necessarily wrong, alerting just in case.")
        # I should consider using xmltodict library, which makes XML feel like JSON, for consistency
        # msg_name has pattern of
        # <xmsbt>
        #     <entry label="nam_chr0_<index_value>_<fighter_code>">
        #         <text>Fighter Unlock Screen name</text>
        #     </entry>
        #     <entry label="nam_chr1_<index_value>_<fighter_code>">
        #         <text>CSS portrait name</text>
        #     </entry>
        #     <entry label="nam_chr2_<index_value>_<fighter_code>">
        #         <text>VS. AND RESULTS SCREEN NAME</text>
        #     </entry>
        #     <entry label="nam_chr3_<index_value>_<fighter_code>">
        #         <text>CSS ICON NAME (FOR SLOT 0)</text>
        #     </entry>
        #     <entry label="nam_stage_name_<index_value>_<fighter_code>">
        #         <text>Boxing Ring Hype Name</text>
        #     </entry>
        # ...
        msg_name_tree = ET.parse(readable_param_patch_msg_name[0])
        xmsbt_root = msg_name_tree.getroot()     # <xmsbt> opening tag; can now iterate through <entry> tags
        entry_labels = [entry.attrib['label'] for entry in xmsbt_root]     # Crucial label names (not text itself)
        if readable_param_patch_ui_chara_db:
            # Read ui_chara_db.prcxml for n0X_index (where X is slot) edits; pattern of
            # <struct>
            #     <list hash="db_root">
            #         <struct index="<0-121 slot number>">
            #             <byte hash="n01_index">1</byte>
            # ...
            ui_chara_db_tree = ET.parse(readable_param_patch_ui_chara_db[0])
            struct_root = ui_chara_db_tree.getroot()  # <struct> opening tag
            mod_slot_index_value_edit = struct_root.findall(fr"./list/struct/byte[@hash='n0{mod_slot}_index']")
            if mod_slot_index_value_edit:
                index_value = int(mod_slot_index_value_edit[0].text)    # e.g. cast '1' to 1
            else:
                print(f"WARNING: no 'n0{mod_slot}_index' value edit found in ui_chara_db.prcxml. "
                      f"Assuming intentional use of default index value '0'.")
                index_value = 0     # Smash Ultimate's default index value is technically 0 (for all slots)
        else:
            index_value = mod_slot  # No ui_chara_db, we'll just assume to check mod_slot
        # Check that there exist labels for either 1) n0X_index value if ui_chara_db.prcxml was found and read
        # or 2) slot number if we couldn't access ui_chara_db (in general, n0X_index value is edited to X)
        # Note the below regex zero-pads index_value - different because index_value can be 0-127, not just 0-7!
        re_index_value_filter = re.compile(fr'(?<!\d){index_value:02}(?!\d)')   # index_value can be 0 or 13 or 105
        correct_slot_labels = []
        wrong_slot_labels = []
        for entry_label in entry_labels:
            if re_index_value_filter.search(entry_label) is None:
                wrong_slot_labels.append(entry_label)
            else:
                correct_slot_labels.append(entry_label)
        if wrong_slot_labels:
            print("WARNING: \"Wrong\" slot msg_name.xmsbt entry labels found! Please manually check/fix these:")
            print(wrong_slot_labels)
        if correct_slot_labels:
            print("\"Correct\" slot msg_name.xmsbt entry labels found:")
            print(correct_slot_labels)
            print(f"SUCCESS: msg_name.xmsbt seems to have configurations for C0{mod_slot}'s 'n0{mod_slot}_index' "
                  f"value '{index_value}'! Moving on...")
        else:
            params_success = False
            print(f"FAILURE: No correct slot msg_name.xmsbt entry labels found! We checked for 'n0{mod_slot}_index' "
                  f"value '{index_value}', e.g. <entry label=\"nam_chr1_{index_value:02}_<fighter_code>\">, etc.")
    else:
        print("No verifiable msg_name (custom text) found. Moving on...")

    print('\n', end='')  # Print newline between sections for aesthetics

    # Fancy - check spelling of fighter codes in
    # 1) fighter/ nested folders
    # 2) individual files (delimiting by _ and maybe . unless we remove suffix), check every word (lol)
    # 3) inside config.json (delimit by /) and maybe msg_name.xmsbt (delimit by _)
    # Make sets of words from each source, eliminate all words that are in knowledge bank,
    # run the rest of the words through spellcheck, return source if there are any suggestion hits!
    try:
        internals_spreadsheet = load_internals_spreadsheet()
        fighter_codes_set = set(get_internals_spreadsheet_fighter_codes(internals_spreadsheet))
        print("'Smash Ultimate 13.0.1 Internal Numbers and Codes' spreadsheet found! "
              "Commencing \"smart spellcheck\" (I had fun with this one, please bear with me):")

        def spellcheck_words_dict(words_dict):
            # The following words unintentionally trigger spellcheck to 'master', 'demon', 'elight', etc.
            standard_false_positives = {'stream;', 'model', 'skin', 'light', 'normal'}
            for key_words_set, value_source in words_dict.items():
                close_matches = []
                for set_word in key_words_set:
                    if set_word not in fighter_codes_set and set_word not in standard_false_positives:
                        close_matches += fuzzy_matches(set_word, knowledge_bank=fighter_codes_set)
                if close_matches:
                    if isinstance(value_source, Path):
                        value_source = value_source.relative_to(mod_path)
                    print(f"- Suggestions for '{value_source}': {close_matches}")

        re_word_sep = re.compile(r'[_./]')
        mod_dirs_words_dict = {frozenset(re_word_sep.split(d.stem)): d for d in mod_dirs}
        mod_files_words_dict = {frozenset(re_word_sep.split(f.stem)): f for f in mod_files}
        # Spellcheck dirs/files words dicts!
        # NOTE: spellcheck meant to be aggressive; for now, I won't link it to the spellcheck_success flag
        spellcheck_words_dict(mod_dirs_words_dict)
        spellcheck_words_dict(mod_files_words_dict)
        if file_addition_config:
            config_json_words_dict = {}
            for key_slot, value_filepathlist in slot_filepathlist_dict.items():
                # Inspection doesn't warn that dict might be referenced before assignment... weird but I'll take it
                config_json_words_dict[frozenset(re_word_sep.split(key_slot))] = "config.json slot: " + key_slot
                for filepath in value_filepathlist:
                    config_json_words_dict[frozenset(re_word_sep.split(filepath))] = "config.json filepath: " + filepath
            # Spellcheck config_json_words_dict!
            spellcheck_words_dict(config_json_words_dict)
        if readable_param_patch_msg_name:
            msg_name_words_dict = {}
            for entry_label in entry_labels:
                # Inspection shows warning that entry_labels might be referenced before assignment, but impossible
                msg_name_words_dict[frozenset(re_word_sep.split(entry_label))] = "msg_name entry label: " + entry_label
            # Spellcheck msg_name_words_dict!
            spellcheck_words_dict(msg_name_words_dict)
        print("Spellcheck complete. Experimental, so no success/failure message. Moving on...")
    except FileNotFoundError as no_internals_spreadsheet_msg:
        print(f"{no_internals_spreadsheet_msg}. Skipping smart spellcheck...\n"
              f"Seriously though you should go get that spreadsheet... Moving on...")

    print('\n', end='')  # Print newline between sections for aesthetics

    success = all((dirfile_success, configjson_success, params_success, spellcheck_success))
    print(f"\nVERIFICATION COMPLETE! TRUE MEANS ALL CLEAR, FALSE MEANS PROBABLY NOT; "
          f"SEE PRINTED STATEMENTS ABOVE FOR DETAILS AND GUIDANCE:\n"
          f"{success}")
    return success


def do_batch_verification(mod_path: Path | str) -> bool:
    if not isinstance(mod_path, Path):
        mod_path = Path(mod_path)
    if not mod_path.is_dir():
        raise ValueError(f"'{mod_path.name}': can't batch-verify a non-directory")
    batch_target_subdirs = [sub for sub in mod_path.iterdir() if sub.is_dir()]
    subdir_results_list = []
    for number, subdir in enumerate(batch_target_subdirs, start=1):
        print(f"\n---------- {number} {''.join(['---------- ']*6)}\n")  # Print an aesthetic dividing line
        try:
            subdir_result = do_verification(subdir)
            subdir_results_list.append(subdir_result)
        except ValueError:
            print(f"Skipping {subdir.name} (directory name doesn't look like single-slot mod)...")
    return all(subdir_results_list)


def do_renaming(mod_root_path, mod_slot_int, new_slot_int):
    fuzzy_slot_specific = mod_path.glob(f'**/*0{mod_slot}*')  # Might latch onto _001.nutexb, which we don't want
    sorted([fuzzy_slot_specific.parts[-1] for fuzzy_slot_specific in mod_path.glob(f'**/*0{mod_slot}*')])
    list(mod_path.glob(f'**/*0{mod_slot}*'))[0].relative_to(mod_path)  # Get that human-readable relative path!
    re.sub(r'(?<!\d)0[0-7](?!\d)', fr'0{new_slot}', glob)  # For renaming 03.bntx or even 03 but not 003
    pass


if __name__ == '__main__':
    USAGE = "Usage: ./change_verify_slot.py path/to/mod/root [<slot_number>]"
    if len(sys.argv) not in [2, 3]:
        print(USAGE)
        exit()

    # Process mod source directory input
    arg_mod_path = sys.argv[1]
    mod_path = Path(arg_mod_path)
    mod_name = mod_path.name    # More human-readable than full path

    # Check that input is actually a directory
    if not mod_path.is_dir():
        print(f"{mod_name} appears to not be a directory...")
        if mod_path.is_file():
            if mod_path.suffix == '.zip':
                print(f"You forgot to unzip the mod after downloading?")
            else:
                print(f"'{mod_path.suffix}': it's a file; you've pointed me to the wrong thing!")
        else:
            print(f"This isn't even a file! Please point me to an unzipped mod directory.")
        exit()

    # Extract source slot number from directory name
    mod_name_slot_first_match = re.search(r'[cC]0(\d)', mod_name)   # re.search() gets first match
    if mod_name_slot_first_match is not None:
        # Got source slot!
        mod_name_slot_match_context = mod_name_slot_first_match.group(0)    # e.g. 'c03' or 'C06'
        mod_name_slot = int(mod_name_slot_first_match.group(1))     # Int from 0 to 7
        verification_result = do_verification(mod_path, mod_name_slot)
    else:
        # No slot in mod name, assume user wants batch verification of subdirectories
        batch_target_subdirs = [sub for sub in mod_path.iterdir() if sub.is_dir()]
        for subdir in batch_target_subdirs:
            do_verification(subdir)
        # i.e. get list of subdirectories and loop Verification until fails, no harm in doing so. Then we're done.
        # Design question: should verification function be responsible for extracting slot? Because
        # batch verification doesn't require slot, yet depends on running a bunch of verification
        # Answer: have independent extraction function, have verification use it, have batch verification literally
        # just be naive logic of running verification (which fails when can't extract) on loop

    # Verification
    # Suggest human correct before allowing renaming, but give option to override

    # Clean up intended new slot
    arg_new_slot = sys.argv[2]
    new_slot = int(arg_new_slot[-1])    # Kind of unhinged way to get slot digit in case it's formatted 'c0X'
    if new_slot > 7 or new_slot < 0:
        print(f"{new_slot} is the detected slot number, but it must be between 0 and 7;\n"
              f"I know additional slots (beyond 8) is now possible in Arcropolis, but I haven't added it yet")
        exit()

    # Renaming
    # Prep: clean command line input arg and generate new directory name (but prepend WIP: until finished)
    # Starting from discovered list from before, prompt for Y to continue
    # Rename in new directory to new number; print (aesthetically) the renamed list
    # Print every single file in file structure as final debrief
    # Should be able to pipe to debug

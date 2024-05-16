# slot-sanity-check

Smash Ultimate modding tool to verify integrity of one-slot (custom skin) mods and help with changing slots. There are more sophisticated/complete alternatives for the latter (I was not aware when I made this); see CSharp's GUI Reslotter and CoolSonicKirby's website (TODO: add links).

## Stream-of-consciousness brainstorm

This script aims to speed up folder/file renaming necessary to change the
effective _character slot_ of Smash Ultimate mods. Note this won't automatically work for every mod - textures for some characters like Wario won't work if transferred from even-numbered slot to odd-numbered slot, etc.

As a blackbox script, we'll try to be non-destructive and explicit by:
1) Creating duplicate folder instead of modifying in existing folder,
2) Pretty-printing everything staged to be "renamed" (not technically renaming since we'll create new files with the name) as sanity check before executing.

This script will NOT change any of your existing files! And if it fails,
rest easy knowing nothing on your computer has been deleted, though there may be a new temporary folder that you can safely delete!

The script will have 2 somewhat standalone features:

### 1. Slot "verification" (run script without specifying new slot)

I'll somewhat rudely require you to include the slot in the name of the mod source folder, e.g. script will reject "cool_falcon_mod" until you rename it "cool_falcon_mod_c00" or "C00". This is honestly just best practice for everyone involved; note if your mod spans multiple slots, it shouldn't need this script in the first place because this script is for changing one numbered slot to another. 

Anyway, I'll use this slot info to sanity check the naming of all files and folders included in the mod, and I'll also check the fighter code name and maybe even config.json. You'd be surprised how often mods are published broken, or containing accidental unrelated files!

Since verification is completely harmless, I've also built in "batch verification", i.e. if you point the script at a folder (no naming requirement) containing a bunch of mod folders, it will try to run its normal verfication on each mod subfolder.

### 2. Slot "renaming" (run script with the new slot argument)

The new slot mod folder I generate will be named following your source folder formatting. Yet another reason we'll require the source folder to include the mod slot in its name!

---

Here is a brainstorming list of folders/files that should be modified to slot (this is not "theoretically" complete, but practically over the hundreds of mods I use, these are the folders/files with slot-specific names):
```
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
    /param/database/ui_chara_db.prcxml -> ideally don't change, because can't
                                          change interchangeable .prcx format
- config.json -> edit declared file additions; just check that new slot is there
```

The above list assumes the mod is designed for one slot number, and that you
would not concurrently set the same mod on multiple slots (you could, but we're keeping files (e.g. vc_narration_characall.nus3audio, msg_name.msbt) that will lead to Arcropolis "file conflict", i.e. one slot's mod files take questionable precendence over another's, because only one can be "active"). You can fix file conflicts by simply renaming the file you'd prefer to deactivate.

Some other renaming notes off the top of my head:
- `item/` subfolder slots should not be renamed, e.g. to modify Snake's items, the new textures must be c00.
- I'm not sure whether to rename Kirby Cap folders included with other fighters. Probably not, because we want Kirby's C00 costumes to change, right?
  - `fighter/kirby/model/copy_<fighter_code>_cap/c0X/ -> c0Y`???
- There is no one-slot solution (yet) for character selection screen (CSS) announcer voice lines. Right now, you have to replace the whole audio file at `sound/bank/narration/vc_narration_characall.nus3audio`
  - Update 2024-05: CoolSonicKirby's "CSK Collection" plugin now offers a great solution for this! We just need to add the single new sound file to `sound/bank/narration/`, write a PRCX/PRCXML param patch to specify its use by name, and activate the plugin's capability by making a flag. TODO: flesh out this description.
- `ui/replace/chara/` subfolders must accomodate numbers 0 to 13; though most mods don't go past 6, you may need to go to 10 for Pokemon Trainer, 12 for boss portraits, 13 for Joker.
  - Character UI:
    - chara_0 = record portrait (square face)
    - **chara_1** = CSS/boxing ring portrait (square, character most in bottom right)
    - **chara_2** = stock icon (square cartoon icon)
    - **chara_3** = vs./results portrait (square, character full in bottom left)
    - **chara_4** = battle portrait (square face in diamond)
    - chara_5 = spirit portrait (no alts)
    - **chara_6** = final smash portrait (1:2 horizontal rectangle, eyes)
    - chara_7 = CSS icon (no alts)
    - chara_10 = Pokemon Trainer Pokemon masks
    - chara_12 = boss portraits
    - chara_13 = alternate battle portrait for unmasked Joker
- `ui/message/msg_name.msbt` and `ui/param/database/ui_chara_db.prc` are often changed in mods to .xmsbt and .prcxml (or .prcx) to take advantage of Arcropolis's "param patching" which allows for one-slot text (really hope a similar system is invented for announcer voice lines). Editing these files to appropriately change active slots of character names may be tricky. Please sanity check by reading WataPascul's or Miguel's fantastic guides.
  - Technically we could be very intrusive and edit numbers in .prcxml, then edit corresponding numbers in .xmsbt. We could even link in code to generate the param patching files by diffing non-one-slotted MSBT and PRC with parcel.exe. But that would be a lot of effort for something not a lot of people would use, I think.

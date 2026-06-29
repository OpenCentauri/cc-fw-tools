### Api control patch

Patched using binary ninja. Patches sub_2e2638 at offset 0x002e2638. For easier searching, search for the string `device is busy,can't set status\n`. Patch out the check that this error message is contained in (right click `if (r0_14 == 1 || r0_16)` > patch > never branch)
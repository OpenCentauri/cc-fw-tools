# EMMC Restore Procedure

This procedure can be performed when you already have a good backup and your printer is not working properly or even cannot boot. Another use case is to fast switch to another printer setup by replacing the system partitions or the entire eMMC with the content from another setup. The procedure uses the uboot functionality to read/write the eMMC and to read/write USB disks. The restore procedure recovers the entire eMMC from a USB disk backup.

To perform a restore follow these steps according to the current printer working state (Case A, B or C):

## Case A (Recommended)

In case your printer is in good working conditions (it can somehow boot) and you are using firmware version that has uboot enabled.

1. Turn on the printer and stop the booting process by holding key 's'
2. Insert a USB disk (FAT32 formatted) with the file [restore.scr](../extra-stuff/emmc/restore.scr) on it for complete emmc restore. If you need to restore just the system partitions use the file [srestore.scr](../extra-stuff/emmc/srestore.scr) instead.
3. From the uboot shell enter the following:

```sh
usb reset
```

```sh
usb dev 0
```

```sh
fatload usb 0:0 42000000 restore.scr
```

If you see an error, try typing in usb part and see what partitions are available. Then enter:

```sh
fatload usb 0:<Enter partition number in here> 42000000 restore.scr
```

Example:

```sh
fatload usb 0:1 42000000 restore.scr
```

(Partition 1)

For a system restore replace the above script name `restore.scr` with the name `srestore.scr`.

4. Remove the USB disk with the scripts and insert the 8GB USB disk with the complete backup.
5. ONLY IN CASE YOU DONT' HAVE A backups on a USB disk you can create them from the backup files on a Linux machine, otherwise go to step 6:

    `dd if=emmc_backup.bin of=/dev/sdh bs=512 count=15269888 status=progress` — replace the `/dev/sdh` with the device name of your USB disk. On Windows, write the image onto the USB stick with [`diskcpy`](https://github.com/suchmememanyskill/diskcpy/releases) instead (run **PowerShell as Administrator**): find the stick with `Get-CimInstance Win32_DiskDrive | Select-Object DeviceID, Model, Size`, then — **double-checking you target the USB stick and not a real disk, as this overwrites it** — `diskcpy.exe emmc_backup.bin \\.\PHYSICALDRIVE#`. (Balena Etcher's "Flash from file" works too.)
6. Type the following to execute the script:

    ```sh
    source 42000000
    ```

    Wait about 15 minutes and the entire emmc will be restored 1:1 from the USB disk sector by sector. If you see an error and the script stopped before showing 100%, insert another type USB disk and enter again:

    ```sh
    source 42000000
    ```
7. Reset the printer or power off / power on and you should have a fully working machine like at the time the backup was taken.

## Case B

With the standard or the custom xfel tool in case your printer cannot boot or you are using a firmware version that disable the UART and you don't have access to the uboot shell.

To boot into uboot shell:

1. Enter the printer in FEL mode and connect the uart to the computer. Open the terminal.
2. Enter the following:

```sh
xfel ddr t113-s3
```

```sh
xfel write 0x43000000 uboot239.bin
```

```sh
xfel exec 0x43000b50
```

Immediately press and hold key 's' in the terminal until the boot process stop in uboot shell and go to step 3 above

You can modify the script and create new restore.scr image by:

```sh
mkimage -T script -n 'EMMC Restore' -d restore.txt restore.scr
```

## Case C

In case when after trying to use case B, you cannot enter in the uboot console for any reason (including the uart has some hardware issues).
Your printer should be in FEL mode. If not, try to enter in FEL mode as described in the document for FEL mode.

- Connect the printer left USB slot (with the camera icon) to the computer with male to male USB cable (1:1 pin connection)
- Execute this command to verify if the printer is in FEL mode

```
xfel extra sdmmc detect
```

- If you don't receive error executing the above command, start restoring the entire eMMC by:

```
xfel extra sdmmc write 0 backup.bin
```

NOTE: Replace `backup.bin` by the filename of your backup file

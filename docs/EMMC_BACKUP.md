# EMMC Backup Procedure

This procedure is recommended to be performed when your printer is completely setup in a well working condition. It is possible to create complete eMMC backup for about 15 minutes for eMMC size of about 8GB. It is recommended to have at least one complete backup. The procedure uses the uboot functionality to read/write the eMMC and to read/write USB disks. The backup procedure copy the entire eMMC on a USB disk. Then on a Linux host you can create image of the USB disk to have it as a backup file.

To perform a backup follow these steps:

## By the uboot console

1. Use the original app version 2.39 and stop the booting process by holding key 's' (or use any custom firmware update that has the UART enabled such as u-boot-sunxi-with-spl-cc1.bin)
2. Insert a USB disk (FAT32 formatted) with the file [backup.scr](../extra-stuff/emmc/backup.scr) on it for complete emmc backup.
3. From the uboot shell enter the following:

```sh
usb reset
```

```sh
usb dev 0
```

```sh
fatload usb 0:0 42000000 backup.scr
```

If you see an error, try typing in usb part and see what partitions are available. Then enter:

```sh
fatload usb 0:<Enter partition number in here> 42000000 backup.scr
```

Example:

```sh
fatload usb 0:1 42000000 backup.scr
```

(Partition 1)

4. Remove the USB disk with the scripts and insert at least 8GB USB disk for a complete backup. It might be formatted or not and it will be completely rewritten by the contents of the eMMC. NOTE: Do not use a disk with important information! All data on it will be lost!

5. Type the following to execute the script:

```sh
source 42000000
```

Wait about 15 minutes and the entire emmc will be transferred 1:1 to the USB disk sector by sector
   If you see an error and the script stopped before showing 100%, insert another type USB disk and enter again:

```sh
source 42000000
```

6. From a Linux machine export the complete backup as a file from the USB disk:

```sh
dd if=/dev/sdh of=emmc_backup.bin bs=512 count=15269888 status=progress
```

Note: replace the `/dev/sdh` with the device name of your USB disk.

### On Windows: pull the image off with diskcpy

Windows has no `dd`. After the script finishes writing the eMMC onto the USB stick, copy the raw
image off the stick with [`diskcpy`](https://github.com/suchmememanyskill/diskcpy/releases) — a
small standalone utility that does a block-level read of a physical drive into a file.

1. Plug the USB stick into your PC. **Click _Cancel_** on any "format this drive" prompt — the
   stick is a raw eMMC dump with no Windows-readable filesystem.
2. In **PowerShell (run as Administrator)**, find the stick's physical-drive number:

```powershell
Get-CimInstance Win32_DiskDrive | Select-Object DeviceID, Model, Size
```

3. Dump it to an image file (replace `PHYSICALDRIVE#` with your stick — **double-check the number
   and size first**):

```powershell
diskcpy.exe \\.\PHYSICALDRIVE# emmc_backup.bin
```

Pair [`diskcpy`](https://github.com/suchmememanyskill/diskcpy/releases) with the precompiled [`sunxi-fel.exe`](../extra-stuff/emmc/sunxi-fel.exe) for a
fully Windows-native workflow (no WSL or `dd` needed).

## By the standard or the custom xfel tool in uboot mode

This mode can be used when the version you are using has the uart disabled and you are unable to stop the booting process and to enter in the uboot shell.

You could either do:

```sh
xfel exec 0x0
```

to boot into uboot and then enter the commands above or:

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

You can modify the script and create new backup.scr image by:

```sh
mkimage -T script -n 'EMMC Backup' -d backup.txt backup.scr
```

## By the custom xfel tool in USB mode

TBD

# OpenCentauri Firmware Tools

## Background

This repo was forked from the wonderful AnyCubic Kobra Firmware tools by ultimateshadsform. Props to them for all the amazing work they put into this!

Scripts have been modified, re-written, tweaked etc. to support similar firmware tasks for the Elegoo Centauri Carbon printer and firmware.

Please note that if a script is not specifically called-out in this README, it probably hasn't been tested with the Carbon firmware and might break something or brick your printer!

If there are two versions of a script, and one has an -ac in the name, this is the original AnyCubic version of the file for reference.

## OpenCentauri Features

1. TBD, but for now check out ./patch.sh at the top level of this repo!
1. Bundled entware with openssh, refreshed branding, lots of quality of life updates for remote access to printer.
1. Default root password is 'OpenCentauri', although you can ssh-copy-id a key over! You should change this.
1. By default root shell fromn Sims on port 4567 is available in OpenCentauri for breakglass access, can use with `nc <my-printer-ip-or-host> 4567`.
1. More to come!!!

## Prerequisites

1. You will need to install git and git-lfs on the host building the FW
  1. If you install git-lfs after, you'll need to run `git lfs pull` in the cc-fw-tools directory before building.
1. You will need to have jailbroken your printer to accept third-party firmware updates. Please reach out to us on [the OpenCentauri Discord](https://discord.gg/t6Cft3wNJ3) for help with this.
1. For the technically savvy, this involves replacing the contents of `/etc/swupdate_public.pem` which is the key used to digitally sign firmware updates:

    1. Stock ELEGOO firmware signing key:

        ```pem
        -----BEGIN PUBLIC KEY-----
        MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAnFBZ/+BuRCESalxGqlEE
        he3eRigUHAZZdW1nPEQZT/6V1gARirJMzT+KUFKqMgtaQuZTtizB3Uo+PbXXwkEl
        MaGUwRYHOY5ebTt+DfBBWEXvvklKIoKypWF6ta6B37PyHJz4ssnCcCtQRroOllXm
        vrYLjt5tinKJUx3XoO6iLYf2R5r6+8FB3J/i1ZhJuwCBDtIsivyxdQSHsH9pX55V
        MOsWKKyuOVyixL42hwiMxOL8HkmumLVDLeXsl0gp34JRN9tR80H5W5+8TUUXnKst
        vjf+YfzbKCIvvLl3qjDDZW9AlwrWE1mhfxFA/N2qjDQ2rsoquLPiLm3CDVBlKCUP
        fwIDAQAB
        -----END PUBLIC KEY-----
        ```

    1. OpenCentauri `/etc/swupdate_public.pem` signing key:

        ```pem
        -----BEGIN PUBLIC KEY-----
        MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAvkLL7VK9svGKBM4Q39uB
        ZNkkxy6zqQeCInOE3PeIhvRa3teowz7MLiYJi+CI/4q6mPysLCo3lfY+cWFCc+U3
        2lhhHJZy2+gEoTt0ecEWKIznd1GNaUMJFzHIHPCc4LssZFQ9ahZPPuoU/wYtguxA
        qPSWsH+SNe8xihy5WRG4363FdvwBQc+Q7DTE7firafCzjfaPuoSClDQsyTcGByxs
        78s23DXbvQ8jLLlVffLMFD4y9KNbuEdyswe9QEUQar+XEwFm7EkVTX+TAHzHn40s
        hW+mpfZZgMxJ6a88A527e7DfBlAnt1ZSIh4xXZMlniv40kdXyqSWO/wqJcbmnUTn
        cQIDAQAB
        -----END PUBLIC KEY-----
        ```

## Reverting back to Stock ELEGOO Firmware

1. To revert back, you will need to replace your original key and then flash an official ELEGOO firmware. I recommend 1.1.25 for now since it has the most features, and this is what OpenCentauri is (currently) based on.
    1. Update the /etc/swupdate_public.pem key in your /etc directory via ssh to the original ELEGOO firmware signing key (above)
    1. Run the script `./fwdl.sh`, to grab the 1.1.25 Firmware into the FW/ directory
    1. Copying the new file `FW/FW-CentauriCarbon-v1.1.40-2025-08-15.bin` to your printer's USB stick at the root level, with filename `update.bin`
    1. Insert USB-stick into printer
    1. Re-boot your printer, and it should offer to update!

## Download the Base Firmware

1. Download the 1.1.25 FW to `./FW/`:
    `./fwdl.sh`

## Configure the OpenCentauri Firmware Image

### Config Instructions

1. Edit the file `./patch_config` with any settings you would like to override

### Documentation of Settings

```sh
# How long to wait until starting /app/app on boot
# If non-zero, you can SSH in after boot and run 'noapp' to prevent start
OC_APP_BOOT_DELAY=0
```

## Build the OpenCentauri Firmware Image

### Option 1: Manual Build

1. Unpack the firmware of choice: (tested with 1.1.25)
    `sudo ./unpack.sh FW-CentauriCarbon-v1.1.40-2025-08-15.bin`
1. Run this patch set of updates to the squashfs extracted:
    `sudo ./patch.sh`
1. Generate a new update.swu:
    `sudo ./pack.sh`

### Option 2: Automatic Build

1. Run through all the steps in Option 1:
    `./build.sh`

## Install to Printer

1. Install to the printer (only works if already running OpenCentauri FW to install an update):
    1. `./install.sh [--stage,--flash,--sendit] <printer-ip-or-hostname>`
    1. Stages, flashes or stages and flashes the file generated in update/update.sw by `pack.sh`.
    1. Run with no arguments for usage.
1. Alternative (if just jailbroken but not running OpenCentauri yet):
    1. Copy update/update.swu to USB stick, in the folder update, file update.swu
    1. Reboot the printer and it should detect an update is available!

## Special Commands on Printer
1. `mount_usb`: Mounts the USB drive if available to /mnt/exUDISK like /app/app does
1. `noapp`: Run after logging in if you configured an OC_APP_BOOT_DELAY to prevent app from starting this boot

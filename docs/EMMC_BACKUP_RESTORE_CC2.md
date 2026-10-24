# Centauri Carbon 2 (CC2) — eMMC Backup / Restore over USB FEL Mode

Make a 1:1 image of the CC2's eMMC and write it back. Tools: `sunxi-fel` + U-Boot. Windows / Linux / macOS.

---

## 0. Warnings

> **⚠️ Hardware** — Use **J6** for FEL. The board's external "USB-C-shaped" connector is actually a 2-pin power terminal, not USB.
>
> **⚠️ Data** — Don't interrupt a write. Verify every backup before relying on it.

---

## 1. What you need

### Hardware

- The **CC2 printer**, powered off and unplugged from mains.
- A **PC** with at least one free USB-A port (Windows 10/11, Linux, or macOS).
- A **USB-A male-to-dupont female cable** (4 wires + USB-A plug). This is the FEL data link from your PC to the printer's J6 header. Sold pre-assembled on Amazon/AliExpress as "USB to dupont," "USB to 4-pin," or "Raspberry Pi USB power cable" — or solder one yourself from a sacrificial USB cable and a 4-pin dupont housing.
- A **3.3 V USB-UART adapter** (FTDI FT232, CP2102, CH340 — anything 3.3 V logic) wired to J20. This gives you the serial console where U-Boot runs. You'll see SoC boot messages here and you'll be typing your `usb reset` / `fatload` / `source` commands into this terminal — **UART is required** for this tutorial, not optional.
- **Two USB flash drives** with different roles:
  - **Stick A — "scripts stick":** FAT32 formatted, ≥ 64 MB. Holds only `backup_cc2.scr` / `restore_cc2.scr` (a few KB each). Anything pre-existing on it can stay.
  - **Stick B — "image stick":** ≥ 8 GB. Will hold the **raw eMMC image** written as a block-level dump — no filesystem. Whatever's on it now gets wiped, so use a stick you're willing to dedicate.

### Software

- `sunxi-fel` (install in §2).
- **Balena Etcher** — used for **restore (§8 only)** to write the `backup.bin` onto a USB stick. *Not* used for backup readback: Etcher's "Clone drive" feature copies one physical drive to another physical drive — it cannot save a drive to an image file. There's no drive-to-file export in Etcher. If the current release errors when flashing, fall back to [**v1.18.11**](https://github.com/balena-io/etcher/releases/tag/v1.18.11).
- **[`diskcpy.exe`](https://github.com/suchmememanyskill/diskcpy/releases)** (Windows only, for §6 backup readback) — small standalone Rust utility that dumps a raw physical drive to a file. Replaces the WSL2/usbipd/dd dance.
- (Windows only) **[Zadig](https://zadig.akeo.ie/)** — installs the WinUSB driver Windows needs to talk to the FEL device.

### Files

> **CC2-specific binaries.** The eMMC sits in **MMC slot 1** on the CC2, but in **slot 0** on the original CC1. As a result, `u-boot-sunxi-with-spl-cc2.bin`, `backup_cc2.scr`, and `restore_cc2.scr` are all built/patched for `mmc dev 1` and **will not work on a CC1**. Only `uart0-helloworld-sdboot.sunxi` is shared between the two boards. Use the CC2-tagged files in this tutorial.

Drop these next to `sunxi-fel.exe`:

- [`uart0-helloworld-sdboot.sunxi`](https://github.com/OpenCentauri/cc-fw-tools/blob/main/extra-stuff/emmc/uart0-helloworld-sdboot.sunxi) — generic; same file CC1 uses
- [`u-boot-sunxi-with-spl-cc2.bin`](https://github.com/OpenCentauri/cc-fw-tools/blob/main/extra-stuff/emmc/u-boot-sunxi-with-spl-cc2.bin) — **CC2 only** (`mmc dev 1`).

Drop these on **Stick A**:

- [`backup_cc2.scr`](https://github.com/OpenCentauri/cc-fw-tools/blob/main/extra-stuff/emmc/backup_cc2.scr) — **CC2 only** backup script (`mmc dev 1`).
- [`restore_cc2.scr`](https://github.com/OpenCentauri/cc-fw-tools/blob/main/extra-stuff/emmc/restore_cc2.scr) — **CC2 only** restore script (`mmc dev 1`).

### Headers on the mainboard

| Header | Use for | Pinout (top → bottom or as noted) |
|---|---|---|
| **J6** (next to SW2) | FEL USB | Pin 1 (closest to eMMC) = GND / D+ / D− / VCC. **D+ and D− are swapped vs USB-A** — see §3. |
| **J20** (left 1×4 near SW1) | UART console | VCC / TX / RX / GND. **Don't connect VCC.** |

---

## 2. Install tools

### Windows

1. Make a working folder: `mkdir C:\Tools\fel`.
2. Download [`sunxi-fel.exe`](https://github.com/OpenCentauri/cc-fw-tools/blob/main/extra-stuff/emmc/sunxi-fel.exe), drop in `C:\Tools\fel\`.
3. Download **Zadig** from [zadig.akeo.ie](https://zadig.akeo.ie/) and drop the `.exe` in the same folder (or anywhere — it's portable).
4. Drop the files from §1 ("Files") into `C:\Tools\fel\`.
5. Enter FEL mode (§4). Run **Zadig** → Options → List All Devices → select `1F3A EFE8` → driver **WinUSB** → **Replace Driver**.

> Commands below are written without a prefix. On Windows, use `.\sunxi-fel.exe ...` from the install folder.

### Linux

```bash
sudo apt install -y sunxi-tools                 # Debian / Ubuntu
# or: sudo dnf install -y sunxi-tools           # Fedora
# or: sudo pacman -S --needed sunxi-tools       # Arch

sudo tee /etc/udev/rules.d/77-fel.rules > /dev/null <<'EOF'
SUBSYSTEM=="usb", ATTR{idVendor}=="1f3a", ATTR{idProduct}=="efe8", MODE="0666"
EOF
sudo udevadm control --reload-rules
```

### macOS

```bash
brew install sunxi-tools
```

---

## 3. Wire J6 to USB-A

Printer powered off, unplugged.

| J6 (CC2)            | USB-A pin    | Wire (typical) |
|---------------------|--------------|----------------|
| 1 (closest to eMMC) | 4 (GND)      | black          |
| 2                   | 3 (D+)       | green          |
| 3                   | 2 (D−)       | white          |
| 4 (farthest)        | 1 (VBUS)     | red            |

> **⚠ Don't build a straight-through cable** — J6 has D+ and D− swapped vs USB-A. Follow the table.

Plug the USB-A into your PC. Don't power the printer on yet.

---

## 4. Enter FEL mode

1. Plug mains into the printer.
2. **Press and hold SW2.** While holding, **press and release SW1.** Keep SW2 held ~2 s after, then release.

PC dings; printer screen stays black.

---

## 5. Boot U-Boot

You'll use **two windows** for this section:

- A **serial terminal** connected to the printer's UART — so you can see the SoC boot, and so you can type U-Boot commands in §6 onward.
- A **regular PC shell** (PowerShell, cmd, or bash) — so you can run `sunxi-fel` commands.

Open both before running anything below. They're independent; the printer doesn't mind having UART and FEL connected at the same time.

### 5.1 Open the UART terminal

1. In **Device Manager → Ports (COM & LPT)**, find your USB-UART adapter and note the COM number (e.g. `COM5`).
2. Open **PuTTY** (or any serial terminal — `minicom`, `screen`, `tio`, Arduino Serial Monitor):
   - **Connection type:** Serial
   - **Serial line:** `COM5` (your number)
   - **Speed:** `115200`
   - Defaults under **Connection → Serial** are correct: 8 data bits, no parity, 1 stop bit, no flow control. Often written as **115200 8N1**.
3. Click **Open**. You should get a blank PuTTY window. Leave it open.

### 5.2 Open the PC shell in the sunxi-fel folder

- **Windows:** open PowerShell or cmd, `cd C:\Tools\fel` (or wherever you unzipped).
- **Linux / macOS:** open a terminal, `cd` into the folder.

### 5.3 Send hello-world (UART init)

In the PC shell:

```
sunxi-fel spl uart0-helloworld-sdboot.sunxi
```

In your PuTTY/serial window you should see:

```
Hello from Allwinner R528/T113!
Returning back to FEL.
```

If you don't see those lines, your UART wiring is wrong — fix it before going further. (See §9 troubleshooting.)

### 5.4 Load U-Boot

In the PC shell:

```
sunxi-fel uboot u-boot-sunxi-with-spl-cc2.bin
```

In your PuTTY/serial window the SPL banner scrolls past (DRAM init, board info), then U-Boot itself starts, and you land at:

```
=>
```

That `=>` is the U-Boot prompt. No key-press needed — the build has `CONFIG_BOOTDELAY=-1` so it skips autoboot. Everything in §6 (backup) and §8 (restore) is typed into the PuTTY window at this prompt.

---

## 6. Back up the eMMC

### (Recommended) Grab `ELEGOO.txt` over SSH first

If your printer is still booting normally and you have SSH access, copy `/mnt/private/ELEGOO.txt` off the printer **before** anything else. That file holds your `SN,short_code,long_key` triplet — the one piece of the eMMC that's irreplaceable if you ever need to rewrite the SN on a restored image (§8A).

Windows 10/11 ships with OpenSSH, so `scp` works in PowerShell:

```powershell
mkdir C:\OpenCentauri\backups -Force
scp root@<printer-ip>:/mnt/private/ELEGOO.txt C:\OpenCentauri\backups\ELEGOO.txt
type C:\OpenCentauri\backups\ELEGOO.txt   # sanity check — single line "F01...,xxxxxxxx,xxxxxxxx..."
```

(On Linux/macOS, same `scp` command using `mkdir -p ~/OpenCentauri/backups` and a Unix destination path.)

This 60-byte file is now safely on your PC regardless of whatever happens to the eMMC. Skipping this step is fine if you only ever plan to restore your own backup back to the same printer.

### Swap-stick dance

You'll swap two USB sticks during this section. Have both next to the printer:

- **Stick A:** FAT32 with `backup_cc2.scr` on the root.
- **Stick B:** ≥ 8 GB, empty.

At the `=>` prompt with **Stick A** plugged into the printer's front USB:

```
usb reset
usb dev 0
fatload usb 0:1 42000000 backup_cc2.scr
```

> **`usb reset` is only needed if you plug the stick in *after* U-Boot's USB scan.** If Stick A was already plugged in when U-Boot booted and you see "1 Storage Device(s) found" in the banner, skip `usb reset` and go straight to `usb dev 0`. If `usb reset` doesn't find a storage device, **unplug the stick, plug it back in, run `usb reset` again** — repeat until a storage device is reported.

Pull **Stick A**, plug in **Stick B**:

```
usb reset
usb dev 0
source 42000000
```

Wait 15–30 min. Don't interrupt. When `=>` returns, the image is on Stick B.

### Copy the image off Stick B

Stick B contains a raw eMMC image. **Balena Etcher cannot read it into a file** — Etcher's only output mode is "flash to drive." Its "Clone drive" feature does drive-to-drive copies, not drive-to-image-file exports. Use `dd` (Linux/macOS) or `diskcpy.exe` (Windows) instead.

Plug Stick B into your PC. **Click Cancel** on any "format this drive" prompt.

#### Linux / macOS

```bash
mkdir -p ~/OpenCentauri/backups && cd ~/OpenCentauri/backups
lsblk                                                # Linux: find e.g. /dev/sdg
diskutil list                                        # macOS: find e.g. /dev/disk4
sudo dd if=/dev/sdX of=backup.bin bs=4M status=progress conv=fsync
truncate -s 7837581312 backup.bin                    # trim to exact eMMC size
```

#### Windows (diskcpy)

Use `diskcpy.exe` — a small standalone utility that does a raw block-level read of a physical drive into a file.

**One-time setup:**

1. Download `diskcpy.exe` from [github.com/suchmememanyskill/diskcpy/releases](https://github.com/suchmememanyskill/diskcpy/releases) and drop it somewhere convenient (e.g. `C:\Tools\diskcpy\`).
2. Create a folder for your backups:
   ```powershell
   mkdir C:\OpenCentauri\backups
   ```

**Each backup readback:**

1. Plug Stick B into your PC. **Click Cancel** on any "format this drive" prompt.

2. In **PowerShell**, list physical drives to find the stick's `\\.\PHYSICALDRIVE#`:
   ```powershell
   Get-CimInstance Win32_DiskDrive | Select-Object DeviceID, Model, Size
   ```
   Sample output:
   ```
   DeviceID            Model                Size
   --------            -----                ----
   \\.\PHYSICALDRIVE0  Samsung SSD 980      1000204886016
   \\.\PHYSICALDRIVE4  USB Mass Storage     8053063680
   ```
   Identify your stick by `Size` (~8 GB = 8,053,063,680 bytes, ~16 GB = 16,109,371,392 bytes, etc.). **Double-check before continuing — picking the wrong DeviceID will read from the wrong drive.**

3. Run `diskcpy.exe` with the source `\\.\PHYSICALDRIVE#` and the output file:
   ```powershell
   cd C:\OpenCentauri\backups
   C:\Tools\diskcpy\diskcpy.exe \\.\PHYSICALDRIVE4 .\backup.bin
   ```
   You'll see a live progress line like `182.00 MB/7.50 GB 2.4%`. Wait for it to finish.

4. **Truncate** the file to the eMMC's exact size — otherwise the trailing bytes outside the image confuse the GPT lookup in §7. Run as a single line in PowerShell:
   ```powershell
   $f=[IO.File]::Open("C:\OpenCentauri\backups\backup.bin",'Open','ReadWrite'); $f.SetLength(7837581312); $f.Close()
   ```
   *(If you paste a multi-line version, PowerShell interprets it as one expression and errors with `Unexpected token '$f'`. Keep it on one line with `;` between statements.)*

> Name your backup with version and SN, e.g.
> `C:\OpenCentauri\backups\cc2-01.03.02.51-F01XXXXXXXXXXXXXX.bin`.

---

## 7. Verify the backup

### Size

```bash
# Linux / macOS / WSL
ls -l /mnt/c/OpenCentauri/backups/backup.bin
```

```powershell
# Windows PowerShell
Get-Item C:\OpenCentauri\backups\backup.bin | Select Length
```

Expect exactly **7,837,581,312 bytes**. Anything else = re-do §6.

### Firmware version + SN

You're looking for two things inside the `.bin`:

- `/opt/inst/firmware_version/versions.json` on **rootfsA (partition 7)** — gives you `ota_version`.
- `/ELEGOO.txt` on **partition 11 (FAT16)** — single line: `<SN>,<short>,<long>`.

#### Linux / macOS / WSL (recommended on Windows)

If you're on Windows and don't have Ubuntu in WSL yet, install it once:

```powershell
wsl --install -d Ubuntu     # reboot, follow prompts to set username
```

Then in your WSL Ubuntu terminal (or any Linux/macOS terminal):

```bash
BACKUP=/mnt/c/OpenCentauri/backups/backup.bin            # Linux/macOS: just backup.bin
LOOP=$(sudo losetup -fP --show "$BACKUP")
sudo mkdir -p /mnt/cc2

sudo mount -o ro ${LOOP}p7 /mnt/cc2                       # rootfsA (try p8 if empty)
cat /mnt/cc2/opt/inst/firmware_version/versions.json
sudo umount /mnt/cc2

sudo mount -o ro ${LOOP}p11 /mnt/cc2
cat /mnt/cc2/ELEGOO.txt
sudo umount /mnt/cc2
sudo losetup -d $LOOP
```

#### Windows GUI fallback — 7-Zip 23+

[7-Zip 23 and later](https://www.7-zip.org/) can open GPT-partitioned disk images.

1. Right-click `C:\OpenCentauri\backups\backup.bin` → **7-Zip → Open archive**.
2. You'll see a list of partitions (`0.img`, `1.img`, …). Open the 7th partition (rootfsA squashfs) — 7-Zip can also browse squashfs.
3. Navigate to `opt/inst/firmware_version/versions.json` — double-click to view in Notepad.
4. Back out, open the 11th partition (FAT16), view `ELEGOO.txt`.

---

Expect a JSON with `ota_version` (the version that shows on the printer's About screen) and a single line:

```
F01XAJI0Y6DPBHS,afqofpva,3zmf8mdd4v30t9nt3w5uzbikcidkwnnh
```

If both look real, the backup is good.

---

## 8. Restore

> **⚠️ Overwrites the printer's eMMC.** Make a fresh backup first if there's anything to lose.
>
> **⚠️ Don't interrupt the write.**

### Prep

- **Stick A:** FAT32 with `restore_cc2.scr` (same as §6 is fine).
- **Stick B:** Use Balena Etcher → **Flash from file** → `backup.bin` → target the USB stick → **Flash!** *(If the latest Etcher errors, use [v1.18.11](https://github.com/balena-io/etcher/releases/tag/v1.18.11).)*

### Run

If you're at `=>` from §6/§7, continue. Otherwise re-do §4 then §5.

With **Stick A** plugged in:

```
usb reset
usb dev 0
fatload usb 0:1 42000000 restore_cc2.scr
```

> Skip `usb reset` if the stick was already plugged in when U-Boot booted and a storage device showed in the banner. If `usb reset` finds no storage, unplug/replug and retry until it does.

Pull **Stick A**, plug in **Stick B**:

```
usb reset
usb dev 0
source 42000000
```

Wait 15–30 min.

### Boot

1. Unplug mains.
2. Remove Stick B and disconnect J6.
3. Power back on normally.

Confirm via **Settings → About / Version**; should match `ota_version` from §7.

---

## 8A. Update the SN (if you restored someone else's backup)

> Skip this section if you restored a backup from the same physical printer.

The backup carries the original machine's SN in `/mnt/private/ELEGOO.txt`. **OTA updates and basic printing still work** with a "wrong" SN — the printer doesn't gate functionality on cloud auth. What you'll see broken is the **cloud-side AI features** (spaghetti / foreign-object detection, AI camera analysis): the printer can't authenticate to Elegoo's inference servers, so you'll get error popups about failed detection. That's expected with an unmatched SN and **safe to ignore** if you don't need those features.

If you do want full functionality, overwrite `ELEGOO.txt` with your printer's real values. SSH into the printer as root:

```sh
mount -o remount,rw /mnt/private
printf '<YOUR_SN>,<YOUR_SHORT_CODE>,<YOUR_LONG_KEY>' > /mnt/private/ELEGOO.txt
cat /mnt/private/ELEGOO.txt
mount -o remount,ro /mnt/private
```

Reboot afterward.

> **All three fields must match.** The sticker on the back of the printer only has the SN; `short_code` and `long_key` live only on the eMMC. Recovery sources, in order of preference:
> 1. The standalone `ELEGOO.txt` you grabbed over SSH in §6 (recommended pre-backup step).
> 2. `cat /mnt/cc2/ELEGOO.txt` from your verified backup (§7).
> 3. Contact Elegoo support — they may be able to re-issue the triplet given the SN.

---

## 9. Troubleshooting

**"No FEL device found"** — Different USB port (no hubs). Windows: Zadig not bound to `1F3A:EFE8`. Retry SW2 + SW1.

**Hello-world prints nothing on UART** — Check 115200 8N1. Swap TX/RX. Verify GND tied. Confirm you're on J20 (left of the cluster), not the DSP header.

**`sunxi-fel uboot` returns "bulk send error -7" or "FEL device not found"** — Re-do hello-world first; the SPL hangs without UART.

**`fatload usb 0:1 ...` "no such partition"** — Run `usb part`, use the partition number it shows.

**After swapping sticks, U-Boot still sees the old one** — Run `usb reset` again after the swap.

**`source` runs but exits instantly** — You downloaded the rendered GitHub page instead of the raw `.scr` blob. Get the raw file.

**Windows offers to "format" Stick B after backup, or it shows as 0 bytes** — Expected. The stick is a raw eMMC dump with no Windows-recognizable filesystem on it. **Click Cancel.** Pull the image off with `diskcpy.exe` (§6's "Copy the image off Stick B" section).

**`diskcpy.exe` errors with "access denied" or similar** — Run PowerShell as Administrator. Raw physical-drive access requires admin.

**`Get-CimInstance` doesn't show my USB stick** — Re-plug it and wait a few seconds. If still missing, try a different USB port (avoid hubs); some sticks need direct connection.

**Etcher refuses to flash for restore — "drive too small"** — Use a 16 GB stick.

**Printer doesn't boot after restore** — Wrong-model backup (must be CC2), or truncated. Verify size = 7,837,581,312 bytes.

---

## 10. References

- **OpenCentauri** — [docs](https://docs.opencentauri.cc) · [GitHub](https://github.com/OpenCentauri) · [Discord](https://discord.gg/t6Cft3wNJ3)
- **cc-fw-tools** — [repo](https://github.com/OpenCentauri/cc-fw-tools) · [EMMC_RESTORE.md](https://github.com/OpenCentauri/cc-fw-tools/blob/main/docs/EMMC_RESTORE.md)
- **Tools** — [sunxi-tools](https://github.com/linux-sunxi/sunxi-tools) · [Zadig](https://zadig.akeo.ie) · [Balena Etcher](https://etcher.balena.io/) · [Etcher v1.18.11 (fallback)](https://github.com/balena-io/etcher/releases/tag/v1.18.11) · [`diskcpy`](https://github.com/suchmememanyskill/diskcpy/releases)
- **Direct downloads**
  - [`uart0-helloworld-sdboot.sunxi`](https://github.com/OpenCentauri/cc-fw-tools/blob/main/extra-stuff/emmc/uart0-helloworld-sdboot.sunxi)
  - [`u-boot-sunxi-with-spl-cc2.bin`](https://github.com/OpenCentauri/cc-fw-tools/blob/main/extra-stuff/emmc/u-boot-sunxi-with-spl-cc2.bin)
  - [`backup_cc2.scr`](https://github.com/OpenCentauri/cc-fw-tools/blob/main/extra-stuff/emmc/backup_cc2.scr) · [`restore_cc2.scr`](https://github.com/OpenCentauri/cc-fw-tools/blob/main/extra-stuff/emmc/restore_cc2.scr) — CC2-specific scripts (target `mmc dev 1`).
  - Reference originals (CC1/generic): [`backup.scr`](https://github.com/OpenCentauri/cc-fw-tools/blob/main/extra-stuff/emmc/backup.scr) · [`restore.scr`](https://github.com/OpenCentauri/cc-fw-tools/blob/main/extra-stuff/emmc/restore.scr)
  - [`sunxi-fel.exe`](https://github.com/OpenCentauri/cc-fw-tools/blob/main/extra-stuff/emmc/sunxi-fel.exe) (Windows binary) · [Zadig (WinUSB driver installer)](https://zadig.akeo.ie/)

# CANVAS Resume channel synchronization (1.4.49)

## Failure and fix

`M6211` maps the file's logical tool to a physical CANVAS channel. If that
channel is already active, it returns early without calling
`set_current_print_channel_id`. The saved current channel can therefore remain
stale or uninitialized. `RESUME` later reads that value and formats
`MULTICOLOR_RESUME CHANNEL_ID=%d`, potentially selecting the wrong channel.

The normal load path already calls this setter. This patch calls the same setter
on the already-loaded path, then returns through the original log/return block:

```diff
 if selected_physical_channel == active_physical_channel:
+    state.set_current_print_channel_id(selected_physical_channel)
     log("current active channel is target channel, don't need to load material.")
     return
```

This addresses stale Resume channel selection. It does not change purge
temperatures or claim to fix every cause of `MULTICOLOR RESUME ERROR`.

## Binary layout

All addresses are ARM virtual addresses; file offsets are VA minus `0x10000`.

| Location | Original | Patched |
| --- | --- | --- |
| `0x278d60` | `beq 0x2794c8` | `beq 0x4519d0` |
| `0x4519d0..0x4519e7` | 24 zero bytes | Six-instruction trampoline |

The trampoline gets the state from `[r11+0x4c]`, passes the mapped physical
channel in `r5`, calls virtual slot `0x58` (setter at `0x2adc68`), and branches to
the original already-loaded block at `0x2794c8`. This matches the normal setter
call at `0x278d9c..0x278dac`. The Resume getter is at `0x2ad588` and the command
formatter call at `0x1b6758`.

Only one branch and the reserved 24-byte cave change. The EQ condition and
normal load branch remain intact. The patch checks firmware version, app size,
SHA-256 of M6211, getter, setter and vtable, the original hook, and an empty cave
before writing. Unsupported, modified or already-patched inputs are rejected.

Verified input app SHA-256:

- Stock 1.4.49: `1a899b50fc104a38fe3f77cf4988c810da6670f3d0cc457de5d876c49fd76843`
- OpenCentauri v0.5.0: `c8a3e3a7e6e4f485cb5ea3259348778b1b3ab79b84e44631d8837404f0fff141`

The relevant handler and state-accessor bytes match in both inputs. Full-file
hashes are recorded here, rather than enforced, because other OpenCentauri
patches also modify this app.

## Reproduce and validate

Use an extracted, unmodified input app. The test never connects to a printer.

```sh
python3 -m venv /tmp/canvas-resume-test
/tmp/canvas-resume-test/bin/pip install unicorn==2.1.4
/tmp/canvas-resume-test/bin/python \
  oc-patches/cc1-app/fix-canvas-resume-channel/test-1.4.49.py /path/to/original/app

python3 oc-patches/patch_planner.py 1.4.49 --dry-run
sudo ./build.sh 1.4.49
/tmp/canvas-resume-test/bin/python \
  oc-patches/cc1-app/fix-canvas-resume-channel/test-1.4.49.py /path/to/original/app \
  --patched-app unpacked/squashfs-root/app/app
```

The ARM regression executes the real mapping branch, setter, getter and Resume
formatter. It substitutes the mapping table, active-channel record, logging,
mutexes and status helpers; it skips normal-path heater/fan preparation and
stops before physical loading. It covers all four logical tools, all four
selected channels, all four active channels, and five previous saved values
(`-1`, `0..3`): 320 combinations. It also checks register/stack preservation,
exact write scope, and eight invalid-input cases.

Expected isolated-patch output:

```text
PASS: 8 incompatible/modified/occupied/repeated inputs refused
BEFORE: reproduced 64 stale/uninitialized already-loaded channel states
PASS: 320 ARM selection/Resume cases for isolated patch
Hardware, heaters, sensor clearing and physical printing are not emulated.
```

With `--patched-app`, the same 320 cases also run against the full patch chain.
The baseline stale-state assertion is intentional: it demonstrates the failure
before checking the corrected state and Resume command.

Validation performed on 2026-11-11:

- Both recorded stock 1.4.49 and released v0.5.0 inputs passed the isolated tests.
- The complete 23-patch `patched` edition built on Ubuntu 24.04 ARM64, including
  firmware repacking and manifest generation. Its final app passed all 320
  regression cases. The rootfs was built on the container's Linux filesystem,
  preserving the stock device node.
- For this macOS-hosted build only, the bootlogo step used `mcopy` in a temporary
  copy of the patch tree instead of loop-mounting its FAT image. The resulting
  bitmap was read back and compared with the upstream source. This environment
  adjustment is not part of the patch.
- The final hook and allocated caves were disassembled. The trampoline was also
  assembled independently and compared byte-for-byte with `patch.py`.

To independently assemble the documented trampoline and inspect the final app:

```sh
arm-none-eabi-as -march=armv7-a \
  oc-patches/cc1-app/fix-canvas-resume-channel/trampoline-1.4.49.S -o /tmp/resume.o
arm-none-eabi-ld -Ttext=0x4519d0 /tmp/resume.o -o /tmp/resume.elf
arm-none-eabi-objcopy -O binary /tmp/resume.elf /tmp/resume.bin
arm-none-eabi-objdump -d --start-address=0x278d58 --stop-address=0x278db0 \
  unpacked/squashfs-root/app/app
arm-none-eabi-objdump -D --start-address=0x4519d0 --stop-address=0x4519e8 \
  unpacked/squashfs-root/app/app
```

## Hardware validation still required

No physical print, heater or CANVAS sensor behavior is established by emulation.
Before using the firmware for unattended printing, validate on a CC1 with CANVAS:

1. Start a small single-material PETG job whose selected physical channel is
   already loaded. Include a logical-to-physical mapping other than identity.
2. Pause from the printer UI, wait for standby temperature, then resume.
3. Check that `MULTICOLOR_RESUME CHANNEL_ID` names the selected physical channel,
   working temperature returns, and extrusion/printing resume normally.
4. Repeat after selecting another channel and with a job that requires an actual
   initial load, to check both the fast and normal branches.

Do not treat the stale-channel fix as proof that a separate purge-temperature or
sensor-clearing problem is resolved.

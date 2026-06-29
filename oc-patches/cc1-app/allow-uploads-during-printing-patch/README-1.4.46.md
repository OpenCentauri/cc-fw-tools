### Allow upload patch for 1.4.46

In the 1.4.46 `sdcp_v3` upload handler, patch out the error flow with the string
`"device is busy,can't upload"`.

The matching upload path block is anchored by `"/uploadFile/upload"` in the function
around `0x003698a4`. The original 1.1.40 patch NOPs two branches that jump to the
busy-upload response. The 1.4.46 port applies the same branch removals:

- `0x003698dc`: replace `beq 0x00369e74` with `mov r0, r0`
- `0x00369904`: replace `bne 0x00369e74` with `mov r0, r0`

These edits skip the busy-state rejection and allow the existing upload parsing path
to run while printing.

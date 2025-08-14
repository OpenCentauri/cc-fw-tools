# Short descriptions for config keys
declare -A help_short=(
    [OC_APP_BOOT_DELAY]="Core app boot delay (in seconds)"
)

# Long descriptions for config keys
declare -A help_long=(
    [OC_APP_BOOT_DELAY]="How long to wait until starting /app/app on boot. If non-zero, you can SSH in after boot and run 'noapp' to prevent start"
)

#!/bin/bash

CONFIG_FILE="patch_config"
HELP_FILE="./key_info.sh"
TEMP_INPUT=$(mktemp)
TEMP_CONFIG=$(mktemp)

# Load help descriptions
if ! source "$HELP_FILE"; then
    echo "Error: Could not load help text from $HELP_FILE"
    exit 1
fi

# Read config into associative array
declare -A config
while IFS='=' read -r raw_key raw_value; do
    [[ -z "$raw_key" || "$raw_key" =~ ^# ]] && continue
    key=$(echo "$raw_key" | xargs)
    value=$(echo "$raw_value" | xargs)
    config["$key"]="$value"
done < "$CONFIG_FILE"

# Edit function
edit_key() {
    local key="$1"
    local current="${config[$key]}"
    local desc="${help_short[$key]:-No description available}"
    local help="${help_long[$key]:-No additional help available.}"

    local prompt="$desc\n\n$help\n\nCurrent value: $current\n\nPress Enter to confirm."

    dialog --clear \
        --inputbox "$prompt" 18 70 "$current" 2> "$TEMP_INPUT"

    [[ $? -ne 0 ]] && return

    local input
    input=$(<"$TEMP_INPUT")
    config["$key"]="$input"
}

# Main loop
while true; do
    menu_items=()
    key_list=()
    index=1

    for key in "${!config[@]}"; do
        desc="${help_short[$key]:-No description available}"
        val="${config[$key]}"
        menu_items+=("$index" "$desc (Current: $val)")
        key_list[$index]="$key"
        ((index++))
    done

    dialog --clear \
        --title "Patch Config Editor" \
        --menu "Select a setting to edit:" \
        20 75 12 \
        "${menu_items[@]}" 2> "$TEMP_INPUT"

    [[ $? -ne 0 ]] && break

    selection=$(<"$TEMP_INPUT")
    selected_key="${key_list[$selection]}"
    edit_key "$selected_key"
done

# Save config
declare -A updated_keys
> "$TEMP_CONFIG"

while IFS= read -r line || [[ -n "$line" ]]; do
    if [[ "$line" =~ ^[[:space:]]*# ]] || [[ -z "$line" ]]; then
        echo "$line" >> "$TEMP_CONFIG"
        continue
    fi

    if [[ "$line" =~ ^[[:space:]]*([^=[:space:]]+)[[:space:]]*=[[:space:]]*(.*)$ ]]; then
        key="${BASH_REMATCH[1]}"
        if [[ -n "${config[$key]+_}" ]]; then
            if [[ -z "${updated_keys[$key]+_}" ]]; then
                echo "$key=${config[$key]}" >> "$TEMP_CONFIG"
                updated_keys[$key]=1
            else
                continue
            fi
        else
            echo "$line" >> "$TEMP_CONFIG"
        fi
    else
        echo "$line" >> "$TEMP_CONFIG"
    fi
done < "$CONFIG_FILE"

# Append any new keys
for key in "${!config[@]}"; do
    if [[ -z "${updated_keys[$key]+_}" ]]; then
        echo "$key=${config[$key]}" >> "$TEMP_CONFIG"
    fi
done

mv "$TEMP_CONFIG" "$CONFIG_FILE"
rm -f "$TEMP_INPUT"

dialog --msgbox "Configuration saved to '$CONFIG_FILE'." 6 50
clear

### Api control patch

Patched using binary ninja. Patches sub_2d6654 at offset 0x002d6654. For easier searching, the function that needs to be patch out contains the string `real_fan_speed = %d`. At the bottom of this function, the following code is present:

``` c
002d6a90        if (result)
002d6a90        {
002d6a9c            result = sub_2c60ac();
002d6a9c            
002d6aa4            if (!result)
002d6ab0                return sub_2c5ed0();
002d6a90        }
```

Patch out `if (result)`.

[Public source reference](https://github.com/elegooofficial/CentauriCarbon/blob/20a2d9b40e0005746c300766e0b526934997805e/firmware/app/e100/app_top.cpp#L697)
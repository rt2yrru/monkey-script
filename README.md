# monkey-script

## script creates and tricks 


## limit checker 

```bash
# Check kernel's swap limit
cat /proc/sys/vm/swappiness
cat /proc/swaps

# Create different sizes
truncate -s 2T test_2tb.img
truncate -s 4T test_4tb.img
truncate -s 8T test_8tb.img

# Mount each
sudo losetup /dev/loop1 test_2tb.img
sudo losetup /dev/loop2 test_4tb.img
sudo losetup /dev/loop3 test_8tb.img

sudo mkswap /dev/loop1
sudo mkswap /dev/loop2
sudo mkswap /dev/loop3

sudo swapon /dev/loop1
sudo swapon /dev/loop2
sudo swapon /dev/loop3

# Check recognized sizes
swapon --show
```

**You'll see:**
```
NAME       SIZE    USED
/dev/loop1  2T      0B    ✓ Full size
/dev/loop2  4T      0B    ✓ Full size  
/dev/loop3  4T      0B    ✗ Capped at 4TB!
```


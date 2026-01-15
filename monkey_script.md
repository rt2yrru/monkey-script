# 🐒 EVIL MONKEY SWAP - Sparse File Swap Simulator

> **A kernel stress-testing tool for exploring Linux virtual memory limits**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.6+](https://img.shields.io/badge/python-3.6+-blue.svg)](https://www.python.org/downloads/)
[![Kernel: 5.0+](https://img.shields.io/badge/kernel-5.0+-green.svg)](https://www.kernel.org/)

---

## 📋 Overview

**Evil Monkey** is a research tool that creates **sparse file-backed swap devices** to simulate systems with massive virtual memory. Originally created for exploring kernel behavior at extreme scales, it's now used for:

- 🧪 Testing software designed for high-memory environments (50TB+ VRAM)
- 🔬 Studying kernel swap subsystem limitations
- 🎓 Educational demonstrations of sparse files and virtual memory
- 🚀 Validating memory-intensive applications without expensive hardware

### What It Does

```
Creates 10 Petabyte sparse file → Mounts as loop device → Enables as swap
                ↓
        Kernel thinks it has 10PB swap space
                ↓
        Actually uses 0 bytes... until you write to it!
```

---

## ⚠️ WARNING: RESEARCH TOOL

```diff
+ ✅ SAFE: Read-only operations, testing, development
- ❌ DANGEROUS: Writing data beyond physical disk capacity
! ⚡ CRITICAL: Monitor disk usage or risk system crash!
```

**This tool is for:**
- Kernel developers and researchers
- Software engineers simulating large-scale environments
- Systems administrators stress-testing infrastructure
- Educational purposes

**Do NOT use in production without understanding the risks!**

---

## 🚀 Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/evil-monkey-swap.git
cd evil-monkey-swap

# No dependencies required (uses stdlib only)
chmod +x monkey_swap.py
```

### Basic Usage

```bash
# Activate the Monkey (creates 10PB virtual swap)
sudo python3 monkey_swap.py --evil

# Output:
# !!! 10PB VIRTUAL RAM ACTIVE !!!
# [*] Status: Kernel has accepted the Monkey Loop.
# [MONKEY ONLINE] Attached to /dev/loop0
# 
# PRESS [ENTER] TO SELF-DESTRUCT AND WIPE TRACES

# Clean up when done
sudo python3 monkey_swap.py --clean
```

---

## 📖 Detailed Usage

### Command Reference

```bash
# Create virtual swap (interactive mode)
sudo python3 monkey_swap.py --evil

# Clean up manually (if script was interrupted)
sudo python3 monkey_swap.py --clean

# Check active swap
swapon --show

# Monitor disk usage (IMPORTANT!)
watch -n 1 df -h
```

### Understanding the Output

```
[MONKEY ONLINE] Attached to /dev/loop0
--------------------------------------------------
  PRESS [ENTER] TO SELF-DESTRUCT AND WIPE TRACES  
--------------------------------------------------
```

The script waits for user input before cleanup. During this time:
- ✅ Kernel sees 10PB of available swap
- ✅ Disk usage remains at ~0 bytes
- ⚠️ Writing data will allocate real disk space
- ❌ Filling physical disk will crash the system

---

## 🔬 How It Works

### 1. Sparse File Creation

```python
with open("evil_monkey.img", "wb") as f:
    f.truncate(10 * 1024**5)  # 10 Petabytes
```

**What happens:**
- File claims 10PB size (metadata only)
- Actual disk usage: **0 bytes**
- Filesystem tracks "holes" instead of zeros

### 2. Loop Device Attachment

```bash
losetup -f --show evil_monkey.img
# Returns: /dev/loop0
```

**What happens:**
- Creates block device from file
- Kernel treats it as physical disk
- Enables swap initialization

### 3. Swap Activation

```bash
mkswap /dev/loop0      # Initialize swap structure
swapon -p 32767 /dev/loop0  # Enable with max priority
```

**What happens:**
- Kernel accepts 10PB swap space
- Priority 32767 = "Use this FIRST"
- No pre-allocation checks performed

### 4. The Illusion

```
App requests 100GB memory
         ↓
Kernel swaps to /dev/loop0
         ↓
Loop device writes to sparse file
         ↓
Filesystem allocates REAL disk space
         ↓
100GB now physically used on disk
```

---

## 🎯 Use Cases

### 1. Software Development for Large-Scale Systems

**Problem:** You need to develop software for a system with 50TB RAM, but only have a 32GB laptop.

**Solution:**
```bash
# Create 50TB virtual swap
sudo python3 monkey_swap.py --evil

# Your code can now allocate "freely"
python3 your_app.py --ram 50TB

# Test logic without crashing
# (Monitor disk usage closely!)
```

### 2. Database Stress Testing

**Scenario:** Testing PostgreSQL with 10TB dataset

```bash
# Enable large virtual swap
sudo python3 monkey_swap.py --evil

# Configure PostgreSQL
psql -c "CREATE TABLESPACE huge LOCATION '/mnt/test';"

# Test queries that assume massive RAM
# Validate index strategies at scale
```

### 3. ML Model Simulation

**Scenario:** Testing model training pipeline for 100GB+ models

```python
import numpy as np

# This would normally crash with OOM
model = np.zeros((100_000, 100_000), dtype=float32)  # ~40GB

# With monkey swap:
# - Kernel accepts allocation
# - You can test serialization logic
# - Validate checkpointing systems
```

### 4. Educational Demonstrations

**Teaching concepts:**
- Virtual memory vs physical memory
- Sparse file mechanics
- Swap subsystem behavior
- Kernel resource management

---

## 🛡️ Safety Guidelines

### ✅ DO:

```bash
# Monitor disk space continuously
watch -n 1 df -h

# Set up alerts for low disk space
df -h | awk '$5+0 > 80 {print "WARNING: Disk " $5 " full!"}'

# Test with small allocations first
# Allocate only 10% of free disk space

# Keep backup systems ready
```

### ❌ DON'T:

```bash
# DON'T write more data than physical disk space
# DON'T use in production environments
# DON'T leave running unattended
# DON'T ignore disk space warnings
```

### 🚨 Emergency Stop

```bash
# If system becomes unresponsive:

# SSH from another machine
ssh user@system

# Force swap disable
sudo swapoff -a

# Kill processes using swap
sudo pkill -9 your_app

# Clean up
sudo python3 monkey_swap.py --clean
```

---

## 📊 Kernel Limitations Discovered

### The 4TB Swap Limit

**Finding:** Linux kernel limits individual swap devices to **4TB**, regardless of claimed size.

```bash
# Test this yourself:
truncate -s 10T huge.img
losetup /dev/loop0 huge.img
mkswap /dev/loop0
swapon /dev/loop0

swapon --show
# Shows only 4TB, not 10TB!
```

**Why?** Kernel uses 32-bit page counting internally:
```
Max pages = 2^30 = 1,073,741,824
× 4KB per page = 4,398,046,511,104 bytes = 4TB
```

**Workaround:** Use multiple swap devices:

```bash
# Create 4× 4TB = 16TB total virtual swap
for i in {1..4}; do
    truncate -s 4T swap_${i}.img
    losetup /dev/loop${i} swap_${i}.img
    mkswap /dev/loop${i}
    swapon -p $((32767 - i)) /dev/loop${i}
done
```

---

## 🔧 Advanced Configuration

### Custom Swap Size

```python
# Edit monkey_swap.py
PB_10_BYTES = 5 * 1024**4  # 5TB instead of 10PB
```

### Priority Tuning

```bash
# Lower priority (use after real swap)
swapon -p 100 /dev/loop0

# Highest priority (use first)
swapon -p 32767 /dev/loop0
```

### Multiple Instances

```bash
# Run multiple monkey swaps
python3 monkey_swap.py --evil  # Terminal 1
python3 monkey_swap.py --evil  # Terminal 2 (will fail - conflict)

# Solution: Edit DEFAULT_IMG variable for unique names
```

---

## 🧪 Testing & Validation

### Verify Sparse File Behavior

```bash
# Create sparse file
truncate -s 10G test.img

# Check reported size
ls -lh test.img
# Output: 10G

# Check actual disk usage
du -h test.img
# Output: 0

# Write 1GB
dd if=/dev/urandom of=test.img bs=1M count=1000 conv=notrunc

# Check again
du -h test.img
# Output: 1.0G (only allocated space used!)
```

### Stress Test

```bash
# Enable monkey swap
sudo python3 monkey_swap.py --evil

# Allocate memory gradually
stress-ng --vm 1 --vm-bytes 10G --vm-method all -t 60s

# Monitor in another terminal
watch -n 1 'free -h && df -h'
```

---

## 🎓 Educational Resources

### Understanding Sparse Files

```bash
# Create examples
truncate -s 1G sparse.img
truncate -s 1G normal.img
dd if=/dev/zero of=normal.img bs=1M count=1024

# Compare
ls -lh sparse.img normal.img  # Both show 1GB
du -h sparse.img normal.img   # Only normal.img uses disk space!
```

### Kernel Memory Management

```bash
# View swap statistics
cat /proc/swaps

# View memory info
cat /proc/meminfo | grep -i swap

# View virtual memory settings
sysctl -a | grep vm.swap
```

---

## 🐛 Troubleshooting

### Issue: "Operation not permitted"

```bash
# Solution: Run with sudo
sudo python3 monkey_swap.py --evil
```

### Issue: "Device busy" when cleaning

```bash
# Check what's using the loop device
lsof /dev/loop0

# Force disable swap
sudo swapoff /dev/loop0

# Force detach loop
sudo losetup -d /dev/loop0

# Remove file
rm evil_monkey.img
```

### Issue: System freezes

```bash
# Prevention: Set disk space alerts
df -h | awk '$5+0 > 90 {system("notify-send \"DISK FULL\"")}'

# Recovery: Boot from USB, mount partition, clean up
```

### Issue: "No loop devices available"

```bash
# Load loop module
sudo modprobe loop

# Increase max loop devices
sudo modprobe loop max_loop=16
```

---

## 🔬 Technical Details

### File Structure

```
evil-monkey-swap/
├── monkey_swap.py          # Main script
├── README.md               # This file
├── LICENSE                 # MIT License
└── examples/
    ├── multi_swap.sh       # Multiple swap devices
    └── stress_test.sh      # Automated testing
```

### Requirements

- **OS:** Linux (kernel 5.0+)
- **Python:** 3.6+
- **Privileges:** root/sudo access
- **Tools:** `losetup`, `mkswap`, `swapon` (standard on most distros)

### Supported Filesystems

| Filesystem | Sparse Files | Recommended |
|------------|--------------|-------------|
| ext4       | ✅ Yes       | ✅ Best     |
| XFS        | ✅ Yes       | ✅ Good     |
| Btrfs      | ✅ Yes       | ⚠️ Careful  |
| ZFS        | ✅ Yes       | ✅ Excellent|
| FAT32      | ❌ No        | ❌ Avoid    |
| NTFS       | ⚠️ Partial   | ⚠️ Use ext4 |

---

## 📚 Related Projects

- **[NitroZen Relay](link)** - FUSE-based caching layer (companion project)
- **[zram-config](https://github.com/foundObjects/zram-swap)** - Compressed RAM swap
- **[earlyoom](https://github.com/rfjakob/earlyoom)** - OOM prevention daemon

---

## 🤝 Contributing

Contributions welcome! Areas of interest:

- [ ] Automated safety checks (disk space monitoring)
- [ ] Support for multiple swap files
- [ ] Benchmark suite for different kernel versions
- [ ] Integration with systemd
- [ ] GUI for monitoring

```bash
# Fork the repo
git checkout -b feature/your-feature
git commit -am "Add feature"
git push origin feature/your-feature
# Open Pull Request
```

---

## 📄 License

```
MIT License

Copyright (c) 2024

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software...
```

See [LICENSE](LICENSE) file for full text.

---

## ⚖️ Disclaimer

```
THIS SOFTWARE IS PROVIDED FOR EDUCATIONAL AND RESEARCH PURPOSES ONLY.

The authors are NOT responsible for:
- Data loss from disk space exhaustion
- System crashes or instability
- Any damages resulting from misuse
- Use in production environments

By using this tool, you acknowledge:
- You understand the risks involved
- You will monitor disk usage actively
- You accept full responsibility for consequences
- This is experimental research software
```

---

## 📞 Support & Contact

- **Issues:** [GitHub Issues](https://github.com/rt2yrru/evil-monkey-swap/issues)
- **Discussions:** [GitHub Discussions](https://github.com/rt2yrru/evil-monkey-swap/discussions)

---

## 🎯 Roadmap

### Version 2.0 (Planned)

- [ ] Real-time disk space monitoring
- [ ] Automatic safety limits
- [ ] Multi-swap orchestration
- [ ] Performance benchmarking suite
- [ ] Systemd integration
- [ ] Web dashboard for monitoring

### Version 3.0 (Future)

- [ ] Kernel patch for >4TB swap
- [ ] Integration with cgroup limits
- [ ] Cloud provider support (AWS, GCP)
- [ ] Distributed swap across nodes

---

## 🙏 Acknowledgments

- Linux kernel memory management team
- Sparse file pioneers
- Systems research community
- All contributors and testers

---

## 📖 Further Reading

- [Linux Kernel Memory Management](https://www.kernel.org/doc/html/latest/admin-guide/mm/index.html)
- [Understanding Sparse Files](https://wiki.archlinux.org/title/Sparse_file)
- [Swap Management in Linux](https://www.kernel.org/doc/html/latest/admin-guide/mm/swap.html)
- [Virtual Memory Concepts](https://www.kernel.org/doc/gorman/html/understand/understand.html)

---

<div align="center">

**Made with 🐒 for kernel explorers**

*"The best way to understand a system is to push it to its limits"*

[⬆ Back to Top](#-evil-monkey-swap---sparse-file-swap-simulator)

</div>

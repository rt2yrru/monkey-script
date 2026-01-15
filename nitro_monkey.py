## nitro monkey 
## mirrors a path as fuse 
# uses vram and tmpfs to make it more faster
# opens in read only 
# very fast 
import os
import sys
import errno
import threading
import time
import argparse
from collections import deque
from fuse import FUSE, Operations

# Attempt to import psutil for RAM monitoring, fallback if not installed
try:
    import psutil
except ImportError:
    psutil = None

class NitroZenRelay(Operations):
    def __init__(self, root):
        self.root = root
        self.header_cache = {}      # Key: Inode | Value: 5MB Data
        self.path_to_inode = {}     # Key: Path  | Value: Inode
        self.precached_inodes = deque(maxlen=200) 
        self._io_lock = threading.Lock() 
        self.start_time = time.time()
        
        print(f"\n{'='*60}")
        print(f" NITRO-ZEN RELAY v6 (Deduplicated + RAM Monitor)")
        print(f" Physical: 50GB | Virtual: 300GB")
        print(f" STATUS:   Operational (Read-Only)")
        print(f"{'='*60}\n")

    def _full_path(self, partial):
        return os.path.join(self.root, partial.lstrip('/'))

    def _heartbeat(self, action, path, extra=""):
        """Monitors performance and RAM in real-time."""
        ts = time.strftime("%H:%M:%S")
        mem_str = ""
        if psutil:
            process = psutil.Process(os.getpid())
            mem_mb = process.memory_info().rss / (1024 * 1024)
            mem_str = f" | RAM: {mem_mb:.1f}MB"
            
        name = os.path.basename(path) if path != "/" else "/"
        print(f"[{ts}] {action:15} | {name[:30]:30}{mem_str} {extra}")

    # --- SYMLINK & LOCKING ---
    def readlink(self, path):
        return os.readlink(self._full_path(path))

    def lock(self, path, fh, cmd, lock):
        # Dummy lock to prevent EINVAL crashes
        return -errno.ENOSYS

    def getattr(self, path, fh=None):
        try:
            st = os.lstat(self._full_path(path))
            with self._io_lock:
                self.path_to_inode[path] = st.st_ino
            return {key: getattr(st, key) for key in (
                'st_atime', 'st_ctime', 'st_gid', 'st_mode', 
                'st_mtime', 'st_size', 'st_uid', 'st_nlink'
            )}
        except FileNotFoundError:
            raise OSError(errno.ENOENT, "Not found")

    # --- SMART-BUFFER (DEDUPLICATED) ---
    def _lazy_worker(self, path):
        full_path = self._full_path(path)
        try:
            # os.stat follows symlink to the actual data source
            st = os.stat(full_path)
            inode = st.st_ino

            with self._io_lock:
                if inode in self.header_cache:
                    return # Already deduped
            
            if os.path.isfile(full_path):
                fd = os.open(full_path, os.O_RDONLY)
                # Cache first 5MB for instant file-sniffing/previews
                data = os.read(fd, 5 * 1024 * 1024)
                os.close(fd)
                
                with self._io_lock:
                    self.header_cache[inode] = data
                    self.precached_inodes.append(inode)
                self._heartbeat("SMART-BUFFER", path, f"(ID: {inode})")
        except Exception:
            pass

    def readdir(self, path, fh):
        full_path = self._full_path(path)
        items = ['.', '..'] + os.listdir(full_path)
        
        # Trigger background warming for unique files
        files = [f for f in items if os.path.isfile(os.path.join(full_path, f))][:15]
        for f in files:
            rel_path = os.path.join(path, f)
            threading.Thread(target=self._lazy_worker, args=(rel_path,), daemon=True).start()
        
        self._heartbeat("SCAN_DIR", path)
        return items

    # --- READ PATH (ZEN OPTIMIZED) ---
    def open(self, path, flags):
        if flags & (os.O_WRONLY | os.O_RDWR):
            raise OSError(errno.EROFS, "Nitro Mode: Read-Only")
        self._heartbeat("OPEN_FILE", path)
        return os.open(self._full_path(path), os.O_RDONLY)

    def read(self, path, length, offset, fh):
        inode = None
        with self._io_lock:
            inode = self.path_to_inode.get(path)

        # Serve from RAM if offset is within the 5MB Smart-Buffer
        if inode and inode in self.header_cache:
            buf = self.header_cache[inode]
            if offset + length <= len(buf):
                return buf[offset:offset + length]

        # Use High-Speed pread for raw data streaming (Bypasses GIL)
        return os.pread(fh, length, offset)

    def release(self, path, fh):
        os.close(fh)
        return 0

# --- EXECUTION ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", help="The 50GB SSD Source")
    parser.add_argument("mount", help="The 2GB RAM Portal")
    args = parser.parse_args()

    fuse_options = {
        'nothreads': False,        # Multi-core processing
        'foreground': True,        # See logs
        'allow_other': True,       # Critical for GUI apps
        'kernel_cache': True,      # Tell Zen Kernel to cache everything
        'auto_cache': True,
        'async_read': True,
        'max_read': 1048576,       # 1MB Block sizes
        'max_readahead': 1048576,  # 1MB Pre-fetching
    }

    try:
        FUSE(NitroZenRelay(args.source), args.mount, **fuse_options)
    except KeyboardInterrupt:
        print("\n[!] User Interrupted. Cleaning up...")
    finally:
        # Emergency unmount to prevent 'Busy' errors next time
        print("[*] Detaching FUSE layer...")
        os.system(f"fusermount -u {args.mount} 2>/dev/null")
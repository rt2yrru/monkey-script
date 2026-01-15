#!/usr/bin/env python3
import os
import sys
import errno
import threading
import time
import lz4.block
import psutil
import argparse
from collections import OrderedDict
from fuse import FUSE, Operations

class NitroMonkeyV12(Operations):
    def __init__(self, root, pool_size_gb=4.0):
        self.root = os.path.realpath(root)
        self.header_cache = OrderedDict()  # Inode: (compressed_data, is_squeezed, orig_size)
        self.path_to_inode = {}
        self._io_lock = threading.Lock()
        
        # Performance Settings
        self.POOL_LIMIT = int(pool_size_gb * 1024**3)
        self.current_usage = 0
        self.last_dir = None
        
        print(f"\n{'='*60}")
        print(f" NITRO-ZEN MONKEY v12.1: KERNEL-OPTIMIZED")
        print(f" Source: {self.root}")
        print(f" Pool:   {pool_size_gb}GB Global RAM Reservoir")
        print(f" Threads: Multi-Threaded I/O Enabled")
        print(f"{'='*60}\n")

    def _full_path(self, partial):
        return os.path.join(self.root, partial.lstrip('/'))

    def _heartbeat(self, action, path, extra=""):
        ts = time.strftime("%H:%M:%S")
        usage_pct = (self.current_usage / self.POOL_LIMIT) * 100
        name = os.path.basename(path)[:20]
        print(f"[{ts}] {action:12} | {name:20} | Pool: {usage_pct:5.1f}% {extra}")

    # --- THE INTELLIGENT SQUEEZE ---
    def _lazy_worker(self, path):
        full_path = self._full_path(path)
        if not os.path.isfile(full_path): return

        try:
            st = os.stat(full_path)
            inode = st.st_ino
            
            with self._io_lock:
                if inode in self.header_cache:
                    self.header_cache.move_to_end(inode)
                    return

            # Read 500MB chunk for the RAM pool
            read_size = min(st.st_size, 500 * 1024 * 1024)
            with open(full_path, 'rb') as f:
                raw_data = f.read(read_size)

            # Selective Compression (LZ4)
            sample = raw_data[:1024*1024]
            compressed_sample = lz4.block.compress(sample, store_size=False)
            
            if len(compressed_sample) < (len(sample) * 0.90):
                final_data = lz4.block.compress(raw_data, store_size=False)
                mode = "SQUEEZED"
                is_sqz = True
            else:
                final_data = raw_data
                mode = "RAW"
                is_sqz = False

            # Thread-safe Pool Eviction
            with self._io_lock:
                while (self.current_usage + len(final_data)) > self.POOL_LIMIT and self.header_cache:
                    _, (old_data, _, _) = self.header_cache.popitem(last=False)
                    self.current_usage -= len(old_data)

                self.header_cache[inode] = (final_data, is_sqz, read_size)
                self.current_usage += len(final_data)
            
            self._heartbeat("POOL-FILL", path, f"[{mode}]")
        except Exception:
            pass

    # --- MIRROR LOGIC (PREDICTIVE PRE-WARMING) ---
    def _mirror_human(self, path):
        """Monitors folder entry to pre-load next files."""
        current_dir = os.path.dirname(path)
        if current_dir != self.last_dir:
            self.last_dir = current_dir
            try:
                full_dir = self._full_path(current_dir)
                items = sorted([f for f in os.listdir(full_dir) 
                               if os.path.isfile(os.path.join(full_dir, f))])[:5]
                for item in items:
                    t = threading.Thread(target=self._lazy_worker, 
                                         args=(os.path.join(current_dir, item),), 
                                         daemon=True)
                    t.start()
            except Exception: pass

    # --- CORE FUSE OPERATIONS (OPTIMIZED) ---
    def getattr(self, path, fh=None):
        full_path = self._full_path(path)
        try:
            st = os.lstat(full_path)
            # Metadata trigger for mirroring
            self._mirror_human(path)
            with self._io_lock:
                self.path_to_inode[path] = st.st_ino
            return {key: getattr(st, key) for key in ('st_atime', 'st_ctime', 'st_gid', 
                    'st_mode', 'st_mtime', 'st_size', 'st_uid', 'st_nlink')}
        except FileNotFoundError:
            raise OSError(errno.ENOENT, "Not found")

    def readdir(self, path, fh):
        return ['.', '..'] + os.listdir(self._full_path(path))

    def readlink(self, path):
        return os.readlink(self._full_path(path))

    def open(self, path, flags):
        # Enforce read-only for nitro stability
        if flags & (os.O_WRONLY | os.O_RDWR):
            raise OSError(errno.EROFS, "Nitro Monkey is Read-Only")
        return os.open(self._full_path(path), os.O_RDONLY)

    def read(self, path, length, offset, fh):
        # 1. Try to serve from the Monkey's RAM pool
        with self._io_lock:
            inode = self.path_to_inode.get(path)
            if inode and inode in self.header_cache:
                self.header_cache.move_to_end(inode)
                data, is_sqz, orig_size = self.header_cache[inode]
                
                # Instant Unsqueeze
                buf = lz4.block.decompress(data, uncompressed_size=orig_size) if is_sqz else data
                
                if offset + length <= len(buf):
                    return buf[offset:offset + length]
        
        # 2. Trigger worker if missing from pool
        if offset == 0:
            threading.Thread(target=self._lazy_worker, args=(path,), daemon=True).start()

        # 3. Fallback to direct disk read
        return os.pread(fh, length, offset)

    def release(self, path, fh):
        os.close(fh)
        return 0

# --- THE NITRO BOOTLOADER ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Nitro-Zen Monkey v12.1")
    parser.add_argument("source", help="Physical source folder")
    parser.add_argument("mount", help="Virtual RAM portal")
    parser.add_argument("--pool", type=float, default=4.0, help="RAM pool size in GB")
    args = parser.parse_args()

    if not os.path.exists(args.mount):
        os.makedirs(args.mount)

    # Use high-performance FUSE flags
    fuse_opts = {
        'foreground': True,
        'allow_other': True,
        'kernel_cache': True,    # CRITICAL: Kernel keeps data in Page Cache
        'entry_timeout': 300,    # Cache file names (5 mins)
        'attr_timeout': 300,     # Cache attributes (5 mins)
        'nothreads': False,      # Enable multi-threaded access
        'big_writes': True
    }

    print(f"[*] Attaching Monkey...")
    try:
        FUSE(NitroMonkeyV12(args.source, args.pool), args.mount, **fuse_opts)
    except Exception as e:
        print(f"\n[!] Detaching: {e}")
        os.system(f"fusermount -u {args.mount} 2>/dev/null")

## nitro monkey -7 
## mirrors a path as fuse 
# uses vram and tmpfs to make it more faster
# opens in read only 
# very fast 

## virtual disk - created 
## shallow copy - mode 

## virtual overlay mode 

## creating new directory , sub direcotry , moving files is permitted inside the portal 
## wont actually create any direcotry or sub direcotry in the actual 

##  deletion is allowed 
## files will be soft marked as removed , but wont actually delete any file 

## any modification is destroyed as soon the program is closed 

## think as a virtual file system or sand boxed enviroment or chroot jailed 

## safe playground - any changes made here is not reflected back to the source 


## nitro playground : activated 
import os
import sys
import errno
import threading
import time
import argparse
from collections import deque
from fuse import FUSE, Operations

try:
    import psutil
except ImportError:
    psutil = None

# --- UI COLORS ---
class Color:
    BLUE = '\033[94m'      # Loading
    PURPLE = '\033[95m'    # Loaded / Cached
    GREEN = '\033[92m'     # Served
    RED = '\033[91m'       # Error
    MAROON = '\033[31m'    # Cleared & Destroyed (Virtual)
    ORANGE = '\033[33m'    # Status/Movement
    RESET = '\033[0m'

class NitroZenRelay(Operations):
    def __init__(self, root):
        self.root = root
        self.header_cache = {}      
        self.path_to_inode = {}     
        self._io_lock = threading.Lock() 
        
        # Virtual Sandbox Layer
        self.virtual_deleted = set()    # Blacklisted paths
        self.virtual_dirs = set()       # RAM-only folders
        self.virtual_moved = {}         # New Path -> Original SSD Path
        
        print(f"\n{Color.ORANGE}{'='*60}")
        print(f" NITRO-ZEN RELAY v10 (Pure Virtual Sandbox)")
        print(f" NO ORIGINAL FILES WILL BE TOUCHED")
        print(f" STATUS:   Virtual Environment Active")
        print(f" MODE : NITRO virtual playground - remove , move , delete , create direcotry, sub -direcotry without deleting or changing the original source")
        print(f"{'='*60}{Color.RESET}\n")

    def _full_path(self, partial):
        """Maps virtual portal paths back to the real SSD source."""
        if partial in self.virtual_moved:
            return self.virtual_moved[partial]
        return os.path.join(self.root, partial.lstrip('/'))

    def _heartbeat(self, action, path, color=Color.ORANGE, extra=""):
        ts = time.strftime("%H:%M:%S")
        mem_mb = psutil.Process(os.getpid()).memory_info().rss / 1048576 if psutil else 0
        name = os.path.basename(path) if path != "/" else "/"
        print(f"[{ts}] {color}{action:20}{Color.RESET} | {color}{name[:30]:30}{Color.RESET} | {mem_mb:.1f}MB {extra}")

    # --- VIRTUAL DIRECTORY LOGIC ---
    def mkdir(self, path, mode):
        """Allows creating folders in the Nitro environment."""
        self.virtual_dirs.add(path)
        self._heartbeat("DIR CREATED", path, color=Color.ORANGE, extra="(RAM-ONLY)")
        return 0

    def create(self, path, mode, fi=None):
        """Blocks actual file creation."""
        self._heartbeat("CREATION DENIED", path, color=Color.RED)
        raise OSError(errno.EROFS, "Nitro Mode: No File Creation Allowed")

    # --- VIRTUAL MOVEMENT & DELETION ---
    def rename(self, old, new):
        """Allows moving files/folders inside the portal."""
        # Determine the true physical source of what we are moving
        phys_source = self._full_path(old)
        self.virtual_moved[new] = phys_source
        self.virtual_deleted.add(old)
        self._heartbeat("MOVED", f"{old} -> {new}", color=Color.ORANGE)
        return 0

    def unlink(self, path):
        """Virtual deletion: File remains on SSD, disappears from Portal."""
        self.virtual_deleted.add(path)
        self._heartbeat("CLEARED & DESTROYED", path, color=Color.MAROON, extra="(VIRTUAL)")
        return 0

    def rmdir(self, path):
        """Virtual folder removal."""
        self.virtual_deleted.add(path)
        if path in self.virtual_dirs:
            self.virtual_dirs.remove(path)
        self._heartbeat("CLEARED & DESTROYED", path, color=Color.MAROON, extra="(DIR)")
        return 0

    # --- READ LOGIC ---
    def getattr(self, path, fh=None):
        if path in self.virtual_deleted and path not in self.virtual_moved:
            raise OSError(errno.ENOENT, "Not found")
        
        if path in self.virtual_dirs:
            return dict(st_mode=(0o40755), st_nlink=2, st_size=4096, 
                        st_ctime=time.time(), st_mtime=time.time(), st_atime=time.time())

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

    def readdir(self, path, fh):
        items = ['.', '..']
        
        # 1. Add physical items from SSD if path isn't a virtual-only folder
        if path not in self.virtual_dirs:
            full_path = self._full_path(path)
            if os.path.exists(full_path):
                items += os.listdir(full_path)
        
        # 2. Add virtual folders that belong here
        for vdir in self.virtual_dirs:
            if os.path.dirname(vdir) == path:
                items.append(os.path.basename(vdir))
        
        # 3. Add virtually moved items that belong here
        for vmove in self.virtual_moved:
            if os.path.dirname(vmove) == path:
                items.append(os.path.basename(vmove))

        # 4. Filter out everything that was virtually deleted
        unique_items = list(set(items))
        final_items = [i for i in unique_items if os.path.join(path, i) not in self.virtual_deleted or os.path.join(path, i) in self.virtual_moved]
        
        # Background Warming
        for i in final_items[:15]:
            if i not in ['.', '..']:
                threading.Thread(target=self._lazy_worker, args=(os.path.join(path, i),), daemon=True).start()

        self._heartbeat("SCAN_DIR", path, color=Color.ORANGE)
        return final_items

    def _lazy_worker(self, path):
        if path in self.virtual_deleted and path not in self.virtual_moved: return
        full_path = self._full_path(path)
        try:
            if os.path.isfile(full_path):
                self._heartbeat("LOADING", path, color=Color.BLUE)
                st = os.stat(full_path)
                inode = st.st_ino
                with self._io_lock:
                    if inode in self.header_cache:
                        self._heartbeat("LOADED", path, color=Color.PURPLE, extra="(CACHE)")
                        return 
                    fd = os.open(full_path, os.O_RDONLY)
                    self.header_cache[inode] = os.read(fd, 5 * 1024 * 1024)
                    os.close(fd)
                self._heartbeat("LOADED", path, color=Color.PURPLE)
        except: pass

    def open(self, path, flags):
        # Block any write flags
        if flags & (os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT):
            self._heartbeat("DENIED WRITE", path, color=Color.RED)
            raise OSError(errno.EROFS, "Nitro Mode: Read/Move/Destroy Only")
        self._heartbeat("SERVED", path, color=Color.GREEN)
        return os.open(self._full_path(path), os.O_RDONLY)

    def read(self, path, length, offset, fh):
        inode = self.path_to_inode.get(path)
        if inode in self.header_cache:
            buf = self.header_cache[inode]
            if offset + length <= len(buf):
                self._heartbeat("SERVED (RAM)", path, color=Color.GREEN)
                return buf[offset:offset + length]
        return os.pread(fh, length, offset)

    def release(self, path, fh):
        os.close(fh)
        return 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("mount")
    args = parser.parse_args()
    try:
        FUSE(NitroZenRelay(args.source), args.mount, nothreads=False, foreground=True, allow_other=True)
    except KeyboardInterrupt:
        pass
    finally:
        os.system(f"fusermount -u {args.mount} 2>/dev/null")

import os
import sys
import subprocess
import argparse
import time

# --- CONFIG ---
PB_10_BYTES = 10 * 1024**5  
DEFAULT_IMG = "evil_monkey.img"

def evil_monkey():
    print("!!! 10PB VIRTUAL RAM ACTIVE !!!")
    print("[*] Status: Kernel has accepted the Monkey Loop.")
    print("[!] DANGER: Do not fill your actual RAM, or the system will panic.")
    
    loop_dev = None
    try:
        # 1. Create and Secure the file
        with open(DEFAULT_IMG, "wb") as f:
            f.truncate(PB_10_BYTES)
        os.chmod(DEFAULT_IMG, 0o600)

        # 2. Attach Loop Device
        res = subprocess.run(["sudo", "losetup", "-f", "--show", DEFAULT_IMG], 
                              capture_output=True, text=True, check=True)
        loop_dev = res.stdout.strip()
        
        # 3. Swap Initialization
        subprocess.run(["sudo", "mkswap", loop_dev], check=True, capture_output=True)
        subprocess.run(["sudo", "swapon", "-p", "32767", loop_dev], check=True) # Max priority
        
        print(f"\n[MONKEY ONLINE] Attached to {loop_dev}")
        print("--------------------------------------------------")
        print("  PRESS [ENTER] TO SELF-DESTRUCT AND WIPE TRACES  ")
        print("--------------------------------------------------")
        
        input() # Wait for user to trigger destruction
        
    except KeyboardInterrupt:
        print("\n[*] Manual Interruption detected...")
    finally:
        cleanup(loop_dev)

def cleanup(specific_dev=None):
    print("\n[*] INITIATING SELF-DESTRUCT...")
    try:
        # If we don't know the dev, try to find it via the image name
        if not specific_dev:
            res = subprocess.run(["losetup", "-j", DEFAULT_IMG], capture_output=True, text=True)
            if res.stdout:
                specific_dev = res.stdout.split(":")[0]

        if specific_dev:
            print(f"[*] Deactivating Swap on {specific_dev}...")
            subprocess.run(["sudo", "swapoff", specific_dev], stderr=subprocess.DEVNULL)
            print(f"[*] Detaching Loop Device {specific_dev}...")
            subprocess.run(["sudo", "losetup", "-d", specific_dev], stderr=subprocess.DEVNULL)
        
        if os.path.exists(DEFAULT_IMG):
            print(f"[*] Shredding {DEFAULT_IMG}...")
            os.remove(DEFAULT_IMG)
            
        print("[+] EVIL MONKEY HAS VANISHED. SYSTEM CLEAN.")
    except Exception as e:
        print(f"[-] Cleanup Error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--evil", action="store_true")
    parser.add_argument("--clean", action="store_true")
    args = parser.parse_args()

    if args.clean:
        cleanup()
    elif args.evil:
        evil_monkey()
    else:
        print("[*] Run with --evil to start or --clean to wipe.")
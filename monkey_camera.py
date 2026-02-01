import os
import subprocess
import platform
import getpass
import glob
import distro
import json

class FakeCamera:
    def __init__(self, scan_directory):
        self.username = getpass.getuser()
        # Local Binary Paths
        self.__ffmpeg_path = f'/home/{self.username}/ffmpeg/bin/ffmpeg'
        self.__ffprobe_path = f'/home/{self.username}/ffmpeg/bin/ffprobe'
        
        # Fallback to system binaries if local not found
        if not os.path.exists(self.__ffmpeg_path):
            self.__ffmpeg_path = 'ffmpeg'
        if not os.path.exists(self.__ffprobe_path):
            self.__ffprobe_path = 'ffprobe'
        
        self._dir = scan_directory
        self.results = []
        self.virtual_device = '/dev/video10'
        
        # Video quality settings - MAXIMUM QUALITY
        self.output_width = None  # Will auto-detect from source
        self.output_height = None
        self.output_fps = None
        self.pixel_format = 'yuyv422'  # Higher quality than yuv420p
        self.use_native_resolution = True
        
        # Check OS and distro
        self.os_check()
        
    def os_check(self):
        """Check if running on Linux"""
        system = platform.system()
        if system == 'Linux':
            print(f"✓ Running on Linux")
            self.distro_check()
        else:
            raise OSError(f"This script only supports Linux. You're running: {system}")
    
    def distro_check(self):
        """Check Linux distribution"""
        try:
            distro_name = distro.name()
            distro_version = distro.version()
            print(f"✓ Detected: {distro_name} {distro_version}")
            
            if 'arch' in distro_name.lower():
                print("✓ Arch Linux detected - Good choice!")
                self.check_dependencies_arch()
            else:
                print(f"⚠ Warning: Detected {distro_name}, but optimized for Arch")
                self.check_dependencies_generic()
        except Exception as e:
            print(f"⚠ Could not detect distro: {e}")
            self.check_dependencies_generic()
    
    def check_dependencies_arch(self):
        """Check and suggest installation of dependencies for Arch"""
        print("\n=== Checking Dependencies ===")
        
        # Check v4l2loopback
        v4l2_check = subprocess.run(['lsmod'], capture_output=True, text=True)
        if 'v4l2loopback' not in v4l2_check.stdout:
            print("✗ v4l2loopback not loaded")
            print("  Install: sudo pacman -S v4l2loopback-dkms")
            print("  Load with HIGH QUALITY settings:")
            print("  sudo modprobe v4l2loopback devices=1 video_nr=10 card_label='FakeCam' exclusive_caps=1 max_buffers=2 max_width=3840 max_height=2160")
        else:
            print("✓ v4l2loopback loaded")
            print("  ⚠ Make sure it's loaded with max_width and max_height!")
        
        # Check ffmpeg
        try:
            result = subprocess.run([self.__ffmpeg_path, '-version'], 
                         capture_output=True, check=True, text=True)
            print(f"✓ ffmpeg found at {self.__ffmpeg_path}")
            # Check for important codecs
            if 'libx264' in result.stdout:
                print("  ✓ libx264 available")
        except:
            print("✗ ffmpeg not found")
            print("  Install: sudo pacman -S ffmpeg")
        
        # Check ffprobe
        try:
            subprocess.run([self.__ffprobe_path, '-version'], 
                         capture_output=True, check=True)
            print(f"✓ ffprobe found at {self.__ffprobe_path}")
        except:
            print("✗ ffprobe not found")
            print("  Install: sudo pacman -S ffmpeg")
        
        # Check virtual device
        if os.path.exists(self.virtual_device):
            print(f"✓ Virtual device {self.virtual_device} exists")
            # Check device capabilities
            try:
                caps = subprocess.run(['v4l2-ctl', '--device', self.virtual_device, '--list-formats-ext'],
                                    capture_output=True, text=True)
                print(f"  Device capabilities:\n{caps.stdout[:200]}...")
            except:
                pass
        else:
            print(f"✗ Virtual device {self.virtual_device} not found")
            print("  Run: sudo modprobe v4l2loopback devices=1 video_nr=10 card_label='FakeCam' exclusive_caps=1 max_buffers=2 max_width=3840 max_height=2160")
    
    def check_dependencies_generic(self):
        """Generic dependency check for other Linux distros"""
        print("\n=== Checking Dependencies ===")
        print("Please ensure you have:")
        print("  - v4l2loopback-dkms")
        print("  - ffmpeg")
        print("  - ffprobe")
        print("  - v4l2-ctl (v4l-utils)")
    
    def scan_media_files(self):
        """Scan directory for video and image files"""
        print(f"\n=== Scanning: {self._dir} ===")
        
        video_extensions = ['*.mp4', '*.avi', '*.mkv', '*.mov', '*.webm', '*.flv', '*.wmv', '*.MP4', '*.AVI', '*.MKV']
        image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.gif', '*.JPG', '*.JPEG', '*.PNG']
        
        all_files = []
        
        for ext in video_extensions + image_extensions:
            pattern = os.path.join(self._dir, ext)
            files = glob.glob(pattern)
            all_files.extend(files)
        
        # Sort files
        all_files.sort()
        self.results = all_files
        
        print(f"✓ Found {len(self.results)} media file(s)")
        for idx, file in enumerate(self.results, 1):
            print(f"  {idx}. {os.path.basename(file)}")
        
        return self.results
    
    def get_video_info(self, video_file):
        """Get video information using ffprobe and return as dict"""
        cmd = [
            self.__ffprobe_path,
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            video_file
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            
            # Extract video stream info
            video_stream = None
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'video':
                    video_stream = stream
                    break
            
            if video_stream:
                width = video_stream.get('width')
                height = video_stream.get('height')
                fps_str = video_stream.get('r_frame_rate', '30/1')
                
                # Calculate FPS
                if '/' in fps_str:
                    num, den = fps_str.split('/')
                    fps = int(num) / int(den)
                else:
                    fps = float(fps_str)
                
                print(f"✓ Video: {os.path.basename(video_file)}")
                print(f"  Resolution: {width}x{height}")
                print(f"  FPS: {fps:.2f}")
                print(f"  Codec: {video_stream.get('codec_name')}")
                print(f"  Pixel Format: {video_stream.get('pix_fmt')}")
                
                return {
                    'width': width,
                    'height': height,
                    'fps': fps,
                    'codec': video_stream.get('codec_name'),
                    'pix_fmt': video_stream.get('pix_fmt')
                }
            
        except Exception as e:
            print(f"✗ Error getting video info: {e}")
        
        return None
    
    def set_quality(self, width=None, height=None, fps=None, native=True):
        """Set output quality parameters"""
        self.use_native_resolution = native
        if not native:
            self.output_width = width or 1920
            self.output_height = height or 1080
            self.output_fps = fps or 30
            print(f"✓ Quality set to: {self.output_width}x{self.output_height} @ {self.output_fps}fps")
        else:
            print(f"✓ Using NATIVE resolution from source (no scaling = best quality)")
    
    def get_quality_ffmpeg_params(self, source_file=None):
        """Get ffmpeg parameters for MAXIMUM quality output"""
        params = []
        
        # Get source video info if using native resolution
        if self.use_native_resolution and source_file:
            info = self.get_video_info(source_file)
            if info:
                width = info['width']
                height = info['height']
                fps = info['fps']
            else:
                # Fallback
                width = 1920
                height = 1080
                fps = 30
        else:
            width = self.output_width or 1920
            height = self.output_height or 1080
            fps = self.output_fps or 30
        
        params.extend([
            # Use rawvideo for NO compression
            '-c:v', 'rawvideo',
            
            # Pixel format - YUYV422 has better quality than YUV420P
            '-pix_fmt', self.pixel_format,
            
            # Frame rate
            '-r', str(int(fps)),
            
            # Video filter for scaling (only if needed) with HIGHEST quality
            '-vf', f'scale={width}:{height}:flags=lanczos:sws_dither=ed',
            
            # Thread settings for better performance
            '-threads', '4',
        ])
        
        return params
    
    def get_ultra_quality_ffmpeg_params(self, source_file=None):
        """ULTRA quality settings - uses more CPU but best quality"""
        params = []
        
        # Get source video info
        if source_file:
            info = self.get_video_info(source_file)
            if info:
                width = info['width']
                height = info['height']
                fps = info['fps']
            else:
                width = 1920
                height = 1080
                fps = 30
        else:
            width = self.output_width or 1920
            height = self.output_height or 1080
            fps = self.output_fps or 30
        
        params.extend([
            # Hardware acceleration (if available)
            # '-hwaccel', 'auto',
            
            # Video codec - rawvideo for zero compression
            '-c:v', 'rawvideo',
            
            # BEST pixel format for quality
            '-pix_fmt', self.pixel_format,
            
            # Frame rate
            '-r', str(int(fps)),
            
            # Advanced video filters for MAXIMUM quality
            '-vf', (
                f'format=yuv444p,'  # Maximum chroma resolution
                f'scale={width}:{height}:flags=lanczos:param0=3,'  # Lanczos with 3 lobes
                f'format={self.pixel_format},'  # Convert to output format
                f'unsharp=5:5:1.0:5:5:0.0'  # Slight sharpening
            ),
            
            # Sync and timing
            '-vsync', 'cfr',  # Constant frame rate
            
            # Threading
            '-threads', '0',  # Auto-detect optimal threads
            
            # Disable any compression
            '-compression_level', '0',
        ])
        
        return params
    
    def stream_single_loop(self, video_file, ultra_quality=True):
        """Stream a single file in loop mode"""
        print(f"\n=== Starting Loop Mode ===")
        print(f"File: {video_file}")
        print(f"Device: {self.virtual_device}")
        print(f"Quality Mode: {'ULTRA' if ultra_quality else 'HIGH'}")
        print("Press Ctrl+C to stop\n")
        
        cmd = [
            self.__ffmpeg_path,
            '-stream_loop', '-1',  # Infinite loop
            '-re',  # Read input at native frame rate
            '-i', video_file,
        ]
        
        # Add quality parameters
        if ultra_quality:
            cmd.extend(self.get_ultra_quality_ffmpeg_params(video_file))
        else:
            cmd.extend(self.get_quality_ffmpeg_params(video_file))
        
        # Output
        cmd.extend([
            '-f', 'v4l2',
            self.virtual_device
        ])
        
        print("Command:", ' '.join(cmd))
        print()
        
        try:
            subprocess.run(cmd)
        except KeyboardInterrupt:
            print("\n✓ Streaming stopped")
    
    def stream_sequential(self, video_files=None, ultra_quality=True):
        """Stream multiple videos sequentially (A → B mode)"""
        if video_files is None:
            video_files = self.results
        
        if not video_files:
            print("✗ No video files to stream")
            return
        
        print(f"\n=== Starting Sequential Mode (A → B) ===")
        print(f"Files: {len(video_files)}")
        print(f"Device: {self.virtual_device}")
        print(f"Quality Mode: {'ULTRA' if ultra_quality else 'HIGH'}")
        print("Press Ctrl+C to stop\n")
        
        for idx, video_file in enumerate(video_files, 1):
            print(f"▶ Now playing ({idx}/{len(video_files)}): {os.path.basename(video_file)}")
            
            cmd = [
                self.__ffmpeg_path,
                '-re',
                '-i', video_file,
            ]
            
            # Add quality parameters
            if ultra_quality:
                cmd.extend(self.get_ultra_quality_ffmpeg_params(video_file))
            else:
                cmd.extend(self.get_quality_ffmpeg_params(video_file))
            
            # Output
            cmd.extend([
                '-f', 'v4l2',
                self.virtual_device
            ])
            
            try:
                subprocess.run(cmd)
            except KeyboardInterrupt:
                print("\n✓ Streaming stopped")
                break
        
        print("✓ All videos completed")
    
    def stream_playlist_loop(self, video_files=None, ultra_quality=True):
        """Stream multiple videos in a continuous loop"""
        if video_files is None:
            video_files = self.results
        
        if not video_files:
            print("✗ No video files to stream")
            return
        
        print(f"\n=== Starting Playlist Loop Mode ===")
        print(f"Files: {len(video_files)}")
        print(f"Device: {self.virtual_device}")
        print(f"Quality Mode: {'ULTRA' if ultra_quality else 'HIGH'}")
        print("Press Ctrl+C to stop\n")
        
        try:
            while True:
                for idx, video_file in enumerate(video_files, 1):
                    print(f"▶ Now playing ({idx}/{len(video_files)}): {os.path.basename(video_file)}")
                    
                    cmd = [
                        self.__ffmpeg_path,
                        '-re',
                        '-i', video_file,
                    ]
                    
                    # Add quality parameters
                    if ultra_quality:
                        cmd.extend(self.get_ultra_quality_ffmpeg_params(video_file))
                    else:
                        cmd.extend(self.get_quality_ffmpeg_params(video_file))
                    
                    # Output
                    cmd.extend([
                        '-f', 'v4l2',
                        self.virtual_device
                    ])
                    
                    subprocess.run(cmd)
                
                print("↻ Restarting playlist...")
        except KeyboardInterrupt:
            print("\n✓ Streaming stopped")
    
    def setup_v4l2loopback(self):
        """Helper to setup v4l2loopback module with OPTIMAL settings"""
        print("\n=== Setting up v4l2loopback for MAXIMUM QUALITY ===")
        print("\n1. Remove existing module:")
        print("   sudo modprobe -r v4l2loopback")
        print("\n2. Load with HIGH QUALITY settings:")
        print("   sudo modprobe v4l2loopback devices=1 video_nr=10 \\")
        print("     card_label='FakeCam' exclusive_caps=1 \\")
        print("     max_buffers=2 max_width=3840 max_height=2160")
        print("\n3. To make it persistent:")
        print("   echo 'v4l2loopback' | sudo tee /etc/modules-load.d/v4l2loopback.conf")
        print("\n4. Create /etc/modprobe.d/v4l2loopback.conf with:")
        print("   options v4l2loopback devices=1 video_nr=10 card_label='FakeCam' \\")
        print("     exclusive_caps=1 max_buffers=2 max_width=3840 max_height=2160")
        print("\n5. Install v4l-utils for debugging:")
        print("   sudo pacman -S v4l-utils")


def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python fake_camera.py <directory> [options]")
        print("Example: python fake_camera.py /camera/1")
        print("\nQuality Options:")
        print("  --ultra            Ultra quality mode (uses more CPU, BEST quality)")
        print("  --high             High quality mode (default)")
        print("  --native           Use native source resolution (default, no scaling)")
        print("  --width WIDTH      Force output width")
        print("  --height HEIGHT    Force output height")
        print("  --fps FPS          Force output FPS")
        print("  --yuyv422          Use YUYV422 pixel format (default, better quality)")
        print("  --yuv420p          Use YUV420P pixel format (lower quality, more compatible)")
        print("\nPresets:")
        print("  --4k               Force 4K output (3840x2160)")
        print("  --1080p            Force 1080p output (1920x1080)")
        print("  --720p             Force 720p output (1280x720)")
        print("\nSetup:")
        print("  --setup            Show v4l2loopback setup instructions")
        sys.exit(1)
    
    scan_dir = sys.argv[1]
    
    # Check for setup flag
    if '--setup' in sys.argv:
        cam = FakeCamera('.')
        cam.setup_v4l2loopback()
        sys.exit(0)
    
    if not os.path.exists(scan_dir):
        print(f"✗ Directory not found: {scan_dir}")
        sys.exit(1)
    
    # Initialize fake camera
    cam = FakeCamera(scan_dir)
    
    # Parse quality options
    ultra_quality = '--ultra' in sys.argv
    use_native = '--native' in sys.argv or ('--width' not in sys.argv and '--height' not in sys.argv)
    
    width = None
    height = None
    fps = None
    
    # Pixel format
    if '--yuv420p' in sys.argv:
        cam.pixel_format = 'yuv420p'
    elif '--yuyv422' in sys.argv:
        cam.pixel_format = 'yuyv422'
    
    # Presets
    if '--4k' in sys.argv:
        width, height = 3840, 2160
        use_native = False
    elif '--1080p' in sys.argv:
        width, height = 1920, 1080
        use_native = False
    elif '--720p' in sys.argv:
        width, height = 1280, 720
        use_native = False
    
    # Custom settings
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == '--width' and i + 1 < len(sys.argv):
            width = int(sys.argv[i + 1])
            use_native = False
            i += 2
        elif sys.argv[i] == '--height' and i + 1 < len(sys.argv):
            height = int(sys.argv[i + 1])
            use_native = False
            i += 2
        elif sys.argv[i] == '--fps' and i + 1 < len(sys.argv):
            fps = int(sys.argv[i + 1])
            i += 2
        else:
            i += 1
    
    cam.set_quality(width, height, fps, use_native)
    
    # Scan for media files
    files = cam.scan_media_files()
    
    if not files:
        print("\n✗ No media files found")
        sys.exit(1)
    
    # Decide mode based on number of files
    if len(files) == 1:
        print("\n→ Single file detected: Running in LOOP mode")
        cam.stream_single_loop(files[0], ultra_quality)
    else:
        print("\n→ Multiple files detected: Running in SEQUENTIAL mode (A → B)")
        print("\nChoose mode:")
        print("  1. Sequential (play once A → B → end)")
        print("  2. Playlist Loop (play A → B → A → B... forever)")
        
        choice = input("\nEnter choice (1 or 2) [default: 1]: ").strip()
        
        if choice == '2':
            cam.stream_playlist_loop(files, ultra_quality)
        else:
            cam.stream_sequential(files, ultra_quality)


if __name__ == '__main__':
    main()

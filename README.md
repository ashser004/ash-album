# 🖼️ Ash Album
### *Fast • Dark • Beautiful*

**Ash Album** is a sleek, modern photo and video gallery for Windows with powerful PDF creation capabilities. Experience lightning-fast browsing, intuitive navigation, and professional image management in one elegant application.

---

## 🚀 **Getting Started**

### **Option 1: Download Ready-to-Use Executable**
1. **Download** the latest release from the [Releases](../../releases) section
2. **Extract** the downloaded file to your preferred location
3. **Create Desktop Shortcut:**
   - Right-click on `Ash Album.exe`
   - Select **"Show more options"** → **"Create shortcut"**
   - Copy the shortcut and paste it on your **Desktop**
   - Rename the shortcut to **"Ash Album"**
4. **Launch** by double-clicking the desktop shortcut

### **Option 2: Run from Source Code**
```bash
# Clone or download the repository
git clone <repository-url>

# Install dependencies
pip install -r requirements.txt

# Launch the application
python main.py
```

---

## 🎯 **Set Ash Album as Your Default Image Viewer**

### **For Images (Recommended)**
1. **Open Windows Settings** (`Win + I`)
2. **Search** for "Default apps" and open it
3. **Navigate** to the "Photos" section
4. **Select** the following file formats one by one:
   - `.jpg`
   - `.jpeg` 
   - `.png`
5. **Click** "Choose an app from the PC"
6. **Browse** to your Ash Album folder and select `Ash Album.exe`
7. **Confirm** the selection

### **For Videos (Optional)**
You can also set Ash Album as the default viewer for videos:
- Follow the same steps for `.mp4` and `.mkv` formats
- *Note: Subtitle display and advanced seeking options are not available for videos*

---

## ✨ **Why This Matters: Standalone Opening**

Once set as your default image viewer, **double-clicking any image in Windows Explorer** will:

🎯 **Instantly open** Ash Album's full-screen viewer  
🎯 **Load only images** from that specific folder  
🎯 **Enable seamless navigation** with arrow keys  
🎯 **Provide instant access** to all editing features  
🎯 **Allow immediate PDF creation** from any folder  

This transforms how you interact with your photos—no more opening a separate gallery app, just **pure, instant image viewing**.

---

## 🏛️ **Application Features**

### **🖼️ Gallery View**
- **Elegant Dark Theme** — Easy on the eyes, professional appearance
- **Lightning-Fast Thumbnails** — Cached for instant loading
- **Smart Organization** — Automatic sorting by date, name, size, or type
- **Multi-Selection** — Ctrl+Click to select multiple images efficiently
- **Folder Discovery** — Automatically finds and organizes all your media

### **📱 Intelligent Tabs**
| Tab | Purpose |
|-----|---------|
| **ALL** | Every photo and video in your collection |
| **PHOTOS** | Images only (JPG, PNG, WEBP, GIF, BMP) |
| **VIDEOS** | Video files only (MP4, MKV, MOV, AVI, WEBM) |
| **RECENT** | Files modified in the last 30 days |
| **SCREENSHOTS** | Automatically detected screenshot folders |
| **FOLDERS** | Browse by specific folder location |
| **HIDDEN** | Private files you've hidden |

### **🔍 Full-Screen Viewer**
- **Immersive Experience** — Distraction-free full-screen viewing
- **Smooth Navigation** — Arrow keys or on-screen controls
- **Instant Actions** — Select, crop, delete, hide with one click
- **Smart Sizing** — Images scale perfectly to your display
- **Video Playback** — Built-in player with play/pause controls

### **✂️ Built-in Image Editor**
- **Intuitive Cropping** — Draw and apply crops instantly
- **Non-destructive** — Original files remain untouched
- **Auto-save** — Cropped images saved with timestamps
- **Live Preview** — See results before applying changes

### **🔒 Privacy Features**
- **Hide Function** — Move sensitive images to a private folder
- **Easy Restoration** — Unhide files from the Hidden tab
- **Local Storage** — Hidden files stay on your computer
- **No Cloud Dependency** — Complete privacy control

### **📄 Professional PDF Export**
- **Multi-Image PDFs** — Combine any number of selected images
- **Page Size Options:**
  - **A4 Mode** — Perfect for printing (210×297mm standard)
  - **Original Mode** — Maintains image dimensions for digital viewing
- **High Quality** — Preserves image clarity and color accuracy
- **Custom Naming** — Automatic timestamps or custom filenames

---

## 🎮 **How to Use**

### **Creating Your First PDF**
1. **Launch** Ash Album
2. **Browse** your photos using the tab system
3. **Select images** by Ctrl+Clicking thumbnails (or use the viewer's Select button)
4. **Click** the "Generate PDF" button
5. **Choose** A4 (for printing) or Original (for digital viewing)
6. **Save** to your preferred location

### **Quick Image Editing**
1. **Click** any thumbnail to open the full-screen viewer
2. **Use** arrow keys to navigate between images
3. **Click** "Crop" to edit the current image
4. **Draw** your selection area and confirm
5. **Find** the edited image in the same folder with a timestamp

### **Managing Private Images**
1. **Open** an image in the viewer
2. **Click** "Hide" to move it to your private folder
3. **Access** hidden images via the "HIDDEN" tab
4. **Click** "Unhide" in the viewer to restore files

### **Folder-Specific Viewing**
1. **Double-click** any image in Windows Explorer
2. **Navigate** through images in that folder only
3. **Use** all features (crop, select, PDF) on those specific images
4. **Press** Escape to close when finished

---

## ⌨️ **Keyboard Shortcuts**

| Shortcut | Action |
|----------|--------|
| `←` `→` | Navigate between images |
| `Space` | Play/Pause videos |
| `Escape` | Close viewer |
| `Ctrl + Click` | Select multiple thumbnails |

---

## 📁 **Smart Folder Management**

Ash Album automatically scans these locations:
- **Pictures** folder and subfolders
- **Videos** folder and subfolders  
- **Desktop** media files
- **Downloads** folder
- **OneDrive** Pictures and Videos (if available)

All discovered folders appear in the **FOLDERS** tab with file counts for easy navigation.

---

## 💾 **Application Data**

Settings and private files are stored locally:
```
📁 C:\Users\[YourName]\Documents\AshAlbum\
   📄 config.json          (App settings)
   📁 cache\              (Fast-loading thumbnails)
   📁 hidden\             (Your private images)
```

---

## 🎨 **Built for Professionals**

- **Dark Theme** — Reduces eye strain during long editing sessions
- **High DPI Support** — Crisp on 4K and high-resolution displays  
- **Memory Efficient** — Smart caching minimizes RAM usage
- **Fast Scanning** — Quickly indexes large photo collections
- **Reliable Performance** — Stable operation with thousands of files

---

## 📋 **System Requirements**

- **Windows 10** or Windows 11
- **4GB RAM** minimum (8GB recommended for large collections)
- **100MB** free disk space for installation
- **Additional space** for thumbnail cache (approx. 1MB per 100 images)

---

## 🆕 **What Makes Ash Album Special**

✅ **Instant Opening** — No splash screens or loading delays  
✅ **True Dark Mode** — Carefully designed for comfort  
✅ **Smart Organization** — Finds and sorts your media automatically  
✅ **Professional PDF Creation** — Publication-ready output  
✅ **Privacy First** — Hidden files stay completely local  
✅ **Seamless Integration** — Works perfectly with Windows Explorer  
✅ **Zero Bloat** — Only the features you actually need  

---

*Transform your photo viewing experience. Download Ash Album today.*
@="AshAlbumImage"

[HKEY_CLASSES_ROOT\.gif]
@="AshAlbumImage"
```

*Replace `C:\Path\To\Ash Album.exe` with the actual path to your executable.*

---

### **Optional: Videos (MP4, MKV)**

> ⚠️ **Note:** While Ash Album can play videos, subtitle support is limited. Use VLC for advanced subtitle handling.

To add video support as default opener:

#### Method 1: Settings
```
1. Open Settings → Apps → Default apps
2. Scroll to ".mp4" and ".mkv"
3. Click each and select Ash Album
```

#### Method 2: Registry
Add to the `.reg` file above:
```registry
[HKEY_CLASSES_ROOT\.mp4]
@="AshAlbumVideo"

[HKEY_CLASSES_ROOT\AshAlbumVideo\shell\open\command]
@="\"C:\\Path\\To\\Ash Album.exe\" \"%%1\""

[HKEY_CLASSES_ROOT\.mkv]
@="AshAlbumVideo"
```

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| **← / →** | Previous / Next image (in viewer) |
| **Escape** | Close viewer |
| **Space** | Play / Pause (videos only) |
| **Ctrl + Click** | Select/deselect thumbnail (gallery) |

---

## 📁 Folder Structure

### Monitored Folders (Auto-Scanned)
The app searches these folders for media:
- `Pictures`
- `Videos`
- `Desktop`
- `Downloads`
- `OneDrive/Pictures` (if available)
- `OneDrive/Videos` (if available)

### App Data Folder
Settings and hidden files stored in:
```
C:\Users\YourUsername\Documents\AshAlbum\
├── config.json           (Settings)
├── cache/                (Thumbnails)
└── hidden/               (Private files)
```

---

## 🎨 Dark Theme

Ash Album features a built-in dark theme optimized for:
- ✅ Reduced eye strain (perfect for late-night browsing)
- ✅ Vibrant accent colors (purple, blue, green)
- ✅ Clear visual hierarchy

All UI elements are carefully crafted for maximum usability.

---

## 🛠️ Troubleshooting

### Issue: App doesn't open when I double-click an image
**Solution:**
1. Right-click the image → "Open with" → "Ash Album"
2. Check "Always use this app"
3. If Ash Album doesn't appear in the list, click "Choose another app" → "Look for another app on this PC"

### Issue: Thumbnails are slow to load
**Solution:**
1. Click **⟳ Refresh** to rebuild the thumbnail cache
2. Close other apps to free up RAM

### Issue: I can't find a file I deleted
**Solution:**
1. Check the **HIDDEN** tab (maybe you hid it by accident)
2. Check your Recycle Bin (files go there, not permanently deleted)

### Issue: Video won't play
**Solution:**
1. Make sure the video format is supported (.mp4, .mkv, .mov, .avi, .webm)
2. Your system may be missing video codecs — install Windows Media Feature Pack
3. Try VLC for advanced codec support

### Issue: PDF generation fails
**Solution:**
1. Ensure you have write permissions to your Downloads folder
2. Make sure images aren't corrupted (try opening them in viewer first)
3. Free up disk space if your drive is nearly full

---

## 📞 Tips & Tricks

### Batch Select Images
```
1. Click first image thumbnail
2. Hold Shift + Click last image
3. All images between are selected
```

### Quickly Find a Photo
1. Use the **RECENT** tab to find photos from the last 30 days
2. Use **FOLDERS** tab to browse by folder location
3. Change **Sort** to quickly find by date/size/name

### Print-Ready PDF
```
1. Select images
2. Click "Generate PDF"
3. Choose "A4" (optimized for standard paper)
4. Print from your PDF reader
```

### Make a Slideshow
```
1. Open a folder in the viewer
2. Press Space to auto-play videos
3. Use ← → to navigate manually
4. Great for presentations!
```

---

## 📋 Features at a Glance

✅ **Browse** — Fast thumbnail gallery  
✅ **Select** — Multi-select for batch operations  
✅ **View** — Full-screen viewer with keyboard nav  
✅ **Crop** — Built-in image cropping  
✅ **Hide** — Private folder for sensitive files  
✅ **Delete** — Safe deletion to Recycle Bin  
✅ **PDF** — Export with A4 or original sizing  
✅ **Sort** — By name, date, size, or type  
✅ **Organize** — Tabs for photos, videos, recent, etc.  
✅ **Cache** — Blazing-fast thumbnail loading  
✅ **Dark Theme** — Easy on the eyes  
✅ **File Association** — Double-click to open  

---

## 🎯 Getting Started Checklist

- [ ] Install Ash Album from executable or source
- [ ] Run once to let it scan your folders
- [ ] Set as default app (right-click → Open with)
- [ ] Try double-clicking an image
- [ ] Select a few images and generate a PDF
- [ ] Try cropping an image
- [ ] Hide a sensitive file and restore it
- [ ] Explore the different tabs and sorting options

---

## 📝 License

See [LICENSE](LICENSE) file for details.

---

**Made with ❤️ for photographers, designers, and media enthusiasts.**

*Ash Album — Simple. Dark. Powerful.*

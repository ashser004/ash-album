# 📸 Ash Album — Image & Video Gallery

A sleek, fast, dark-themed media gallery and PDF creator for Windows. Organize, view, edit, and export your photos and videos with ease.

**Version:** 1.1.2

---

## 🚀 Quick Start

### Installation

1. Download the latest `Ash Album.exe` from the releases folder
2. Run the executable — it will auto-detect your picture libraries
3. On first run, you'll be asked to select your media folders

### Running from Source

```bash
pip install -r requirements.txt
python main.py
```

---

## ✨ Features

- **Gallery View** — Browse all your photos & videos in a beautiful dark theme
- **Tabs & Organization** — Filter by type, date, folder, or status (hidden)
- **Full-Featured Viewer** — Navigate, select, crop, hide, delete from full-screen view
- **PDF Export** — Create PDFs with A4 or original-size pages
- **File Association** — Double-click images in Explorer to open them directly
- **Hide Files** — Private folder for sensitive images (password-free, stored locally)
- **Thumbnail Cache** — Lightning-fast loading with cached previews
- **Keyboard Shortcuts** — Arrow keys, Escape, Space — all the essentials

---

## 📖 User Guide

### 🎯 Main Interface

The app opens with a clean interface:

```html
<div style="background: linear-gradient(135deg, #0b0b12 0%, #1a1a28 100%); color: #ededf4; 
            padding: 20px; border-radius: 12px; font-family: 'Segoe UI', Arial; 
            border: 1px solid #2a2a3e; line-height: 1.6;">
  
  <div style="display: flex; justify-content: space-between; align-items: center; 
              padding-bottom: 15px; border-bottom: 1px solid #2a2a3e;">
    <div style="font-size: 20px; font-weight: bold; letter-spacing: 1px;">ASH ALBUM</div>
    <div style="display: flex; gap: 12px;">
      <button style="background: #232336; color: #ededf4; border: 1px solid #2a2a3e; 
                     border-radius: 6px; padding: 8px 16px; cursor: pointer; font-size: 12px; font-weight: 600;">
        ⟳ Refresh
      </button>
      <div style="color: #8686a4; font-size: 12px;">
        Sort: <span style="color: #7c5cfc;">Date Modified (Newest First)</span>
      </div>
    </div>
  </div>

  <div style="display: flex; gap: 8px; padding: 12px 0; border-bottom: 1px solid #2a2a3e; 
              overflow-x: auto; font-size: 12px; font-weight: 600;">
    <button style="background: #7c5cfc; color: #fff; border: none; border-radius: 6px; 
                   padding: 8px 14px; cursor: pointer;">ALL</button>
    <button style="background: #1a1a28; color: #8686a4; border: 1px solid #2a2a3e; 
                   border-radius: 6px; padding: 8px 14px; cursor: pointer;">PHOTOS</button>
    <button style="background: #1a1a28; color: #8686a4; border: 1px solid #2a2a3e; 
                   border-radius: 6px; padding: 8px 14px; cursor: pointer;">VIDEOS</button>
    <button style="background: #1a1a28; color: #8686a4; border: 1px solid #2a2a3e; 
                   border-radius: 6px; padding: 8px 14px; cursor: pointer;">RECENT</button>
    <button style="background: #1a1a28; color: #8686a4; border: 1px solid #2a2a3e; 
                   border-radius: 6px; padding: 8px 14px; cursor: pointer;">FOLDERS</button>
    <button style="background: #1a1a28; color: #8686a4; border: 1px solid #2a2a3e; 
                   border-radius: 6px; padding: 8px 14px; cursor: pointer;">HIDDEN</button>
  </div>

  <div style="margin: 16px 0; height: 200px; background: #111119; border: 1px solid #2a2a3e; 
              border-radius: 8px; display: flex; align-items: center; justify-content: center; 
              color: #8686a4; font-size: 14px;">
    🖼️ Gallery Grid (Thumbnails appear here)
  </div>

  <div style="display: flex; justify-content: space-between; align-items: center; 
              padding-top: 12px; border-top: 1px solid #2a2a3e; font-size: 12px;">
    <div style="color: #7c5cfc; font-weight: 600;">0 selected</div>
    <div style="color: #8686a4;">1,243 files found • 18 folders</div>
  </div>
  
  <div style="display: flex; gap: 12px; margin-top: 12px; justify-content: flex-end;">
    <button style="background: #232336; color: #ededf4; border: 1px solid #2a2a3e; 
                   border-radius: 6px; padding: 6px 12px; cursor: pointer; font-size: 11px; font-weight: 600;">
      Clear
    </button>
    <button style="background: #ef5350; color: #fff; border: none; 
                   border-radius: 6px; padding: 6px 12px; cursor: pointer; font-size: 11px; font-weight: 600;">
      Delete Selected
    </button>
    <button style="background: #7c5cfc; color: #fff; border: none; 
                   border-radius: 6px; padding: 8px 24px; cursor: pointer; font-size: 13px; font-weight: 700;">
      Generate PDF
    </button>
  </div>
</div>
```

---

### 1️⃣ **Selecting Images & Creating a PDF** (Quickstart)

#### Step 1: Browse to Images
- Open **Ash Album**
- Use the **tab bar** to filter (ALL, PHOTOS, VIDEOS, etc.)
- Scroll through the gallery grid

#### Step 2: Select Images
You can select images in **two ways**:

**Method A: Gallery view (Ctrl+Click)**
```
• Ctrl + Click a thumbnail to select it
• The thumbnail gets a checkmark with a number (selection order)
• Repeat for more images
```

**Method B: Viewer (Full-Screen)**
```
• Click on any thumbnail to open the full-screen viewer
• Press the "Select" button to toggle selection
• Navigate with arrow keys or next/previous buttons
• When selected, the button changes to "Deselect ✓ (Page X)"
```

Visual example of a selected image in gallery:

```html
<div style="display: inline-block; position: relative; width: 180px; height: 180px; 
            background: #1a1a28; border: 2px solid #7c5cfc; border-radius: 8px; 
            overflow: hidden; margin: 10px;">
  <div style="width: 100%; height: 100%; background: linear-gradient(135deg, #7c5cfc, #536dfe); 
              display: flex; align-items: center; justify-content: center; color: #fff; font-size: 64px;">
    🖼️
  </div>
  <div style="position: absolute; top: 8px; right: 8px; background: #7c5cfc; 
              color: #fff; width: 28px; height: 28px; border-radius: 50%; 
              display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 14px;">
    1
  </div>
  <div style="position: absolute; bottom: 0; left: 0; right: 0; background: rgba(0,0,0,0.6); 
              color: #fff; padding: 6px; font-size: 11px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
    vacation-pic.jpg
  </div>
</div>
```

#### Step 3: Generate PDF
- Click the **"Generate PDF"** button (purple, bottom-right)
- A dialog appears asking for page size:

```html
<div style="background: #1a1a28; color: #ededf4; padding: 24px; border: 1px solid #2a2a3e; 
            border-radius: 12px; max-width: 500px; font-family: 'Segoe UI', Arial; text-align: center;">
  <div style="font-size: 18px; font-weight: 700; margin-bottom: 12px;">PDF Page Size</div>
  <div style="color: #8686a4; font-size: 13px; line-height: 1.6; margin-bottom: 20px;">
    <strong style="color: #ededf4;">A4</strong> — Each image is scaled to fit a standard A4 page 
    (210 × 297 mm). Ideal for <strong>printing</strong>.<br><br>
    <strong style="color: #ededf4;">Default</strong> — Each page matches the original image dimensions. 
    Best for <strong>digital viewing</strong> at full quality.
  </div>
  <div style="display: flex; gap: 12px; justify-content: center;">
    <button style="background: #7c5cfc; color: #fff; border: none; border-radius: 6px; 
                   padding: 8px 24px; cursor: pointer; font-weight: 600;">A4</button>
    <button style="background: #7c5cfc; color: #fff; border: none; border-radius: 6px; 
                   padding: 8px 24px; cursor: pointer; font-weight: 600;">Default</button>
    <button style="background: #232336; color: #ededf4; border: 1px solid #2a2a3e; 
                   border-radius: 6px; padding: 8px 24px; cursor: pointer; font-weight: 600;">Cancel</button>
  </div>
</div>
```

- Choose **A4** (for printing) or **Default** (for viewing)
- Pick a save location (defaults to Downloads folder)
- ✅ PDF created!

---

### 2️⃣ **Double-Click to Open Image** (File Association)

The best way to use Ash Album is to set it as your default image viewer.

#### In Explorer:
```
Right-click an image (JPG, PNG, etc.)
→ "Open with" or "Open with..."
→ "Choose another app"
→ Select "Ash Album"
→ Check "Always use this app"
→ Click OK
```

Now **double-clicking any image** will:
1. ✅ Open **Ash Album viewer** directly to that image
2. ✅ Show **only images from that folder** (left/right arrows)
3. ✅ Enable all features: **Select, Crop, Delete, Hide, Add to PDF, Generate PDF**

**Example:**
```
My Pictures/
  ├── vacation-2024/
  │   ├── beach.jpg       ← Double-click this
  │   ├── sunset.jpg
  │   ├── family.png
  │   └── group.jpg

Opens viewer with:
  • Starts on beach.jpg
  • Arrows navigate: beach → sunset → family → group → beach (loops)
  • Only these 4 files shown
  • All editing features available
  • Can select and generate PDF from these 4 images only
```

---

### 3️⃣ **Full-Screen Viewer** (All Features)

Click any thumbnail to open the full-screen viewer:

```html
<div style="background: #0b0b12; color: #ededf4; padding: 20px; border-radius: 12px; 
            font-family: 'Segoe UI', Arial; min-height: 400px;">
  
  <div style="display: flex; gap: 12px; align-items: center; margin-bottom: 20px;">
    <button style="background: transparent; color: #8686a4; font-size: 26px; cursor: pointer; 
                   padding: 0 12px; border: none;">❮</button>
    <div style="flex: 1; height: 300px; background: #111119; border: 1px solid #2a2a3e; 
                border-radius: 8px; display: flex; align-items: center; justify-content: center; 
                font-size: 14px; color: #8686a4;">
      📸 Image Display Area
    </div>
    <button style="background: transparent; color: #8686a4; font-size: 26px; cursor: pointer; 
                   padding: 0 12px; border: none;">❯</button>
  </div>

  <div style="background: #111119; border: 1px solid #2a2a3e; padding: 12px 16px; 
              border-radius: 6px; text-align: center; color: #8686a4; font-size: 11px; margin-bottom: 16px;">
    photo.jpg  •  2.3 MB  •  1 / 42
  </div>

  <div style="display: flex; gap: 12px; justify-content: center; flex-wrap: wrap;">
    <button style="background: #7c5cfc; color: #fff; border: none; border-radius: 8px; 
                   padding: 6px 22px; font-weight: 700; font-size: 12px; cursor: pointer;">
      Select
    </button>
    <button style="background: #3d5afe; color: #fff; border: none; border-radius: 8px; 
                   padding: 6px 22px; font-weight: 700; font-size: 12px; cursor: pointer;">
      Crop
    </button>
    <button style="background: #ef5350; color: #fff; border: none; border-radius: 8px; 
                   padding: 6px 22px; font-weight: 700; font-size: 12px; cursor: pointer;">
      Delete
    </button>
    <button style="background: #ff9800; color: #fff; border: none; border-radius: 8px; 
                   padding: 6px 22px; font-weight: 700; font-size: 12px; cursor: pointer;">
      Hide
    </button>
    <button style="background: #43c667; color: #fff; border: none; border-radius: 8px; 
                   padding: 6px 22px; font-weight: 700; font-size: 12px; cursor: pointer;">
      Add to PDF
    </button>
  </div>
</div>
```

#### Viewer Controls:

| Button | Shortcut | Action |
|--------|----------|--------|
| **❮ ❯** (Navigation) | ← → (Arrow Keys) | Move to previous/next image |
| **Select** | - | Add/remove current image to selection |
| **Crop** | - | Open crop tool (images only) |
| **Delete** | - | Move to Recycle Bin |
| **Hide** | - | Move to private hidden folder |
| **Add to PDF** | - | Select for PDF export |
| **Esc** | Escape | Close viewer |
| **Play/Pause** | Space | Play/pause video (videos only) |

---

### 4️⃣ **Cropping Images**

In the full-screen viewer, click the **Crop** button:

1. **Draw rectangle** on the image to select the area you want to keep
2. **Crop** button applies the crop
3. **Cancel** to discard
4. Saved image appears in the **same folder** with a timestamped name
5. Thumbnail regenerates automatically

---

### 5️⃣ **Hiding Files**

Click the **Hide** button to move files to a private folder (stored locally in your AshAlbum data folder).

To access hidden files:
- Click the **HIDDEN** tab in the main gallery
- All hidden files appear here
- Click **Unhide** in the viewer to restore a file to its original location

---

### 6️⃣ **Sorting & Organization**

#### Sort Options:
- Name (A → Z / Z → A)
- Date Created (Newest/Oldest First)
- Date Modified (Newest/Oldest First)
- File Size (Small → Large / Large → Small)

#### Tabs:
| Tab | Shows |
|-----|-------|
| **ALL** | Every photo & video found |
| **PHOTOS** | .jpg, .jpeg, .png, .bmp, .webp, .gif |
| **VIDEOS** | .mp4, .mkv, .mov, .avi, .webm |
| **RECENT** | Files modified in the last 30 days |
| **SCREENSHOTS** | Files in Pictures/Screenshots folder |
| **FOLDERS** | Browse by folder (sidebar shows folder counts) |
| **HIDDEN** | Files you've marked as private |

---

### 7️⃣ **Refreshing**

Click the **⟳ Refresh** button to:
- Rescan all monitored folders
- Rebuild thumbnails
- Update view with new/deleted files

---

## 🖥️ Making Ash Album Your Default App

### **For Images (JPG, JPEG, PNG, BMP, WebP, GIF)**

#### Method 1: Right-Click Context Menu (Easiest)
```
1. Find any image file in Explorer
2. Right-click → "Open with" → "Choose another app"
3. Click "Look for another app on this PC"
4. Navigate to your Ash Album folder and select "Ash Album.exe"
5. Check "Always use this app to open ..." 
6. Click OK
```

#### Method 2: Settings App (Windows 11/10)
```
1. Open Settings (Win + I)
2. Go to "Apps" → "Default apps"
3. Scroll down and click on ".jpg" (or .png, .jpeg, .bmp, .webp, .gif)
4. Click "Choose an app"
5. If Ash Album doesn't appear, click "Look for another app on this PC"
6. Navigate to Ash Album.exe and select it
7. Repeat for each image format:
   - .jpg / .jpeg
   - .png
   - .bmp
   - .webp
   - .gif
```

#### Method 3: File Association (Advanced - Windows Registry)

Save this as `set_ash_album_images.reg` and run it:

```registry
Windows Registry Editor Version 5.00

[HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.jpg\UserChoice]
; (Will be set by Windows when you use Method 1 or 2)

[HKEY_CLASSES_ROOT\.jpg]
@="AshAlbumImage"

[HKEY_CLASSES_ROOT\AshAlbumImage\shell\open\command]
@="\"C:\\Path\\To\\Ash Album.exe\" \"%%1\""

[HKEY_CLASSES_ROOT\.jpeg]
@="AshAlbumImage"

[HKEY_CLASSES_ROOT\.png]
@="AshAlbumImage"

[HKEY_CLASSES_ROOT\.bmp]
@="AshAlbumImage"

[HKEY_CLASSES_ROOT\.webp]
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

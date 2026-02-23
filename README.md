Ash Album
=========

Ash Album is a fast, dark-themed media gallery and PDF creator for Windows. It helps you browse photos and videos, open a full-screen viewer, crop images, hide files, and export selected images to PDF.

Version: 1.1.2

Overview
--------

- Browse photos and videos in a clean, modern gallery.
- Open a full-screen viewer with navigation and actions.
- Select multiple images and generate a PDF (A4 or original size).
- Hide files to a private folder and restore them later.
- Set Ash Album as the default app to open images from Explorer.

Quick Start (PDF First)
-----------------------

1. Open Ash Album.
2. Select images:
   - In the gallery: Ctrl + Click thumbnails.
   - In the viewer: click an image, then press Select.
3. Click Generate PDF.
4. Choose the page size:
   - A4: scales each image to fit a standard A4 page.
   - Default: each page matches the original image size.
5. Choose the save location and confirm.

Installation
------------

Run the executable:

- Launch Ash Album.exe.
- On first run, choose your media folders.

Run from source:

```bash
pip install -r requirements.txt
python main.py
```

Features
--------

- Gallery view with tabs and sorting.
- Full-screen viewer with keyboard navigation.
- Crop, delete, hide, and add to PDF from the viewer.
- Folder-based navigation and hidden media view.
- PDF export with page size choice.
- File association for double-click opening.
- Thumbnail cache for faster loading.

Using the App
-------------

Gallery
- Tabs: All, Photos, Videos, Recent, Screenshots, Folders, Hidden.
- Sort: name, created date, modified date, file size (ascending/descending).
- Selection: Ctrl + Click thumbnails to select multiple images.

Viewer
- Open a thumbnail to view full-screen.
- Use left/right arrows or the on-screen buttons to navigate.
- Actions: Select, Crop (images only), Delete, Hide, Add to PDF.
- Videos: Play/Pause with Space.

Cropping
- Open an image in the viewer and click Crop.
- Draw the selection and confirm.
- The cropped image is saved in the same folder.

Hidden Files
- Click Hide in the viewer to move a file to the hidden folder.
- Open the Hidden tab to view and restore hidden files.

Default App for Images (Windows)
-------------------------------

Method 1: Open with
1. Right-click any .jpg, .jpeg, or .png file.
2. Choose Open with > Choose another app.
3. Select Ash Album and check Always use this app.

Method 2: Settings
1. Open Settings (Win + I).
2. Go to Apps > Default apps.
3. Search for .jpg, .jpeg, .png, etc., and set Ash Album for each.

When set as the default app:
- Double-clicking an image opens Ash Album directly.
- The viewer shows only images from the same folder.
- All viewer features are available.

Optional: Default App for Videos
--------------------------------

Ash Album can open videos, but subtitle support is limited. If you still want it:

1. Go to Settings > Apps > Default apps.
2. Set Ash Album for .mp4 and .mkv.

Keyboard Shortcuts
------------------

- Left / Right Arrow: Previous / Next image in viewer
- Escape: Close viewer
- Space: Play/Pause video
- Ctrl + Click: Select thumbnail in gallery

Folders Scanned by Default
--------------------------

- Pictures
- Videos
- Desktop
- Downloads
- OneDrive equivalents (if available)

App Data Location
-----------------

Ash Album stores settings, cache, and hidden files here:

```
C:\Users\YourUsername\Documents\AshAlbum\
  config.json
  cache\
  hidden\
```

Troubleshooting
---------------

- App does not open on double-click: set Ash Album as the default app for .jpg/.jpeg/.png.
- Thumbnails are slow: click Refresh to rebuild cache.
- Video playback fails: install missing codecs or use a dedicated video player.
- PDF generation fails: check file permissions and free disk space.

License
-------

See [LICENSE](LICENSE).
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

# 🔍 Complete Data Pipeline Testing Guide

## Problem Statement

Graph plots and 3D model not updating despite ESP32 sending CSV data at 115200 baud.

## Expected Data Flow

```
ESP32 (printf CSV) → UART → SerialWorker
  ↓
raw_data_received signal (emit raw int16 values normalized to floats)
  ├→ Handler._on_data_received() → Wand3DWidget.update_orientation() [immediate]
  └→ Handler._on_raw_data_received() → buffer accumulation → PageRecord.update_plot_data()
    ↓
    QTimer 60fps → PageRecord._render_plots()
      ↓
      curve_ax.setData(), curve_ay.setData(), etc. [all 6 curves]
```

---

## Step-by-Step Testing Sequence

### **Stage 1: Verify Serial Connection** (No plots yet)

1. **Start the app:**

   ```bash
   cd e:/03.Python/02.reboot
   source .venv/Scripts/activate
   python main.py
   ```

2. **Check console output:**
   - Should see: `[PageRecord] Initialized - is_live=True, QTimer started for plot rendering`
   - If you don't see this → **PageRecord failed to initialize**

3. **Connect serial:**
   - On "Wand" tab, click **SCAN** button
   - Select ESP32 COM port from dropdown
   - Click **CONNECT** button
   - Console should show: `>> Connected to COM# at 115200 baud`
   - ESP32 should show as "connected" (status light)

4. **Check data arriving:**
   - On "Wand" tab, you should see CSV data appearing in terminal:
     ```
     1234,5678,-9012,-123,456,-789
     2345,6789,1234,-234,567,-890
     ```
   - If you see this → **SerialWorker is working correctly**

---

### **Stage 2: Buffer Accumulation** (Check if data reaches PageRecord)

1. **Navigate to "Record" tab**

2. **Observer console for debug output:**
   - Watch for: `[Handler._on_raw_data_received] Buffer size: 50, sample: [...]`
   - This should start appearing ~1 second after connecting

3. **If you see buffer messages:**
   - ✅ Data is flowing from SerialWorker → Handler → buffer
   - ✅ Continue to Stage 3

4. **If you DON'T see buffer messages:**
   - ❌ `raw_data_received()` signal not being received
   - Check if: `is_live=True` (it should be by default)
   - Check if: SerialWorker is actually connected
   - Run Stage 1 verification again

---

### **Stage 3: Plot Rendering** (Check if graphs update)

1. **Still on "Record" tab**

2. **Watch console for render messages:**
   - Watch for: `[PageRecord.update_plot_data] Received 50 samples, latest: [...]`
   - Watch for: `[PageRecord._render_plots] Rendering 50 samples - ax_data has 50 points`

3. **Check UI:**
   - Look at **Graph 1 (Acceleration)** - should see 3 colored lines scrolling left:
     - 🔴 Red line (aX axis)
     - 🟢 Green line (aY axis)
     - 🔵 Blue line (aZ axis)
   - Look at **Graph 2 (Gyroscope)** - should see 3 colored lines:
     - 🟣 Magenta line (gX axis)
     - 🔵 Cyan line (gY axis)
     - 🟡 Yellow line (gZ axis)

4. **If graphs ARE updating:**
   - ✅ Everything is working! Skip to Stage 5

5. **If graphs ARE NOT updating but console shows render messages:**
   - ❌ Data is there but UI not displaying
   - Check: Are the tabs visible? Click explicitly on Graph1/Graph2
   - Check: Are the visibility checkboxes enabled?
   - Run: `print(len(ax_data))` in \_render_plots to verify data exists

---

### **Stage 4: 3D Wand Animation** (Check if rotation works)

1. **Navigate to "Home" tab**

2. **Move/rotate your ESP32-MPU6050 physically**

3. **Verify wand 3D model rotates:**
   - Tilt ESP32 forward → Wand should pitch forward
   - Rotate ESP32 left → Wand should roll/yaw
   - If model rotates properly → ✅ 3D visualization working

4. **If model doesn't move:**
   - Check console for errors
   - Verify data arriving (check Graph plots instead - if they move, 3D data is there)
   - Check if `update_orientation()` is being called

---

### **Stage 5: Recording & Plotting**

1. **Back to "Record" tab**

2. **Enter action name:** `"TEST_MOVEMENT"` in the text field

3. **Click START button:**
   - Console should show: `>> RECORDING: TEST_MOVEMENT`
   - Button should change (START disabled, STOP enabled)

4. **Move your ESP32:**
   - Graphs should show increasing number of data points
   - Lines should scroll left as buffer fills
   - Each axis should show characteristic motion pattern

5. **Click STOP button:**
   - Console: `>> RECORD STOPPED - Ready to snip`
   - Graphs should freeze (stop scrolling)
   - Crop region should appear (draggable box on graph)

6. **Verify crop/snip works:**
   - Drag crop region to select portion
   - Change "SPELL LABEL" to "TEST"
   - Click SNIP button
   - Should save CSV file to `dataset/TEST/`

---

## 🔧 Debugging Checklist

### If graphs don't show data:

- [ ] SerialWorker connected? (check Wand tab status)
- [ ] Data in console CSV? (watch Wand tab terminal)
- [ ] Buffer accumulating? (watch console for `[Handler._on_raw_data_received]`)
- [ ] is_live=True? (should be default)
- [ ] QTimer running? (watch console for `[PageRecord._render_plots]`)
- [ ] Graphs visible? (not hidden, checkboxes checked)

### If 3D wand doesn't rotate:

- [ ] ESP32 orientation changing?
- [ ] `update_orientation()` being called?
- [ ] Try plots first - if they work, 3D data exists
- [ ] Check: camera position set? (should default to distance=9)

### if signal routing issues:

- [ ] Handler created before UI pages? (check main_window.py)
- [ ] `_connect_signals()` called? (should be in Handler.**init**)
- [ ] Serial port actually opened? (console should show connection message)

---

## 📊 Expected Console Output Sequence

```
[PageRecord] Initialized - is_live=True, QTimer started for plot rendering
>> Scanned 1 UART port(s).
>> Connecting to COM3 @ 115200 baud...
>> Connected to COM3 at 115200 baud
[Handler._on_raw_data_received] Buffer size: 50, sample: [0.087, -0.112, 0.956, 0.01, -0.02, 0.001]
[Handler._on_raw_data_received] Buffer size: 100, sample: [0.089, -0.115, 0.951, 0.01, -0.02, 0.002]
[PageRecord.update_plot_data] Received 50 samples, latest: [0.087, -0.112, 0.956, 0.01, -0.02, 0.001]
[PageRecord._render_plots] Rendering 50 samples - ax_data has 50 points
```

---

## 🚀 Next Steps

1. **Run `python main.py`** with the debugging output active
2. **Connect to ESP32**
3. **Report what console messages appear:**
   - Do you see `[PageRecord]` initialization message?
   - Do you see `[Handler._on_raw_data_received]` buffer reports?
   - Do you see `[PageRecord._render_plots]` rendering messages?
   - Do you see any ERROR messages?

4. **Report what UI shows:**
   - Graphs visible?
   - Lines drawn?
   - 3D wand rotates?

This will tell us exactly where the data pipeline is broken!

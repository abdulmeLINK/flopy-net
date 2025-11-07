# Screenshot Guide for FLOPY-NET README

This document specifies the screenshots needed for the README.md file to make it more visual and intuitive for new users.

## Required Screenshots

### 1. Dashboard Overview (`dashboard-overview.png`)
**Location in README**: Right after "What Makes FLOPY-NET Unique"
**What to capture**: 
- Full dashboard homepage/overview page
- Show system status indicators (green/connected)
- Display any active scenario information
- Include navigation sidebar
**Recommended size**: 1920x1080 or 1600x900, then resize to 1200px wide for README

---

### 2. FL Training Progress (`fl-training-progress.png`)
**Location in README**: In the "Quick Demo" section
**What to capture**:
- FL Monitoring page showing training rounds
- Line chart with accuracy/loss curves over multiple rounds
- Active training round indicator
- Client participation status
**Recommended size**: 1600x900, resize to 1000px wide

---

### 3. Dashboard Monitoring Full View (`dashboard-monitoring.png`)
**Location in README**: After Step 7 in Quick Start
**What to capture**:
- Full view of FL monitoring with network topology side-by-side
- Shows the complete monitoring workflow
- Include metrics panel and topology visualization
**Recommended size**: 1920x1080, resize to 1200px wide

---

### 4. Dashboard Overview Detailed (`dashboard-overview-detailed.png`)
**Location in README**: Dashboard Usage section, Overview subsection
**What to capture**:
- Close-up of the Overview/Home page
- System health status cards clearly visible
- Quick statistics panel
- Active scenarios list
**Recommended size**: 1600x900, resize to 1000px wide

---

### 5. Network Topology (`network-topology.png`)
**Location in README**: Dashboard Usage section, Network Topology subsection
**What to capture**:
- GNS3 network topology visualization
- Show nodes (FL server, clients, switches, policy engine)
- Display connection lines/links
- Node status indicators (green dots or similar)
- Ideally with one node selected showing details popup
**Recommended size**: 1400x1000, resize to 1000px wide

---

## How to Capture Screenshots

### For Dashboard Screenshots:

1. **Setup Environment**:
   ```powershell
   cd dashboard
   docker compose up -d
   # Wait for services to start
   ```

2. **Open Browser**:
   - Navigate to http://localhost:8085
   - Use Chrome/Edge for consistent rendering
   - Set browser zoom to 100%

3. **Deploy a Scenario** (for active data):
   ```powershell
   cd ..
   python src/scenarios/basic/scenario.py --config config/scenarios/basic_main.json --topology config/topology/basic_topology.json
   ```

4. **Capture Screenshots**:
   - Use Windows Snipping Tool (Win + Shift + S) or Greenshot
   - Capture full-width sections
   - Ensure no sensitive information is visible

5. **Edit Screenshots**:
   - Crop to relevant content (remove browser chrome if needed)
   - Resize to recommended dimensions
   - Save as PNG (preferred) or JPG (if size is a concern)
   - Optimize with tools like TinyPNG or ImageOptim

### For Network Topology Screenshots:

1. **Use GNS3 GUI**:
   - Open the deployed project in GNS3 GUI
   - Arrange topology for optimal viewing
   - Ensure all nodes are visible and clearly labeled

2. **Or Use Dashboard Topology View**:
   - Navigate to Network → Topology in the dashboard
   - Capture the interactive topology visualization
   - Zoom to fit all nodes in view

---

## File Organization

Place all screenshots in: `docs/images/`

```
docs/
└── images/
    ├── dashboard-overview.png
    ├── fl-training-progress.png
    ├── dashboard-monitoring.png
    ├── dashboard-overview-detailed.png
    └── network-topology.png
```

---

## Image Optimization

After capturing, optimize images:

```powershell
# Using ImageMagick (if installed)
magick convert dashboard-overview.png -resize 1200x -quality 85 dashboard-overview.png

# Or use online tools:
# - https://tinypng.com/
# - https://squoosh.app/
```

Target file sizes:
- Large screenshots (1200px wide): < 500KB
- Medium screenshots (1000px wide): < 300KB

---

## Alternative: Placeholder Images

If screenshots are not immediately available, you can use placeholder images temporarily:

```markdown
![Dashboard Overview](https://via.placeholder.com/1200x675/1e40af/ffffff?text=Dashboard+Overview+-+Coming+Soon)
```

Then replace with actual screenshots when available.

---

## Adding Screenshots to README

The screenshot references have already been added to the README.md with the following paths:

1. `docs/images/dashboard-overview.png`
2. `docs/images/fl-training-progress.png`
3. `docs/images/dashboard-monitoring.png`
4. `docs/images/dashboard-overview-detailed.png`
5. `docs/images/network-topology.png`

Once you capture and place the images in `docs/images/`, they will automatically appear in the README.

---

## Tips for High-Quality Screenshots

1. **Clean Environment**: Remove any test data, errors, or debug information
2. **Consistent Theme**: Use the same color theme across all screenshots
3. **Readable Text**: Ensure all text is legible at the target resolution
4. **Highlight Key Elements**: Consider adding subtle arrows or boxes to highlight important features
5. **Show Success States**: Capture screenshots when systems are connected and running successfully
6. **Consistent Browser Width**: Use the same browser window width for all dashboard screenshots

---

## Example Screenshot Workflow

```powershell
# 1. Start everything
cd dashboard
docker compose up -d
Start-Sleep -Seconds 30  # Wait for services

# 2. Open browser to http://localhost:8085

# 3. Navigate through each section and capture:
#    - Overview page
#    - FL Monitoring (after deploying a scenario)
#    - Network Topology
#    - Metrics Explorer

# 4. Deploy scenario for live data
cd ..
python src/scenarios/basic/scenario.py --config config/scenarios/basic_main.json --topology config/topology/basic_topology.json

# 5. Return to dashboard and capture active training screenshots

# 6. Process images and place in docs/images/
```

---

## Verification

After adding screenshots, verify:

1. All image files exist in `docs/images/`
2. File sizes are reasonable (< 500KB each)
3. Images are referenced correctly in README.md
4. Images display properly when viewing README on GitHub
5. Alt text is descriptive and accurate

---

## Future Enhancements

Consider creating:
- GIF animations showing scenario deployment process
- Video walkthrough (embed YouTube link)
- Architecture diagram (professional SVG/PNG instead of ASCII)
- Interactive topology demo (embed CodePen or similar)

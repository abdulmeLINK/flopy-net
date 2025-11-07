# Quick Screenshot Checklist

## Status: 📸 Screenshots Needed

The README.md has been updated with screenshot placeholders. Follow the guide below to capture and add them.

### Screenshot List

- [ ] **dashboard-overview.png** - Main dashboard view showing system overview
  - Location: After "What Makes FLOPY-NET Unique" section
  - Shows: System status, navigation, overall layout
  
- [ ] **fl-training-progress.png** - FL training with accuracy/loss curves  
  - Location: In "Quick Demo" section
  - Shows: Active training rounds, metrics charts
  
- [ ] **dashboard-monitoring.png** - Full monitoring view
  - Location: After Quick Start Step 7
  - Shows: Complete workflow, metrics + topology
  
- [ ] **dashboard-overview-detailed.png** - Overview page close-up
  - Location: Dashboard Usage → Overview section
  - Shows: Health status cards, statistics, active scenarios
  
- [ ] **network-topology.png** - Network topology visualization
  - Location: Dashboard Usage → Network Topology section
  - Shows: GNS3 topology with nodes and links

---

## Quick Capture Instructions

1. **Start the system**:
   ```powershell
   cd dashboard
   docker compose up -d
   ```

2. **Deploy a scenario** (for active data):
   ```powershell
   cd ..
   python src/scenarios/basic/scenario.py --config config/scenarios/basic_main.json --topology config/topology/basic_topology.json
   ```

3. **Open browser**: http://localhost:8085

4. **Capture screenshots** of each section using Windows Snipping Tool (Win + Shift + S)

5. **Save to**: `docs/images/` with the exact filenames listed above

6. **Optimize** images to keep file sizes under 500KB

---

## See Full Guide

For detailed instructions, see [README-SCREENSHOTS.md](./README-SCREENSHOTS.md)

---

## Alternative: Temporary Placeholders

Until screenshots are available, the README will show broken image links. This is expected and will be resolved when images are added.

To use temporary placeholders, you can replace the image paths in README.md with:

```markdown
![Dashboard Overview](https://via.placeholder.com/1200x675/1e40af/ffffff?text=Dashboard+Overview)
```

But actual screenshots are strongly recommended for the best user experience.

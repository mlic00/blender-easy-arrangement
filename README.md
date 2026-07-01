![Easy Arrangement](images/banner.png)

# Easy Arrangement

A Blender add-on for arranging multiple selected objects into precise **linear**, **stair-step**, **circular**, **grid**, **between**, or **curve-based** layouts — directly from a clean sidebar panel, with live preview and one-click reset.

[![Blender](https://img.shields.io/badge/Blender-4.2%2B-orange?logo=blender)](https://www.blender.org/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)

---

## ✨ Features

### Linear Arrangement
Distributes objects along any axis (X, Y, or Z) with configurable spacing. Optionally uses each object's actual bounding box size to calculate gaps automatically, so mixed-size objects stay evenly spaced without manual adjustments.

### Stair Arrangement
Extends the linear layout with a secondary step axis and height offset, building staircase-style sequences. Step height and step axis are controlled independently — useful for architectural steps, rising formations, or layered compositions.

### Circular Arrangement
Places objects around a center point on a chosen plane (XY, XZ, or YZ).

- **Center** can be the 3D Cursor, the active object, or any object in the scene
- **Radius** can be uniform, gradually increasing from a start to an end value, or incremented by a fixed step per object
- **Angle** distribution supports both per-object angle and total arc angle modes

Rotation handling — three modes:

| Mode | Behavior |
|------|----------|
| **Default** | Objects keep their original orientation |
| **Rotate Along Axis** | Each object rotates progressively around the circular axis |
| **Rotate Toward Center** | Each object automatically faces the center point |

---

### *(New in v0.2.2)*

### Between Arrangement
Distributes selected objects in a straight line between the **active object** and a chosen **target object**. The target can be part of the selection or not.The **target** is specified separately in the panel.

- Two distribution modes: **Center** (evenly spaced by object centers) or **Gap** (evenly spaced by surface distance)
- The target object acts as the endpoint — objects fill the space between active and target
- **Rotation Offset** and **Random** arrangement are both supported

### Grid Arrangement
Arranges objects into a configurable grid of rows and columns, on any of the three coordinate planes (XY, XZ, YZ).

- Row count, column count, and spacing between both are independently adjustable
- **Rotation Offset** applies uniformly across all cells
- **Random** arrangement is supported — shuffles object positions within the grid

### Curve Arrangement
Places objects along any drawn curve path in the scene.

- Two distribution modes: **Center** (objects centered along the curve) or **Gap** (distributed with a fixed gap between surfaces)
- Orientation control: **Default** (keeps original rotation) or **Tangent** — with six tangent direction options to align each object to the curve direction
- **Rotation Offset** and **Random** arrangement are both supported

---

### Shared Features (all arrangement types)

#### Rotation Offset
An independent X / Y / Z rotation offset applied on top of any arrangement — available across Linear, Stair, Circular, Between, Grid, and Curve modes.

#### Random Arrangement *(New in v0.2.2)*
Randomizes object positions within the current arrangement. Works proportionally to each mode's layout, so the result remains spatially coherent rather than fully scattered. Available in all six arrangement types.

---

## 🖼️ Interface

![Panel overview — Linear, Stair, and Circular modes](images/ui_overview_02.png)

![Panel overview — Linear, Stair, and Circular modes](images/ui_overview_03.png)

The panel adapts to the selected arrangement type, showing only the settings relevant to that mode — plus the shared Rotation Offset and Random sections at the bottom.

---

## 📦 Installation

1. Download the latest `.zip` from the [Releases](../../releases) page.
2. In Blender: **Edit > Preferences > Get Extensions > Install from Disk**.
3. Select the downloaded `.zip` file.
4. The panel appears in the **View3D Sidebar** under the **Easy Arrang** tab.

Requires **Blender 4.2 or newer**.

---

## 🚀 Quick Start

1. Select two or more objects in the 3D Viewport.
2. Open the **Easy Arrang** tab in the sidebar (`N` to toggle).
3. Choose an arrangement type.
4. Adjust the relevant settings.
5. Click **Apply** — or enable **Live Update** to preview changes in real time.
6. Click **Reset** to return objects to their position at the last Apply.

---

## 🐞 Bug Reports & Feedback

**[github.com/mlic00/blender-easy-arrangement/issues](https://github.com/mlic00/blender-easy-arrangement/issues)**

---

## 📄 License

GPL-3.0-or-later — see [LICENSE](LICENSE).

---

## 🙌 Author

Created and maintained by **mlico**.

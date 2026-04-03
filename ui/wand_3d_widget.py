"""
ui/wand_3d_widget.py — 3D Wand orientation visualizer.

Physical layout:
    - MPU6050 at top, ESP32 at bottom, ~25cm total length.
    - The wand's long axis = Z axis in the GL scene (points up when wand points up).

Orientation logic:
    - Uses absolute setTransform() each frame → NO DRIFT, NO GLITCHING.
    - Gravity vector from accel defines the wand's "down" direction.
    - When wand held upright: MPU Z-axis ≈ -1g (pointing away from gravity).
    - When wand laid flat: MPU X or Y axis ≈ ±1g.

Architecture (SKILL.md §2A):
    - Pure VIEW widget. No data processing.
    - Receives orientation data via update_orientation() from Handler signal.
"""

from __future__ import annotations
import math
import numpy as np
import pyqtgraph.opengl as gl
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QVBoxLayout, QWidget


# Colors (RGBA float 0-1)
_CLR_STICK  = (0.45, 0.30, 0.18, 1.0)   # dark wood brown
_CLR_ESP32  = (0.05, 0.45, 0.15, 1.0)   # green PCB
_CLR_MPU    = (0.10, 0.30, 0.70, 1.0)   # blue PCB
_CLR_CHIP   = (0.15, 0.15, 0.15, 1.0)   # dark IC chip
_CLR_PIN    = (0.75, 0.75, 0.20, 1.0)   # gold pins
_CLR_USB    = (0.60, 0.60, 0.60, 1.0)   # silver USB port


def _make_box(cx: float, cy: float, cz: float,
              sx: float, sy: float, sz: float,
              color: tuple) -> gl.GLMeshItem:
    """Create a box mesh centered at (cx, cy, cz)."""
    hx, hy, hz = sx / 2, sy / 2, sz / 2
    verts = np.array([
        [cx-hx, cy-hy, cz-hz], [cx+hx, cy-hy, cz-hz],
        [cx+hx, cy+hy, cz-hz], [cx-hx, cy+hy, cz-hz],
        [cx-hx, cy-hy, cz+hz], [cx+hx, cy-hy, cz+hz],
        [cx+hx, cy+hy, cz+hz], [cx-hx, cy+hy, cz+hz],
    ], dtype=np.float32)
    faces = np.array([
        [0,1,2],[0,2,3], [4,6,5],[4,7,6],
        [0,4,5],[0,5,1], [2,6,7],[2,7,3],
        [0,3,7],[0,7,4], [1,5,6],[1,6,2],
    ], dtype=np.uint32)
    colors = np.tile(color, (len(faces), 1))
    return gl.GLMeshItem(vertexes=verts, faces=faces, faceColors=colors.astype(np.float32),
                         smooth=False, drawEdges=True, edgeColor=(0.2, 0.2, 0.2, 0.4))


def _make_cylinder(cx: float, cy: float, z_bot: float,
                   radius: float, height: float, n: int,
                   color: tuple) -> gl.GLMeshItem:
    """Create a cylinder along Z axis."""
    theta = np.linspace(0, 2 * np.pi, n + 1)
    x = cx + radius * np.cos(theta)
    y = cy + radius * np.sin(theta)
    vb = np.column_stack([x, y, np.full_like(x, z_bot)])
    vt = np.column_stack([x, y, np.full_like(x, z_bot + height)])
    verts = np.vstack([vb, vt]).astype(np.float32)
    m = n + 1
    faces = []
    for i in range(n):
        j = i + 1
        faces += [[i, j, m+j], [i, m+j, m+i]]
    faces = np.array(faces, dtype=np.uint32)
    colors = np.tile(color, (len(faces), 1))
    return gl.GLMeshItem(vertexes=verts, faces=faces, faceColors=colors.astype(np.float32),
                         smooth=True, drawEdges=False)


def _rotation_matrix_from_gravity(ax: float, ay: float, az: float) -> np.ndarray:
    """
    Compute a 4x4 rotation matrix that aligns the wand's +Z axis (tip = up)
    with the direction OPPOSITE to gravity.

    When the wand is held upright:
        The MPU sits at the top → gravity pulls DOWN along wand length.
        Measured accel ≈ (0, 0, +1g) in MPU frame when pointing up
        (sensor Z faces up = reports +1g).

    We want the GL wand's Z (length) axis to point along -gravity direction.
    """
    # Normalize gravity vector
    g = np.array([ax, ay, az], dtype=float)
    norm = np.linalg.norm(g)
    if norm < 1e-6:
        return np.eye(4)
    g = g / norm

    # The wand's "up" direction = opposite of gravity
    # (when pointing up, accel vector points up because it measures reaction)
    wand_up = -g   # direction the tip should face
    # wand_up = g  # flip if inverted

    # GL wand model's natural up direction = +Z
    z_axis = np.array([0.0, 0.0, 1.0])

    # Rotation axis = cross product of z_axis and wand_up
    rot_axis = np.cross(z_axis, wand_up)
    sin_angle = np.linalg.norm(rot_axis)
    cos_angle = np.dot(z_axis, wand_up)

    if sin_angle < 1e-6:
        # Already aligned (or exactly opposite)
        if cos_angle > 0:
            return np.eye(4)
        else:
            # 180° flip around X
            m = np.eye(4)
            m[1, 1] = -1
            m[2, 2] = -1
            return m

    rot_axis = rot_axis / sin_angle
    angle = math.atan2(sin_angle, cos_angle)

    # Rodrigues' rotation formula → 3x3 matrix
    c, s = math.cos(angle), math.sin(angle)
    t = 1 - c
    ux, uy, uz = rot_axis
    R = np.array([
        [t*ux*ux + c,    t*ux*uy - s*uz, t*ux*uz + s*uy],
        [t*ux*uy + s*uz, t*uy*uy + c,    t*uy*uz - s*ux],
        [t*ux*uz - s*uy, t*uy*uz + s*ux, t*uz*uz + c   ],
    ])

    # Embed in 4x4 homogeneous matrix (column-major for pyqtgraph)
    M = np.eye(4)
    M[:3, :3] = R
    return M


class Wand3DWidget(QWidget):
    """3D wand visualization using OpenGL."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Top bar with Reset button ──────────────────────────────
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(6, 4, 6, 0)
        top_bar.addStretch()
        self.btn_reset = QPushButton("⌂ HOME")
        self.btn_reset.setFixedSize(70, 24)
        self.btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reset.setStyleSheet(
            "QPushButton { background-color: #f3f4f6; border: 1px solid #d1d5db; "
            "border-radius: 5px; font-size: 10px; font-weight: bold; color: #374151; } "
            "QPushButton:hover { background-color: #e5e7eb; border-color: #9ca3af; }"
        )
        self.btn_reset.clicked.connect(self._reset_camera)
        top_bar.addWidget(self.btn_reset)
        outer.addLayout(top_bar)

        # ── OpenGL view ────────────────────────────────────────────
        self.gl_view = gl.GLViewWidget()
        self.gl_view.setBackgroundColor("w")  # white
        self.gl_view.setCameraPosition(distance=9, elevation=20, azimuth=130)
        outer.addWidget(self.gl_view, stretch=1)

        # Reference grid (dark on white bg)
        grid = gl.GLGridItem()
        grid.setSize(6, 6, 1)
        grid.setSpacing(0.5, 0.5, 1)
        grid.setColor((0, 0, 0, 35))
        self.gl_view.addItem(grid)

        # Axis indicator (world frame, does not rotate)
        axis = gl.GLAxisItem()
        axis.setSize(1.2, 1.2, 1.2)
        self.gl_view.addItem(axis)

        # Build model — all parts stored in a parent transform item
        self._parts: list[gl.GLMeshItem] = []
        self._build_wand()

        # Low-pass filter state for smoothing (α = 0.15)
        self._smooth_ax = 0.0
        self._smooth_ay = 0.0
        self._smooth_az = 1.0   # resting: gravity points "down" along Z
        self._ALPHA = 0.15      # smoothing factor (lower = smoother, more lag)
        self._HOME_DIST = 9
        self._HOME_ELEV = 20
        self._HOME_AZIM = 130

    # ── Public API ───────────────────────────────────────────────────────

    def _reset_camera(self) -> None:
        """Reset the camera to the default home position."""
        self.gl_view.setCameraPosition(
            distance=self._HOME_DIST,
            elevation=self._HOME_ELEV,
            azimuth=self._HOME_AZIM,
        )

    def update_orientation(self, buffer_snapshot: list) -> None:
        """Receive buffer snapshot and orient wand from latest sample.

        Uses absolute setTransform() — no accumulation, no drift.
        Low-pass filter removes noise/glitching.
        """
        if not buffer_snapshot:
            return

        latest = buffer_snapshot[-1]  # [aX, aY, aZ, gX, gY, gZ]
        ax_raw, ay_raw, az_raw = latest[0], latest[1], latest[2]

        # Fix orientation axes:
        # The MPU6050 is mounted flat on the wand, so the wand's long axis is the 
        # sensor's Y axis.
        ax_mapped = -ax_raw  # Invert sensor X to GL X to fix roll (left/right)
        ay_mapped = az_raw
        az_mapped = -ay_raw  # Invert sensor Y to GL Z to fix pitch (up/down)

        # Low-pass filter (exponential moving average) to smooth jitter
        self._smooth_ax += self._ALPHA * (ax_mapped - self._smooth_ax)
        self._smooth_ay += self._ALPHA * (ay_mapped - self._smooth_ay)
        self._smooth_az += self._ALPHA * (az_mapped - self._smooth_az)

        # Computation of absolute rotation matrix
        M = _rotation_matrix_from_gravity(
            self._smooth_ax, self._smooth_ay, self._smooth_az
        )

        # Dynamic acceleration (raw minus smoothed gravity)
        # We use this to simulate physical space translation ("flying" effect)
        dyn_x = ax_mapped - self._smooth_ax
        dyn_y = ay_mapped - self._smooth_ay
        dyn_z = az_mapped - self._smooth_az
        
        mult = 2.5 # Amplification for visual effect
        tx = dyn_x * mult
        ty = dyn_y * mult
        tz = dyn_z * mult

        # Apply to ALL wand parts as absolute transform + translation
        for part in self._parts:
            # Note: pyqtgraph uses column-major QMatrix4x4. We can safely set
            # the translation directly into the 4x4 numpy array:
            M[0, 3] = tx
            M[1, 3] = ty
            M[2, 3] = tz
            part.setTransform(M)

    # ── Model Construction ───────────────────────────────────────────────

    def _build_wand(self) -> None:
        """
        Wand layout along Z axis (~5 GL units = 25cm, 1 unit = 5cm):
            z = 0.0..1.0  → ESP32 board (bottom)
            z = 1.0..4.2  → wooden stick body
            z = 4.2..5.0  → MPU6050 module (top)
        Centered at origin (offset_z = -2.5).
        """
        oz = 0.0  # Pivot point set to the handle (ESP32 bottom) instead of the middle

        # ── ESP32 (bottom) ─────────────────────────
        self._add(_make_box(0, 0, 0.50+oz, 0.50, 0.28, 1.00, _CLR_ESP32))   # PCB
        self._add(_make_box(0, 0.05, 0.50+oz, 0.22, 0.04, 0.30, _CLR_CHIP)) # IC
        self._add(_make_box(0, 0, 0.05+oz, 0.18, 0.10, 0.10, _CLR_USB))     # USB
        self._add(_make_box(-0.22, 0, 0.50+oz, 0.04, 0.04, 0.80, _CLR_PIN)) # pins L
        self._add(_make_box(0.22, 0, 0.50+oz, 0.04, 0.04, 0.80, _CLR_PIN))  # pins R

        # ── Stick body (middle) ────────────────────
        self._add(_make_cylinder(0, 0, 1.0+oz, 0.10, 3.2, 16, _CLR_STICK))

        # ── MPU6050 (top) ──────────────────────────
        self._add(_make_box(0, 0, 4.50+oz, 0.36, 0.25, 0.60, _CLR_MPU))     # PCB
        self._add(_make_box(0, 0.06, 4.50+oz, 0.16, 0.04, 0.18, _CLR_CHIP)) # sensor IC
        self._add(_make_box(0, 0, 4.15+oz, 0.30, 0.04, 0.06, _CLR_PIN))     # pin header

    def _add(self, mesh: gl.GLMeshItem) -> None:
        self._parts.append(mesh)
        self.gl_view.addItem(mesh)

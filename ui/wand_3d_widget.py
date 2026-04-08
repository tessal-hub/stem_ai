"""
ui/wand_3d_widget.py — 3D Wand orientation visualizer.

Physical layout:
    - MPU6050 at top, ESP32 at bottom, ~25 cm total length.
    - The wand's long axis = Z axis in the GL scene (points up when wand points up).

Orientation logic:
    - Uses absolute setTransform() each frame → NO DRIFT, NO GLITCHING.
    - Complementary filter: 96 % gyro (smooth) + 4 % accel (drift correction).
    - Yaw is gyro-only (no magnetometer reference).

Architecture:
    - Pure VIEW widget. No data processing.
    - Receives orientation data via update_orientation() from Handler signal.
"""

from __future__ import annotations

import logging
import math
import time

import numpy as np
import pyqtgraph.opengl as gl
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QVBoxLayout, QWidget

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Colors (RGBA float 0–1)
# ---------------------------------------------------------------------------
_CLR_STICK = (0.45, 0.30, 0.18, 1.0)   # dark wood brown
_CLR_ESP32 = (0.05, 0.45, 0.15, 1.0)   # green PCB
_CLR_MPU   = (0.10, 0.30, 0.70, 1.0)   # blue PCB
_CLR_CHIP  = (0.15, 0.15, 0.15, 1.0)   # dark IC chip
_CLR_PIN   = (0.75, 0.75, 0.20, 1.0)   # gold pins
_CLR_USB   = (0.60, 0.60, 0.60, 1.0)   # silver USB port

# ---------------------------------------------------------------------------
# Wand geometry constants  (1 GL unit ≈ 5 cm)
# ---------------------------------------------------------------------------
_ESP32_W,  _ESP32_D,  _ESP32_H  = 0.50, 0.28, 1.00
_STICK_R,  _STICK_H,  _STICK_N  = 0.10, 3.20, 16
_MPU_W,    _MPU_D,    _MPU_H    = 0.36, 0.25, 0.60
_Z_ESP32_CENTER = 0.50   # centre of ESP32 along Z
_Z_STICK_BOT    = 1.00   # stick starts here
_Z_MPU_CENTER   = 4.50   # centre of MPU along Z

# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------
_STYLE_RESET_BTN = (
    "QPushButton {"
    "  background-color: #f3f4f6;"
    "  border: 1px solid #d1d5db;"
    "  border-radius: 5px;"
    "  font-size: 10px;"
    "  font-weight: bold;"
    "  color: #374151;"
    "}"
    "QPushButton:hover {"
    "  background-color: #e5e7eb;"
    "  border-color: #9ca3af;"
    "}"
)

# ---------------------------------------------------------------------------
# Mesh helpers
# ---------------------------------------------------------------------------

def _color_array(color: tuple, n_faces: int) -> np.ndarray:
    """Return an (n_faces, 4) float32 array filled with *color*."""
    return np.broadcast_to(
        np.array(color, dtype=np.float32), (n_faces, 4)
    ).copy()


def _make_box(
    cx: float, cy: float, cz: float,
    sx: float, sy: float, sz: float,
    color: tuple,
) -> gl.GLMeshItem:
    """Axis-aligned box mesh centred at (cx, cy, cz) with side lengths (sx, sy, sz)."""
    hx, hy, hz = sx / 2, sy / 2, sz / 2
    verts = np.array([
        [cx-hx, cy-hy, cz-hz], [cx+hx, cy-hy, cz-hz],
        [cx+hx, cy+hy, cz-hz], [cx-hx, cy+hy, cz-hz],
        [cx-hx, cy-hy, cz+hz], [cx+hx, cy-hy, cz+hz],
        [cx+hx, cy+hy, cz+hz], [cx-hx, cy+hy, cz+hz],
    ], dtype=np.float32)
    faces = np.array([
        [0,1,2],[0,2,3],  # bottom
        [4,6,5],[4,7,6],  # top
        [0,4,5],[0,5,1],  # front
        [2,6,7],[2,7,3],  # back
        [0,3,7],[0,7,4],  # left
        [1,5,6],[1,6,2],  # right
    ], dtype=np.uint32)
    return gl.GLMeshItem(
        vertexes=verts,
        faces=faces,
        faceColors=_color_array(color, len(faces)),
        smooth=False,
        drawEdges=True,
        edgeColor=(0.2, 0.2, 0.2, 0.4),
    )


def _make_cylinder(
    cx: float, cy: float, z_bot: float,
    radius: float, height: float, n: int,
    color: tuple,
) -> gl.GLMeshItem:
    """Closed-side cylinder along +Z starting at z_bot."""
    theta = np.linspace(0, 2 * math.pi, n + 1)
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
    faces_arr = np.array(faces, dtype=np.uint32)

    return gl.GLMeshItem(
        vertexes=verts,
        faces=faces_arr,
        faceColors=_color_array(color, len(faces_arr)),
        smooth=True,
        drawEdges=False,
    )


# ---------------------------------------------------------------------------
# Math helpers
# ---------------------------------------------------------------------------

def _euler_to_transform(
    roll_deg: float, pitch_deg: float, yaw_deg: float
) -> gl.Transform3D:
    """
    Convert ZYX Euler angles (degrees) → pyqtgraph Transform3D.

    Convention (intrinsic):
        Roll  — rotation around X (left/right tilt)
        Pitch — rotation around Y (forward/backward tilt)
        Yaw   — rotation around Z (spin around vertical)
    """
    r = math.radians(roll_deg)
    p = math.radians(pitch_deg)
    y = math.radians(yaw_deg)

    cr, sr = math.cos(r), math.sin(r)
    cp, sp = math.cos(p), math.sin(p)
    cy, sy = math.cos(y), math.sin(y)

    # Combined: Rz(yaw) · Ry(pitch) · Rx(roll)
    rot = np.array([
        [cy*cp,  cy*sp*sr - sy*cr,  cy*sp*cr + sy*sr],
        [sy*cp,  sy*sp*sr + cy*cr,  sy*sp*cr - cy*sr],
        [-sp,    cp*sr,             cp*cr            ],
    ], dtype=np.float32)

    M = np.eye(4, dtype=np.float32)
    M[:3, :3] = rot
    return gl.Transform3D(M)


# ---------------------------------------------------------------------------
# Widget
# ---------------------------------------------------------------------------

class Wand3DWidget(QWidget):
    """3D wand visualization using OpenGL."""

    # ── Camera home ─────────────────────────────────────────────────────
    _HOME_DIST: float = 9.0
    _HOME_ELEV: float = 20.0
    _HOME_AZIM: float = 130.0

    # ── Complementary-filter tuning ──────────────────────────────────────
    # 96 % gyro (smooth, real-time) + 4 % accel (long-term drift correction).
    # Raise _ACCEL_WEIGHT to reduce drift at the cost of more noise.
    _GYRO_WEIGHT:  float = 0.96
    _ACCEL_WEIGHT: float = 0.04

    # Nominal sensor sample period (50 Hz ESP32 output).
    _DT: float = 1 / 50
    _MIN_DT: float = 1 / 240
    _MAX_DT: float = 0.1

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Top bar ────────────────────────────────────────────────────
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(6, 4, 6, 0)
        top_bar.addStretch()

        self.btn_reset = QPushButton("⌂ HOME")
        self.btn_reset.setFixedSize(70, 24)
        self.btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reset.setStyleSheet(_STYLE_RESET_BTN)
        self.btn_reset.clicked.connect(self.reset_camera)
        top_bar.addWidget(self.btn_reset)
        outer.addLayout(top_bar)

        # ── OpenGL viewport ────────────────────────────────────────────
        self.gl_view = gl.GLViewWidget()
        self.gl_view.setBackgroundColor("w")
        self.gl_view.setCameraPosition(
            distance=self._HOME_DIST,
            elevation=self._HOME_ELEV,
            azimuth=self._HOME_AZIM,
        )
        outer.addWidget(self.gl_view, stretch=1)

        # Reference grid
        grid = gl.GLGridItem()
        grid.setSize(6, 6, 1)
        grid.setSpacing(0.5, 0.5, 1)
        grid.setColor((0, 0, 0, 35))
        self.gl_view.addItem(grid)

        # World-frame axis indicator (does not rotate with the wand)
        axis = gl.GLAxisItem()
        axis.setSize(1.2, 1.2, 1.2)
        self.gl_view.addItem(axis)

        # Build 3-D wand model
        self._parts: list[gl.GLMeshItem] = []
        self._build_wand()

        # ── Orientation state ─────────────────────────────────────────
        self._roll  = 0.0   # degrees
        self._pitch = 0.0   # degrees
        self._yaw   = 0.0   # degrees
        self._last_update_ts: float | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def reset_camera(self) -> None:
        """Restore the GL camera to its default home position."""
        self.gl_view.setCameraPosition(
            distance=self._HOME_DIST,
            elevation=self._HOME_ELEV,
            azimuth=self._HOME_AZIM,
        )

    def update_orientation(
        self,
        ax: float, ay: float, az: float,
        gx: float, gy: float, gz: float,
    ) -> None:
        """
        Update the wand's 3-D orientation from normalised 6-axis IMU data.

        Uses a complementary filter:
            90 % gyro integration  — fast, smooth, but accumulates drift.
            10 % accel correction  — removes long-term roll/pitch drift.
            Yaw is gyro-only (no magnetometer available).

        Args:
            ax, ay, az: Normalised acceleration (±1.0 g range).
            gx, gy, gz: Angular velocity in degrees/second.
        """
        now = time.perf_counter()
        if self._last_update_ts is None:
            dt = self._DT
        else:
            dt = max(self._MIN_DT, min(now - self._last_update_ts, self._MAX_DT))
        self._last_update_ts = now

        # ── 1. Gyro integration ────────────────────────────────────────
        self._roll += gx * dt
        self._pitch += gy * dt
        self._yaw += gz * dt

        # ── 2. Accel-derived roll & pitch ──────────────────────────────
        accel_roll  = math.degrees(math.atan2(ay, az))
        accel_pitch = math.degrees(
            math.atan2(-ax, math.hypot(ay, az) + 1e-6)
        )

        # ── 3. Complementary blend ─────────────────────────────────────
        blend = self._GYRO_WEIGHT ** max(1.0, dt / self._DT)
        accel_blend = 1.0 - blend
        self._roll = blend * self._roll + accel_blend * accel_roll
        self._pitch = blend * self._pitch + accel_blend * accel_pitch

        # ── 4. Apply to all mesh parts ─────────────────────────────────
        try:
            M = _euler_to_transform(self._roll, self._pitch, self._yaw)
            for part in self._parts:
                part.setTransform(M)
        except Exception:
            log.exception("Wand3DWidget: failed to apply orientation transform")

    # ------------------------------------------------------------------
    # Model construction
    # ------------------------------------------------------------------

    def _build_wand(self) -> None:
        """
        Assemble the wand model along the +Z axis.

        Layout (1 GL unit ≈ 5 cm):
            z = 0.0–1.0   ESP32 board  (handle / bottom)
            z = 1.0–4.2   wooden stick (shaft)
            z = 4.2–5.0   MPU6050      (tip / top)

        Pivot is at z = 0 (the handle base).
        """
        z = _Z_ESP32_CENTER

        # ESP32 board ──────────────────────────────────────────────────
        self._add(_make_box(0,     0,    z,      _ESP32_W, _ESP32_D, _ESP32_H, _CLR_ESP32))
        self._add(_make_box(0,     0.05, z,      0.22,     0.04,     0.30,     _CLR_CHIP))
        self._add(_make_box(0,     0,    0.05,   0.18,     0.10,     0.10,     _CLR_USB))
        self._add(_make_box(-0.22, 0,    z,      0.04,     0.04,     0.80,     _CLR_PIN))
        self._add(_make_box( 0.22, 0,    z,      0.04,     0.04,     0.80,     _CLR_PIN))

        # Stick shaft ──────────────────────────────────────────────────
        self._add(_make_cylinder(0, 0, _Z_STICK_BOT, _STICK_R, _STICK_H, _STICK_N, _CLR_STICK))

        # MPU6050 module ───────────────────────────────────────────────
        z = _Z_MPU_CENTER
        self._add(_make_box(0, 0,    z,      _MPU_W, _MPU_D, _MPU_H, _CLR_MPU))
        self._add(_make_box(0, 0.06, z,      0.16,   0.04,   0.18,   _CLR_CHIP))
        self._add(_make_box(0, 0,    z-0.35, 0.30,   0.04,   0.06,   _CLR_PIN))

    def _add(self, mesh: gl.GLMeshItem) -> None:
        """Register a mesh part and add it to the GL scene."""
        self._parts.append(mesh)
        self.gl_view.addItem(mesh)
# -*- coding: utf-8 -*-
import os, sys, math, json, time, traceback
from pathlib import Path
import importlib.util

LUMAPI = r"D:\Program Files\Lumerical\v202\api\python\lumapi.py"
spec = importlib.util.spec_from_file_location("lumapi", LUMAPI)
lumapi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lumapi)

META = {
  "category": "C2对称结构",
  "name": "双脊",
  "safe": "dual_ridges",
  "symmetry": "C2，旋转 180° 重合",
  "reason": "适合和波导/平台结合",
  "breaks": "脊宽差、顶槽差、位置差",
  "period_um": 0.9,
  "height_um": 0.42,
  "substrate_um": 1.0,
  "lambda_start_nm": 900,
  "lambda_stop_nm": 1700
}
PATHS = {
  "folder": "H:\\FDTD outcome\\struct\\C2对称结构\\双脊",
  "fsp": "H:\\FDTD outcome\\struct\\C2对称结构\\双脊\\dual_ridges_CodexAstra_20260426_231746.fsp",
  "png": "H:\\FDTD outcome\\struct\\C2对称结构\\双脊\\dual_ridges_prelim_T_20260426_231746.png",
  "py": "H:\\FDTD outcome\\struct\\C2对称结构\\双脊\\dual_ridges_build_20260426_231746.py",
  "note": "H:\\FDTD outcome\\struct\\C2对称结构\\双脊\\dual_ridges_note_20260426_231746.md",
  "csv": "H:\\FDTD outcome\\struct\\C2对称结构\\双脊\\dual_ridges_prelim_T_20260426_231746.csv",
  "result": "H:\\FDTD outcome\\struct\\C2对称结构\\双脊\\dual_ridges_result_20260426_231746.json"
}

NM = 1e-9
UM = 1e-6

def lsf_str(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'

def add_rect(fdtd, name, x, y, xs, ys, zmin, zmax, material, rot=0, mesh=None):
    fdtd.addrect()
    fdtd.set("name", name)
    fdtd.set("x", x); fdtd.set("y", y)
    fdtd.set("x span", xs); fdtd.set("y span", ys)
    fdtd.set("z min", zmin); fdtd.set("z max", zmax)
    fdtd.set("material", material)
    if rot:
        fdtd.set("first axis", "z")
        fdtd.set("rotation 1", rot)
    if mesh is not None:
        fdtd.set("override mesh order from material database", 1)
        fdtd.set("mesh order", mesh)

def add_circle(fdtd, name, x, y, rx, ry, zmin, zmax, material, rot=0, mesh=None):
    fdtd.addcircle()
    fdtd.set("name", name)
    fdtd.set("x", x); fdtd.set("y", y)
    fdtd.set("x radius", rx); fdtd.set("y radius", ry)
    fdtd.set("z min", zmin); fdtd.set("z max", zmax)
    fdtd.set("material", material)
    if rot:
        fdtd.set("first axis", "z")
        fdtd.set("rotation 1", rot)
    if mesh is not None:
        fdtd.set("override mesh order from material database", 1)
        fdtd.set("mesh order", mesh)

def poly_points(n, radius, rotation_deg=0):
    pts = []
    rot = math.radians(rotation_deg)
    for i in range(n):
        a = rot + 2*math.pi*i/n
        pts.append([radius*math.cos(a), radius*math.sin(a)])
    return pts

def add_poly(fdtd, name, pts, zmin, zmax, material):
    fdtd.addpoly()
    fdtd.set("name", name)
    fdtd.set("vertices", pts)
    fdtd.set("z min", zmin); fdtd.set("z max", zmax)
    fdtd.set("material", material)

def add_common(fdtd):
    P = META["period_um"] * UM
    H = META["height_um"] * UM
    sub = META["substrate_um"] * UM
    fdtd.addfdtd()
    fdtd.set("dimension", "3D")
    fdtd.set("x", 0); fdtd.set("y", 0)
    fdtd.set("x span", P); fdtd.set("y span", P)
    fdtd.set("z min", -0.55*sub); fdtd.set("z max", H + 1.2*UM)
    fdtd.set("x min bc", "Periodic"); fdtd.set("x max bc", "Periodic")
    fdtd.set("y min bc", "Periodic"); fdtd.set("y max bc", "Periodic")
    fdtd.set("z min bc", "PML"); fdtd.set("z max bc", "PML")
    fdtd.set("mesh accuracy", 1)
    fdtd.set("simulation time", 1000e-15)
    add_rect(fdtd, "SiO2_substrate", 0, 0, P, P, -sub, 0, "SiO2 (Glass)")
    fdtd.addplane()
    fdtd.set("name", "source")
    fdtd.set("injection axis", "z")
    fdtd.set("direction", "Backward")
    fdtd.set("x span", P); fdtd.set("y span", P)
    fdtd.set("z", H + 0.8*UM)
    fdtd.set("wavelength start", META["lambda_start_nm"]*NM)
    fdtd.set("wavelength stop", META["lambda_stop_nm"]*NM)
    fdtd.addpower()
    fdtd.set("name", "T")
    fdtd.set("monitor type", "2D Z-normal")
    fdtd.set("x span", P); fdtd.set("y span", P)
    fdtd.set("z", -0.25*UM)
    fdtd.set("frequency points", 501)

def build_geometry(fdtd):
    P = META["period_um"] * UM
    H = META["height_um"] * UM
    Si = "Si (Silicon - Palik)"
    air = "air"
    safe = META["safe"]
    if safe == "dual_pillars":
        for x in [-0.18*UM, 0.18*UM]:
            add_circle(fdtd, "Si_pillar", x, 0, 0.105*UM, 0.16*UM, 0, H, Si)
    elif safe == "dual_ridges":
        add_rect(fdtd, "Si_slab", 0, 0, 0.74*UM, 0.74*UM, 0, 0.08*UM, Si)
        for x in [-0.16*UM, 0.16*UM]:
            add_rect(fdtd, "Si_ridge", x, 0, 0.11*UM, 0.56*UM, 0.08*UM, H, Si)
    elif safe == "dual_disks":
        for x in [-0.18*UM, 0.18*UM]:
            add_circle(fdtd, "Si_disk", x, 0, 0.145*UM, 0.145*UM, 0, H, Si)
    elif safe == "dual_beams":
        for x in [-0.21*UM, 0.21*UM]:
            add_rect(fdtd, "Si_beam", x, 0, 0.30*UM, 0.12*UM, 0, H, Si)
    elif safe == "dual_ellipses":
        add_circle(fdtd, "Si_ellipse_L", -0.18*UM, 0, 0.09*UM, 0.22*UM, 0, H, Si, -25)
        add_circle(fdtd, "Si_ellipse_R",  0.18*UM, 0, 0.09*UM, 0.22*UM, 0, H, Si, 25)
    elif safe == "cross":
        add_rect(fdtd, "Si_cross_vertical", 0, 0, 0.16*UM, 0.58*UM, 0, H, Si)
        add_rect(fdtd, "Si_cross_horizontal", 0, 0, 0.58*UM, 0.16*UM, 0, H, Si)
    elif safe == "square_ring":
        add_rect(fdtd, "Si_outer_square", 0, 0, 0.58*UM, 0.58*UM, 0, H, Si)
        add_rect(fdtd, "air_inner_square", 0, 0, 0.30*UM, 0.30*UM, -1*NM, H+1*NM, air, mesh=1)
    elif safe == "square_block":
        add_rect(fdtd, "Si_square_block", 0, 0, 0.55*UM, 0.55*UM, 0, H, Si)
    elif safe == "four_pillar_cluster":
        for x,y in [(0.20*UM,0),(0,0.20*UM),(-0.20*UM,0),(0,-0.20*UM)]:
            add_circle(fdtd, "Si_pillar", x, y, 0.095*UM, 0.095*UM, 0, H, Si)
    elif safe == "four_hole_square":
        add_rect(fdtd, "Si_square_host", 0, 0, 0.60*UM, 0.60*UM, 0, H, Si)
        for x,y in [(-0.16*UM,-0.16*UM),(0.16*UM,-0.16*UM),(-0.16*UM,0.16*UM),(0.16*UM,0.16*UM)]:
            add_circle(fdtd, "air_hole", x, y, 0.055*UM, 0.055*UM, -1*NM, H+1*NM, air, mesh=1)
    elif safe == "four_slit_ring":
        add_circle(fdtd, "Si_outer_ring", 0,0,0.30*UM,0.30*UM,0,H,Si)
        add_circle(fdtd, "air_inner_ring", 0,0,0.19*UM,0.19*UM,-1*NM,H+1*NM,air,mesh=1)
        for a in [0,90,180,270]:
            x = 0.27*UM*math.cos(math.radians(a)); y = 0.27*UM*math.sin(math.radians(a))
            add_rect(fdtd, "air_slit", x, y, 0.06*UM, 0.18*UM, -1*NM, H+1*NM, air, a, mesh=1)
    elif safe == "hex_block":
        add_poly(fdtd, "Si_hex_block", poly_points(6, 0.31*UM, 30), 0, H, Si)
    elif safe == "six_pillar_ring":
        for i in range(6):
            a = 2*math.pi*i/6
            add_circle(fdtd, "Si_pillar", 0.24*UM*math.cos(a), 0.24*UM*math.sin(a), 0.075*UM, 0.075*UM, 0, H, Si)
    elif safe == "six_arm_star":
        for a in [0,60,120]:
            add_rect(fdtd, "Si_arm", 0, 0, 0.11*UM, 0.62*UM, 0, H, Si, a)
    elif safe == "six_hole_ring":
        add_circle(fdtd, "Si_disk_host", 0,0,0.32*UM,0.32*UM,0,H,Si)
        for i in range(6):
            a = 2*math.pi*i/6
            add_circle(fdtd, "air_hole", 0.20*UM*math.cos(a), 0.20*UM*math.sin(a), 0.045*UM, 0.045*UM, -1*NM, H+1*NM, air, mesh=1)
    elif safe == "six_slit_ring":
        add_circle(fdtd, "Si_outer_ring", 0,0,0.31*UM,0.31*UM,0,H,Si)
        add_circle(fdtd, "air_inner_ring", 0,0,0.20*UM,0.20*UM,-1*NM,H+1*NM,air,mesh=1)
        for a in [0,60,120,180,240,300]:
            x = 0.28*UM*math.cos(math.radians(a)); y = 0.28*UM*math.sin(math.radians(a))
            add_rect(fdtd, "air_slit", x, y, 0.045*UM, 0.15*UM, -1*NM, H+1*NM, air, a, mesh=1)
    elif safe == "three_pillar_cluster":
        for i in range(3):
            a = math.pi/2 + 2*math.pi*i/3
            add_circle(fdtd, "Si_pillar", 0.21*UM*math.cos(a), 0.21*UM*math.sin(a), 0.095*UM, 0.095*UM, 0, H, Si)
    elif safe == "three_lobed_star":
        for a in [0,120,240]:
            add_rect(fdtd, "Si_lobe", 0, 0.13*UM, 0.12*UM, 0.44*UM, 0, H, Si, a)
    elif safe == "three_hole_disk":
        add_circle(fdtd, "Si_disk_host", 0,0,0.32*UM,0.32*UM,0,H,Si)
        for i in range(3):
            a = math.pi/2 + 2*math.pi*i/3
            add_circle(fdtd, "air_hole", 0.17*UM*math.cos(a), 0.17*UM*math.sin(a), 0.055*UM, 0.055*UM, -1*NM, H+1*NM, air, mesh=1)
    elif safe == "three_slit_ring":
        add_circle(fdtd, "Si_outer_ring", 0,0,0.31*UM,0.31*UM,0,H,Si)
        add_circle(fdtd, "air_inner_ring", 0,0,0.20*UM,0.20*UM,-1*NM,H+1*NM,air,mesh=1)
        for a in [90,210,330]:
            x = 0.28*UM*math.cos(math.radians(a)); y = 0.28*UM*math.sin(math.radians(a))
            add_rect(fdtd, "air_slit", x, y, 0.05*UM, 0.17*UM, -1*NM, H+1*NM, air, a, mesh=1)
    elif safe == "radial_disk":
        add_circle(fdtd, "Si_radial_disk", 0,0,0.30*UM,0.30*UM,0,H,Si)
    elif safe == "radial_ring":
        add_circle(fdtd, "Si_outer_ring", 0,0,0.31*UM,0.31*UM,0,H,Si)
        add_circle(fdtd, "air_inner_ring", 0,0,0.18*UM,0.18*UM,-1*NM,H+1*NM,air,mesh=1)
    elif safe == "concentric_double_ring":
        add_circle(fdtd, "Si_outer_ring", 0,0,0.32*UM,0.32*UM,0,H,Si)
        add_circle(fdtd, "air_gap_ring", 0,0,0.245*UM,0.245*UM,-1*NM,H+1*NM,air,mesh=1)
        add_circle(fdtd, "Si_inner_ring", 0,0,0.17*UM,0.17*UM,0,H,Si)
        add_circle(fdtd, "air_center", 0,0,0.09*UM,0.09*UM,-1*NM,H+1*NM,air,mesh=1)
    elif safe == "bullseye_multi_ring":
        for r in [0.34,0.24,0.14]:
            add_circle(fdtd, "Si_bullseye_ring", 0,0,r*UM,r*UM,0,H,Si)
            add_circle(fdtd, "air_bullseye_gap", 0,0,(r-0.045)*UM,(r-0.045)*UM,-1*NM,H+1*NM,air,mesh=1)
        add_circle(fdtd, "Si_center", 0,0,0.055*UM,0.055*UM,0,H,Si)
    elif safe == "center_pillar_outer_ring":
        add_circle(fdtd, "Si_outer_ring", 0,0,0.31*UM,0.31*UM,0,H,Si)
        add_circle(fdtd, "air_inner_ring", 0,0,0.21*UM,0.21*UM,-1*NM,H+1*NM,air,mesh=1)
        add_circle(fdtd, "Si_center_pillar", 0,0,0.095*UM,0.095*UM,0,H,Si)
    else:
        raise RuntimeError("unknown safe name: " + safe)

def save_placeholder_png(reason):
    import struct, zlib
    w, h = 900, 560
    rows = []
    for y in range(h):
        row = bytearray([0])
        for x in range(w):
            bg = 255
            if x < 70 or x > w-40 or y < 50 or y > h-70:
                bg = 245
            row.extend([bg, bg, bg])
        rows.append(bytes(row))
    raw = b"".join(rows)
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t+d)&0xffffffff)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w,h,8,2,0,0,0)) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    Path(PATHS["png"]).write_bytes(png)

def main():
    Path(PATHS["folder"]).mkdir(parents=True, exist_ok=True)
    fdtd = lumapi.FDTD(hide=True)
    fdtd.switchtolayout()
    fdtd.deleteall()
    add_common(fdtd)
    build_geometry(fdtd)
    fdtd.save(PATHS["fsp"])
    result = {"status": "fsp_saved", "peak_T": None, "peak_nm": None, "reason": ""}
    try:
        fdtd.run()
        T = fdtd.getresult("T", "T")
        lam = T["lambda"].flatten()
        val = T["T"].flatten()
        import numpy as np
        lam_nm = lam / NM
        TT = np.abs(val)**2 if np.iscomplexobj(val) else np.array(val, dtype=float)
        np.savetxt(PATHS["csv"], np.column_stack([lam_nm, TT]), delimiter=",", header="Wavelength_nm,Transmittance_T", comments="")
        imax = int(np.nanargmax(TT))
        result["status"] = "simulated"
        result["peak_T"] = float(TT[imax])
        result["peak_nm"] = float(lam_nm[imax])
    except Exception as e:
        result["status"] = "simulation_failed_png_placeholder"
        result["reason"] = str(e)
        save_placeholder_png(str(e))
    finally:
        fdtd.close()
    Path(PATHS["result"]).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0

if __name__ == "__main__":
    sys.exit(main())

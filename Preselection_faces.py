# ##### BEGIN GPL LICENSE BLOCK #####
#
#  3dview_edit_preselect.py
#  Draw the mesh element under the cursor thicker in Edit Mode
#  Copyright (C) 2015 Quentin Wenger
#  Updated for Blender 5.2 + high-poly optimisations (face-first path)
#
# ##### END GPL LICENSE BLOCK #####

bl_info = {
    "name": "Edit Preselect",
    "description": "Draw the mesh element under the cursor thicker in Edit Mode.",
    "author": "Quentin Wenger (Matpi), high-poly optimisations",
    "version": (1, 6),
    "blender": (5, 2, 0),
    "location": "3D Viewport > Sidebar (N) > View > Edit Preselect",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "category": "3D View"
}

import bpy
import gpu
import math
import time
import numpy as np
from bpy.app.handlers import persistent
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from gpu_extras.batch import batch_for_shader
from bpy_extras.view3d_utils import (
    region_2d_to_origin_3d,
    region_2d_to_vector_3d,
    location_3d_to_region_2d,
)
from bmesh import from_edit_mesh

DIST_MAX = 27
DIST_MAX_WIDE = 50
BIG = 1.0e9
GRID_CELL = 40.0          # slightly coarser = faster hash

CIRCLE_SEGMENTS = 24
CIRCLE_UNIT = [
    (math.cos(2.0 * math.pi * i / CIRCLE_SEGMENTS),
     math.sin(2.0 * math.pi * i / CIRCLE_SEGMENTS))
    for i in range(CIRCLE_SEGMENTS + 1)
]


def _bool_array(collection, name, n):
    arr = np.zeros(n, dtype=bool)
    if n:
        try:
            collection.foreach_get(name, arr)
        except Exception:
            pass
    return arr


class MeshCache:
    def __init__(self, obj, sig):
        self.sig = sig
        me = obj.data
        obj.update_from_editmode()

        nv = len(me.vertices)
        ne = len(me.edges)
        nf = len(me.polygons)
        nl = len(me.loops)
        self.nv = nv
        self.ne = ne

        co = np.empty(nv * 3, dtype=np.float32)
        if nv:
            me.vertices.foreach_get("co", co)
        self.co = co.reshape(nv, 3).astype(np.float64)

        self.vhide = _bool_array(me.vertices, "hide", nv)

        edges = np.empty(ne * 2, dtype=np.int32)
        if ne:
            me.edges.foreach_get("vertices", edges)
        edges = edges.reshape(ne, 2)
        self.i0 = np.ascontiguousarray(edges[:, 0])
        self.i1 = np.ascontiguousarray(edges[:, 1])
        self.ehide = _bool_array(me.edges, "hide", ne)
        if ne and nv:
            self.ehide |= self.vhide[self.i0] | self.vhide[self.i1]

        fhide = _bool_array(me.polygons, "hide", nf)
        self.fhide_any = bool(fhide.any())

        loop_total = np.empty(nf, dtype=np.int32)
        if nf:
            me.polygons.foreach_get("loop_total", loop_total)
        loop_start = np.empty(nf, dtype=np.int32)
        try:
            if nf:
                me.polygons.foreach_get("loop_start", loop_start)
        except Exception:
            loop_start = np.cumsum(loop_total) - loop_total
        self.loop_total = loop_total
        self.loop_start = loop_start

        loop_vert = np.empty(nl, dtype=np.int32)
        if nl:
            me.loops.foreach_get("vertex_index", loop_vert)
        self.loop_vert = loop_vert

        if hasattr(me, "calc_loop_triangles"):
            me.calc_loop_triangles()
        nt = len(me.loop_triangles)
        tri_v = np.empty(nt * 3, dtype=np.int32)
        tri_poly = np.empty(nt, dtype=np.int32)
        if nt:
            me.loop_triangles.foreach_get("vertices", tri_v)
            me.loop_triangles.foreach_get("polygon_index", tri_poly)
        tri_v = tri_v.reshape(nt, 3)
        keep = ~fhide[tri_poly] if nt else np.zeros(0, dtype=bool)
        self.tri_v = tri_v[keep]
        self.tri_poly = tri_poly[keep]
        self.nt = len(self.tri_poly)

        self.bvh = None
        self.bvh_tri = False

    def get_bvh(self, obj):
        if self.bvh is None and self.nt:
            bvh = None
            if not self.fhide_any:
                try:
                    bm = from_edit_mesh(obj.data)
                    bm.faces.index_update()
                    bvh = BVHTree.FromBMesh(bm)
                    self.bvh_tri = False
                except Exception:
                    bvh = None
            if bvh is None:
                bvh = BVHTree.FromPolygons(
                    self.co.tolist(), self.tri_v.tolist(), all_triangles=True
                )
                self.bvh_tri = True
            self.bvh = bvh
        return self.bvh


class ProjCache:
    __slots__ = (
        "key", "sxv", "syv", "has_edges",
        "x0", "y0", "x1", "y1", "xmin", "xmax", "ymin", "ymax",
        "grid_v", "cell", "inv_cell"
    )

    def __init__(self):
        self.grid_v = None
        self.has_edges = False


class ViewPreselectWorker:
    def __init__(self):
        self.handle = None
        self.handle_px = None
        self.region_ptr = None
        self.select_verts = False
        self.select_edges = False
        self.select_faces = False
        self.running = False
        self.modal_active = False

        self.cache = None
        self.cache_dirty = True
        self.proj = None

        self.pending = None
        self.last_mouse = None
        self.next_time = 0.0
        self.last_pick_mouse = None   # dead-zone

        self.draw_face = None
        self.draw_edges = []
        self.draw_verts = []

        self.custom_color = (0.0, 1.0, 0.0)
        self.face_opacity = 0.0
        self.edge_opacity = 1.0
        self.vert_opacity = 1.0
        self.pick_range = float(DIST_MAX)
        self.edge_width = 3.0
        self.vert_radius = 5.0

        self._shader_poly = None
        self._shader_uniform = None

    def _get_poly_shader(self):
        if self._shader_poly is None:
            self._shader_poly = gpu.shader.from_builtin('POLYLINE_UNIFORM_COLOR')
        return self._shader_poly

    def _get_uniform_shader(self):
        if self._shader_uniform is None:
            self._shader_uniform = gpu.shader.from_builtin('UNIFORM_COLOR')
        return self._shader_uniform

    def updateSelectionModes(self, context):
        (self.select_verts,
         self.select_edges,
         self.select_faces) = context.tool_settings.mesh_select_mode

    def clear(self):
        self.draw_face = None
        self.draw_edges = []
        self.draw_verts = []

    def drawCallback(self):
        if not (self.running and bpy.context.mode == 'EDIT_MESH'):
            return
        region = bpy.context.region
        if region is None or region.as_pointer() != self.region_ptr:
            return

        gpu.state.blend_set('ALPHA')
        gpu.state.depth_test_set('NONE')

        if self.select_faces and self.face_opacity and self.draw_face is not None:
            shader = self._get_poly_shader()
            coords = list(self.draw_face)
            coords.append(coords[0])
            batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": coords})
            shader.uniform_float("viewportSize", (region.width, region.height))
            shader.uniform_float("lineWidth", 1.0)
            shader.uniform_float("color", (*self.custom_color, self.face_opacity))
            batch.draw(shader)

        if (self.select_edges or self.select_faces) and self.edge_opacity and self.draw_edges:
            shader = self._get_poly_shader()
            coords = []
            for a, b in self.draw_edges:
                coords.append(a)
                coords.append(b)
            batch = batch_for_shader(shader, 'LINES', {"pos": coords})
            shader.uniform_float("viewportSize", (region.width, region.height))
            shader.uniform_float("lineWidth", self.edge_width)
            shader.uniform_float("color", (*self.custom_color, self.edge_opacity))
            batch.draw(shader)

        gpu.state.depth_test_set('NONE')
        gpu.state.blend_set('NONE')

    def drawPixelCallback(self):
        if not (self.running and self.select_verts and self.vert_opacity and self.draw_verts):
            return
        if bpy.context.mode != 'EDIT_MESH':
            return
        region = bpy.context.region
        rv3d = bpy.context.region_data
        if region is None or rv3d is None or region.as_pointer() != self.region_ptr:
            return

        shader = self._get_uniform_shader()
        r = self.vert_radius
        gpu.state.blend_set('ALPHA')
        shader.uniform_float("color", (*self.custom_color, self.vert_opacity))
        for p in self.draw_verts:
            p2 = location_3d_to_region_2d(region, rv3d, Vector(p))
            if p2 is None:
                continue
            coords = [(p2.x, p2.y)]
            coords += [(p2.x + r * cx, p2.y + r * cy) for cx, cy in CIRCLE_UNIT]
            batch = batch_for_shader(shader, 'TRI_FAN', {"pos": coords})
            batch.draw(shader)
        gpu.state.blend_set('NONE')

    def _get_cache(self, obj):
        bm = from_edit_mesh(obj.data)
        sig = (obj.as_pointer(), len(bm.verts), len(bm.edges), len(bm.faces))
        if self.cache is None or self.cache_dirty or self.cache.sig != sig:
            self.cache = MeshCache(obj, sig)
            self.cache_dirty = False
            self.proj = None
        return self.cache

    def _get_proj(self, c, M, P, mvp, w, h, want_edges):
        # Only build full projection when we really need the fallback path
        key = (id(c), M.tobytes(), P.tobytes(), w, h, float(self.pick_range))
        pr = self.proj
        if pr is not None and pr.key == key:
            return pr

        pr = ProjCache()
        pr.key = key
        pr.cell = GRID_CELL
        pr.inv_cell = 1.0 / GRID_CELL

        clip = c.co @ mvp[:, :3].T + mvp[:, 3]
        cw = clip[:, 3]
        dd = clip[:, 2] + cw
        infront = dd >= 0.0
        ws = np.where(infront, cw, 1.0)
        sx = ((clip[:, 0] / ws * 0.5 + 0.5) * w).astype(np.float32)
        sy = ((clip[:, 1] / ws * 0.5 + 0.5) * h).astype(np.float32)

        ok = infront & ~c.vhide
        pr.sxv = np.where(ok, sx, np.float32(BIG))
        pr.syv = np.where(ok, sy, np.float32(BIG))

        # Cheap vertex grid only (edges are too expensive on dense meshes)
        if c.nv > 15000 and ok.any():
            gx = np.floor(pr.sxv * pr.inv_cell).astype(np.int32)
            gy = np.floor(pr.syv * pr.inv_cell).astype(np.int32)
            gdict = {}
            for i in np.nonzero(ok)[0]:
                keyg = (int(gx[i]), int(gy[i]))
                lst = gdict.get(keyg)
                if lst is None:
                    gdict[keyg] = [i]
                else:
                    lst.append(i)
            pr.grid_v = gdict
        else:
            pr.grid_v = None

        # Edges: only prepare data, never build a spatial hash on dense meshes
        if want_edges and c.ne and c.ne < 80000:
            i0, i1 = c.i0, c.i1
            f0 = infront[i0]
            f1 = infront[i1]
            live = ~c.ehide & (f0 | f1)

            x0 = sx[i0].copy()
            y0 = sy[i0].copy()
            x1 = sx[i1].copy()
            y1 = sy[i1].copy()

            one = np.nonzero(live & (f0 != f1))[0]
            if len(one):
                ca = clip[i0[one]]
                cb = clip[i1[one]]
                da = dd[i0[one]]
                db = dd[i1[one]]
                t = (da / (da - db))[:, None]
                hp = ca + t * (cb - ca)
                a2 = np.where((da < 0.0)[:, None], hp, ca)
                b2 = np.where((db < 0.0)[:, None], hp, cb)
                wa = np.maximum(a2[:, 3], 1e-9)
                wb = np.maximum(b2[:, 3], 1e-9)
                x0[one] = (a2[:, 0] / wa * 0.5 + 0.5) * w
                y0[one] = (a2[:, 1] / wa * 0.5 + 0.5) * h
                x1[one] = (b2[:, 0] / wb * 0.5 + 0.5) * w
                y1[one] = (b2[:, 1] / wb * 0.5 + 0.5) * h

            dead = ~live
            x0[dead] = BIG
            y0[dead] = BIG
            x1[dead] = BIG
            y1[dead] = BIG

            pr.x0, pr.y0, pr.x1, pr.y1 = x0, y0, x1, y1
            pr.xmin = np.minimum(x0, x1)
            pr.xmax = np.maximum(x0, x1)
            pr.ymin = np.minimum(y0, y1)
            pr.ymax = np.maximum(y0, y1)
            pr.has_edges = True
        else:
            pr.has_edges = False

        self.proj = pr
        return pr

    @staticmethod
    def _edge_point(c, mvp, k, mx, my, w, h):
        pa = c.co[c.i0[k]]
        pb = c.co[c.i1[k]]
        ca = mvp @ np.append(pa, 1.0)
        cb = mvp @ np.append(pb, 1.0)
        da = ca[2] + ca[3]
        db = cb[2] + cb[3]
        ta = 0.0
        tb = 1.0
        a2 = ca
        b2 = cb
        if da < 0.0 or db < 0.0:
            t = da / (da - db)
            hp = ca + t * (cb - ca)
            if da < 0.0:
                ta = t
                a2 = hp
            if db < 0.0:
                tb = t
                b2 = hp
        wa = max(a2[3], 1e-9)
        wb = max(b2[3], 1e-9)
        x0 = (a2[0] / wa * 0.5 + 0.5) * w
        y0 = (a2[1] / wa * 0.5 + 0.5) * h
        x1 = (b2[0] / wb * 0.5 + 0.5) * w
        y1 = (b2[1] / wb * 0.5 + 0.5) * h
        xa = x1 - x0
        ya = y1 - y0
        len2 = xa * xa + ya * ya
        s = ((mx - x0) * xa + (my - y0) * ya) / len2 if len2 > 0.0 else 0.0
        s = min(max(s, 0.0), 1.0)
        sc = s * wa / ((1.0 - s) * wb + s * wa)
        tg = ta + sc * (tb - ta)
        return pa + tg * (pb - pa)

    def _pick(self, obj, region, rv3d, mx, my, xray):
        none = (None, [], [])
        dist = float(self.pick_range)
        dist_sqr = dist * dist

        c = self._get_cache(obj)
        if c.nv == 0:
            return none

        w = float(region.width)
        h = float(region.height)
        M = np.array(obj.matrix_world, dtype=np.float64)
        P = np.array(rv3d.perspective_matrix, dtype=np.float64)
        mvp = P @ M
        Lm = M[:3, :3]
        tm = M[:3, 3]

        def world(pts_local):
            return (np.atleast_2d(pts_local) @ Lm.T + tm).tolist()

        # ------------------------------------------------------------------
        # 1. FACE RAY-CAST – this is the path that runs 95 % of the time
        # ------------------------------------------------------------------
        if c.nt:
            bvh = c.get_bvh(obj)
            if bvh is not None:
                coords = (mx, my)
                ro = region_2d_to_origin_3d(region, rv3d, coords)
                rd = region_2d_to_vector_3d(region, rv3d, coords)
                Minv = np.linalg.inv(M)
                o = (Minv @ np.array([ro.x, ro.y, ro.z, 1.0]))[:3]
                d = Minv[:3, :3] @ np.array([rd.x, rd.y, rd.z])
                dn = float(np.linalg.norm(d))
                if dn > 0.0:
                    hit = bvh.ray_cast(
                        Vector(o.tolist()), Vector((d / dn).tolist())
                    )
                    if hit[0] is not None:
                        idx = hit[2]
                        fi = int(c.tri_poly[idx]) if c.bvh_tri else int(idx)
                        start = c.loop_start[fi]
                        verts = c.loop_vert[start : start + c.loop_total[fi]]
                        pts = [tuple(p) for p in world(c.co[verts])]
                        edges = [(pts[i - 1], p) for i, p in enumerate(pts)]

                        # Face mode → instant return
                        if self.select_faces:
                            return (pts, edges, pts)

                        # Vert / Edge mode → only examine this face
                        if self.select_verts or self.select_edges:
                            local_pts = c.co[verts]
                            clip = local_pts @ mvp[:, :3].T + mvp[:, 3]
                            cw = np.maximum(clip[:, 3], 1e-8)
                            sx = (clip[:, 0] / cw * 0.5 + 0.5) * w
                            sy = (clip[:, 1] / cw * 0.5 + 0.5) * h

                            best_d2 = dist_sqr
                            best_vert = None
                            best_edge = None

                            if self.select_verts:
                                d2 = (sx - mx) ** 2 + (sy - my) ** 2
                                i = int(np.argmin(d2))
                                if d2[i] <= dist_sqr:
                                    best_d2 = float(d2[i])
                                    best_vert = int(verts[i])

                            if self.select_edges:
                                n = len(verts)
                                for i in range(n):
                                    a = i
                                    b = (i + 1) % n
                                    xa = sx[b] - sx[a]
                                    ya = sy[b] - sy[a]
                                    len2 = xa * xa + ya * ya
                                    if len2 < 1e-8:
                                        continue
                                    s = ((mx - sx[a]) * xa + (my - sy[a]) * ya) / len2
                                    s = max(0.0, min(1.0, s))
                                    dx = mx - (sx[a] + s * xa)
                                    dy = my - (sy[a] + s * ya)
                                    d2e = dx * dx + dy * dy
                                    if d2e < best_d2:
                                        best_d2 = d2e
                                        best_vert = None
                                        best_edge = (int(verts[a]), int(verts[b]))

                            if best_vert is not None:
                                p = tuple(world(c.co[best_vert])[0])
                                return (None, [], [p])
                            if best_edge is not None:
                                p0, p1 = [
                                    tuple(p) for p in world(c.co[list(best_edge)])
                                ]
                                return (None, [(p0, p1)], [p0, p1])

                        # Nothing close enough on the hit face → fall through
                        # only if the user is in pure vert/edge mode

        # ------------------------------------------------------------------
        # 2. FALLBACK – only when mouse is NOT over a face
        # ------------------------------------------------------------------
        # Extremely limited budgets
        max_tests = 8 if c.nt > 100000 else 14

        pr = self._get_proj(c, M, P, mvp, w, h, self.select_edges)

        # occlusion (only used in fallback)
        occ = {}
        def visible(p_l):
            if xray or not c.nt:
                return True
            bvh = c.get_bvh(obj)
            if bvh is None:
                return True
            if not occ:
                Minv = np.linalg.inv(M)
                view_inv = rv3d.view_matrix.inverted()
                occ["persp"] = rv3d.is_perspective
                if occ["persp"]:
                    eye_w = np.array(view_inv.translation, dtype=np.float64)
                    occ["eye"] = (Minv @ np.append(eye_w, 1.0))[:3]
                else:
                    tv = np.array(view_inv.col[2].xyz, dtype=np.float64)
                    tv /= np.linalg.norm(tv)
                    dl = Minv[:3, :3] @ tv
                    scale = np.linalg.norm(dl)
                    occ["dir"] = dl / scale
                    occ["eps"] = 1e-4 * max(rv3d.view_distance, 1e-3) * scale
            if occ["persp"]:
                d = p_l - occ["eye"]
                dlen = float(np.linalg.norm(d))
                if dlen <= 0.0:
                    return True
                hit = bvh.ray_cast(
                    Vector(occ["eye"].tolist()),
                    Vector((d / dlen).tolist()),
                    dlen * (1.0 - 1e-4),
                    )
            else:
                o = p_l + occ["dir"] * occ["eps"]
                hit = bvh.ray_cast(Vector(o.tolist()), Vector(occ["dir"].tolist()))
            return hit[0] is None

        # vertices only (edges are deliberately limited)
        if self.select_verts:
            cand = None
            if pr.grid_v is not None:
                cx = int(mx * pr.inv_cell)
                cy = int(my * pr.inv_cell)
                ids = []
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        lst = pr.grid_v.get((cx + dx, cy + dy))
                        if lst:
                            ids.extend(lst)
                if ids:
                    ids = np.asarray(ids, dtype=np.int32)
                    d2 = (pr.sxv[ids] - mx) ** 2 + (pr.syv[ids] - my) ** 2
                    mask = d2 <= dist_sqr
                    if mask.any():
                        ids = ids[mask]
                        d2 = d2[mask]
                        order = np.argsort(d2)[:max_tests]
                        cand = ids[order]
            else:
                d2 = (pr.sxv - mx) ** 2 + (pr.syv - my) ** 2
                cand = np.nonzero(d2 <= dist_sqr)[0]
                if len(cand):
                    cand = cand[np.argsort(d2[cand])][:max_tests]

            if cand is not None and len(cand):
                for i in cand:
                    if visible(c.co[i]):
                        return (None, [], [tuple(world(c.co[i])[0])])

        # edges – only on relatively light meshes
        if self.select_edges and pr.has_edges and c.ne < 80000:
            m = (
                    (pr.xmin <= mx + dist)
                    & (pr.xmax >= mx - dist)
                    & (pr.ymin <= my + dist)
                    & (pr.ymax >= my - dist)
            )
            sub = np.nonzero(m)[0]
            if len(sub):
                x0 = pr.x0[sub].astype(np.float64)
                y0 = pr.y0[sub].astype(np.float64)
                xa = pr.x1[sub].astype(np.float64) - x0
                ya = pr.y1[sub].astype(np.float64) - y0
                len2 = xa * xa + ya * ya
                s = ((mx - x0) * xa + (my - y0) * ya) / np.where(len2 > 0.0, len2, 1.0)
                s = np.clip(s, 0.0, 1.0)
                d2 = (mx - (x0 + s * xa)) ** 2 + (my - (y0 + s * ya)) ** 2
                cl = np.nonzero(d2 <= dist_sqr)[0]
                if len(cl):
                    cl = cl[np.argsort(d2[cl])][:max_tests]
                    for j in cl:
                        k = int(sub[j])
                        p_l = self._edge_point(c, mvp, k, mx, my, w, h)
                        if visible(p_l):
                            p0, p1 = [
                                tuple(p) for p in world(c.co[[c.i0[k], c.i1[k]]])
                            ]
                            return (None, [(p0, p1)], [p0, p1])

        return none

    def modal(self, context, event):
        region = context.region
        rv3d = context.region_data
        if region is None or rv3d is None:
            return

        obj = context.object
        in_edit = (
                self.running
                and context.mode == 'EDIT_MESH'
                and obj is not None
                and obj.type == 'MESH'
        )

        if not in_edit:
            self.pending = None
            if self.draw_face is not None or self.draw_edges or self.draw_verts:
                self.clear()
                region.tag_redraw()
            return

        if event.type in {'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE'}:
            self.last_mouse = (event.mouse_region_x, event.mouse_region_y)
            self.pending = self.last_mouse
        elif self.cache_dirty and self.last_mouse is not None:
            self.pending = self.last_mouse

        if self.pending is None:
            return
        if time.perf_counter() < self.next_time:
            return

        mx, my = self.pending
        self.pending = None

        # Small dead-zone – ignore tiny movements
        if self.last_pick_mouse is not None:
            dx = mx - self.last_pick_mouse[0]
            dy = my - self.last_pick_mouse[1]
            if dx * dx + dy * dy < 2.5:          # ~1.6 px
                return
        self.last_pick_mouse = (mx, my)

        t_start = time.perf_counter()

        self.region_ptr = region.as_pointer()
        self.updateSelectionModes(context)

        shading = context.space_data.shading
        if shading.type == 'WIREFRAME':
            xray = shading.show_xray_wireframe
        else:
            xray = shading.show_xray

        if 0 <= mx < region.width and 0 <= my < region.height:
            result = self._pick(obj, region, rv3d, mx, my, xray)
        else:
            result = (None, [], [])

        if (
                result[0] != self.draw_face
                or result[1] != self.draw_edges
                or result[2] != self.draw_verts
        ):
            self.draw_face, self.draw_edges, self.draw_verts = result
            region.tag_redraw()

        cost = time.perf_counter() - t_start
        self.next_time = time.perf_counter() + max(0.022, cost)   # ~45 Hz max

    def register(self):
        if self.handle is not None:
            bpy.types.SpaceView3D.draw_handler_remove(self.handle, 'WINDOW')
        self.handle = bpy.types.SpaceView3D.draw_handler_add(
            self.drawCallback, (), 'WINDOW', 'POST_VIEW'
        )
        if self.handle_px is not None:
            bpy.types.SpaceView3D.draw_handler_remove(self.handle_px, 'WINDOW')
        self.handle_px = bpy.types.SpaceView3D.draw_handler_add(
            self.drawPixelCallback, (), 'WINDOW', 'POST_PIXEL'
        )

    def unregister(self):
        if self.handle is not None:
            bpy.types.SpaceView3D.draw_handler_remove(self.handle, 'WINDOW')
            self.handle = None
        if self.handle_px is not None:
            bpy.types.SpaceView3D.draw_handler_remove(self.handle_px, 'WINDOW')
            self.handle_px = None


class ViewOperatorPreselect(bpy.types.Operator):
    bl_idname = "view3d.modal_operator_preselect"
    bl_label = "Preselect View Operator"
    bl_options = {'INTERNAL'}

    worker = ViewPreselectWorker()

    def modal(self, context, event):
        w = self.worker
        if not w.running:
            w.modal_active = False
            w.clear()
            w.pending = None
            timer = getattr(self, "_timer", None)
            if timer is not None:
                context.window_manager.event_timer_remove(timer)
                self._timer = None
            return {'FINISHED', 'PASS_THROUGH'}
        w.modal(context, event)
        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        if context.space_data.type == 'VIEW_3D':
            self.worker.modal_active = True
            wm = context.window_manager
            self._timer = wm.event_timer_add(0.05, window=context.window)
            wm.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        else:
            self.report({'WARNING'}, "Active space must be a View3d")
            return {'CANCELLED'}


ADDON_ID = __package__ or __name__


def get_prefs(context=None):
    try:
        return (context or bpy.context).preferences.addons[ADDON_ID].preferences
    except Exception:
        return None


def syncWorker(prefs):
    w = ViewOperatorPreselect.worker
    w.edge_width = prefs.preselect_width
    w.vert_radius = prefs.preselect_radius
    w.custom_color = tuple(prefs.custom_color)
    w.face_opacity = prefs.opacity_face
    w.edge_opacity = prefs.opacity_edges
    w.vert_opacity = prefs.opacity_vertices
    w.pick_range = prefs.pick_range


def updatePrefs(self, context):
    syncWorker(self)
    wm = bpy.context.window_manager
    if wm is not None:
        for window in wm.windows:
            for area in window.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()


def updateBGLData(self, context):
    VOP = ViewOperatorPreselect
    if self.preselect_use:
        VOP.worker.running = True
        if not VOP.worker.modal_active:
            try:
                bpy.ops.view3d.modal_operator_preselect('INVOKE_REGION_WIN')
            except RuntimeError:
                pass
            if not VOP.worker.modal_active:
                VOP.worker.running = False
                return
        prefs = get_prefs(context)
        if prefs is not None:
            syncWorker(prefs)
        return
    VOP.worker.running = False


@persistent
def depsgraph_handler(scene, depsgraph=None):
    w = ViewOperatorPreselect.worker
    if not w.running or w.cache_dirty:
        return
    if depsgraph is None:
        w.cache_dirty = True
        return
    for update in depsgraph.updates:
        if update.is_updated_geometry:
            w.cache_dirty = True
            return


@persistent
def load_post_handler(*args):
    w = ViewOperatorPreselect.worker
    w.running = False
    w.modal_active = False
    w.cache = None
    w.cache_dirty = True
    w.clear()
    try:
        for wm in bpy.data.window_managers:
            wm.preselect.preselect_use = False
    except Exception:
        pass


class PreselectCollectionGroup(bpy.types.PropertyGroup):
    preselect_use: bpy.props.BoolProperty(
        name="Preselect",
        description="Highlight the element under the cursor",
        default=False,
        update=updateBGLData,
    )


def draw_settings(layout, prefs, mode=None):
    if mode is None:
        v = e = f = True
    else:
        v, e, f = mode
    layout.prop(prefs, "pick_range")
    r = layout.row()
    r.active = v
    r.prop(prefs, "preselect_radius")
    r = layout.row()
    r.active = e or f
    r.prop(prefs, "preselect_width")
    r = layout.row()
    r.active = v
    r.prop(prefs, "opacity_vertices")
    r = layout.row()
    r.active = e or f
    r.prop(prefs, "opacity_edges")
    r = layout.row()
    r.active = f
    r.prop(prefs, "opacity_face")
    layout.prop(prefs, "custom_color", text="")


class PreselectPreferences(bpy.types.AddonPreferences):
    bl_idname = ADDON_ID

    pick_range: bpy.props.FloatProperty(
        name="Range",
        description="Maximum distance in pixels",
        min=float(DIST_MAX),
        max=float(DIST_MAX_WIDE),
        default=float(DIST_MAX),
        subtype='PIXEL',
        update=updatePrefs,
    )
    preselect_width: bpy.props.FloatProperty(
        name="Width",
        description="Edge width in pixels",
        min=1.0,
        max=10.0,
        default=3.0,
        subtype='PIXEL',
        update=updatePrefs,
    )
    preselect_radius: bpy.props.FloatProperty(
        name="Radius",
        description="Vertex radius in pixels",
        min=1.0,
        max=20.0,
        default=5.0,
        subtype='PIXEL',
        update=updatePrefs,
    )
    opacity_vertices: bpy.props.FloatProperty(
        name="Vertices Opacity",
        min=0.0,
        max=1.0,
        default=1.0,
        subtype='FACTOR',
        update=updatePrefs,
    )
    opacity_edges: bpy.props.FloatProperty(
        name="Edges Opacity",
        min=0.0,
        max=1.0,
        default=1.0,
        subtype='FACTOR',
        update=updatePrefs,
    )
    opacity_face: bpy.props.FloatProperty(
        name="Face Opacity",
        min=0.0,
        max=1.0,
        default=0.0,
        subtype='FACTOR',
        update=updatePrefs,
    )
    custom_color: bpy.props.FloatVectorProperty(
        name="Custom Color",
        min=0.0,
        max=1.0,
        default=(0.0, 1.0, 0.0),
        size=3,
        subtype='COLOR',
        update=updatePrefs,
    )

    def draw(self, context):
        draw_settings(self.layout, self)


class VIEW3D_PT_edit_preselect(bpy.types.Panel):
    bl_label = "Edit Preselect"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "View"

    def draw(self, context):
        layout = self.layout
        preselect = context.window_manager.preselect
        if context.mode == 'EDIT_MESH':
            layout.prop(preselect, "preselect_use")
            if preselect.preselect_use:
                prefs = get_prefs(context)
                if prefs is None:
                    layout.label(text="Enable as an add-on to adjust settings")
                    return
                split = layout.split(factor=0.1)
                split.separator()
                col = split.column()
                draw_settings(col, prefs, context.tool_settings.mesh_select_mode)


classes = (
    PreselectCollectionGroup,
    PreselectPreferences,
    ViewOperatorPreselect,
    VIEW3D_PT_edit_preselect,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.WindowManager.preselect = bpy.props.PointerProperty(
        type=PreselectCollectionGroup
    )
    ViewOperatorPreselect.worker.register()

    prefs = get_prefs()
    if prefs is not None:
        syncWorker(prefs)

    if depsgraph_handler not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(depsgraph_handler)
    if load_post_handler not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(load_post_handler)


def unregister():
    if depsgraph_handler in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(depsgraph_handler)
    if load_post_handler in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(load_post_handler)

    ViewOperatorPreselect.worker.running = False
    ViewOperatorPreselect.worker.unregister()
    del bpy.types.WindowManager.preselect
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
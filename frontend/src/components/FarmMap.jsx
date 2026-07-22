"use client";
// OpenLayers map (Esri World Imagery tiles), matching Agriverse's map stack.
// mode "pins": many farms as status-colored dots. mode "field": one farm's
// boundary polygon with a semi-transparent index overlay + stress patch.
import { useEffect, useRef } from "react";

const INDEX_COLORS = {
  NDVI: [202, 138, 4], NDMI: [234, 88, 12], EVI: [101, 163, 13], MSAVI: [180, 83, 9],
  NDRE: [147, 51, 234], NDWI: [37, 99, 235], NBR: [185, 28, 28],
};

export default function FarmMap({ farms = [], mode = "pins", index = "NDVI", height = 300, onSelect, focus }) {
  const ref = useRef(null);
  const mapRef = useRef(null);
  const tipRef = useRef(null);

  useEffect(() => {
    let map;
    let disposed = false;

    (async () => {
      const [{ default: Map }, { default: View }, { default: TileLayer }, { default: XYZ },
        { default: VectorLayer }, { default: VectorSource }, { default: Feature },
        { default: Point }, { default: Polygon }, { fromLonLat },
        { default: Style }, { default: Fill }, { default: Stroke }, { default: CircleStyle },
        { default: Icon }] =
        await Promise.all([
          import("ol/Map"), import("ol/View"), import("ol/layer/Tile"), import("ol/source/XYZ"),
          import("ol/layer/Vector"), import("ol/source/Vector"), import("ol/Feature"),
          import("ol/geom/Point"), import("ol/geom/Polygon"), import("ol/proj"),
          import("ol/style/Style"), import("ol/style/Fill"), import("ol/style/Stroke"), import("ol/style/Circle"),
          import("ol/style/Icon"),
        ]);
      if (disposed || !ref.current) return;

      const source = new VectorSource();
      const features = [];

      if (mode === "pins") {
        for (const f of farms) {
          if (!f.lat) continue;
          const feat = new Feature({
            geometry: new Point(fromLonLat([f.lon, f.lat])),
            farmId: f.id,
            farmerName: f.farmer,
            village: f.tipSub || f.village,
          });
          if (f.pinIcon) {
            feat.setStyle(new Style({
              image: new Icon({ src: f.pinIcon, width: 26, height: 26 }),
            }));
          } else {
            const color = f.pinColor || "#4caf50";
            feat.setStyle(new Style({
              image: new CircleStyle({
                radius: 6,
                fill: new Fill({ color }),
                stroke: new Stroke({ color: "rgba(10,11,14,0.9)", width: 2 }),
              }),
            }));
          }
          features.push(feat);
        }
      } else if (mode === "field" && farms[0]?.boundary) {
        const f = farms[0];
        const ring = f.boundary.map(([lon, lat]) => fromLonLat([lon, lat]));
        const poly = new Feature({ geometry: new Polygon([ring]) });
        poly.setStyle(new Style({ stroke: new Stroke({ color: "#7db2ff", width: 2.5 }) }));
        features.push(poly);

        const c = INDEX_COLORS[index] || INDEX_COLORS.NDVI;
        const overlay = new Feature({ geometry: new Polygon([ring]) });
        overlay.setStyle(new Style({ fill: new Fill({ color: [c[0], c[1], c[2], 0.35] }) }));
        features.push(overlay);

        const cx = ring.reduce((s, p) => s + p[0], 0) / ring.length;
        const cy = ring.reduce((s, p) => s + p[1], 0) / ring.length;
        const k = 0.45;
        const stress = new Feature({
          geometry: new Polygon([ring.map(([x, y]) => [cx + (x - cx) * k + 40, cy + (y - cy) * k + 30])]),
        });
        stress.setStyle(new Style({
          fill: new Fill({ color: "rgba(226,75,74,0.55)" }),
          stroke: new Stroke({ color: "rgba(226,75,74,0.9)", width: 1.5 }),
        }));
        features.push(stress);
      }

      source.addFeatures(features);

      map = new Map({
        target: ref.current,
        layers: [
          new TileLayer({
            source: new XYZ({
              url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
              attributions: "Tiles © Esri",
              crossOrigin: "anonymous",
            }),
          }),
          new VectorLayer({ source }),
        ],
        view: new View({ center: fromLonLat([70.95, 30.97]), zoom: 11 }),
      });
      mapRef.current = map;

      if (mode === "field" && features[0]) {
        map.getView().fit(features[0].getGeometry().getExtent(), { padding: [40, 40, 40, 40], maxZoom: 17 });
      } else if (mode === "pins" && features.length) {
        map.getView().fit(source.getExtent(), { padding: [30, 30, 30, 30], maxZoom: 13 });
      }
      if (focus && mode === "pins") {
        map.getView().animate({ center: fromLonLat(focus), zoom: 15, duration: 400 });
      }

      if (onSelect) {
        map.on("click", (e) => {
          map.forEachFeatureAtPixel(e.pixel, (feat) => {
            const id = feat.get("farmId");
            if (id) onSelect(id);
            return true;
          });
        });
      }

      // Hover tooltip: farmer name + village on pin hover.
      if (mode === "pins") {
        const tip = document.createElement("div");
        Object.assign(tip.style, {
          position: "absolute", pointerEvents: "none", display: "none", zIndex: 10,
          background: "var(--surface-4)", border: "1px solid var(--border-default)",
          color: "var(--text-primary)", borderRadius: "8px", padding: "6px 10px",
          fontSize: "12px", fontWeight: "600", whiteSpace: "nowrap",
          boxShadow: "0 4px 14px rgba(0,0,0,0.45)", transform: "translate(12px, -50%)",
        });
        ref.current.style.position = "relative";
        ref.current.appendChild(tip);
        tipRef.current = tip;

        map.on("pointermove", (e) => {
          let found = null;
          map.forEachFeatureAtPixel(e.pixel, (feat) => {
            if (feat.get("farmerName")) { found = feat; return true; }
          });
          if (found) {
            tip.innerHTML = `${found.get("farmerName")}<span style="color:var(--text-muted);font-weight:400"> · ${found.get("village")}</span>`;
            tip.style.left = e.pixel[0] + "px";
            tip.style.top = e.pixel[1] + "px";
            tip.style.display = "block";
          } else {
            tip.style.display = "none";
          }
          map.getTargetElement().style.cursor = found ? "pointer" : "";
        });
      } else if (onSelect) {
        map.on("pointermove", (e) => {
          const hit = map.hasFeatureAtPixel(e.pixel);
          map.getTargetElement().style.cursor = hit ? "pointer" : "";
        });
      }
    })();

    return () => {
      disposed = true;
      if (tipRef.current) { tipRef.current.remove(); tipRef.current = null; }
      if (mapRef.current) {
        mapRef.current.setTarget(undefined);
        mapRef.current.dispose();
        mapRef.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, index, farms.length, farms[0]?.id, focus?.[0]]);

  return <div ref={ref} style={{ width: "100%", height, borderRadius: 10, overflow: "hidden", background: "#10131a" }} />;
}

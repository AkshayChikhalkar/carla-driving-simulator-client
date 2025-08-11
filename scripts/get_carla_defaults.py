import argparse, json
import carla

def _safe_attr_value(a):
    """Return attribute value across CARLA versions without raising.
    Tries string, bool, int, float in that order.
    """
    for meth in ("as_str", "as_string", "as_bool", "as_int", "as_float"):
        if hasattr(a, meth):
            try:
                return getattr(a, meth)()
            except Exception:
                pass
    return getattr(a, "value", None)


def serialize_attr(a):
    atype = getattr(a, "type", None)
    if hasattr(atype, "name"):
        atype = atype.name
    else:
        atype = str(atype)
    rec_vals = getattr(a, "recommended_values", [])
    try:
        rec_vals = list(rec_vals)
    except Exception:
        rec_vals = []
    return {
        "id": getattr(a, "id", None),
        "type": atype,
        "recommended_values": rec_vals,
        "value": _safe_attr_value(a),
    }

def bp_to_dict(bp):
    try:
        tags = list(bp.tags)
    except Exception:
        tags = []
    attrs = []
    try:
        attrs = [serialize_attr(a) for a in bp]
    except Exception:
        pass
    return {"id": bp.id, "tags": tags, "attributes": attrs}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="hal9000.skim.th-owl.de")
    p.add_argument("--port", type=int, default=2000)
    p.add_argument("--timeout", type=float, default=5.0)
    p.add_argument("--out", default="carla_0100_catalog.json")
    args = p.parse_args()

    client = carla.Client(args.host, args.port)
    client.set_timeout(args.timeout)

    maps = sorted(client.get_available_maps())
    world = client.get_world()
    lib = world.get_blueprint_library()

    vehicles = sorted([bp.id for bp in lib.filter("vehicle.*")])
    walkers  = sorted([bp.id for bp in lib.filter("walker.*")])
    sensors  = sorted([bp.id for bp in lib.filter("sensor.*")])
    traffic  = sorted([bp.id for bp in lib.filter("traffic.*")])

    all_bps = [bp_to_dict(bp) for bp in lib]
    all_bps.sort(key=lambda d: d.get("id", ""))

    data = {
        "carla_version": "0.10.0",
        "maps": maps,
        "blueprints": {
            "vehicles": vehicles,
            "walkers": walkers,
            "sensors": sensors,
            "traffic": traffic,
            "all": all_bps
        }
    }

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Wrote {args.out} with {len(maps)} maps and {len(all_bps)} blueprints.")

if __name__ == "__main__":
    main()
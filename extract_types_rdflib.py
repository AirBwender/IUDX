from rdflib import Graph
import json

def get_iudx_types(rdf_url="https://voc.iudx.org.in/", output_file="types.json"):
    g = Graph()
    print(f"[INFO] Fetching RDF from {rdf_url} ...")
    
    # Explicitly declare the format
    g.parse(rdf_url, format="json-ld")

    types = set()
    for s, p, o in g.triples((None, None, None)):
        if "iudx:" in str(o) and ("range" in str(p) or "type" in str(p)):
            types.add(str(o).split("/")[-1])  # only the last part of the URI

    sorted_types = sorted(types)

    with open(output_file, "w") as f:
        json.dump(sorted_types, f, indent=2)
        print(f"[INFO] Saved {len(sorted_types)} IUDX types to {output_file}")

    return sorted_types

if __name__ == "__main__":
    iudx_types = get_iudx_types()
    print(f"[INFO] Extracted {len(iudx_types)} IUDX types:")
    print(iudx_types)

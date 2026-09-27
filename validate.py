"""Validate LHO-mapped laboratory data with SHACL.

Usage:
    python validate.py                      # validate the four example files
    python validate.py path/to/data.ttl ... # validate your own RDF files

For each data file the script loads the LHO ontology next to the data, runs
pySHACL with the shapes in shapes/lho-shapes.ttl, prints a short summary and
writes the full SHACL validation report to reports/<file>_report.ttl.
"""
import sys
from collections import Counter
from pathlib import Path

from pyshacl import validate
from rdflib import Graph, Namespace, OWL, RDF

HERE = Path(__file__).parent
SHAPES = HERE / "shapes" / "lho-shapes.ttl"
ONTOLOGY = HERE / "ontology" / "LivestockHealthOntology_v1.5.rdf"
REPORTS = HERE / "reports"
SH = Namespace("http://www.w3.org/ns/shacl#")
LHO = "http://www.purl.org/decide/LiveStockHealthOnto/LHO#"


def short(term):
    return str(term).replace(LHO, "LHO:").replace(str(SH), "sh:")


def property_declarations(onto):
    """Keep only the property declarations of the ontology.

    The LHO file also contains example individuals; mixing those into the data
    would make them focus nodes of the shapes.
    """
    decl = Graph()
    for kind in (OWL.ObjectProperty, OWL.DatatypeProperty):
        for p in onto.subjects(RDF.type, kind):
            decl.add((p, RDF.type, kind))
    return decl


def check(data_file, shapes, ontology):
    data = Graph().parse(data_file)
    conforms, report, _ = validate(
        data,
        shacl_graph=shapes,
        ont_graph=ontology,     # property declarations, used by the declared-property check
        inference="none",
        allow_warnings=True,    # warnings do not make the file fail
        advanced=True,          # needed for the SPARQL-based check
    )
    REPORTS.mkdir(exist_ok=True)
    out = REPORTS / f"{Path(data_file).stem}_report.ttl"
    report.serialize(out, format="turtle")

    results = list(report.subjects(RDF.type, SH.ValidationResult))
    focus = {report.value(r, SH.focusNode) for r in results}
    samples = len({s for s, o in data.subject_objects(RDF.type)
                   if str(o).startswith(LHO) and str(o).endswith("Sample")})
    by_severity = Counter(short(report.value(r, SH.resultSeverity)) for r in results)
    by_message = Counter((short(report.value(r, SH.resultSeverity)), str(report.value(r, SH.resultMessage)))
                         for r in results)

    print(f"\n{Path(data_file).name}")
    print(f"  samples checked : {samples}")
    print(f"  samples with issues: {len(focus)}")
    print(f"  conforms (no violations): {conforms}")
    print(f"  violations: {by_severity.get('sh:Violation', 0)}, warnings: {by_severity.get('sh:Warning', 0)}")
    for (sev, msg), n in by_message.most_common():
        print(f"    {n:>5} x [{sev[3:]}] {msg}")
    print(f"  full report: {out.relative_to(HERE)}")


def main():
    files = sys.argv[1:] or sorted(str(p) for p in (HERE / "examples").glob("*.ttl"))
    shapes = Graph().parse(SHAPES)
    ontology = property_declarations(Graph().parse(ONTOLOGY))
    for f in files:
        check(f, shapes, ontology)


if __name__ == "__main__":
    main()

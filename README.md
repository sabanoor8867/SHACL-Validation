# SHACL validation of LHO-mapped laboratory data

This repository contains SHACL shapes that check whether laboratory data mapped to the [Livestock Health Ontology (LHO)](https://github.com/decide-project-eu/LivestockHealthOntology) are complete and consistent before they are combined, queried with SPARQL or shown in a dashboard.

I developed the LHO in the EU Horizon 2020 project [DECIDE](https://decideproject.eu/) to describe diagnostic data from veterinary laboratories in one shared model. The data come from different
laboratories and countries, and each laboratory exports its data in its own way. Mapping to the ontology gives the data a common meaning, but it does not guarantee that every record is complete or written in the same format. SHACL is used here for that second step.

The shapes cover four use cases:

| Use case                                         | LHO class             | Source of the RDF structure |
| ------------------------------------------------ | --------------------- | --------------------------- |
| Cattle, bovine respiratory disease (7 pathogens) | `LHO:CattleSample`  | Cattle Barometer            |
| Pigs, respiratory and enteric pathogens          | `LHO:PigSample`     | Pig Barometer               |
| Poultry, infectious bronchitis virus genotypes   | `LHO:PoultrySample` | Poultry Barometer           |
| Salmon, monthly mortality and biomass reports    | `LHO:SalmonSample`  | Scottish salmon use case    |

## How it works

```mermaid
flowchart LR
    A["Lab export<br/>(CSV, Excel, PDF)"] --> B["Python / RDFLib<br/>mapping to LHO"]
    B --> C["RDF data<br/>(Turtle)"]
    S["SHACL shapes<br/>shapes/lho-shapes.ttl"] --> V{"pySHACL<br/>validate.py"}
    O["LHO ontology v1.5<br/>(property declarations)"] --> V
    C --> V
    V -->|"no violations"| D["Use the data:<br/>SPARQL, dashboards,<br/>federated learning"]
    V -->|"violations or warnings"| R["Validation report<br/>reports/*_report.ttl"]
    R --> F["Fix the mapping<br/>or the source data"]
    F --> B
```

Each record (sample) in the data is a *focus node*. For every class there is a node shape, and each node shape has property shapes that say which properties a sample must have, how many values, and which values are allowed. pySHACL checks every sample against its shape and writes a report with one result per problem.

Results have two severity levels:

- **Violation**: the record cannot be used as it is (for example no test result, or a date that cannot be read).
- **Warning**: the record can be used, but a value needs attention (for example province "nan", left over from the conversion).

## The shapes

### Cattle sample shape

```mermaid
classDiagram
    class CattleSampleShape {
        targetClass LHO:CattleSample
        hasPathogen : exactly 1, one of BRSV BCV PI3 MH PM HS MB
        hasResult : exactly 1, LHO:0 or LHO:1
        hasDiagnosticTest : exactly 1, PCR Culture NPS
        hasSampleType : exactly 1, BAL Swab Autopsy TTA
        hasDate : exactly 1, pattern YYYY-MM-DD
        hasCountry : exactly 1, IRI
    }
```

### All shapes

| Shape                     | Target                | What it checks                                                                                                                                                 | Severity  |
| ------------------------- | --------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------- |
| `CattleSampleShape`     | `LHO:CattleSample`  | one of the seven BRD pathogens, one result (0/1), one diagnostic test, one sample type, one ISO date, one country                                              | Violation |
| `PigSampleShape`        | `LHO:PigSample`     | one pig pathogen, one result (0/1), one diagnostic test, at most one production stage, one ISO date, one country                                               | Violation |
|                           |                       | sample type is one of the LHO sample type classes                                                                                                              | Warning   |
| `PoultrySampleShape`    | `LHO:PoultrySample` | one IBV genotype from the Poultry Barometer list (or "other"), one result, one production stage, one sample type, date as YYYY-MM-DD or YYYY-Qn                | Violation |
| `SalmonSampleShape`     | `LHO:SalmonSample`  | one mortality value (`LHO:CS58`, hasMortality), one biomass value, water type Seawater or Freshwater, at most one local authority, one ISO date, one country | Violation |
| `PlaceholderValueShape` | cattle, pig, poultry  | province, breed and production stage are not "nan". "Missing" and "Unknown" are accepted, because they are explicit categories in the barometer data           | Warning   |
| `DeclaredPropertyShape` | all four              | every LHO property used in the data is declared in the ontology (SPARQL-based constraint)                                                                      | Warning   |

## Example: from data to report

The folder `examples/` has a few synthetic records per use case. They follow the same structure as
the DECIDE data. `ideal_example.ttl` has one complete record per use case and passes every check.
The other files contain problems on purpose. Real laboratory data are not included in this repository.

**1. The data.** `LHO:ExampleCattleSample_3` has a date written as day/month/year:

```turtle
LHO:ExampleCattleSample_3 a LHO:CattleSample ;
    LHO:hasPathogen LHO:PM ;
    LHO:hasResult LHO:0 ;
    LHO:hasDiagnosticTest LHO:NPS ;
    LHO:hasSampleType LHO:BAL ;
    LHO:hasDate <http://www.purl.org/decide/LiveStockHealthOnto/LHO#08/06/2022> ;
    LHO:hasCountry LHO:Belgium ;
    LHO:hasProvince LHO:nan ;
    LHO:hasBreed LHO:Unknown .
```

**2. The rule.** The cattle shape asks for one date in ISO format:

```turtle
sh:property [
    sh:path LHO:hasDate ; sh:minCount 1 ; sh:maxCount 1 ;
    sh:pattern "#[0-9]{4}-[0-9]{2}-[0-9]{2}$" ;
    sh:message "One date is required, written as an ISO date (YYYY-MM-DD), so that data from different labs can be combined." ] ;
```

**3. The result.** pySHACL reports the problem, the sample and the value:

```turtle
[] a sh:ValidationResult ;
    sh:focusNode LHO:ExampleCattleSample_3 ;
    sh:resultPath LHO:hasDate ;
    sh:value <http://www.purl.org/decide/LiveStockHealthOnto/LHO#08/06/2022> ;
    sh:resultSeverity sh:Violation ;
    sh:sourceConstraintComponent sh:PatternConstraintComponent ;
    sh:resultMessage "One date is required, written as an ISO date (YYYY-MM-DD), so that data from different labs can be combined." .
```

The same sample also gets a warning, because its province is "nan". Its breed "Unknown" is accepted.

### Results on the example files

| File                    | Samples | Problems planted                                                                        | Violations | Warnings |
| ----------------------- | ------- | --------------------------------------------------------------------------------------- | ---------- | -------- |
| `ideal_example.ttl`   | 4       | none (one complete record per use case)                                                 | 0          | 0        |
| `cattle_example.ttl`  | 5       | date format, missing result, pathogen outside the BRD list, two results, province "nan" | 4          | 1        |
| `pig_example.ttl`     | 4       | missing result, sample type outside the LHO classes, two production stages              | 2          | 1        |
| `poultry_example.ttl` | 4       | genotype "4/91" converted to "491", missing production stage, unreadable date           | 3          | 0        |
| `salmon_example.ttl`  | 4       | missing mortality, water type "sea", two local authorities, missing date                | 4          | 0        |

The ideal records pass with no violations and no warnings, and every planted problem is found.
The full output is in `reports/summary_examples.txt`, and the full SHACL reports are in `reports/`.

### What the validation showed about the ontology itself

The `DeclaredPropertyShape` checks that every LHO property used in the data is declared in the
ontology. Run against the earlier LHO version (v1.4), it warned on three properties used by the mapping scripts:
`LHO:hasResult`, `LHO:hasProductionStages` and `LHO:CS61`. I fixed this in LHO v1.5 (included in `ontology/`):

- `LHO:hasResult` is now declared, as a subproperty of `LHO:hasSampleResult`.
- `LHO:hasProductionStages` is now declared, with range `LHO:LivestockProductionStages`.
- the class name `LivestockProductionSatges` was corrected to `LivestockProductionStages`.
- `LHO:CS61` is a lab reference individual in the ontology, so salmon mortality is linked with the
  declared property `LHO:CS58` (hasMortality).

With v1.5 these warnings no longer appear. This is a good example of how SHACL helps to keep the
ontology and the data that use it in line.

## Current pipeline and how it can become an RML–SHACL pipeline

### Current pipeline in DECIDE

Laboratories deliver their diagnostic data as CSV, Excel or PDF files, each with its own columns,
codes and languages. For every laboratory, a Python (pandas, PySpark) or R notebook cleans the data,
anonymises farm and sample identifiers with SHA-256, and writes RDF with RDFLib, using the LHO
classes and properties. The RDF is then stored in a triplestore (Virtuoso) or in one Solid Pod per
laboratory, queried with SPARQL, and used for the barometer dashboards and for federated learning.

```mermaid
flowchart LR
    L1["Lab 1 export<br/>(CSV / Excel / PDF)"] --> P1["Python / R notebook<br/>lab 1"]
    L2["Lab 2 export"] --> P2["Python / R notebook<br/>lab 2"]
    L3["Lab n export"] --> P3["Python / R notebook<br/>lab n"]
    P1 --> R1["RDF (Turtle)<br/>mapped to LHO"]
    P2 --> R1
    P3 --> R1
    R1 --> S["Virtuoso or<br/>Solid Pods"]
    S --> Q["SPARQL"]
    Q --> D["Dashboards, federated<br/>data access and learning"]
```

In this pipeline the mapping rules are inside the code of each notebook, and there is no automatic
check of the RDF before it is published. Running the shapes in this repository on the existing lab
exports showed the kind of problems this causes: missing test results, dates in different formats,
placeholder values and properties that were not declared in the ontology.

### Towards an RML–SHACL pipeline

The same steps can be organised in three separate parts:

1. **Preparation** (Python): only the steps that need code, such as anonymisation and recoding lab
   specific values (for example "Pos" or "+++" to 1).
2. **Mapping** (RML): one mapping file per data layout describes which column becomes which LHO
   property. An RML engine such as Morph-KGC produces the RDF.
3. **Validation** (SHACL): the shapes in this repository check the RDF before it is loaded. Only data
   without violations are published; the validation report goes back to the person who prepared the
   data.

```mermaid
flowchart LR
    L["Lab exports<br/>(CSV / Excel)"] --> PR["Preparation<br/>(Python: anonymise,<br/>recode values)"]
    PR --> C["Clean CSV"]
    C --> M{"RML engine<br/>(Morph-KGC)"}
    Y["RML mapping<br/>(YARRRML, one per layout)"] --> M
    O["LHO ontology"] --> Y
    M --> R["RDF (Turtle)"]
    R --> V{"SHACL validation<br/>(pySHACL)"}
    SH["SHACL shapes"] --> V
    V -->|"no violations"| S["Virtuoso or Solid Pods"]
    V -->|"violations"| REP["Validation report"]
    REP --> PR
    S --> Q["SPARQL, dashboards,<br/>federated learning"]
```

| Step | Current pipeline | RML–SHACL pipeline |
|---|---|---|
| Mapping to LHO | written in Python or R code, one notebook per lab | written as RML rules in a mapping file; the same file is reused for labs with the same layout |
| Change in a column name or a new lab | edit and test the code | edit or add one mapping file |
| Checking the RDF | manual, after problems show up in queries or dashboards | automatic SHACL check before the data are loaded |
| Feedback to data providers | informal | a validation report per file, listing each record and problem |

Some steps stay in Python, because they are not mapping rules: anonymisation, recoding lab specific
values, and reading PDF files. RML can call functions (for example through the Function Ontology),
but keeping these steps in a small preparation script is simpler to maintain.

## How to run it

```bash
pip install -r requirements.txt

# validate the example files (ideal, cattle, pig, poultry, salmon)
python validate.py

# validate your own LHO-mapped RDF files
python validate.py path/to/your_data.ttl
```

On Windows PowerShell, put the path in quotes: `python validate.py "C:\Users\you\data\file.ttl"`.

For each file the script prints a summary (number of samples, violations and warnings, grouped by
message) and writes the full SHACL report to `reports/<file>_report.ttl`.

## Files

```
shapes/lho-shapes.ttl          SHACL shapes (node shapes, property shapes, one SPARQL constraint)
examples/ideal_example.ttl     one complete record per use case, passes all checks
examples/*_example.ttl         synthetic records for cattle, pig, poultry and salmon, with planted problems
ontology/LivestockHealthOntology_v1.5.rdf   LHO v1.5
validate.py                    runs pySHACL and summarises the report
reports/                       validation reports of the example files
```

## Related work

- Livestock Health Ontology: https://github.com/decide-project-eu/LivestockHealthOntology
- Noor, S., Bokma, J., Pardon, B., van Schaik, G., Hostens, M., 2024. Agri Semantics: developments to improve data interoperability to support farm information management and decision support systems in agriculture. Burleigh Dodds Science Publishing. https://doi.org/10.19103/AS.2023.0132.05
- Noor, S. et al., 2026. From data silos to actionable insights: a comparative evaluation of data access models and practical guidelines for animal health surveillance. Frontiers in Veterinary Science. https://doi.org/10.3389/fvets.2026.1962800

## License

The code (`validate.py`) is released under the MIT License (see `LICENSE`). The SHACL shapes and
example data are released under CC BY 4.0.

## Author

Saba Noor, Ghent University.



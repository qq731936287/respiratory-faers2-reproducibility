# Respiratory FAERS2 beautiful homepage

Run:

```bash
cd /path/to/respiratory-faers2-public-staging
streamlit run dashboard/app.py --server.port 8507
```

The homepage intentionally avoids a network graph. The main visual is the
current openFDA recovery map; provenance and lineage artefacts are kept as
small secondary links.

Map interactions:

- Click any recovery-map point to open a readable local openFDA detail page for
  the corresponding drug + MedDRA preferred-term pair.
- Click a highlighted drug label to open a readable local drug-level openFDA
  reaction profile.
- Hover over any recovery-map point or highlighted drug label to display the
  drug structure context: PubChem 3D conformer sketches for small molecules and
  biologic class glyphs for antibodies/fusion proteins.
- The homepage background includes a slow animated chemistry field: eight
  translucent small-molecule conformer slots rotate through the recovered drug
  set with varied scale, opacity, and drift timing.
- Biologics are excluded from the small-molecule background to avoid inaccurate
  structural display; local detail pages use the selected drug structure as a
  soft background watermark.
- Official API URLs are retained in audit/provenance files rather than exposed
  as default reader-facing links.

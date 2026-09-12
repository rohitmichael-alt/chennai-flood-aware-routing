# Preserved Evidence Sources

## `gcc_wards_2022.kml.gz`

- Dataset: OpenCity `GCC Ward Information`
- Resource: `Chennai GCC Ward Map - 2022`
- Resource ID: `e90176d4-319a-45bd-918e-ecce4f048c4d`
- Provider organization: Greater Chennai Corporation (GCC)
- Resource source: `https://chennaicorporation.gov.in`
- Resource licence field: `Public Domain`
- Uncompressed bytes: `2,815,875`
- Uncompressed SHA-256:
  `be48ef7eb4320279e790f59da1691ece9efc92b34459ca73c492957943c347e0`
- Retrieval and geometry-repair details:
  [`../STAGE3_BOUNDARY_RESULTS.json`](../STAGE3_BOUNDARY_RESULTS.json)

The gzip container is generated with a fixed timestamp. Decompression restores
the unchanged provider KML. The archive is committed because the provider URL
may later serve a revised file even though the resource identifier remains the
same.

## Geofabrik India `india-260901.osm.pbf`

The India-wide PBF is not committed (about 1.71 GB). Stage 3 records:

- URL: `https://download.geofabrik.de/asia/india-260901.osm.pbf`
- Provider MD5: `44ec6a7dff8ff2f3382da80a546b505f`
- Last-Modified: `Wed, 02 Sep 2026 05:19:21 GMT`
- Licence: ODbL 1.0
- Clipped PBF SHA-256:
  `00fced3d1e4a8c4b938f32d8b902141fc121cb910fcb8b070465d38b139b487b`

See [`../STAGE3_GRAPH_RESULTS.json`](../STAGE3_GRAPH_RESULTS.json).

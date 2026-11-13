# Leaflet 1.9.4 (vendored)

The search and restaurant maps use these files. They're copied unchanged
from the npm release tarball, so the site loads no third-party script.

- Source: https://registry.npmjs.org/leaflet/-/leaflet-1.9.4.tgz
- npm integrity: `sha512-nxS1ynzJOmOlHp+iL3FyWqK89GtNL8U8rvlMOsQdTTssxZwCXh8N2NB3GDQOL+YR3XnWyZAxwQixURb+FA74PA==`
- License: BSD-2-Clause (`LICENSE`)
- Copied: `package/dist/leaflet.js`, `package/dist/leaflet.css`, `package/LICENSE`

To check the files, run `sha256sum -c` on the block below from this folder.
`src/dsv-app/tests/test_vendor_leaflet.py` checks them too.

```
db49d009c841f5ca34a888c96511ae936fd9f5533e90d8b2c4d57596f4e5641a  leaflet.js
a7837102824184820dfa198d1ebcd109ff6d0ff9a2672a074b9a1b4d147d04c6  leaflet.css
53e8dc25862014e4324741ca18fbe3611e11d42ef69f59f86ea8c5389647d4cb  LICENSE
```

To upgrade, download the new tarball, check its npm integrity, copy the same
three files, and update this page and the test.

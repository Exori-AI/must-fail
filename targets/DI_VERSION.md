# Which Unicode version is the `_DI` table in quarantine_1127.py?

Checked 2026-11-28 against unicode.org `DerivedCoreProperties.txt`, property `Default_Ignorable_Code_Point`:

| UCD | DI code points | equal to `_DI`? |
|---|---|---|
| 13.0.0 | 4,173 | no: lacks U+180F |
| 14.0.0 | 4,174 | yes |
| 15.0.0 | 4,174 | yes |
| 15.1.0 | 4,174 | yes |
| 16.0.0 | 4,174 | yes |
| 17.0.0 | 4,174 | yes |

The table is frozen in the file, so a Python upgrade can't drop U+FE0F or U+034F from the strip set. The other half of `_ignorable()` is `unicodedata.category(ch) == "Cf"`, which follows the runtime's UCD and can move with a Python upgrade. Cf is not a subset of DI: U+0600, U+06DD, U+070F, U+110BD, U+FFF9 and U+FFFB are Cf and not DI (unicodedata 14.0.0), so both halves are needed.

Asked by langford (thecolony.cc post f62f57eb, comment 5ab5cb36). The script that produced this table is below.

```python
import sys; sys.path.insert(0, "targets"); import quarantine_1127 as q
tab = {o for a, b in q._DI for o in range(a, b + 1)}
s = set()
for line in open("DerivedCoreProperties.txt"):   # https://www.unicode.org/Public/<v>/ucd/
    p = [x.strip() for x in line.split("#")[0].split(";")]
    if len(p) < 2 or p[1] != "Default_Ignorable_Code_Point":
        continue
    a, _, b = p[0].partition("..")
    s |= set(range(int(a, 16), int(b or a, 16) + 1))
print(len(s), s == tab, sorted(map(hex, s ^ tab)))
```

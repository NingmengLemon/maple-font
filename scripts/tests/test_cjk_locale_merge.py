from __future__ import annotations

import tempfile
import unittest
import xml.etree.ElementTree as ElementTree
from pathlib import Path

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen

from font_module_dev.generate_configs import rewrite_config
from merge_cjk_locales import merge_chain
from scripts.font_ops.fonttools import TTFont


def write_test_font(path: Path, glyphs: dict[int, str]) -> None:
    glyph_order = [".notdef", *glyphs.values()]
    builder = FontBuilder(1000, isTTF=True)
    builder.setupGlyphOrder(glyph_order)
    builder.setupCharacterMap(glyphs)
    builder.setupGlyf(
        {glyph_name: TTGlyphPen(None).glyph() for glyph_name in glyph_order}
    )
    builder.setupHorizontalMetrics({glyph_name: (600, 0) for glyph_name in glyph_order})
    builder.setupHorizontalHeader(ascent=800, descent=-200)
    builder.setupNameTable(
        {
            "familyName": "Merge Test",
            "styleName": "Regular",
            "uniqueFontIdentifier": "Merge Test Regular",
            "fullName": "Merge Test Regular",
            "psName": "MergeTest-Regular",
        }
    )
    builder.setupOS2()
    builder.setupPost()
    builder.setupMaxp()
    builder.save(path)


class CJKLocaleMergeTest(unittest.TestCase):
    def test_merge_chain_preserves_priority_cmap_and_adds_missing_codepoints(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base_path = root / "base.ttf"
            jp_path = root / "jp.ttf"
            tc_path = root / "tc.ttf"
            output_path = root / "merged.ttf"

            write_test_font(base_path, {0x4E00: "cn_one", 0x4E01: "cn_two"})
            write_test_font(jp_path, {0x4E00: "jp_one", 0x4E02: "jp_three"})
            write_test_font(tc_path, {0x4E02: "tc_three", 0x4E03: "tc_four"})

            merge_chain(base_path, [jp_path, tc_path], output_path)

            merged = TTFont(output_path)
            try:
                cmap = merged.getBestCmap()
                self.assertIsNotNone(cmap)
                assert cmap is not None
                self.assertEqual(cmap[0x4E00], "cn_one")
                self.assertEqual(cmap[0x4E01], "cn_two")
                self.assertEqual(cmap[0x4E02], "jp_three")
                self.assertEqual(cmap[0x4E03], "tc_four")
            finally:
                merged.close()

            self.assertEqual(list(root.glob(".merge_tmp_*")), [])

    def test_config_retains_original_cjk_fallback_after_maple_faces(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.xml"
            output = root / "output.xml"
            source.write_text(
                """<?xml version=\"1.0\" encoding=\"utf-8\"?>
<familyset>
  <family name=\"sans-serif\"><font>Roboto-Regular.ttf</font></family>
  <family name=\"monospace\"><font>DroidSansMono.ttf</font></family>
  <family lang=\"zh-Hans\"><font index=\"2\">NotoSansCJK-Regular.ttc</font></family>
  <family lang=\"zh-Hant,zh-Bopo\"><font index=\"3\">NotoSansCJK-Regular.ttc</font></family>
  <family lang=\"ja\"><font index=\"0\">NotoSansCJK-Regular.ttc</font></family>
  <family lang=\"ko\"><font index=\"1\">NotoSansCJK-Regular.ttc</font></family>
</familyset>""",
                encoding="utf-8",
            )

            rewrite_config(source, output)

            generated = ElementTree.parse(output).getroot()
            hans_families = [
                family
                for family in generated.findall("family")
                if family.get("lang") == "zh-Hans"
            ]
            self.assertEqual(len(hans_families), 1)
            faces = hans_families[0].findall("font")
            self.assertEqual(faces[0].text, "MapleMono-NF-AllCJK-Thin.ttf")
            self.assertEqual(faces[-1].text, "MapleMono-NF-AllCJK-ExtraBold.ttf")
            self.assertIsNone(faces[-1].get("index"))


if __name__ == "__main__":
    unittest.main()

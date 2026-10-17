# Third-party notices

ROX Enchantment Overlay redistributes or depends on the following third-party components. They remain under their own licenses and are not relicensed under the project's MIT license.

| Component | Version | License | Project/source |
|---|---:|---|---|
| Python | 3.12.14 | PSF License | https://www.python.org/ |
| PySide6 / Qt for Python | 6.12.0 | LGPL-3.0-only, GPL-2.0-only or GPL-3.0-only; this distribution uses the LGPL-3.0 option | https://pyside.org/ |
| Qt runtime libraries | 6.12.0 | LGPL-3.0-only or applicable Qt license | https://www.qt.io/ |
| Shiboken6 | 6.12.0 | LGPL-3.0-only, GPL-2.0-only or GPL-3.0-only; this distribution uses the LGPL-3.0 option | https://pyside.org/ |
| NumPy | 2.5.4 | BSD-3-Clause and bundled component licenses | https://numpy.org/ |
| OpenCV / opencv-python-headless | 5.0.0.93 | Apache-2.0 for OpenCV; MIT for the Python packaging; bundled component licenses also apply | https://github.com/opencv/opencv-python |
| MSS | 10.2.0 | MIT | https://github.com/BoboTiG/python-mss |
| windows-capture | 1.5.0 | MIT | https://github.com/NiiightmareXD/windows-capture |
| PyInstaller bootloader | 6.22.3 | GPL-2.0-or-later with a special exception for distributing bundled applications | https://pyinstaller.org/ |
| Tesseract OCR | 4.0.0-beta.1 Windows x86 static build | Apache-2.0 | https://github.com/tesseract-ocr/tesseract |
| tessdata_fast Portuguese and English models | bundled | Apache-2.0 | https://github.com/tesseract-ocr/tessdata_fast |
| Inter font | bundled | SIL Open Font License 1.1 | https://github.com/rsms/inter |

The complete license texts shipped with the portable application are in its top-level `third_party/licenses` directory.

PySide6, Shiboken6 and Qt libraries remain separate dynamically loaded files inside the portable folder. Users may replace those compatible library files as permitted by the LGPL. Corresponding source code is available from the upstream project links above.

## Bundled Tesseract binary

The bundled executable identifies itself as Tesseract `4.0.0-beta.1`, build identifier `adaf57cc`, with Leptonica `1.75.3`. Its SHA-256 is `C0928EB1F453A4DF23432227F87BF7FE8530534EADABABCA471A31FF58CECA63`. It statically incorporates the following image libraries, reported by `tesseract.exe --version`:

| Embedded component | Version | License text included as |
|---|---:|---|
| Leptonica | 1.75.3 | `Leptonica-BSD.txt` |
| giflib | 5.1.4 | `giflib-COPYING.txt` |
| IJG libjpeg | 9b | `libjpeg-IJG-README.txt` |
| libpng | 1.6.34 | `libpng-LICENSE.txt` |
| libtiff | 4.0.9 | `libtiff-COPYRIGHT.txt` |
| zlib | 1.2.11 | `zlib-LICENSE.txt` |
| libwebp | 0.6.1 | `libwebp-COPYING.txt` |
| OpenJPEG / libopenjp2 | 2.3.0 | `OpenJPEG-LICENSE.txt` |

The corresponding upstream source is available from each component's public project. These libraries are used only through the standalone OCR executable.

## Game-related visual material

The images under `tests/fixtures` contain visual material from Ragnarok X and are included only to validate visual recognition. They are **not** covered by the project's MIT license. Ragnarok X names, artwork, interface elements and related rights remain with their respective owners.

`src/rox_overlay/assets/crystal-currency.png` is an original project asset created specifically for ROX Enchantment Overlay and is covered by the project's MIT license; it is not extracted from the game.

This project is independent and is not endorsed by or affiliated with Ragnarok X, Nuverse, Gravity, Qt, or the maintainers of the listed libraries.

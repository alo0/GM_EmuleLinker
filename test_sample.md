# Test sample page for EmuleLinker

## Summary

This is a page to test the GreaseMonkey EmuleLinker Script. It is composed of several ed2k links and for each link the description should match the results

## ED2K Links Table

| # | ED2K Links | Size | Description |
|---|------------|------|-------------|
| 1 | [example1.mp3](ed2k://\|file\|example1.mp3\|1048576\|ABCDEF1234567890\|/) | 1 MiB | Sample audio file |
| 2 | [example2.avi](ed2k://\|file\|example2.avi\|734003200\|123456ABCDEF7890\|/) | 700 MiB | Sample video file |
| 3 | [example3.txt](ed2k://\|file\|example8.txt\|12288\|FEDCBA1234567890\|/) | 12 KiB | Sample text file |
| 4 | [example4.iso](ed2k://\|file\|example9.iso\|1073741824\|1234567890ABCDEF\|/) | 1 GiB | Sample ISO image |
| 5 | [Documentary Planet Earth 4K.mp4](ed2k://\|file\|Documentary Planet Earth 4K.mp4\|4294967296\|1A2B3C4D5E6F7A8B9C0D1E2F3A4B5C6D\|h=YNCKHTQCWBTRHHQTGPWDQPGBIZJREOB5\|/) | 4 GB | Lien ed2k avec hash **AICH** (h=...) en plus du hash MD4 — doit être détecté et affiché normalement |
| 6 | [Été à Paris (Café).mp3](ed2k://\|file\|Été à Paris (Café).mp3\|8543210\|3F8E1D2C4B5A69786950413EAB7CD821\|/) | 8.1 MB | Caractères spéciaux **bruts** dans le href (accents, espaces, parenthèses) — doit afficher le nom tel quel |
| 7 | [Conférence Téléphonique (v2.0).mkv](ed2k://\|file\|Conf%C3%A9rence%20T%C3%A9l%C3%A9phonique%20%28v2.0%29.mkv\|1879048192\|9C8B7A6D5E4F32107856943A12BCDE01\|/) | 1.75 GB | Nom **encodé une fois** dans le href (URL encoding UTF-8) — doit décoder et afficher : Conférence Téléphonique (v2.0).mkv |
| 8 | [François & Marie \[Résumé\].docx](ed2k://\|file\|Fran%25C3%25A7ois%2520%2526%2520Marie%2520%255BR%25C3%25A9sum%25C3%25A9%255D.docx\|56789012\|AB12CD34EF56789012ABCDEF34567890\|/) | 54.1 MB | Nom **double-encodé** dans le href (% → %25) — doit décoder deux fois et afficher : François & Marie \[Résumé\].docx |
| 9 | [Ópera Española (Colección).flac](ed2k://%7Cfile%7C%C3%93pera%20Espa%C3%B1ola%20%28Colecci%C3%B3n%29.flac%7C287654321%7C5E6F7A8B9C0D1E2F3A4B5C6D7E8F9012%7C%2F) | 274.3 MB | `ed2k://` préservé mais **tout le reste encodé** (%7C, %2F...) — complémentaire du cas 13 : doit être détecté (commence par ed2k://) et décoder le nom correctement |
| 10 | [Bücher über Geräte (édition).pdf](ed2k%3A%2F%2F%7Cfile%7CB%C3%BCcher%20%C3%BCber%20Ger%C3%A4te%20%28%C3%A9dition%29.pdf%7C15728640%7CF0E1D2C3B4A5968778695047312ABCDE%7C%2F) | 15 MB | Lien ed2k **intégralement encodé** dans le href (ed2k:// → ed2k%3A%2F%2F) — Ne sera PAS détecté par le script (test de limitation) |

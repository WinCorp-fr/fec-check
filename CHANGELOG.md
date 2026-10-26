# Journal des versions

## 1.0.0 (25 octobre 2026)

Première version publique.

- Contrôles de format T1 à T11, comptables C1 à C10 et de forme ou de clôture ECF-1 à ECF-4.
- Lecture tolérante : tabulation ou pipe, UTF-8 ou ISO-8859-15, virgule ou point décimal, variantes d'en-tête des logiciels du marché.
- Ligne de commande `fec-check` (texte ou JSON), API Python `verifier_fec`, skill Claude.
- 176 tests, dont 106 sur le moteur et un garde-fou qui bloque toute donnée sensible, et 6 FEC entièrement fictifs.
